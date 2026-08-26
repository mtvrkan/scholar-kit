"""The results table and figure, generated from the register (results_table.py,
results_figure.py).

The reason these exist is that the alternative was transcription, so the tests
check the two things transcription gets wrong and one thing a generator can get
wrong on its own: the numbers match the register, the difference carries an
interval, and nothing in the output ranks the models.
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

import results_table as rt  # noqa: E402

NO_MPL = importlib.util.find_spec("matplotlib") is None


def _project(tmp_path, with_predictions=True):
    analysis = tmp_path / "analysis"
    (analysis / "predictions").mkdir(parents=True, exist_ok=True)
    runs = []
    # majority is deliberately the WORSE model and is listed FIRST, so a table
    # that sorted by score would visibly reorder it.
    for model, base in (("majority", 0.50), ("logreg", 0.90)):
        for seed in (1, 2, 3):
            rec = {"id": f"RUN-{model}-{seed}", "experiment": "e", "model": model,
                   "dataset": "DS-0001", "seed": seed,
                   "metrics": {"roc_auc": round(base + seed / 1000, 4)}}
            if with_predictions:
                path = analysis / "predictions" / f"e__{model}__seed{seed}.csv"
                rows = ["fold,id,y_true,y_pred,y_prob"]
                for i in range(40):
                    label = i % 2
                    prob = (0.5 if model == "majority"
                            else (0.9 if label else 0.1))
                    rows.append(f"0,S{i},{label},{label if model != 'majority' else 0},{prob}")
                path.write_text("\n".join(rows) + "\n", encoding="utf-8")
                rec["predictions"] = f"analysis/predictions/{path.name}"
            runs.append(rec)
    (analysis / "runs.jsonl").write_text(
        "\n".join(json.dumps(r) for r in runs) + "\n", encoding="utf-8")


def _run(cwd, script, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


# ---------- the table ----------

def test_the_numbers_come_from_the_register(tmp_path):
    _project(tmp_path)
    _run(tmp_path, "results_table.py", "--experiment", "e", "--metric", "roc_auc")
    table = (tmp_path / "analysis" / "tables" / "e-roc_auc.md").read_text(encoding="utf-8")
    assert "0.902" in table and "0.502" in table  # the means of the three seeds


def test_every_row_carries_its_seeds(tmp_path):
    """0.809 and 0.809 ± 0.014 are different claims and only one is checkable."""
    _project(tmp_path)
    _run(tmp_path, "results_table.py", "--experiment", "e", "--metric", "roc_auc")
    table = (tmp_path / "analysis" / "tables" / "e-roc_auc.md").read_text(encoding="utf-8")
    assert "| Seeds |" in table and "1–3" in table
    assert "±" in table


def test_rows_stay_in_register_order_and_nothing_is_bold(tmp_path):
    _project(tmp_path)
    _run(tmp_path, "results_table.py", "--experiment", "e", "--metric", "roc_auc")
    table = (tmp_path / "analysis" / "tables" / "e-roc_auc.md").read_text(encoding="utf-8")
    assert table.index("majority") < table.index("logreg"), "the table sorted by score"
    assert "**" not in table, "a bold cell nominates a winner the interval may not support"


def test_the_difference_is_reported_as_a_paired_interval(tmp_path):
    _project(tmp_path)
    out = json.loads(_run(tmp_path, "results_table.py", "--experiment", "e",
                          "--metric", "roc_auc", "--reference", "majority").stdout)
    delta = out["deltas"]["logreg"]
    assert delta["available"] and delta["n_ids"] == 40
    lo, hi = delta["ci95"]
    assert lo <= delta["delta"] <= hi


def test_without_predictions_the_column_says_why_instead_of_subtracting(tmp_path):
    """A bare subtraction of two means is the claim the interval exists to qualify."""
    _project(tmp_path, with_predictions=False)
    out = json.loads(_run(tmp_path, "results_table.py", "--experiment", "e",
                          "--metric", "roc_auc", "--reference", "majority").stdout)
    delta = out["deltas"]["logreg"]
    assert delta["available"] is False and "prediction" in delta["reason"]


def test_latex_escapes_the_per_cent_sign(tmp_path):
    """An unescaped % comments out the rest of the row and the table still
    compiles — one column short, silently."""
    _project(tmp_path)
    _run(tmp_path, "results_table.py", "--experiment", "e", "--metric", "roc_auc",
         "--reference", "majority", "--format", "latex")
    tex = (tmp_path / "analysis" / "tables" / "e-roc_auc.tex").read_text(encoding="utf-8")
    assert r"95\%" in tex and "95% " not in tex
    assert r"\toprule" in tex and r"$\pm$" in tex


def test_an_unknown_metric_names_itself(tmp_path):
    _project(tmp_path)
    proc = _run(tmp_path, "results_table.py", "--metric", "bleu", expect=2)
    assert "bleu" in (proc.stderr + proc.stdout)


# ---------- the metric implementations, which are stdlib on purpose ----------

def test_auc_matches_the_rank_definition():
    # Perfect separation is 1.0; a reversed ranking is 0.0; ties land at 0.5.
    assert rt._auc([(1, 0.9), (1, 0.8), (0, 0.2), (0, 0.1)]) == 1.0
    assert rt._auc([(0, 0.9), (0, 0.8), (1, 0.2), (1, 0.1)]) == 0.0
    assert rt._auc([(1, 0.5), (0, 0.5)]) == 0.5


def test_auc_is_undefined_with_one_class_rather_than_zero():
    assert rt._auc([(1, 0.9), (1, 0.2)]) is None


def test_regression_metrics():
    pairs = [(3.0, 2.0), (5.0, 5.0), (7.0, 9.0)]
    assert rt.regression_metric("mae", pairs) == pytest.approx(1.0)
    assert rt.regression_metric("rmse", pairs) == pytest.approx((5 / 3) ** 0.5)


# ---------- the figure ----------

@pytest.mark.skipif(NO_MPL, reason="matplotlib is optional (requirements-ml.txt)")
def test_the_figure_draws_a_pdf_and_a_png_and_writes_its_caption(tmp_path):
    _project(tmp_path)
    out = json.loads(_run(tmp_path, "results_figure.py", "--experiment", "e",
                          "--metric", "roc_auc", "--lang", "tr").stdout)
    assert len(out["files"]) == 2
    for path in out["files"]:
        assert (tmp_path / path).stat().st_size > 0
    caption = (tmp_path / "analysis" / "captions.md").read_text(encoding="utf-8")
    assert "tohum" in caption and "standart sapma" in caption


@pytest.mark.skipif(NO_MPL, reason="matplotlib is optional (requirements-ml.txt)")
def test_the_figure_keeps_register_order(tmp_path):
    _project(tmp_path)
    out = json.loads(_run(tmp_path, "results_figure.py", "--experiment", "e",
                          "--metric", "roc_auc").stdout)
    assert out["models"] == ["majority", "logreg"]
