"""The four checkable leaks (scripts/leakage_check.py).

A leak does not look like an error — it looks like a good result. These tests pin
the four it catches, and, just as hard, the one it does not: preprocessing fitted
outside the fold is reported from the manifest's declaration and never detected,
because nothing in a split can see it.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import leakage_check as lc  # noqa: E402,F401  (import smoke: the module must load)


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "leakage_check.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _write(tmp_path, manifest, rows=None):
    (tmp_path / "analysis").mkdir(exist_ok=True)
    (tmp_path / "analysis" / "splits.json").write_text(
        json.dumps(manifest), encoding="utf-8")
    if rows is not None:
        header = ",".join(rows[0])
        body = "\n".join(",".join(str(r[k]) for k in rows[0]) for r in rows)
        (tmp_path / "analysis" / "data.csv").write_text(header + "\n" + body + "\n",
                                                        encoding="utf-8")
    return tmp_path


CLEAN = {"dataset": "DS-0001", "protocol": "holdout", "id_column": "sid",
         "target": "label", "preprocessing_fitted": "within-fold",
         "folds": [{"fold": 0, "train": [1, 2, 3], "test": [4, 5]}]}


def _rows(**overrides):
    base = [{"sid": i, "x": i * 2, "label": i % 2} for i in range(1, 6)]
    for row in base:
        row.update(overrides.get(row["sid"], {}))
    return base


# ---------- 1. index overlap ----------

def test_the_same_id_on_both_sides_is_caught(tmp_path):
    manifest = {**CLEAN, "folds": [{"fold": 0, "train": [1, 2, 3], "test": [3, 4]}]}
    _write(tmp_path, manifest)
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json", expect=2).stdout)
    finding = out["findings"][0]
    assert finding["check"] == "index_overlap" and finding["examples"] == ["3"]


def test_ids_compare_as_strings_so_1_and_01_are_the_same_row(tmp_path):
    # A join key read as int on one side and str on the other is how an overlap
    # check passes on data that overlaps.
    manifest = {**CLEAN, "folds": [{"fold": 0, "train": ["3"], "test": [3]}]}
    _write(tmp_path, manifest)
    _run(tmp_path, "--splits", "analysis/splits.json", expect=2)


# ---------- 2. group leakage ----------

def test_the_same_subject_on_both_sides_is_caught(tmp_path):
    manifest = {**CLEAN, "group_column": "patient",
                "folds": [{"fold": 0, "train": [1, 2], "test": [3, 4]}]}
    rows = [{"sid": 1, "patient": "P1", "x": 1, "label": 0},
            {"sid": 2, "patient": "P2", "x": 2, "label": 1},
            {"sid": 3, "patient": "P1", "x": 3, "label": 0},
            {"sid": 4, "patient": "P3", "x": 4, "label": 1}]
    _write(tmp_path, manifest, rows)
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json",
                          "--data", "analysis/data.csv", expect=2).stdout)
    finding = next(f for f in out["findings"] if f["check"] == "group_overlap")
    assert finding["examples"] == ["P1"]


def test_a_declared_group_column_that_cannot_be_checked_says_so(tmp_path):
    # Silence here would read as "no group leakage", which is not what happened.
    manifest = {**CLEAN, "group_column": "patient"}
    _write(tmp_path, manifest)
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json").stdout)
    skipped = next(f for f in out["findings"] if f.get("skipped"))
    assert skipped["check"] == "group_overlap"
    assert out["result"] == "CLEAN"  # a skipped check is not a finding


# ---------- 3. duplicate rows ----------

def test_identical_feature_rows_under_different_ids_are_caught(tmp_path):
    manifest = {**CLEAN, "folds": [{"fold": 0, "train": [1, 2], "test": [3]}]}
    rows = [{"sid": 1, "x": 7, "label": 1},
            {"sid": 2, "x": 9, "label": 0},
            {"sid": 3, "x": 7, "label": 1}]  # same features as sid 1
    _write(tmp_path, manifest, rows)
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json",
                          "--data", "analysis/data.csv", expect=2).stdout)
    finding = next(f for f in out["findings"] if f["check"] == "duplicate_rows")
    assert finding["examples"][0] == {"test_id": "3", "train_id": "1"}


# ---------- 4. a feature that determines the target ----------

def test_a_column_that_maps_one_to_one_onto_the_label_is_reported(tmp_path):
    manifest = {**CLEAN, "folds": [{"fold": 0, "train": [1, 2], "test": [3, 4]}]}
    rows = [{"sid": 1, "x": 1, "outcome_code": "A", "label": 0},
            {"sid": 2, "x": 2, "outcome_code": "B", "label": 1},
            {"sid": 3, "x": 3, "outcome_code": "A", "label": 0},
            {"sid": 4, "x": 4, "outcome_code": "B", "label": 1}]
    _write(tmp_path, manifest, rows)
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json",
                          "--data", "analysis/data.csv", expect=2).stdout)
    columns = [f["column"] for f in out["findings"]
               if f["check"] == "target_determined_by_feature"]
    assert "outcome_code" in columns


def test_the_report_leaves_the_judgement_to_the_author(tmp_path):
    # A genuinely deterministic feature exists; the script says what it saw and
    # what the two readings are, rather than calling it a leak.
    manifest = {**CLEAN, "folds": [{"fold": 0, "train": [1], "test": [2]}]}
    rows = [{"sid": 1, "code": "A", "label": 0}, {"sid": 2, "code": "B", "label": 1}]
    _write(tmp_path, manifest, rows)
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json",
                          "--data", "analysis/data.csv", expect=2).stdout)
    finding = next(f for f in out["findings"] if f["check"] == "target_determined_by_feature")
    assert "decide" in finding["detail"]


# ---------- the limit, asserted by name ----------

def test_preprocessing_is_a_declaration_and_says_so(tmp_path):
    _write(tmp_path, {**CLEAN, "preprocessing_fitted": "whole-dataset"})
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json", expect=2).stdout)
    finding = next(f for f in out["findings"] if f["check"] == "preprocessing")
    assert "DECLARATION, not a check" in finding["detail"]


def test_an_undeclared_preprocessing_step_is_a_finding_not_a_pass(tmp_path):
    manifest = {k: v for k, v in CLEAN.items() if k != "preprocessing_fitted"}
    _write(tmp_path, manifest)
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json", expect=2).stdout)
    assert any(f["check"] == "preprocessing" for f in out["findings"])


def test_a_clean_split_says_what_clean_does_not_mean(tmp_path):
    _write(tmp_path, CLEAN)
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json").stdout)
    assert out["result"] == "CLEAN"
    assert "never detected" in out["note"]


# ---------- CLI contract ----------

def test_a_missing_manifest_says_why_reconstruction_will_not_do(tmp_path):
    proc = _run(tmp_path, "--splits", "analysis/splits.json", expect=1)
    assert "reconstruction" in proc.stderr


def test_a_manifest_with_no_folds_is_refused(tmp_path):
    _write(tmp_path, {"dataset": "DS-0001", "folds": []})
    proc = _run(tmp_path, "--splits", "analysis/splits.json", expect=1)
    assert "no folds" in proc.stderr


def test_a_fold_without_train_and_test_is_refused(tmp_path):
    _write(tmp_path, {"dataset": "DS-0001", "folds": [{"fold": 0, "train": [1]}]})
    _run(tmp_path, "--splits", "analysis/splits.json", expect=1)


def test_a_path_outside_the_project_is_refused(tmp_path):
    proc = _run(tmp_path, "--splits", "../elsewhere.json", expect=1)
    assert "--splits" in proc.stderr


def test_every_fold_is_checked_not_just_the_first(tmp_path):
    manifest = {**CLEAN, "folds": [{"fold": 0, "train": [1], "test": [2]},
                                   {"fold": 1, "train": [2], "test": [2]}]}
    _write(tmp_path, manifest)
    out = json.loads(_run(tmp_path, "--splits", "analysis/splits.json", expect=2).stdout)
    assert [f["fold"] for f in out["findings"] if f["check"] == "index_overlap"] == [1]
