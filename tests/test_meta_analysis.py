"""Tests for meta_analysis.py.

Every numeric expectation here is either hand-computed from the published
formula in the comment above it, or derived from a construction whose answer is
exact by algebra (a homogeneous set has Q = 0; studies generated as
yi = theta + b*sei have Egger intercept exactly b). Nothing is asserted against
a number remembered from a package's output — that would test agreement with a
memory, not correctness.
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "meta_analysis.py"
sys.path.insert(0, str(ROOT / "scripts"))

import meta_analysis as ma  # noqa: E402


def pre(label, yi, sei):
    return {"study": label, "yi": yi, "sei": sei}


@pytest.fixture
def project(tmp_path):
    (tmp_path / "PROJECT.md").write_text("# p\n", encoding="utf-8")
    (tmp_path / "analysis").mkdir()
    return tmp_path


def run(project, *args):
    proc = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=project,
                          capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout, proc.stderr


# ---------- per-study effect sizes, hand-computed ----------

def test_log_odds_ratio_and_its_variance():
    # a=10 b=90 c=5 d=95 -> OR = (10*95)/(90*5) = 2.11111
    # v = 1/a + 1/b + 1/c + 1/d
    yi, vi, notes = ma.effect_binary({"e1": 10, "n1": 100, "e2": 5, "n2": 100}, "s", "or")
    assert yi == pytest.approx(math.log(950 / 450), rel=1e-12)
    assert vi == pytest.approx(1 / 10 + 1 / 90 + 1 / 5 + 1 / 95, rel=1e-12)
    assert notes == []


def test_log_risk_ratio_and_its_variance():
    # RR = (10/100)/(5/100) = 2 ; v = 1/a - 1/n1 + 1/c - 1/n2
    yi, vi, _ = ma.effect_binary({"e1": 10, "n1": 100, "e2": 5, "n2": 100}, "s", "rr")
    assert yi == pytest.approx(math.log(2.0), rel=1e-12)
    assert vi == pytest.approx(1 / 10 - 1 / 100 + 1 / 5 - 1 / 100, rel=1e-12)


def test_risk_difference_and_its_variance():
    # RD = 0.10 - 0.05 ; v = a*b/n1^3 + c*d/n2^3
    yi, vi, _ = ma.effect_binary({"e1": 10, "n1": 100, "e2": 5, "n2": 100}, "s", "rd")
    assert yi == pytest.approx(0.05, rel=1e-12)
    assert vi == pytest.approx((10 * 90) / 1e6 + (5 * 95) / 1e6, rel=1e-12)


def test_mean_difference_and_its_variance():
    row = {"m1": 10, "sd1": 2, "n1": 25, "m2": 8, "sd2": 3, "n2": 25}
    yi, vi, _ = ma.effect_continuous(row, "s", "md")
    assert yi == pytest.approx(2.0, rel=1e-12)
    assert vi == pytest.approx(4 / 25 + 9 / 25, rel=1e-12)


def test_hedges_g_and_its_variance():
    # s_pooled = sqrt((24*4 + 24*9)/48) = sqrt(6.5)
    # d = 2/sqrt(6.5) ; J = 1 - 3/(4*48-1) ; Vd = 50/625 + d^2/100 ; Vg = J^2*Vd
    row = {"m1": 10, "sd1": 2, "n1": 25, "m2": 8, "sd2": 3, "n2": 25}
    g, vg, _ = ma.effect_continuous(row, "s", "smd")
    d = 2.0 / math.sqrt(6.5)
    j = 1 - 3 / 191
    assert g == pytest.approx(j * d, rel=1e-12)
    assert vg == pytest.approx(j * j * (50 / 625 + d * d / 100), rel=1e-12)


def test_hedges_correction_shrinks_the_effect_and_fades_with_sample_size():
    small = ma.effect_continuous({"m1": 1, "sd1": 1, "n1": 5, "m2": 0, "sd2": 1, "n2": 5},
                                 "s", "smd")[0]
    big = ma.effect_continuous({"m1": 1, "sd1": 1, "n1": 5000, "m2": 0, "sd2": 1,
                                "n2": 5000}, "s", "smd")[0]
    raw = 1.0  # d, before correction, is the same in both
    assert small < big < raw
    assert big == pytest.approx(raw, abs=1e-3)


def test_precomputed_accepts_either_a_standard_error_or_a_variance():
    a = ma.effect_precomputed({"yi": 0.4, "sei": 0.2}, "s")
    b = ma.effect_precomputed({"yi": 0.4, "vi": 0.04}, "s")
    assert a[0] == b[0] and a[1] == pytest.approx(b[1])


def test_precomputed_without_an_uncertainty_column_is_an_error():
    with pytest.raises(ValueError, match="standard error"):
        ma.effect_precomputed({"yi": 0.4}, "s")


# ---------- zero cells ----------

def test_a_zero_cell_gets_a_reported_continuity_correction():
    # Silent correction would move the estimate toward the null and inflate its
    # variance with nothing in the output to say why.
    yi, vi, notes = ma.effect_binary({"e1": 0, "n1": 50, "e2": 5, "n2": 50}, "s", "or")
    assert yi == pytest.approx(math.log((0.5 * 45.5) / (50.5 * 5.5)), rel=1e-12)
    assert notes and "continuity" in notes[0]


def test_zero_events_in_both_arms_is_refused_for_ratio_measures():
    for measure in ("or", "rr"):
        with pytest.raises(ValueError, match="BOTH arms"):
            ma.effect_binary({"e1": 0, "n1": 40, "e2": 0, "n2": 40}, "s", measure)


def test_zero_events_in_both_arms_is_fine_for_a_risk_difference():
    # RD = 0 with zero variance is degenerate, but the measure itself is defined;
    # the failure must name the real problem, not pretend the rows are the same.
    with pytest.raises(ValueError, match="zero variance"):
        ma.effect_binary({"e1": 0, "n1": 40, "e2": 0, "n2": 40}, "s", "rd")


def test_impossible_counts_are_rejected():
    with pytest.raises(ValueError, match="outside"):
        ma.effect_binary({"e1": 60, "n1": 50, "e2": 5, "n2": 50}, "s", "or")
    with pytest.raises(ValueError, match="must be > 0"):
        ma.effect_binary({"e1": 0, "n1": 0, "e2": 5, "n2": 50}, "s", "or")


# ---------- pooling, hand-computed ----------

def test_homogeneous_studies_give_zero_heterogeneity_and_identical_models():
    rows = [pre("A", 0.5, 0.1), pre("B", 0.5, 0.1), pre("C", 0.5, 0.1)]
    out = ma.analyze(rows, "precomputed", 0.05, 10)
    assert out["heterogeneity"]["Q"] == pytest.approx(0.0, abs=1e-12)
    assert out["heterogeneity"]["I2_percent"] == 0.0
    assert out["heterogeneity"]["tau2"] == 0.0
    assert out["fixed_effect"]["estimate"] == pytest.approx(0.5, rel=1e-12)
    assert out["random_effects"]["estimate"] == pytest.approx(
        out["fixed_effect"]["estimate"], rel=1e-12)
    assert out["random_effects"]["se"] == pytest.approx(out["fixed_effect"]["se"], rel=1e-12)


def test_two_study_pooling_matches_hand_arithmetic():
    # y = 0 and 2, both se = 1 -> w = 1 each. theta_F = 1, var_F = 1/2.
    # Q = 1*(0-1)^2 + 1*(2-1)^2 = 2, df = 1.
    # C = sum(w) - sum(w^2)/sum(w) = 2 - 2/2 = 1 -> tau2 = (2-1)/1 = 1.
    # I2 = (2-1)/2 = 50%.  w* = 1/(1+1) = 0.5 -> theta_R = 1, var_R = 1.
    out = ma.analyze([pre("A", 0.0, 1.0), pre("B", 2.0, 1.0)], "precomputed", 0.05, 10)
    assert out["fixed_effect"]["estimate"] == pytest.approx(1.0, rel=1e-12)
    assert out["fixed_effect"]["se"] == pytest.approx(math.sqrt(0.5), rel=1e-12)
    assert out["heterogeneity"]["Q"] == pytest.approx(2.0, rel=1e-12)
    assert out["heterogeneity"]["df"] == 1
    assert out["heterogeneity"]["tau2"] == pytest.approx(1.0, rel=1e-12)
    assert out["heterogeneity"]["I2_percent"] == pytest.approx(50.0, rel=1e-12)
    assert out["random_effects"]["estimate"] == pytest.approx(1.0, rel=1e-12)
    assert out["random_effects"]["se"] == pytest.approx(1.0, rel=1e-12)


def test_tau_squared_is_floored_at_zero_never_negative():
    # Q < df happens by chance; DerSimonian-Laird's raw formula goes negative,
    # which would make random-effects weights larger than fixed-effect ones.
    out = ma.analyze([pre("A", 0.5, 1.0), pre("B", 0.5, 1.0), pre("C", 0.5, 1.0)],
                     "precomputed", 0.05, 10)
    assert out["heterogeneity"]["Q"] < out["heterogeneity"]["df"]
    assert out["heterogeneity"]["tau2"] == 0.0
    assert out["heterogeneity"]["I2_percent"] == 0.0


def test_random_effects_gives_small_studies_more_relative_weight():
    # Only true when tau2 > 0 — adding a constant to every variance compresses
    # the ratio between them. With tau2 = 0 the two weightings are identical, so
    # the set must be genuinely heterogeneous for the claim to mean anything.
    rows = [pre("big-a", 0.0, 0.1), pre("big-b", 1.0, 0.1), pre("small", 3.0, 1.0)]
    out = ma.analyze(rows, "precomputed", 0.05, 10)
    assert out["heterogeneity"]["tau2"] > 0
    small = next(s for s in out["studies"] if s["label"] == "small")
    assert small["weight_random_percent"] > small["weight_fixed_percent"]


def test_with_no_heterogeneity_the_two_weightings_are_identical():
    rows = [pre("big", 0.5, 0.1), pre("small", 0.5, 1.0)]
    out = ma.analyze(rows, "precomputed", 0.05, 10)
    assert out["heterogeneity"]["tau2"] == 0.0
    for s in out["studies"]:
        assert s["weight_random_percent"] == pytest.approx(s["weight_fixed_percent"])


def test_weights_sum_to_one_hundred_percent():
    rows = [pre("A", 0.2, 0.3), pre("B", 0.9, 0.15), pre("C", -0.1, 0.5)]
    out = ma.analyze(rows, "precomputed", 0.05, 10)
    assert sum(s["weight_fixed_percent"] for s in out["studies"]) == pytest.approx(100.0)
    assert sum(s["weight_random_percent"] for s in out["studies"]) == pytest.approx(100.0)


def test_confidence_interval_uses_the_requested_alpha():
    rows = [pre("A", 0.5, 0.1), pre("B", 0.6, 0.1)]
    tight = ma.analyze(rows, "precomputed", 0.05, 10)["fixed_effect"]
    wide = ma.analyze(rows, "precomputed", 0.01, 10)["fixed_effect"]
    assert (wide["ci_high"] - wide["ci_low"]) > (tight["ci_high"] - tight["ci_low"])


def test_pooled_estimate_lies_between_the_extreme_studies():
    rows = [pre("A", -1.0, 0.4), pre("B", 0.0, 0.2), pre("C", 3.0, 0.9)]
    out = ma.analyze(rows, "precomputed", 0.05, 10)
    for block in ("fixed_effect", "random_effects"):
        assert -1.0 <= out[block]["estimate"] <= 3.0


# ---------- prediction interval ----------

def test_prediction_interval_is_wider_than_the_confidence_interval():
    rows = [pre("A", 0.0, 0.2), pre("B", 1.0, 0.2), pre("C", 2.0, 0.2)]
    r = ma.analyze(rows, "precomputed", 0.05, 10)["random_effects"]
    assert r["tau2"] > 0
    assert r["prediction_low"] < r["ci_low"]
    assert r["prediction_high"] > r["ci_high"]


def test_prediction_interval_is_not_computed_below_three_studies():
    r = ma.analyze([pre("A", 0.0, 0.2), pre("B", 1.0, 0.2)], "precomputed", 0.05,
                   10)["random_effects"]
    assert "prediction_low" not in r
    assert "k >= 3" in r["prediction_note"]


# ---------- Egger's test ----------

def test_egger_is_not_run_below_the_minimum_and_says_why():
    rows = [pre(f"S{i}", 0.5, 0.1 * (i + 1)) for i in range(5)]
    egger = ma.analyze(rows, "precomputed", 0.05, 10)["publication_bias"]["egger"]
    assert egger["status"] == "not_run"
    assert "power" in egger["reason"]


def test_egger_intercept_is_exactly_zero_for_a_symmetric_funnel():
    # yi constant -> SND = theta * precision, a line through the origin.
    rows = [pre(f"S{i}", 0.5, 0.05 * (i + 1)) for i in range(12)]
    egger = ma.analyze(rows, "precomputed", 0.05, 10)["publication_bias"]["egger"]
    assert egger["status"] == "run"
    assert egger["intercept"] == pytest.approx(0.0, abs=1e-9)
    assert egger["slope"] == pytest.approx(0.5, rel=1e-9)


def test_egger_recovers_a_planted_asymmetry_exactly():
    # yi = theta + b*sei -> SND = theta*precision + b, so the intercept IS b.
    b = 1.4
    rows = [pre(f"S{i}", 0.5 + b * (0.05 * (i + 1)), 0.05 * (i + 1)) for i in range(12)]
    egger = ma.analyze(rows, "precomputed", 0.05, 10)["publication_bias"]["egger"]
    assert egger["intercept"] == pytest.approx(b, rel=1e-9)


def test_egger_reports_that_asymmetry_has_causes_other_than_publication_bias():
    rows = [pre(f"S{i}", 0.5, 0.05 * (i + 1)) for i in range(12)]
    egger = ma.analyze(rows, "precomputed", 0.05, 10)["publication_bias"]["egger"]
    assert "not by itself evidence of publication bias" in egger["interpretation"]


def test_egger_minimum_is_configurable_but_defaults_to_ten():
    rows = [pre(f"S{i}", 0.5, 0.05 * (i + 1)) for i in range(6)]
    assert ma.analyze(rows, "precomputed", 0.05, 10)["publication_bias"]["egger"][
        "status"] == "not_run"
    assert ma.analyze(rows, "precomputed", 0.05, 5)["publication_bias"]["egger"][
        "status"] == "run"
    assert ma.DEFAULT_EGGER_MIN == 10


# ---------- degenerate inputs ----------

def test_a_single_study_is_reported_but_not_pooled():
    out = ma.analyze([pre("only", 0.5, 0.1)], "precomputed", 0.05, 10)
    assert out["status"] == "insufficient"
    assert "not a meta-analysis" in out["message"]
    assert "fixed_effect" not in out and "heterogeneity" not in out


def test_no_usable_rows_is_an_error_that_names_the_failures():
    out = ma.analyze([{"study": "bad", "yi": 1.0}], "precomputed", 0.05, 10)
    assert out["status"] == "error"
    assert out["excluded"][0]["label"] == "bad"


def test_an_unusable_row_is_excluded_with_a_reason_not_dropped(project):
    rows = [pre("A", 0.5, 0.1), {"study": "B", "yi": 0.4}, pre("C", 0.6, 0.2)]
    out = ma.analyze(rows, "precomputed", 0.05, 10)
    assert out["k"] == 2
    assert [e["label"] for e in out["excluded"]] == ["B"]
    assert any("excluded" in c for c in out["caveats"])


def test_a_nonpositive_variance_is_excluded():
    out = ma.analyze([pre("A", 0.5, 0.1), pre("B", 0.5, 0.0), pre("C", 0.5, 0.2)],
                     "precomputed", 0.05, 10)
    assert [e["label"] for e in out["excluded"]] == ["B"]


def test_unknown_measure_is_refused():
    with pytest.raises(ValueError, match="unknown"):
        ma.analyze([pre("A", 0.5, 0.1)], "hazard_ratio", 0.05, 10)


# ---------- log-scale reporting ----------

def test_ratio_measures_report_exponentiated_estimates():
    rows = [{"study": "A", "e1": 10, "n1": 100, "e2": 5, "n2": 100},
            {"study": "B", "e1": 20, "n1": 200, "e2": 12, "n2": 200}]
    out = ma.analyze(rows, "or", 0.05, 10)
    assert out["scale"] == "log"
    f = out["fixed_effect"]
    assert f["exp_estimate"] == pytest.approx(math.exp(f["estimate"]), rel=1e-12)
    assert f["exp_ci_low"] == pytest.approx(math.exp(f["ci_low"]), rel=1e-12)
    assert any("log scale" in c for c in out["caveats"])


def test_difference_measures_report_no_exponentiated_fields():
    rows = [{"study": "A", "m1": 10, "sd1": 2, "n1": 25, "m2": 8, "sd2": 3, "n2": 25},
            {"study": "B", "m1": 11, "sd1": 2, "n1": 30, "m2": 8, "sd2": 3, "n2": 30}]
    out = ma.analyze(rows, "md", 0.05, 10)
    assert out["scale"] == "raw"
    assert "exp_estimate" not in out["fixed_effect"]


# ---------- honesty layer ----------

def test_caveats_always_state_that_i_squared_does_not_license_pooling():
    out = ma.analyze([pre("A", 0.5, 0.1), pre("B", 0.6, 0.1)], "precomputed", 0.05, 10)
    joined = " ".join(out["caveats"])
    assert "does NOT test" in joined and "appropriate" in joined


def test_caveats_forbid_choosing_the_model_after_seeing_the_numbers():
    out = ma.analyze([pre("A", 0.5, 0.1), pre("B", 0.6, 0.1)], "precomputed", 0.05, 10)
    assert any("BEFORE seeing these numbers" in c for c in out["caveats"])


def test_substantial_heterogeneity_adds_the_prediction_interval_caveat():
    rows = [pre("A", 0.0, 0.1), pre("B", 1.0, 0.1), pre("C", 2.0, 0.1)]
    out = ma.analyze(rows, "precomputed", 0.05, 10)
    assert out["heterogeneity"]["I2_percent"] >= 50
    assert any("prediction interval" in c for c in out["caveats"])


def test_both_models_are_always_reported():
    out = ma.analyze([pre("A", 0.5, 0.1), pre("B", 0.6, 0.1)], "precomputed", 0.05, 10)
    assert out["fixed_effect"] and out["random_effects"]


# ---------- forest plot ----------

def test_forest_plot_lists_every_study_and_both_pooled_rows():
    rows = [pre("Kaya 2019", 0.2, 0.2), pre("Demir 2021", 0.8, 0.3),
            pre("Yilmaz 2023", 0.5, 0.15)]
    plot = ma.analyze(rows, "precomputed", 0.05, 10)["forest_ascii"]
    for label in ("Kaya 2019", "Demir 2021", "Yilmaz 2023", "Fixed effect",
                  "Random effects"):
        assert label in plot
    assert "scale:" in plot


def test_forest_plot_shows_ratios_not_log_values_for_ratio_measures():
    rows = [{"study": "A", "e1": 10, "n1": 100, "e2": 5, "n2": 100},
            {"study": "B", "e1": 20, "n1": 200, "e2": 12, "n2": 200}]
    out = ma.analyze(rows, "or", 0.05, 10)
    assert "ratio" in out["forest_ascii"]
    assert "no effect (1)" in out["forest_ascii"]


def test_forest_plot_marks_the_no_effect_line_at_zero_for_differences():
    rows = [pre("A", -0.3, 0.2), pre("B", 0.4, 0.2)]
    assert "no effect (0)" in ma.analyze(rows, "precomputed", 0.05, 10)["forest_ascii"]


def test_forest_plot_survives_an_interval_that_excludes_the_null():
    rows = [pre("A", 5.0, 0.1), pre("B", 5.2, 0.1)]
    plot = ma.analyze(rows, "precomputed", 0.05, 10)["forest_ascii"]
    assert "no effect" not in plot  # off-scale: drawing it would be a lie
    assert "scale:" in plot


# ---------- input parsing ----------

def test_column_aliases_including_turkish_ones_are_understood():
    row = ma.canonical({"Çalışma": "x", "Olay1": 10, "Toplam1": 100,
                        "olay2": 5, "TOPLAM2": 100})
    assert row["e1"] == 10 and row["n1"] == 100 and row["e2"] == 5 and row["n2"] == 100


def test_study_label_falls_back_to_a_position_when_absent():
    out = ma.analyze([{"yi": 0.1, "sei": 0.2}, {"yi": 0.3, "sei": 0.2}],
                     "precomputed", 0.05, 10)
    assert [s["label"] for s in out["studies"]] == ["study-1", "study-2"]


def test_decimal_commas_are_accepted():
    yi, vi, _ = ma.effect_precomputed({"yi": "0,5", "sei": "0,2"}, "s")
    assert yi == pytest.approx(0.5) and vi == pytest.approx(0.04)


def test_csv_and_json_inputs_give_the_same_answer(project):
    (project / "analysis" / "e.csv").write_text(
        "study,yi,sei\nA,0.5,0.1\nB,0.7,0.2\n", encoding="utf-8")
    (project / "analysis" / "e.json").write_text(json.dumps(
        [{"study": "A", "yi": 0.5, "sei": 0.1}, {"study": "B", "yi": 0.7, "sei": 0.2}]),
        encoding="utf-8")
    a = ma.analyze(ma.load_rows(project / "analysis" / "e.csv"), "precomputed", 0.05, 10)
    b = ma.analyze(ma.load_rows(project / "analysis" / "e.json"), "precomputed", 0.05, 10)
    assert a["fixed_effect"]["estimate"] == pytest.approx(b["fixed_effect"]["estimate"])


def test_jsonl_input_is_accepted(project):
    p = project / "analysis" / "e.jsonl"
    p.write_text('{"study":"A","yi":0.5,"sei":0.1}\n{"study":"B","yi":0.7,"sei":0.2}\n',
                 encoding="utf-8")
    assert len(ma.load_rows(p)) == 2


# ---------- CLI ----------

def test_cli_emits_json(project):
    (project / "analysis" / "e.csv").write_text(
        "study,yi,sei\nA,0.5,0.1\nB,0.7,0.2\n", encoding="utf-8")
    code, out, err = run(project, "--input", "analysis/e.csv", "--json")
    assert code == 0, err
    assert json.loads(out)["status"] == "ok"


def test_cli_forest_flag_prints_the_plot_not_json(project):
    (project / "analysis" / "e.csv").write_text(
        "study,yi,sei\nA,0.5,0.1\nB,0.7,0.2\n", encoding="utf-8")
    code, out, err = run(project, "--input", "analysis/e.csv", "--forest")
    assert code == 0, err
    assert "Study" in out and not out.strip().startswith("{")


def test_cli_rejects_a_path_outside_the_project(project):
    assert run(project, "--input", "../escape.csv")[0] != 0


def test_cli_rejects_a_nonsensical_alpha(project):
    (project / "analysis" / "e.csv").write_text("study,yi,sei\nA,0.5,0.1\n", encoding="utf-8")
    for bad in ("0", "1", "1.5"):
        assert run(project, "--input", "analysis/e.csv", "--alpha", bad)[0] != 0


def test_cli_reports_a_missing_file_cleanly(project):
    code, out, err = run(project, "--input", "analysis/nope.csv")
    assert code != 0
    assert "not found" in (out + err)


def test_cli_reports_an_empty_file_cleanly(project):
    (project / "analysis" / "e.csv").write_text("study,yi,sei\n", encoding="utf-8")
    code, out, err = run(project, "--input", "analysis/e.csv")
    assert code != 0
    assert "no rows" in (out + err)
