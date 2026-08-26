#!/usr/bin/env python3
"""evidence_db.py — add/query/stats/conflicts over evidence/cards.jsonl.

The ONLY sanctioned writer of cards.jsonl. Card schema (see evidence-cards skill):
  {"id":"EV-0042","source":"kaya2023deep","type":"finding|method|definition|statistic|
   quote|gap|own-result","claim":"...","detail":"...","page":"12-13","verbatim":false,
   "strength":1-5,"tags":[...],"metrics":{...},"conflicts_with":[...],"lang":"en|tr"}

Usage:
  python scripts/evidence_db.py add --payload '{"source":"kaya2023deep","type":"finding",...}'
  python scripts/evidence_db.py add --stdin            # one JSON object or JSONL stream
  python scripts/evidence_db.py query --tags rq1 --min-strength 3 [--type finding] [--source key]
  python scripts/evidence_db.py get EV-0042
  python scripts/evidence_db.py set-field EV-0042 page "5"    # qa-auditor fix path
  python scripts/evidence_db.py stats
  python scripts/evidence_db.py conflicts
All commands accept --file (default evidence/cards.jsonl) and --json.
`add` additionally cross-checks "source" against sources/registry.jsonl's
bib_key/id (--registry, default sources/registry.jsonl; skipped if that file
doesn't exist yet).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (die, emit, file_lock, next_id, parse_json_or_jsonl,
                        read_jsonl, read_stdin_text, require_within_cwd, write_jsonl)

VALID_TYPES = {"finding", "method", "definition", "statistic", "quote", "gap", "own-result"}
REQUIRED = ("source", "type", "claim")


def known_sources(registry_path: str | Path) -> set[str] | None:
    """Valid card "source" values — every bib_key (and id, as a fallback
    before a bib_key is assigned) currently in the registry. Returns None if
    the registry file doesn't exist, so validate() skips the cross-check
    gracefully rather than block card creation in setups without one yet
    (unit-testing evidence_db.py in isolation, or a project not following the
    default registry-first pipeline) — evidence-cards/SKILL.md documents this
    as an enforced invariant, but nothing previously checked it: a typo'd or
    fabricated source slipped through silently.

    Callers must not pass an explicitly-user-supplied --registry through here
    unchecked: a typo'd or wrong-cwd path would silently take this same
    "doesn't exist yet" branch and disable the cross-check entirely, exactly
    the Invariant-1 gap this function exists to close. cmd_add() below dies
    loudly on a named-but-absent --registry instead, and only calls this
    function with a path known to exist or with the untouched default."""
    p = Path(registry_path)
    if not p.exists():
        return None
    sources = set()
    for r in read_jsonl(p):
        if r.get("bib_key"):
            sources.add(r["bib_key"])
        if r.get("id"):
            sources.add(r["id"])
    return sources


def validate(card: dict, known: set[str] | None = None) -> list[str]:
    if not isinstance(card, dict):
        return [f"expected a JSON object, got {type(card).__name__}"]
    errs = [f"missing required field '{f}'" for f in REQUIRED if not card.get(f)]
    if card.get("type") and card["type"] not in VALID_TYPES:
        errs.append(f"type '{card['type']}' not in {sorted(VALID_TYPES)}")
    s = card.get("strength")
    if s is not None and (not isinstance(s, int) or isinstance(s, bool) or not 1 <= s <= 5):
        errs.append("strength must be an integer 1-5")
    if card.get("verbatim") and not card.get("page"):
        errs.append("verbatim:true requires a page reference (plagiarism discipline)")
    if known is not None and card.get("source") and card["source"] not in known:
        errs.append(f"source '{card['source']}' not found in {{bib_key, id}} of the registry "
                    f"(Invariant 1: never cite anything absent from sources/registry.jsonl)")
    return errs


def cmd_add(args, path):
    if args.stdin:
        # Codepage-independent UTF-8 (+ BOM tolerance) lives in
        # lib_common.read_stdin_text() — shared with registry_db.py, which had
        # the identical --stdin contract and none of the handling.
        raw = read_stdin_text()
        try:
            payloads = parse_json_or_jsonl(raw)
        except json.JSONDecodeError as e:
            die(f"stdin is not valid JSON/JSONL — {e.msg}")
    elif args.json_payload:
        try:
            payloads = [json.loads(args.json_payload)]
        except json.JSONDecodeError as e:
            die(f"--json payload invalid — {e.msg}")
    else:
        die("add requires --json '<object>' or --stdin")
    if args.registry and not Path(args.registry).exists():
        die(f"--registry {args.registry} does not exist — a typo'd or wrong-cwd path would "
            f"otherwise silently skip the Invariant 1 source cross-check")
    known = known_sources(args.registry or "sources/registry.jsonl")
    for card in payloads:
        errs = validate(card, known)
        if errs:
            die(f"card rejected: {'; '.join(errs)} — payload: {json.dumps(card, ensure_ascii=False)[:200]}")
    added = []
    # Locked: parallel source-analyst invocations (--fast) race on
    # read-all -> compute-next-id -> append without this (lost cards, dup IDs).
    # The batch is staged in `cards` and committed with ONE write_jsonl() call
    # (atomic temp-file + os.replace) instead of one append per card — a
    # crash/disk-full partway through a multi-card --stdin batch now leaves
    # the file exactly as it was before the call, never a partially-added batch.
    with file_lock(path):
        cards = read_jsonl(path)
        for card in payloads:
            card.setdefault("verbatim", False)
            card.setdefault("strength", 3)
            card.setdefault("tags", [])
            card.setdefault("lang", "en")
            card["id"] = next_id(cards, "EV")
            cards.append(card)
            added.append(card["id"])
        write_jsonl(path, cards)
        total = len(cards)
    emit({"added": added, "total": total}, args.json_out)


def cmd_query(args, path):
    cards = read_jsonl(path)
    out = []
    want_tags = set(args.tags.split(",")) if args.tags else set()
    for c in cards:
        if want_tags and not want_tags & set(c.get("tags", [])):
            continue
        if args.min_strength and c.get("strength", 0) < args.min_strength:
            continue
        if args.type and c.get("type") != args.type:
            continue
        if args.source and c.get("source") != args.source:
            continue
        out.append(c)
    emit(out, True)


def cmd_get(args, path):
    for c in read_jsonl(path):
        if c.get("id") == args.card_id:
            emit(c, True)
            return
    die(f"card {args.card_id} not found in {path}")


def cmd_stats(args, path):
    cards = read_jsonl(path)
    by_type, by_source, by_tag = {}, {}, {}
    for c in cards:
        by_type[c.get("type", "?")] = by_type.get(c.get("type", "?"), 0) + 1
        by_source[c.get("source", "?")] = by_source.get(c.get("source", "?"), 0) + 1
        for t in c.get("tags", []):
            by_tag[t] = by_tag.get(t, 0) + 1
    emit({"total": len(cards), "by_type": by_type, "by_source": by_source,
          "by_tag": by_tag,
          "avg_strength": round(sum(c.get("strength", 0) for c in cards) / len(cards), 2) if cards else 0},
         args.json_out)


def cmd_set_field(args, path):
    """Targeted correction path (e.g., qa-auditor found a wrong page attribution).
    id/source/type stay immutable — a wrong claim means a new card, not an edit."""
    if args.field in ("id", "source", "type"):
        die(f"'{args.field}' is immutable — delete-and-recreate semantics are deliberate")
    with file_lock(path):
        cards = read_jsonl(path)
        for c in cards:
            if c.get("id") == args.card_id:
                try:
                    c[args.field] = json.loads(args.value)
                except json.JSONDecodeError:
                    c[args.field] = args.value
                errs = validate(c)
                if errs:
                    die(f"edit rejected: {'; '.join(errs)}")
                write_jsonl(path, cards)
                emit({"updated": args.card_id, "field": args.field}, True)
                return
    die(f"card {args.card_id} not found in {path}")


def cmd_conflicts(args, path):
    # Skip a card missing 'id' entirely rather than raising KeyError or
    # colliding multiple id-less cards under the same None key — cards.jsonl
    # is script-owned and cmd_add always sets 'id', but a hand-edited/corrupt
    # file shouldn't crash a read-only inspection command.
    cards = {c["id"]: c for c in read_jsonl(path) if c.get("id")}
    pairs = []
    for c in cards.values():
        conflicts_with = c.get("conflicts_with", [])
        # A hand-edited/corrupt card can carry conflicts_with as a bare string
        # (e.g. "EV-0001") instead of a list — `for other in "EV-0001"` silently
        # iterates CHARACTER BY CHARACTER, producing a run of bogus single-char
        # "conflict" pairs instead of the one real conflict (or a clean skip).
        if not isinstance(conflicts_with, list):
            continue
        for other in conflicts_with:
            if other in cards and [other, c["id"]] not in [p["pair"] for p in pairs]:
                pairs.append({"pair": [c["id"], other],
                              "claims": [c.get("claim"), cards[other].get("claim")]})
            elif other not in cards:
                pairs.append({"pair": [c["id"], other], "warning": f"{other} does not exist"})
    emit(pairs, True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", default="evidence/cards.jsonl")
    ap.add_argument("--registry", default=None,
                    help="add cross-checks card 'source' against this registry's bib_key/id "
                         "(default sources/registry.jsonl)")
    ap.add_argument("--json", dest="json_out", action="store_true", help="JSON output (default for query/get)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add")
    # "--payload" is the primary name: the top-level --json above (output-mode
    # toggle, action="store_true") and this add-only --json (a value: the
    # record itself) are unrelated flags that happen to share literal text,
    # differing only by which side of the "add" sub-command they're placed
    # on — a real footgun, not just a naming quirk (getting the position
    # wrong silently reroutes the JSON payload text into the wrong argparse
    # slot). "--json" is kept as an alias, same dest, for anyone already
    # using the form documented in this file's own usage block above.
    p_add.add_argument("--payload", "--json", dest="json_payload")
    p_add.add_argument("--stdin", action="store_true")
    p_q = sub.add_parser("query")
    p_q.add_argument("--tags"); p_q.add_argument("--min-strength", type=int, dest="min_strength")
    p_q.add_argument("--type"); p_q.add_argument("--source")
    p_get = sub.add_parser("get"); p_get.add_argument("card_id")
    p_sf = sub.add_parser("set-field")
    p_sf.add_argument("card_id"); p_sf.add_argument("field"); p_sf.add_argument("value")
    sub.add_parser("stats")
    sub.add_parser("conflicts")
    args = ap.parse_args()
    args.json_out = getattr(args, "json_out", False)
    require_within_cwd(args.file, "--file")
    if args.registry:
        require_within_cwd(args.registry, "--registry")
    {"add": cmd_add, "query": cmd_query, "get": cmd_get, "set-field": cmd_set_field,
     "stats": cmd_stats, "conflicts": cmd_conflicts}[args.cmd](args, args.file)


if __name__ == "__main__":
    try:
        main()
    except TimeoutError as e:
        die(f"timed out waiting for another process to release the data-file lock — {e}")
    except OSError as e:
        die(f"failed to write the data file — {e}")
