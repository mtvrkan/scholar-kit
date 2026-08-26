"""Running the experiment matrix (scripts/train_runner.py).

The config validation runs everywhere; the training itself is skipped where
scikit-learn is not installed, which is the normal state of a review-only
install. What the tests pin is what the runner refuses — unregistered data, no
seeds, a group protocol with no group column — and the one guarantee that no
instruction ever reliably produced: preprocessing fitted inside the fold, and a
split manifest that says so because it was built that way.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import train_runner as tr  # noqa: E402,F401  (import smoke: the module must load)

NO_ML = not all(importlib.util.find_spec(m) for m in ("sklearn", "pandas", "numpy"))

BASE = {"experiment": "t", "dataset": "DS-0001", "data": "analysis/data/f.csv",
        "target": "label", "task": "classification", "seeds": [1, 2],
        "models": {"logreg": {"type": "logreg"}}}


def _write(tmp_path, config=None, rows=60, register=True):
    (tmp_path / "analysis" / "data").mkdir(parents=True, exist_ok=True)
    lines = ["sample_id,group_id,x1,x2,cat,label"]
    for i in range(rows):
        lines.append(f"S{i},G{i // 2},{i % 7},{(i * 3) % 11},{'ab'[i % 2]},{i % 2}")
    (tmp_path / "analysis" / "data" / "f.csv").write_text("\n".join(lines) + "\n",
                                                          encoding="utf-8")
    if register:
        (tmp_path / "analysis" / "datasets.jsonl").write_text(json.dumps(
            {"id": "DS-0001", "name": "t", "source": "other", "license": "CC0-1.0",
             "license_verified": True, "files": []}) + "\n", encoding="utf-8")
    cfg = {**BASE, **(config or {})}
    (tmp_path / "analysis" / "experiment.json").write_text(
        json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return "analysis/experiment.json"


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "train_runner.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


# ---------- what it refuses, before importing a single ML package ----------

def test_a_config_with_no_seeds_is_refused(tmp_path):
    """There is no default seed. A run nobody can repeat is not evidence, and
    this is the field most easily left out."""
    cfg = _write(tmp_path, {"seeds": []})
    proc = _run(tmp_path, "--config", cfg, "--dry-run", expect=1)
    assert "seeds" in (proc.stderr + proc.stdout)


def test_unregistered_data_stops_the_run(tmp_path):
    cfg = _write(tmp_path, register=False)
    out = json.loads(_run(tmp_path, "--config", cfg, "--dry-run", expect=2).stdout)
    assert out["result"] == "REFUSED"
    assert out["dataset"]["status"] == "UNREGISTERED"


def test_group_kfold_without_a_group_column_is_refused(tmp_path):
    cfg = _write(tmp_path, {"protocol": {"kind": "group-kfold", "folds": 3}})
    proc = _run(tmp_path, "--config", cfg, "--dry-run", expect=1)
    assert "group_column" in (proc.stderr + proc.stdout)


def test_an_unknown_metric_is_named_rather_than_ignored(tmp_path):
    cfg = _write(tmp_path, {"metrics": ["roc_auc", "bleu"]})
    proc = _run(tmp_path, "--config", cfg, "--dry-run", expect=1)
    assert "bleu" in (proc.stderr + proc.stdout)


def test_the_dry_run_adds_the_trivial_baseline_and_says_so(tmp_path):
    """A model compared only against other models has no floor under it."""
    cfg = _write(tmp_path)
    out = json.loads(_run(tmp_path, "--config", cfg, "--dry-run").stdout)
    assert out["baseline_added"] == "majority"
    assert "majority" in out["models"] and out["runs"] == 4


def test_the_dry_run_writes_nothing(tmp_path):
    cfg = _write(tmp_path)
    _run(tmp_path, "--config", cfg, "--dry-run")
    assert not (tmp_path / "analysis" / "runs.jsonl").exists()
    assert not (tmp_path / "analysis" / "splits.json").exists()


def test_there_is_no_best_flag():
    # Same refusal as the register's: ranking without an uncertainty estimate is
    # the single most common overclaim in applied ML papers.
    flags = [ln for ln in (SCRIPTS / "train_runner.py").read_text(
        encoding="utf-8").splitlines() if "ap.add_argument(" in ln]
    assert not any("--best" in ln for ln in flags)


# ---------- the training itself ----------

@pytest.mark.skipif(NO_ML, reason="the ML stack is optional (requirements-ml.txt)")
def test_a_full_run_records_every_seed_and_writes_the_manifest(tmp_path):
    cfg = _write(tmp_path, {"group_column": "group_id", "id_column": "sample_id",
                            "protocol": {"kind": "group-kfold", "folds": 3,
                                         "stratified": True},
                            "metrics": ["accuracy"]}, rows=90)
    out = json.loads(_run(tmp_path, "--config", cfg).stdout)
    assert out["runs"] == 4  # (logreg + majority) × 2 seeds
    runs = [json.loads(ln) for ln in
            (tmp_path / "analysis" / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert {r["seed"] for r in runs} == {1, 2}
    assert all(r["env"] and r["config_hash"] for r in runs)

    manifest = json.loads((tmp_path / "analysis" / "splits.json").read_text(encoding="utf-8"))
    # True by construction, not by declaration: the preprocessing is a Pipeline
    # step, so it cannot have been fitted anywhere but inside the fold.
    assert manifest["preprocessing_fitted"] == "within-fold"
    assert manifest["group_column"] == "group_id"
    assert len(manifest["folds"]) == 3


@pytest.mark.skipif(NO_ML, reason="the ML stack is optional (requirements-ml.txt)")
def test_no_group_straddles_a_fold_boundary(tmp_path):
    """The leak whose absence silently inflates every metric — checked on the
    manifest the runner wrote, not on a reconstruction of it."""
    cfg = _write(tmp_path, {"group_column": "group_id", "id_column": "sample_id",
                            "protocol": {"kind": "group-kfold", "folds": 3,
                                         "stratified": True},
                            "metrics": ["accuracy"]}, rows=90)
    _run(tmp_path, "--config", cfg)
    manifest = json.loads((tmp_path / "analysis" / "splits.json").read_text(encoding="utf-8"))
    groups = {f"S{i}": f"G{i // 2}" for i in range(90)}
    for fold in manifest["folds"]:
        train = {groups[i] for i in fold["train"]}
        test = {groups[i] for i in fold["test"]}
        assert not (train & test), f"fold {fold['fold']} shares a group across the split"
