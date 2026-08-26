#!/usr/bin/env python3
"""provenance.py — an append-only, hash-chained record of what was attested, when.

WHAT THIS IS FOR
Three things gate in this kit (outline approval, verify=PASS, Major=0) and all
three are FILE-BASED: the gate reads a file, and the same session that must pass
the gate can write that file. `phase_gate.py` says so in its own docstrings, and
closes the careless versions — a PASS inconsistent with its own counts, an
approval left stale after the outline changed underneath it,
`write_verify_status.py`'s live re-check of the bibliography. What none of that
reaches is the shape of the problem: an attestation nobody can distinguish,
afterwards, from one that was earned.

That gap cannot be closed by making the gate stricter. A gate is a decision made
at one moment by a process that has write access to its own evidence. What CAN
be closed is the second question, the one a supervisor, a co-author or a journal
actually asks: **is this record of what happened internally consistent, and does
it still describe the files on disk?**

So every attestation appends a record carrying the SHA-256 of the artifact it
attests and the hash of the record before it. Rewriting any earlier record — a
timestamp, a digest, a whole event — breaks every hash after it, and `--verify`
says exactly where. Editing an attested artifact after the fact leaves the chain
intact and the digest no longer matching, which `--verify` reports separately,
because those are different failures and collapsing them would be the
"missing data reported, never zeroed" rule broken in a new place.

WHAT THIS IS NOT
Not tamper-PROOF, and the difference is the whole honest content of this file.
A hash chain with no secret proves only that the sequence was not rewritten. It
cannot prove a record was earned, because nothing here is signed: an orchestrator
that never showed the outline to anyone can still run this script and append a
perfectly valid `outline-approved` record right now. There is no key it could not
read, since it runs with the same filesystem access this script does — and a key
committed next to the ledger it protects is decoration, not cryptography.

What changes is that the forgery becomes a RECORD instead of an absence. An
invisible bypass becomes a dated, hashed, ordered line that a reader can hold
against the rest of the chain, the file digests and the artifacts themselves. The
kit's whole posture is that a gap must refuse to be invisible (see
`enforcement_notice.py`, `_degrade.py`); this applies it to the one place where
prevention is architecturally out of reach.

Also not a security boundary, for the same reason SECURITY.md says the hooks are
not one, and not a claim about the RESEARCH: a chain over fabricated data is an
intact chain over fabricated data. POSITIONING.md's honest-failure-shape section
governs here unchanged.

USAGE
  python scripts/provenance.py --record outline-approved --path outline/outline.md
  python scripts/provenance.py --verify [--strict]
  python scripts/provenance.py --attests outline/outline.md

Canonical events (any `[a-z][a-z0-9-]{2,39}` slug is accepted; these are the ones
the kit itself writes and reads):
  outline-approved · verify-status · review-round · build · template-ingested

Exit codes: 0 ok · 1 error · 2 --verify --strict found a broken chain or drift.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import append_jsonl, die, emit, file_lock, read_jsonl, require_within_cwd

LEDGER = "provenance.jsonl"
GENESIS = "0" * 64
EVENT_RE = re.compile(r"^[a-z][a-z0-9-]{2,39}$")
# The fields that go into a record's own hash, in this order. `hash` itself is
# excluded (it is the output) and so is anything added later: a field appended
# to the record but not to this tuple would be silently unprotected, so the
# tuple is the contract and test_provenance.py pins it.
HASHED_FIELDS = ("seq", "ts", "event", "path", "sha256", "prev", "note")


def digest_file(path: Path) -> str:
    """SHA-256 of a file's BYTES, not its parsed content.

    Bytes on purpose: an attestation that survived a re-encode or a line-ending
    change would be attesting something other than the file the next reader
    opens. On this kit's two platforms that is a real difference, not a
    theoretical one.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def record_hash(record: dict) -> str:
    """Hash over the canonical serialisation of HASHED_FIELDS.

    `sort_keys` plus a fixed separator set, so a record hashed on Windows and
    re-verified on Linux — or by a future version of this file that happens to
    build the dict in a different order — produces the same digest. A chain
    whose validity depends on dict insertion order is a chain that breaks on
    somebody else's machine and reports it as tampering.
    """
    payload = {k: record.get(k) for k in HASHED_FIELDS}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")


def add_record(ledger_path: str, event: str, target: str, note: str | None) -> dict:
    if not EVENT_RE.match(event):
        die(f"--record must be a slug matching {EVENT_RE.pattern}, got {event!r}")
    target_path = Path(target)
    if not target_path.is_file():
        # Refused rather than recorded with a null digest: a record that attests
        # nothing is worse than no record, because it still reads as one.
        die(f"--path {target} does not exist — nothing to attest")
    with file_lock(ledger_path):
        records = read_jsonl(ledger_path) if Path(ledger_path).exists() else []
        prev = records[-1].get("hash") if records else GENESIS
        record = {
            "seq": len(records) + 1,
            "ts": _now(),
            "event": event,
            "path": target_path.as_posix(),
            "sha256": digest_file(target_path),
            "prev": prev,
            "note": note or "",
        }
        record["hash"] = record_hash(record)
        append_jsonl(ledger_path, record)
    return record


