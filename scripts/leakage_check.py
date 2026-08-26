#!/usr/bin/env python3
"""leakage_check.py — the four leaks that are checkable, checked.

WHY THIS EXISTS
A leak does not look like an error. It looks like a good result: the metric goes
up, nothing crashes, and the paper reports a model that will never reproduce.
Every other validity question in this kit is either a design conversation
(methodology-advisor) or a human's judgement; these four are arithmetic, and
arithmetic belongs in a script rather than in a checklist someone reads once.

  1. **Index overlap** — the same row in train and test. The classic, and still
     the most common: a shuffle applied after the split, an off-by-one slice, a
     re-index that silently reordered.
  2. **Group leakage** — different rows, same subject/patient/session/device on
     both sides. The model memorises the individual, not the phenomenon, and no
     row-level check can see it.
  3. **Duplicate records across splits** — byte-identical feature rows in both
     splits under different ids. Common in scraped and augmented data, invisible
     to an index check.
  4. **A feature that determines the target** — a column that maps one-to-one onto
     the label (an id assigned after diagnosis, a "treatment_outcome" left in the
     matrix). Deterministic to detect, and it is the leak that survives every
     splitting discipline because it is inside the data.

WHAT IT CANNOT SEE — read this before quoting a PASS
- **Preprocessing fitted outside the fold** (a scaler, an imputer, a feature
  selector, SMOTE applied before splitting) is the second most common leak in
  applied ML and it leaves no trace in the split itself. This script reports what
  your manifest *declares* about it and nothing more. A declaration is not a check
  — but an undeclared one is at least visible, which is the difference between a
  known gap and a silent one.
- **Temporal leakage** beyond ordering it cannot know: if a split is chronological,
  whether the cut is at the right moment is a domain question.
- A PASS means these four are clean. It does not mean the experiment is valid.

USAGE
The analysis writes `analysis/splits.json` while it splits:

  {"dataset": "DS-0001", "protocol": "5fold-grouped", "id_column": "sample_id",
   "target": "label", "group_column": "patient_id",
   "preprocessing_fitted": "within-fold",
   "folds": [{"fold": 0, "train": [...], "test": [...]}, ...]}

  python scripts/leakage_check.py --splits analysis/splits.json
  python scripts/leakage_check.py --splits analysis/splits.json --data analysis/data/train.csv

Exit codes: 0 clean · 1 error · 2 findings.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd

DECLARATIONS = {"within-fold", "whole-dataset", "none", "not-declared"}


def load_manifest(path: Path) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(manifest, dict):
        die(f"{path} must hold a JSON object, got {type(manifest).__name__}")
    folds = manifest.get("folds")
    if not isinstance(folds, list) or not folds:
        die(f"{path} declares no folds — write one object per fold with 'train' and "
            f"'test' id lists, even for a single holdout split")
    for i, fold in enumerate(folds):
        if not isinstance(fold, dict) or "train" not in fold or "test" not in fold:
            die(f"{path}: fold {i} has no 'train'/'test' lists")
    return manifest


def read_rows(path: Path) -> tuple[list[dict], list[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    delim = "\t" if path.suffix.lower() == ".tsv" else ","
    reader = csv.DictReader(text.splitlines(), delimiter=delim)
    rows = list(reader)
    if not rows:
        die(f"{path} holds no data rows")
    return rows, list(reader.fieldnames or [])


def _row_hash(row: dict, ignore: set[str]) -> str:
    payload = {k: v for k, v in sorted(row.items()) if k not in ignore}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def index_overlap(manifest: dict) -> list[dict]:
    findings = []
    for fold in manifest["folds"]:
        both = sorted(set(map(str, fold["train"])) & set(map(str, fold["test"])),
                      key=str)
        if both:
            findings.append({"fold": fold.get("fold"), "check": "index_overlap",
                             "count": len(both), "examples": both[:10],
                             "detail": "the same id is in train and test"})
    return findings


def group_overlap(manifest: dict, rows: list[dict] | None) -> list[dict]:
    group_col = manifest.get("group_column")
    if not group_col:
        return []
    id_col = manifest.get("id_column")
    if rows is None or not id_col:
        return [{"check": "group_overlap", "skipped": True,
                 "detail": f"group_column {group_col!r} is declared but cannot be "
                           f"checked without --data and an 'id_column'"}]
    by_id = {str(r.get(id_col)): r for r in rows}
    findings = []
    for fold in manifest["folds"]:
        train_groups = {by_id[str(i)].get(group_col) for i in fold["train"] if str(i) in by_id}
        test_groups = {by_id[str(i)].get(group_col) for i in fold["test"] if str(i) in by_id}
        shared = sorted(g for g in (train_groups & test_groups) if g is not None)
        if shared:
            findings.append({"fold": fold.get("fold"), "check": "group_overlap",
                             "count": len(shared), "examples": shared[:10],
                             "detail": f"the same {group_col} appears on both sides — "
                                       f"the model can memorise the subject rather than "
                                       f"the phenomenon"})
    return findings


def duplicate_rows(manifest: dict, rows: list[dict] | None) -> list[dict]:
    id_col = manifest.get("id_column")
    if rows is None or not id_col:
        return []
    ignore = {id_col}
    by_id = {str(r.get(id_col)): r for r in rows}
    findings = []
    for fold in manifest["folds"]:
        train_hashes = {}
        for i in fold["train"]:
            row = by_id.get(str(i))
            if row is not None:
                train_hashes.setdefault(_row_hash(row, ignore), str(i))
        hits = []
        for i in fold["test"]:
            row = by_id.get(str(i))
            if row is None:
                continue
            h = _row_hash(row, ignore)
            if h in train_hashes:
                hits.append({"test_id": str(i), "train_id": train_hashes[h]})
        if hits:
            findings.append({"fold": fold.get("fold"), "check": "duplicate_rows",
                             "count": len(hits), "examples": hits[:10],
                             "detail": "identical feature rows under different ids on "
                                       "both sides — an index check cannot see this"})
    return findings


def target_determining_columns(manifest: dict, rows: list[dict] | None) -> list[dict]:
    """Columns that map one-to-one onto the target.

    Not a correlation: an exact functional dependency, which is what an id
    assigned after the outcome or a leftover 'result' column looks like. Reported
    with the mapping's size so a genuinely binary feature on a binary target — a
    legitimate case — is visible as such rather than hidden behind a verdict.
    """
    target = manifest.get("target")
    if rows is None or not target or target not in rows[0]:
        return []
    findings = []
    n = len(rows)
    for column in rows[0]:
        if column in (target, manifest.get("id_column")):
            continue
        mapping = {}
        determines = True
        for row in rows:
            key = row.get(column)
            value = row.get(target)
            if key in mapping and mapping[key] != value:
                determines = False
                break
            mapping[key] = value
        if determines and len(mapping) > 1:
            findings.append({"check": "target_determined_by_feature", "column": column,
                             "distinct_values": len(mapping), "rows": n,
                             "detail": (f"every value of {column!r} maps to exactly one "
                                        f"target value. With {len(mapping)} distinct "
                                        f"values over {n} rows this is either a leak or "
                                        f"a genuinely deterministic feature — decide, "
                                        f"do not assume")})
    return findings


def preprocessing_declaration(manifest: dict) -> list[dict]:
    declared = manifest.get("preprocessing_fitted", "not-declared")
    if declared not in DECLARATIONS:
        return [{"check": "preprocessing", "declared": declared,
                 "detail": f"unrecognised declaration; expected one of {sorted(DECLARATIONS)}"}]
    if declared == "within-fold":
        return []
    return [{"check": "preprocessing", "declared": declared,
             "detail": ("a scaler, imputer, feature selector or resampler fitted on "
                        "the whole dataset leaks the test set into training. This is a "
                        "DECLARATION, not a check — nothing here can see it in the "
                        "split, which is exactly why it has to be declared")}]


def run(manifest: dict, rows: list[dict] | None) -> dict:
    findings = (index_overlap(manifest) + group_overlap(manifest, rows)
                + duplicate_rows(manifest, rows)
                + target_determining_columns(manifest, rows)
                + preprocessing_declaration(manifest))
    real = [f for f in findings if not f.get("skipped")]
    return {
        "result": "CLEAN" if not real else "FINDINGS",
        "dataset": manifest.get("dataset"),
        "protocol": manifest.get("protocol"),
        "folds": len(manifest["folds"]),
        "data_inspected": rows is not None,
        "findings": findings,
        "note": ("clean means these four are clean. Preprocessing fitted outside "
                 "the fold is reported from your declaration, never detected, and "
                 "temporal validity is a domain question no script answers"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--splits", default="analysis/splits.json",
                    help="the split manifest the analysis wrote")
    ap.add_argument("--data", help="the data file, for the checks that need the rows")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.splits, "--splits")
    splits = Path(args.splits)
    if not splits.is_file():
        die(f"{args.splits} does not exist — the analysis has to write the split "
            f"manifest while it splits; reconstructing it afterwards checks the "
            f"reconstruction, not the run")
    manifest = load_manifest(splits)

    rows = None
    if args.data:
        require_within_cwd(args.data, "--data")
        data = Path(args.data)
        if not data.is_file():
            die(f"{args.data} does not exist")
        if data.suffix.lower() not in (".csv", ".tsv"):
            die(f"{args.data} is not a delimited text file — the row-level checks "
                f"read CSV/TSV; run them on the exported feature table")
        rows, _ = read_rows(data)

    result = run(manifest, rows)
    result["splits_file"] = splits.as_posix()
    emit(result, args.json_out)
    sys.exit(2 if result["result"] == "FINDINGS" else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"file is not valid UTF-8 — {e}")
