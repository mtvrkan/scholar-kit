#!/usr/bin/env python3
"""dataset_db.py — the dataset register. The ONLY sanctioned writer of analysis/datasets.jsonl.

WHY THIS EXISTS
The kit binds every claim from the literature to a source that was fetched from
an authoritative record, and every claim from the author's own analysis to an
evidence card. The data those analyses ran on had no such binding at all: a file
appeared under `analysis/`, and the sentence "we used the CWRU bearing dataset"
rested on nothing — no version, no licence, no citation, and no way to tell
afterwards whether the bytes that produced the numbers are the bytes still on
disk. That was the one link in the chain with nothing under it.

A record here answers four questions the methods section has to answer anyway:
  WHERE it came from (source, url, version, access date)
  WHETHER you may use it (licence — and whether that licence was actually read)
  HOW to cite it (DOI → `doi2bib.py`, the same authoritative path as any paper)
  WHAT exactly ran (per-file SHA-256, so `verify` can say the bytes are unchanged)

WHAT IT REFUSES
- To guess a licence. A dataset whose licence was not read is recorded
  `license: "unknown", license_verified: false`, never as permissive. "No licence
  found" and "free to use" are different findings and the register keeps them
  different — an unlicensed dataset is closer to all-rights-reserved than to
  public domain, and a tool that smooths that over is writing a legal opinion.
- To invent a row count. `n_rows` comes from `attach` measuring the file, or from
  a caller who states it; it is never inferred from a description.
- To decide whether the ethics of a collection are sound. It records what you
  declare (human subjects, PII state, IRB reference) and `--verify` reports what
  is missing. An ethics review is a human institution's judgement, not a field.

USAGE
  python scripts/dataset_db.py add --payload '{"name":"...","source":"uci",...}'
  python scripts/dataset_db.py attach DS-0001 analysis/data/train.csv [more...]
  python scripts/dataset_db.py verify [--id DS-0001]
  python scripts/dataset_db.py set-field DS-0001 license CC-BY-4.0
  python scripts/dataset_db.py list [--source huggingface] · stats

Exit codes: 0 ok · 1 error · 2 verification found a problem (drift, missing file,
or an undeclared licence on a dataset the paper depends on).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (die, emit, file_lock, next_id, parse_json_or_jsonl, read_jsonl,
                        read_stdin_text, require_within_cwd, write_jsonl)

SOURCES = {"huggingface", "kaggle", "openml", "uci", "zenodo", "figshare", "dataverse",
           "physionet", "trdizin", "tuik", "url", "own-scraped", "own-survey",
           "own-instrument", "other"}
PII_STATES = {"none", "removed", "pseudonymised", "present", "unknown"}
DEFAULT_FILE = "analysis/datasets.jsonl"
CHUNK = 1 << 20


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def count_rows(path: Path) -> int | None:
    """Data rows in a delimited text file, header excluded. None for anything
    else — a row count is a measurement, and there is no honest measurement of
    "rows" in a directory of images or a parquet blob this script cannot read."""
    if path.suffix.lower() not in (".csv", ".tsv", ".txt", ".jsonl"):
        return None
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            n = sum(1 for line in fh if line.strip())
    except OSError:
        return None
    if path.suffix.lower() == ".jsonl":
        return n
    return max(n - 1, 0)  # header


def _validate(rec: dict):
    if not rec.get("name"):
        die("dataset rejected: no 'name' — the register is read by a human first")
    source = rec.get("source")
    if source not in SOURCES:
        die(f"source {source!r} not in {sorted(SOURCES)} — 'other' is allowed and "
            f"honest; an unlisted invented value is not")
    pii = (rec.get("ethics") or {}).get("pii", "unknown")
    if pii not in PII_STATES:
        die(f"ethics.pii {pii!r} not in {sorted(PII_STATES)}")


def _normalise(rec: dict) -> dict:
    """Fill in only what is structural. Never a licence, never a count."""
    rec.setdefault("license", "unknown")
    # license_verified means "a human or an agent actually read the licence at
    # license_url", and nothing else sets it. Recording a licence string without
    # it is allowed — that is the common case of copying what a dataset page
    # claims — but the two are not the same claim and the register keeps them apart.
    rec.setdefault("license_verified", False)
    rec.setdefault("access_date", datetime.date.today().isoformat())
    rec.setdefault("files", [])
    ethics = rec.setdefault("ethics", {})
    ethics.setdefault("human_subjects", None)  # None = not declared, not "no"
    ethics.setdefault("pii", "unknown")
    ethics.setdefault("irb", "not-declared")
    return rec


def cmd_add(args, path):
    raw = read_stdin_text() if args.stdin else args.payload
    if not raw:
        die("add requires --stdin or --payload '<object>'")
    try:
        payloads = parse_json_or_jsonl(raw)
    except json.JSONDecodeError as e:
        die(f"input is not valid JSON/JSONL — {e.msg}")
    for rec in payloads:
        if not isinstance(rec, dict):
            die(f"record rejected: expected a JSON object, got {type(rec).__name__}")
        _validate(rec)
    added, dups = [], []
    with file_lock(path):
        records = read_jsonl(path)
        for rec in payloads:
            _normalise(rec)
            dup = _duplicate_of(rec, records)
            rec["id"] = next_id(records, "DS")
            if dup:
                rec["duplicate_of"] = dup
                dups.append(rec["id"])
            else:
                added.append(rec["id"])
            records.append(rec)
        write_jsonl(path, records)
    emit({"added": added, "duplicates": dups, "total": len(records)}, True)


def _duplicate_of(rec: dict, existing: list[dict]) -> str | None:
    """Same dataset AND same version. Version is half the identity: ImageNet-1k
    and ImageNet-21k are not the same data, and a register that collapsed them
    would make two papers' methods sections describe each other's experiment."""
    key = ((rec.get("url") or rec.get("source_id") or rec.get("name", "")).lower(),
           str(rec.get("version") or "").lower())
    for e in existing:
        if ((e.get("url") or e.get("source_id") or e.get("name", "")).lower(),
                str(e.get("version") or "").lower()) == key:
            return e.get("id")
    return None


def cmd_attach(args, path):
    measured = []
    for rel in args.files:
        require_within_cwd(rel, "files")
        p = Path(rel)
        if not p.is_file():
            die(f"{rel} does not exist — attach measures files, it does not describe them")
        measured.append({"path": p.as_posix(), "sha256": sha256_of(p),
                         "bytes": p.stat().st_size, "rows": count_rows(p)})
    with file_lock(path):
        records = read_jsonl(path)
        for r in records:
            if r.get("id") != args.rec_id:
                continue
            known = {f["path"]: f for f in r.get("files", [])}
            for f in measured:
                known[f["path"]] = f
            r["files"] = sorted(known.values(), key=lambda f: f["path"])
            rows = [f["rows"] for f in r["files"] if f.get("rows") is not None]
            if rows and not args.keep_rows:
                # Measured, not asserted: this is the number the methods section
                # should state, and it now has a file behind it.
                r["n_rows"] = sum(rows)
            write_jsonl(path, records)
            emit({"updated": args.rec_id, "files": len(r["files"]),
                  "n_rows": r.get("n_rows")}, True)
            return
    die(f"dataset {args.rec_id} not found in {path}")


def verify(records: list[dict], only: str | None = None) -> dict:
    """Do the bytes still match, and is the record complete enough to publish from?

    Two different findings, reported separately for the same reason
    `provenance.py` separates tampering from revision: a changed file is usually
    an ordinary re-export, while a missing one means the paper's numbers have no
    surviving input at all.
    """
    report, worst = [], "PASS"
    for rec in records:
        if only and rec.get("id") != only:
            continue
        problems, drift, missing = [], [], []
        for f in rec.get("files", []):
            p = Path(f["path"])
            if not p.is_file():
                missing.append(f["path"])
            elif sha256_of(p) != f["sha256"]:
                drift.append(f["path"])
        if not rec.get("files"):
            problems.append("no files attached — nothing binds this record to bytes on disk")
        if rec.get("license", "unknown") == "unknown":
            problems.append("licence not recorded — 'unknown' is not permission")
        elif not rec.get("license_verified"):
            problems.append(f"licence '{rec['license']}' recorded but not verified "
                            f"against the source's own licence page")
        if not (rec.get("citation") or {}).get("doi"):
            problems.append("no citation DOI — the dataset cannot enter the "
                            "bibliography through doi2bib.py")
        eth = rec.get("ethics", {})
        if eth.get("human_subjects") and eth.get("irb") in (None, "", "not-declared"):
            problems.append("human-subjects data with no IRB/ethics reference declared")
        if eth.get("pii") == "present":
            problems.append("PII present — declare removal/pseudonymisation before "
                            "the data leaves this machine")
        status = "PASS"
        if missing:
            status, worst = "MISSING", "FAIL"
        elif drift:
            status = "DRIFT"
            worst = "FAIL"
        elif problems:
            status = "INCOMPLETE"
            if worst == "PASS":
                worst = "INCOMPLETE"
        report.append({"id": rec.get("id"), "name": rec.get("name"), "status": status,
                       "drift": drift, "missing": missing, "problems": problems})
    return {"result": worst, "checked": len(report), "datasets": report,
            "note": ("bytes and paperwork are checked separately: DRIFT/MISSING is "
                     "about the data, INCOMPLETE is about what the methods section "
                     "will not be able to state")}


def cmd_verify(args, path):
    records = read_jsonl(path)
    if not records:
        die(f"{path} holds no datasets — nothing to verify")
    result = verify(records, args.id)
    if not result["checked"]:
        die(f"no dataset with id {args.id!r} in {path}")
    emit(result, True)
    sys.exit(0 if result["result"] == "PASS" else 2)


def cmd_set_field(args, path):
    if args.field in ("id", "files"):
        die("id is immutable; use attach for files (a checksum is measured, not typed)")
    try:
        value = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    with file_lock(path):
        records = read_jsonl(path)
        for r in records:
            if r.get("id") == args.rec_id:
                if args.field == "source" and value not in SOURCES:
                    die(f"source {value!r} not in {sorted(SOURCES)}")
                r[args.field] = value
                write_jsonl(path, records)
                emit({"updated": args.rec_id, "field": args.field}, True)
                return
    die(f"dataset {args.rec_id} not found in {path}")


def cmd_list(args, path):
    records = read_jsonl(path)
    if args.source:
        records = [r for r in records if r.get("source") == args.source]
    emit(records, True)


def cmd_stats(args, path):
    records = read_jsonl(path)
    by_source, by_license = {}, {}
    for r in records:
        by_source[r.get("source", "?")] = by_source.get(r.get("source", "?"), 0) + 1
        lic = r.get("license", "unknown")
        by_license[lic] = by_license.get(lic, 0) + 1
    emit({"total": len(records), "by_source": by_source, "by_license": by_license,
          "with_citation": sum(1 for r in records if (r.get("citation") or {}).get("doi")),
          "license_verified": sum(1 for r in records if r.get("license_verified"))}, True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", default=DEFAULT_FILE)
    ap.add_argument("--json", dest="json_out", action="store_true",
                    help="accepted for CLI consistency — output is always JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add")
    p_add.add_argument("--stdin", action="store_true")
    p_add.add_argument("--payload", "--json", dest="payload")
    p_at = sub.add_parser("attach")
    p_at.add_argument("rec_id")
    p_at.add_argument("files", nargs="+")
    p_at.add_argument("--keep-rows", action="store_true",
                      help="do not derive n_rows from the attached files")
    p_v = sub.add_parser("verify")
    p_v.add_argument("--id")
    p_sf = sub.add_parser("set-field")
    p_sf.add_argument("rec_id")
    p_sf.add_argument("field")
    p_sf.add_argument("value")
    p_l = sub.add_parser("list")
    p_l.add_argument("--source")
    sub.add_parser("stats")
    args = ap.parse_args()
    require_within_cwd(args.file, "--file")
    {"add": cmd_add, "attach": cmd_attach, "verify": cmd_verify,
     "set-field": cmd_set_field, "list": cmd_list, "stats": cmd_stats}[args.cmd](args, args.file)


if __name__ == "__main__":
    try:
        main()
    except TimeoutError as e:
        die(f"timed out waiting for another process to release the data-file lock — {e}")
    except OSError as e:
        die(f"failed to read or write a file — {e}")
