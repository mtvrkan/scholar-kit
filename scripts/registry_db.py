#!/usr/bin/env python3
"""registry_db.py — add/update/list over sources/registry.jsonl (the source register).

The ONLY sanctioned writer of registry.jsonl (Invariant 6). Record schema:
  {"id":"SRC-0007","title":"...","authors":["..."],"year":2023,"venue":"...",
   "doi":"10.x/y","lang":"en|tr","relevance_score":0.87,"one_line_why":"...",
   "venue_meta":{...},"status":"candidate|screened|included|excluded|duplicate",
   "reason":"...","stage":"screening|fulltext","bib_key":"kaya2023deep","pdf":"sources/pdf/x.pdf"}

Usage:
  python scripts/registry_db.py add --stdin                 # JSON object or JSONL stream
  python scripts/registry_db.py add --payload '{"title":"...","authors":[...],...}'
  python scripts/registry_db.py set-status SRC-0007 included [--reason "..."] [--stage fulltext]
  python scripts/registry_db.py set-field SRC-0007 bib_key kaya2023deep
  python scripts/registry_db.py list [--status candidate] [--lang tr] [--db scopus]
  python scripts/registry_db.py stats
  python scripts/registry_db.py log-query --db scopus --query "..." --hits 78 [--note "..."]
      appends to sources/search-log.jsonl (SLR reproducibility; exported to the
      Excel `queries` sheet). Records may carry a "db" field naming their source
      database (scopus|wos|ieee|wiley|pubmed|scholar|trdizin|dergipark|yoktez|mcp).
All commands accept --file (default sources/registry.jsonl).
Dedup on add: same DOI (case-insensitive) or ≥95% normalized-title similarity → status:duplicate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (append_jsonl, clean_doi, die, emit, file_lock, next_id, normalize_title,
                        parse_json_or_jsonl, read_jsonl, read_stdin_text, require_within_cwd,
                        warn_missing_rapidfuzz, write_jsonl)

STATUSES = {"candidate", "screened", "included", "excluded", "duplicate",
            "unretrieved"}
# "unretrieved" = sought for retrieval, never obtained (paywall, access-restricted
# thesis, dead link). PRISMA 2020 gives it its own box precisely because folding it
# into "excluded" claims an eligibility judgement that was never made, and leaving it
# in "candidate" lets prisma_flow.py count it as assessed at full text.


def is_duplicate(rec: dict, existing: list[dict]) -> str | None:
    # clean_doi() strips the https://doi.org/ prefix and lowercases — without
    # it, the same paper registered once with a bare DOI and once with a
    # doi.org URL (plausible: different literature-scout search sources
    # return DOIs in different shapes) isn't recognized as a duplicate here,
    # even though every other DOI comparison in this codebase goes through
    # clean_doi() first (doi2bib.py, bib_doctor.py).
    doi = clean_doi(rec.get("doi") or "").lower()
    if doi:
        for e in existing:
            if clean_doi(e.get("doi") or "").lower() == doi:
                return e.get("id")
    title = normalize_title(rec.get("title", ""))
    if title:
        try:
            from rapidfuzz import fuzz
            for e in existing:
                if fuzz.token_sort_ratio(title, normalize_title(e.get("title", ""))) >= 95:
                    return e.get("id")
        except ImportError:  # pragma: no cover
            warn_missing_rapidfuzz()
            for e in existing:
                if normalize_title(e.get("title", "")) == title:
                    return e.get("id")
    return None


def cmd_add(args, path):
    # read_stdin_text(), not sys.stdin.read(): the latter decodes with the
    # locale codepage, so on Turkish Windows every source title reaching the
    # register through `literature-scout` (which holds no Write tool and must
    # use this CLI) was written mojibake'd into the file the whole citation
    # chain is rooted in. evidence_db.py fixed this for cards.jsonl; the
    # sibling ingest path kept the bug. See lib_common.read_stdin_text.
    raw = read_stdin_text() if args.stdin else args.json_payload
    if not raw:
        die("add requires --stdin or --json '<object>'")
    try:
        payloads = parse_json_or_jsonl(raw)
    except json.JSONDecodeError as e:
        die(f"input is not valid JSON/JSONL — {e.msg}")
    for rec in payloads:
        if not isinstance(rec, dict):
            die(f"record rejected: expected a JSON object, got {type(rec).__name__} — "
                f"{json.dumps(rec, ensure_ascii=False)[:150]}")
        if not rec.get("title"):
            die(f"record rejected: missing 'title' — {json.dumps(rec, ensure_ascii=False)[:150]}")
    added, dups = [], []
    # Locked: parallel scouts/analysts racing on read-all -> next-id -> append
    # would otherwise lose records and mint duplicate SRC-#### IDs. The whole
    # batch is staged in `records` and committed with ONE write_jsonl() call
    # (atomic temp-file + os.replace) rather than one append per record — a
    # crash/disk-full partway through a multi-record --stdin batch now leaves
    # the file exactly as it was before the call, never a partially-added
    # batch with only some records persisted.
    with file_lock(path):
        records = read_jsonl(path)
        for rec in payloads:
            dup_of = is_duplicate(rec, records)
            rec["id"] = next_id(records, "SRC")
            rec.setdefault("status", "candidate")
            rec.setdefault("lang", "en")
            if dup_of:
                rec["status"] = "duplicate"
                rec["duplicate_of"] = dup_of
                dups.append(rec["id"])
            else:
                added.append(rec["id"])
            records.append(rec)
        write_jsonl(path, records)
        total = len(records)
    emit({"added": added, "duplicates": dups, "total": total}, True)


def cmd_set_status(args, path):
    if args.status not in STATUSES:
        die(f"status '{args.status}' not in {sorted(STATUSES)}")
    with file_lock(path):
        records = read_jsonl(path)
        for r in records:
            if r.get("id") == args.rec_id:
                r["status"] = args.status
                if args.reason:
                    r["reason"] = args.reason
                if args.stage:
                    r["stage"] = args.stage
                write_jsonl(path, records)
                emit({"updated": args.rec_id, "status": args.status}, True)
                return
    die(f"record {args.rec_id} not found in {path}")


def _validate_field(field: str, value, records: list[dict], target: dict):
    """Light per-field validation so set-field can't silently persist garbage
    (the two fields with a checkable invariant): a non-year 'year' and a
    duplicate 'bib_key'. Other free-text fields (reason, db, pdf, ...) are
    left unconstrained on purpose."""
    if field == "year":
        if isinstance(value, bool) or not isinstance(value, int) or not (1000 <= value <= 2100):
            die(f"year must be an integer between 1000 and 2100, got {value!r}")
    elif field == "bib_key":
        if not isinstance(value, str) or not value.strip():
            die(f"bib_key must be a non-empty string, got {value!r}")
        dup = [r.get("id") for r in records if r is not target and r.get("bib_key") == value]
        if dup:
            die(f"bib_key '{value}' already used by {dup[0]} — bib keys must be unique "
                f"(pandoc [@key] would resolve ambiguously)")


def cmd_set_field(args, path):
    if args.field in ("id", "status"):
        die("use set-status for status; id is immutable")
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    with file_lock(path):
        records = read_jsonl(path)
        for r in records:
            if r.get("id") == args.rec_id:
                _validate_field(args.field, value, records, r)
                r[args.field] = value
                write_jsonl(path, records)
                emit({"updated": args.rec_id, "field": args.field}, True)
                return
    die(f"record {args.rec_id} not found in {path}")


def cmd_list(args, path):
    records = read_jsonl(path)
    if args.status:
        records = [r for r in records if r.get("status") == args.status]
    if args.lang:
        records = [r for r in records if r.get("lang") == args.lang]
    if args.db:
        records = [r for r in records if r.get("db") == args.db]
    emit(records, True)


def cmd_log_query(args, path):
    import datetime
    if args.hits < 0:
        die(f"--hits must be non-negative, got {args.hits} — a search can't return "
            f"a negative number of results")
    log_path = Path(args.log_file)
    rec = {"db": args.db, "query": args.query, "hits": args.hits,
           "date": datetime.date.today().isoformat()}
    if args.note:
        rec["note"] = args.note
    with file_lock(log_path):
        append_jsonl(log_path, rec)
    emit({"logged": rec, "file": log_path.as_posix()}, True)


def cmd_stats(args, path):
    records = read_jsonl(path)
    by_status, by_lang = {}, {}
    for r in records:
        by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
        by_lang[r.get("lang", "?")] = by_lang.get(r.get("lang", "?"), 0) + 1
    emit({"total": len(records), "by_status": by_status, "by_lang": by_lang}, True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", default="sources/registry.jsonl")
    ap.add_argument("--json", dest="json_out", action="store_true",
                     help="accepted for CLI consistency — output is always JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add"); p_add.add_argument("--stdin", action="store_true")
    # "--payload" is the primary name: the top-level --json above (output-mode
    # toggle, action="store_true") and this add-only --json (a value: the
    # record itself) are unrelated flags that happen to share literal text,
    # differing only by which side of "add" they're placed on — a real
    # footgun, not just a naming quirk. "--json" is kept as an alias, same
    # dest, for anyone already using the form this file used to document.
    p_add.add_argument("--payload", "--json", dest="json_payload")
    p_st = sub.add_parser("set-status"); p_st.add_argument("rec_id"); p_st.add_argument("status")
    p_st.add_argument("--reason"); p_st.add_argument("--stage")
    p_sf = sub.add_parser("set-field"); p_sf.add_argument("rec_id"); p_sf.add_argument("field"); p_sf.add_argument("value")
    p_l = sub.add_parser("list"); p_l.add_argument("--status"); p_l.add_argument("--lang"); p_l.add_argument("--db")
    sub.add_parser("stats")
    p_q = sub.add_parser("log-query")
    p_q.add_argument("--db", required=True); p_q.add_argument("--query", required=True)
    p_q.add_argument("--hits", type=int, required=True); p_q.add_argument("--note")
    p_q.add_argument("--log-file", default="sources/search-log.jsonl",
                     help="fixed default (not derived from --file's parent) so it always "
                          "matches xlsx_export.py's --search-log default")
    args = ap.parse_args()
    require_within_cwd(args.file, "--file")
    if args.cmd == "log-query":
        require_within_cwd(args.log_file, "--log-file")
    {"add": cmd_add, "set-status": cmd_set_status, "set-field": cmd_set_field,
     "list": cmd_list, "stats": cmd_stats, "log-query": cmd_log_query}[args.cmd](args, args.file)


if __name__ == "__main__":
    try:
        main()
    except TimeoutError as e:
        die(f"timed out waiting for another process to release the data-file lock — {e}")
    except OSError as e:
        die(f"failed to write the data file — {e}")
