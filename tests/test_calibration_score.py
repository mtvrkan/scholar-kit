"""Tests for calibration_score.py — reviewer error-profile measurement.

The two things this script must never do are report a rate it cannot support,
and score a run whose reviewer could see the answer. Most of these tests are
about those refusals; the arithmetic is the easy part.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import calibration_score as cs  # noqa: E402


def _write(tmp_path, name, rows):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                 encoding="utf-8")
    return p


def _pair(tmp_path, gold_rows, verdict_rows):
    return (_write(tmp_path, "gold.jsonl", gold_rows),
            _write(tmp_path, "verdicts.jsonl", verdict_rows))


def _five_paper_set(pred_for=None):
    """5 papers spanning both classes; `pred_for` overrides predicted decisions."""
    gold = [
        {"id": "p1", "label": "accept"},
        {"id": "p2", "label": "minor_revision"},
        {"id": "p3", "label": "major_revision"},
        {"id": "p4", "label": "reject"},
        {"id": "p5", "label": "minor_revision"},
    ]
    default = {"p1": "Accept", "p2": "Minor Revision", "p3": "Major Revision",
               "p4": "Reject", "p5": "Minor Revision"}
    default.update(pred_for or {})
    verdicts = [{"id": pid, "run": 1, "decision": d} for pid, d in default.items()]
    return gold, verdicts


# ---------- gold-label isolation ----------

def test_verdict_carrying_gold_label_is_refused(tmp_path):
    # A label-shaped field in a verdict record means the answer was reachable
    # while the verdict was formed. Scoring it would launder a contaminated run
    # into a published error profile.
    g, v = _pair(tmp_path,
                 [{"id": "p1", "label": "accept"}],
                 [{"id": "p1", "run": 1, "decision": "Accept", "label": "accept"}])
    with pytest.raises(SystemExit):
        cs.load_verdicts(v, {"p1"})


@pytest.mark.parametrize("field", ["gold", "gold_label", "expected", "ground_truth",
                                   "truth", "answer",
                                   # Spelling variants an emitter plausibly
                                   # produces; a check they can walk through is
                                   # not a check.
                                   "GoldLabel", "gold-label", "Ground Truth",
                                   "LABEL", "goldLabel"])
def test_all_contamination_field_spellings_refused(tmp_path, field):
    g, v = _pair(tmp_path,
                 [{"id": "p1", "label": "accept"}],
                 [{"id": "p1", "run": 1, "decision": "Accept", field: "x"}])
    with pytest.raises(SystemExit):
        cs.load_verdicts(v, {"p1"})


def test_clean_verdict_record_accepted(tmp_path):
    g, v = _pair(tmp_path,
                 [{"id": "p1", "label": "accept"}],
                 [{"id": "p1", "run": 1, "decision": "Accept", "major_issues": 0}])
    assert list(cs.load_verdicts(v, {"p1"})) == ["p1"]


# ---------- input validation ----------

def test_unknown_gold_label_rejected(tmp_path):
    g = _write(tmp_path, "gold.jsonl", [{"id": "p1", "label": "borderline"}])
    with pytest.raises(SystemExit):
        cs.load_gold(g)


def test_duplicate_gold_id_rejected(tmp_path):
    g = _write(tmp_path, "gold.jsonl", [{"id": "p1", "label": "accept"},
                                        {"id": "p1", "label": "reject"}])
    with pytest.raises(SystemExit):
        cs.load_gold(g)


def test_verdict_without_gold_entry_rejected(tmp_path):
    _, v = _pair(tmp_path, [{"id": "p1", "label": "accept"}],
                 [{"id": "ghost", "run": 1, "decision": "Accept"}])
    with pytest.raises(SystemExit):
        cs.load_verdicts(v, {"p1"})


def test_unknown_decision_rejected(tmp_path):
    _, v = _pair(tmp_path, [{"id": "p1", "label": "accept"}],
                 [{"id": "p1", "run": 1, "decision": "Probably Fine"}])
    with pytest.raises(SystemExit):
        cs.load_verdicts(v, {"p1"})


# ---------- refusing rates it cannot support ----------

def test_single_class_gold_set_refused(tmp_path):
    # With no negative-side papers FPR is undefined; emitting FNR alone would
    # read as a complete profile.
    gold = [{"id": f"p{i}", "label": "accept"} for i in range(1, 6)]
    verdicts = [{"id": f"p{i}", "run": 1, "decision": "Accept"} for i in range(1, 6)]
    by_paper = {v["id"]: [v] for v in verdicts}
    with pytest.raises(SystemExit):
        cs.score({g["id"]: g for g in gold}, by_paper, "full")


def test_directional_tier_emits_no_rates(tmp_path):
    gold = {g["id"]: g for g in [{"id": "p1", "label": "minor_revision"},
                                 {"id": "p2", "label": "major_revision"},
                                 {"id": "p3", "label": "accept"}]}
    by_paper = {"p1": [{"id": "p1", "run": 1, "decision": "Minor Revision"}],
                "p2": [{"id": "p2", "run": 1, "decision": "Major Revision"}],
                "p3": [{"id": "p3", "run": 1, "decision": "Accept"}]}
    rep = cs.score(gold, by_paper, "directional")
    assert rep["rates"] is None
    assert any("NOT an error-rate estimate" in c for c in rep["caveats"])


def test_full_tier_rejects_too_few_papers(run, tmp_path):
    _pair(tmp_path, [{"id": "p1", "label": "accept"}, {"id": "p2", "label": "reject"}],
          [{"id": "p1", "run": 1, "decision": "Accept"},
           {"id": "p2", "run": 1, "decision": "Reject"}])
    code, _, err = run("calibration_score.py", "--gold", "gold.jsonl",
                       "--verdicts", "verdicts.jsonl")
    assert code == 1 and "5-20" in err


def test_directional_tier_rejects_wrong_paper_count(run, tmp_path):
    _pair(tmp_path, [{"id": "p1", "label": "accept"}, {"id": "p2", "label": "reject"}],
          [{"id": "p1", "run": 1, "decision": "Accept"},
           {"id": "p2", "run": 1, "decision": "Reject"}])
    code, _, err = run("calibration_score.py", "--gold", "gold.jsonl",
                       "--verdicts", "verdicts.jsonl", "--tier", "directional")
    assert code == 1 and "exactly 3" in err


def test_directional_tier_rejects_ensembled_runs(run, tmp_path):
    gold = [{"id": f"p{i}", "label": lab} for i, lab in
            enumerate(["accept", "minor_revision", "major_revision"], 1)]
    verdicts = [{"id": "p1", "run": 1, "decision": "Accept"},
                {"id": "p1", "run": 2, "decision": "Accept"},
                {"id": "p2", "run": 1, "decision": "Minor Revision"},
                {"id": "p3", "run": 1, "decision": "Major Revision"}]
    _pair(tmp_path, gold, verdicts)
    code, _, err = run("calibration_score.py", "--gold", "gold.jsonl",
                       "--verdicts", "verdicts.jsonl", "--tier", "directional")
    assert code == 1 and "one run per paper" in err


# ---------- scoring arithmetic ----------

def test_perfect_agreement_gives_zero_error_rates(tmp_path):
    gold, verdicts = _five_paper_set()
    rep = cs.score({g["id"]: g for g in gold},
                   {v["id"]: [v] for v in verdicts}, "full")
    assert rep["rates"]["fnr_over_harsh"] == 0.0
    assert rep["rates"]["fpr_lenient"] == 0.0
    assert rep["rates"]["balanced_accuracy"] == 1.0


def test_over_harsh_error_counts_as_fnr(tmp_path):
    # p2 is gold minor_revision (positive) but predicted Major (negative):
    # the reviewer sent a publishable paper back.
    gold, verdicts = _five_paper_set({"p2": "Major Revision"})
    rep = cs.score({g["id"]: g for g in gold},
                   {v["id"]: [v] for v in verdicts}, "full")
    assert rep["confusion_matrix"]["fn"] == 1
    assert rep["rates"]["fnr_over_harsh"] > 0 and rep["rates"]["fpr_lenient"] == 0.0


def test_lenient_error_counts_as_fpr(tmp_path):
    # p3 is gold major_revision (negative) but predicted Minor (positive).
    gold, verdicts = _five_paper_set({"p3": "Minor Revision"})
    rep = cs.score({g["id"]: g for g in gold},
                   {v["id"]: [v] for v in verdicts}, "full")
    assert rep["confusion_matrix"]["fp"] == 1
    assert rep["rates"]["fpr_lenient"] > 0 and rep["rates"]["fnr_over_harsh"] == 0.0


def test_majority_vote_across_runs(tmp_path):
    gold = {"p1": {"id": "p1", "label": "minor_revision"}}
    runs = [{"id": "p1", "run": i, "decision": d} for i, d in
            enumerate(["Minor Revision", "Minor Revision", "Major Revision"], 1)]
    rep = cs.score(gold, {"p1": runs}, "directional")
    assert rep["per_paper"][0]["predicted"] == "Minor Revision"
    assert rep["per_paper"][0]["unanimous"] is False


def test_tie_breaks_toward_the_more_conservative_decision(tmp_path):
    # A reviewer split evenly has not established the friendlier verdict;
    # resolving ties optimistically would flatter the profile being measured.
    runs = [{"id": "p1", "run": 1, "decision": "Minor Revision"},
            {"id": "p1", "run": 2, "decision": "Major Revision"}]
    assert cs.majority_decision(runs)[0] == "Major Revision"


def test_unstable_papers_reported_and_caveated(tmp_path):
    gold, verdicts = _five_paper_set()
    by_paper = {v["id"]: [v] for v in verdicts}
    by_paper["p1"] = [{"id": "p1", "run": 1, "decision": "Accept"},
                      {"id": "p1", "run": 2, "decision": "Major Revision"}]
    rep = cs.score({g["id"]: g for g in gold}, by_paper, "full")
    assert "p1" in rep["unstable_papers"]
    assert any("unanimous" in c for c in rep["caveats"])


def test_small_n_caveat_present(tmp_path):
    gold, verdicts = _five_paper_set()
    rep = cs.score({g["id"]: g for g in gold},
                   {v["id"]: [v] for v in verdicts}, "full")
    assert any("<10" in c for c in rep["caveats"])


def test_positive_class_convention_stated_in_every_report(tmp_path):
    gold, verdicts = _five_paper_set()
    rep = cs.score({g["id"]: g for g in gold},
                   {v["id"]: [v] for v in verdicts}, "full")
    assert rep["positive_class"] == "accept + minor_revision"
    assert any("OVER-HARSH" in c for c in rep["caveats"])


# ---------- boundary sub-matrix ----------

def test_boundary_submatrix_reported_when_both_labels_present(tmp_path):
    gold, verdicts = _five_paper_set({"p3": "Minor Revision"})
    rep = cs.score({g["id"]: g for g in gold},
                   {v["id"]: [v] for v in verdicts}, "full")
    sub = rep["boundary_submatrix"]
    assert sub["major_revision"]["crossed"] == 1
    assert sub["minor_revision"]["stayed"] == 2


def test_boundary_submatrix_absent_without_both_labels(tmp_path):
    gold = {f"p{i}": {"id": f"p{i}", "label": lab} for i, lab in
            enumerate(["accept", "accept", "reject", "reject", "reject"], 1)}
    by_paper = {pid: [{"id": pid, "run": 1, "decision": "Accept"}] for pid in gold}
    rep = cs.score(gold, by_paper, "full")
    assert rep["boundary_submatrix"] is None


# ---------- reproducibility ----------

def test_bootstrap_ci_is_reproducible(tmp_path):
    gold, verdicts = _five_paper_set({"p2": "Major Revision"})
    g = {x["id"]: x for x in gold}
    by = {v["id"]: [v] for v in verdicts}
    a = cs.score(g, by, "full")["rates"]["fnr_ci95"]
    b = cs.score(g, by, "full")["rates"]["fnr_ci95"]
    # A CI redrawn on every run is not a reported figure, it is noise.
    assert a == b and a is not None


# ---------- CLI ----------

def test_cli_scores_a_clean_run(run, tmp_path):
    gold, verdicts = _five_paper_set()
    _pair(tmp_path, gold, verdicts)
    code, out, err = run("calibration_score.py", "--gold", "gold.jsonl",
                         "--verdicts", "verdicts.jsonl")
    assert code == 0, err
    assert json.loads(out)["papers"] == 5


def test_cli_rejects_path_outside_project(run, tmp_path):
    code, _, err = run("calibration_score.py", "--gold", "../g.jsonl",
                       "--verdicts", "v.jsonl")
    assert code == 1 and "--gold" in err


def test_cli_reports_missing_input_file(run, tmp_path):
    code, _, err = run("calibration_score.py", "--gold", "nope.jsonl",
                       "--verdicts", "also-nope.jsonl")
    assert code == 1 and "does not exist" in err