def verify(ledger_path: str) -> dict:
    """Chain integrity and artifact drift, reported as two separate findings.

    A record whose own hash does not recompute, or whose `prev` does not name
    the record before it, is a BROKEN CHAIN: the history was rewritten. An
    intact record whose attested file no longer digests to the recorded value is
    DRIFT: the history is honest and the artifact moved on. Only the first is
    tampering; the second is the ordinary, expected consequence of revising a
    draft, and reporting them as one number would make the common case look like
    the alarming one.
    """
    if not Path(ledger_path).exists():
        # "No ledger" is not "no problems" — see CONTRIBUTING.md's
        # missing-data-is-reported rule. Callers distinguish on `status`.
        return {"status": "absent", "ledger": ledger_path, "records": 0,
                "chain": "unknown", "broken_at": None, "drift": [], "missing": [],
                "note": "no provenance ledger in this project — nothing has been "
                        "attested, which is different from everything checking out"}
    records = read_jsonl(ledger_path)
    broken_at = None
    prev = GENESIS
    for index, rec in enumerate(records):
        expected_seq = index + 1
        if rec.get("seq") != expected_seq or rec.get("prev") != prev \
                or rec.get("hash") != record_hash(rec):
            broken_at = expected_seq
            break
        prev = rec["hash"]

    drift, missing = [], []
    # Only records in the intact prefix are worth checking against disk: past a
    # break, the recorded digest is not evidence of anything.
    intact = records[: (broken_at - 1) if broken_at else len(records)]
    for rec in intact:
        p = Path(rec.get("path", ""))
        if not p.is_file():
            missing.append({"seq": rec.get("seq"), "event": rec.get("event"),
                            "path": rec.get("path")})
        elif digest_file(p) != rec.get("sha256"):
            drift.append({"seq": rec.get("seq"), "event": rec.get("event"),
                          "path": rec.get("path"), "ts": rec.get("ts")})
    return {
        "status": "ok" if broken_at is None else "broken",
        "ledger": ledger_path,
        "records": len(records),
        "chain": "intact" if broken_at is None else "broken",
        "broken_at": broken_at,
        "drift": drift,
        "missing": missing,
        "note": ("the chain proves this record was not rewritten; it does not "
                 "prove any record was earned — provenance.py has no key and "
                 "signs nothing"),
    }


def attests(ledger_path: str, target: str) -> dict:
    """The LATEST record for `target`, and whether it still matches disk.

    Latest, not first: an artifact legitimately gets re-attested (an outline
    revised and re-approved), and the question a gate asks is always about the
    current state, never the original one.
    """
    result = {"path": Path(target).as_posix(), "attested": False,
              "matches_current": False, "seq": None, "event": None, "ts": None}
    if not Path(ledger_path).exists():
        return result
    wanted = Path(target).as_posix()
    for rec in reversed(read_jsonl(ledger_path)):
        if rec.get("path") == wanted:
            result.update(attested=True, seq=rec.get("seq"),
                          event=rec.get("event"), ts=rec.get("ts"))
            p = Path(target)
            result["matches_current"] = p.is_file() and digest_file(p) == rec.get("sha256")
            return result
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", metavar="EVENT",
                    help="append an attestation for --path (slug: outline-approved, "
                         "verify-status, review-round, build, template-ingested)")
    ap.add_argument("--path", help="the artifact --record attests")
    ap.add_argument("--note", default="", help="free-text context stored in the record")
    ap.add_argument("--verify", action="store_true",
                    help="check chain integrity and whether attested files still match")
    ap.add_argument("--attests", metavar="PATH",
                    help="report the latest attestation for PATH")
    ap.add_argument("--strict", action="store_true",
                    help="with --verify: exit 2 on a broken chain or on drift")
    ap.add_argument("--file", default=LEDGER, help=f"ledger path (default {LEDGER})")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.file, "--file")

    if args.record:
        if not args.path:
            die("--record requires --path")
        require_within_cwd(args.path, "--path")
        emit({"recorded": add_record(args.file, args.record, args.path, args.note)},
             args.json_out)
        return
    if args.attests:
        require_within_cwd(args.attests, "--attests")
        emit(attests(args.file, args.attests), args.json_out)
        return
    if args.verify:
        result = verify(args.file)
        emit(result, args.json_out)
        # WARN-only unless asked otherwise (CONTRIBUTING.md: a new check exits 0
        # even when it finds something, and offers --strict for callers that
        # want it to gate). `absent` never exits 2: a project that has attested
        # nothing has not failed a check, it has not run one.
        if args.strict and (result["chain"] == "broken" or result["drift"]
                            or result["missing"]):
            sys.exit(2)
        return
    ap.error("one of --record, --verify or --attests is required")


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"provenance ledger I/O failed — {e}")
