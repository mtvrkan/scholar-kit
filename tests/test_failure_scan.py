"""Tests for failure_scan.py — the deterministic half of the 7-mode AI-research
failure-mode checklist.

The modes come from Lu et al. (2026, Nature 651:914-919); what is tested here is
the boundary the script draws around them: which modes a machine can decide
(M1/M3/M5/M6/M7), which are delegated (M2) or explicitly left to a human (M4),
and — the part most checklists get wrong — that the quantitative modes switch
off for paper types that report no measurements, visibly rather than silently.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import failure_scan as fs  # noqa: E402


def _project(tmp_path, drafts: dict, analysis: dict | None = None, ptype: str | None = None):
    d = tmp_path / "drafts"
    d.mkdir(parents=True, exist_ok=True)
    for name, text in drafts.items():
        (d / name).write_text(text, encoding="utf-8")
    a = tmp_path / "analysis"
    if analysis is not None:
        a.mkdir(parents=True, exist_ok=True)
        for name, text in analysis.items():
            (a / name).write_text(text, encoding="utf-8")
    return d, a, ptype


def _run(tmp_path, drafts, analysis=None, ptype=None):
    d, a, t = _project(tmp_path, drafts, analysis, ptype)
    return fs.check(d, a, t)


# ---------- M1: implementation bug tells ----------

def test_exact_round_metric_flagged(tmp_path):
    res = _run(tmp_path, {"results.md": "The model reached an accuracy of 1.00 on the test set."})
    hits = [f for f in res["modes"]["M1"]["findings"] if f["signal"] == "exact-round-metric"]
    assert len(hits) == 1
    # Reported as written, not as the normalized comparison key ("1"), so the
    # author can find the sentence in their own draft.
    assert hits[0]["value"] == "1.00" and "1.00" in hits[0]["msg"]


def test_ordinary_metric_value_not_flagged(tmp_path):
    res = _run(tmp_path, {"results.md": "The model reached an accuracy of 0.873."})
    assert res["modes"]["M1"]["findings"] == []


def test_zero_variance_flagged(tmp_path):
    res = _run(tmp_path, {"results.md": "Performance was stable (0.812 ± 0.00 across seeds)."})
    assert any(f["signal"] == "zero-variance" for f in res["modes"]["M1"]["findings"])


def test_one_value_serving_many_metrics_flagged(tmp_path):
    res = _run(tmp_path, {"results.md": "Accuracy was 0.873, precision 0.873, and recall 0.873."})
    hit = [f for f in res["modes"]["M1"]["findings"] if f["signal"] == "one-value-many-metrics"]
    assert len(hit) == 1 and hit[0]["value"] == "0.873"


def test_same_value_for_one_metric_repeated_is_not_flagged(tmp_path):
    # Restating one result across sections is normal writing, not a constant leak.
    res = _run(tmp_path, {
        "abstract.md": "We report an accuracy of 0.873.",
        "results.md": "Accuracy reached 0.873.",
        "discussion.md": "The accuracy of 0.873 exceeds the baseline."})
    assert [f for f in res["modes"]["M1"]["findings"] if f["signal"] == "one-value-many-metrics"] == []


# ---------- M3: unbacked own result ----------

def test_number_absent_from_analysis_flagged(tmp_path):
    res = _run(tmp_path, {"results.md": "The improvement reached 12.4 points."},
               {"counts.json": '{"n_models": 4}'})
    assert [f["value"] for f in res["modes"]["M3"]["findings"]] == ["12.4"]


def test_number_present_in_analysis_not_flagged(tmp_path):
    res = _run(tmp_path, {"results.md": "The improvement reached 12.4 points."},
               {"metrics.csv": "delta\n12.4\n"})
    assert res["modes"]["M3"]["findings"] == []


def test_prose_rounding_of_artefact_number_accepted(tmp_path):
    # A table holding 0.8712 legitimately becomes "0.87" in prose.
    res = _run(tmp_path, {"results.md": "Accuracy was 0.87 overall."},
               {"metrics.csv": "acc\n0.8712\n"})
    assert res["modes"]["M3"]["findings"] == []


def test_prose_more_precise_than_artefact_is_flagged(tmp_path):
    # The reverse direction is not rounding — it is precision from nowhere.
    res = _run(tmp_path, {"results.md": "Accuracy was 0.8712 overall."},
               {"metrics.csv": "acc\n0.87\n"})
    assert [f["value"] for f in res["modes"]["M3"]["findings"]] == ["0.8712"]


def test_cited_number_is_literature_not_own_result(tmp_path):
    res = _run(tmp_path, {"results.md": "Prior work reports 0.91 accuracy [@kaya2023]."},
               {"counts.json": "{}"})
    assert res["modes"]["M3"]["findings"] == []


def test_table_pointer_exempts_number(tmp_path):
    res = _run(tmp_path, {"results.md": "Table 3 lists the 12.4 point gain."},
               {"counts.json": "{}"})
    assert res["modes"]["M3"]["findings"] == []


def test_integers_are_not_treated_as_measurements(tmp_path):
    res = _run(tmp_path, {"results.md": "We evaluated 4 models over 2023 and 2024."},
               {"counts.json": "{}"})
    assert res["modes"]["M3"]["findings"] == []


def test_m3_skipped_when_no_analysis_artefacts(tmp_path):
    res = _run(tmp_path, {"results.md": "The improvement reached 12.4 points."})
    assert res["modes"]["M3"]["status"] == "SKIPPED"
    assert "analysis/" in res["modes"]["M3"]["reason"]


def test_m3_only_scans_result_narrating_files(tmp_path):
    res = _run(tmp_path, {"intro.md": "Background rates hover near 12.4 per capita."},
               {"counts.json": "{}"})
    assert res["modes"]["M3"]["findings"] == []


# ---------- M5: bug reframed as insight ----------

def test_unanchored_surprise_flagged(tmp_path):
    res = _run(tmp_path, {"discussion.md": "Surprisingly, the effect reversed under load."})
    assert len(res["modes"]["M5"]["findings"]) == 1


def test_surprise_with_citation_not_flagged(tmp_path):
    res = _run(tmp_path,
               {"discussion.md": "Surprisingly, the effect reversed under load [@kaya2023]."})
    assert res["modes"]["M5"]["findings"] == []


def test_surprise_anchored_by_previous_sentence_not_flagged(tmp_path):
    res = _run(tmp_path, {"discussion.md":
                          "Earlier work predicted a monotone increase [@kaya2023]. "
                          "Unexpectedly, the effect reversed under load."})
    assert res["modes"]["M5"]["findings"] == []


def test_turkish_surprise_marker_flagged(tmp_path):
    res = _run(tmp_path, {"tartisma.md": "Beklenenin aksine, etki yük altında tersine döndü."})
    assert len(res["modes"]["M5"]["findings"]) == 1


# ---------- M6: methodology fabrication ----------

def test_hyperparameter_absent_from_analysis_flagged(tmp_path):
    res = _run(tmp_path, {"methods.md": "We trained with a learning rate of 0.003."},
               {"config.json": '{"learning_rate": 0.01}'})
    hits = res["modes"]["M6"]["findings"]
    assert len(hits) == 1 and hits[0]["value"] == "0.003"


def test_hyperparameter_written_value_first_flagged(tmp_path):
    # English Methods prose puts the value before the name as often as after
    # ("for 50 epochs"), and Turkish puts it before by default.
    res = _run(tmp_path, {"methods.md": "We trained for 50 epochs."},
               {"config.json": '{"epochs": 30}'})
    hits = res["modes"]["M6"]["findings"]
    assert len(hits) == 1 and hits[0]["value"] == "50" and hits[0]["hyperparameter"] == "epochs"


def test_hyperparameter_present_in_analysis_not_flagged(tmp_path):
    res = _run(tmp_path, {"methods.md": "We trained with a learning rate of 0.003."},
               {"config.json": '{"learning_rate": 0.003}'})
    assert res["modes"]["M6"]["findings"] == []


def test_m6_only_scans_methods_files(tmp_path):
    res = _run(tmp_path, {"results.md": "We trained with a learning rate of 0.003."},
               {"config.json": "{}"})
    assert res["modes"]["M6"]["findings"] == []


# ---------- M7: frame-lock tells ----------

def test_hindsight_phrase_flagged(tmp_path):
    res = _run(tmp_path, {"discussion.md": "In hindsight, a different split would have been better."})
    assert len(res["modes"]["M7"]["findings"]) == 1


def test_turkish_hindsight_phrase_flagged(tmp_path):
    res = _run(tmp_path, {"tartisma.md": "Sonradan fark ettiğimiz üzere, bölünme oranı dardı."})
    assert len(res["modes"]["M7"]["findings"]) == 1


# ---------- paper-type pre-filter ----------

def test_quantitative_modes_off_for_theoretical_paper(tmp_path):
    res = _run(tmp_path, {"results.md": "The construct reached a value of 1.00."},
               {"counts.json": "{}"}, ptype="theoretical")
    assert res["quantitative_modes_active"] is False
    for mode in ("M1", "M3", "M6"):
        assert res["modes"][mode]["status"] == "SKIPPED"
        assert "theoretical" in res["modes"][mode]["reason"]


def test_type_skip_is_reported_not_silent(tmp_path):
    # A mistyped PROJECT.md must not be a quiet way to disable half the scan.
    res = _run(tmp_path, {"results.md": "Accuracy of 1.00."}, {"c.json": "{}"}, ptype="qualitative")
    assert res["modes"]["M1"]["reason"]
    assert res["warnings"] == 0


def test_narrative_modes_stay_on_for_non_quantitative_types(tmp_path):
    res = _run(tmp_path, {"discussion.md": "Surprisingly, the framing collapsed."},
               ptype="theoretical")
    assert res["modes"]["M5"]["status"] == "FLAGGED"


def test_unknown_type_keeps_quantitative_modes_on(tmp_path):
    res = _run(tmp_path, {"results.md": "Accuracy of 1.00."}, {"c.json": "{}"}, ptype=None)
    assert res["quantitative_modes_active"] is True
    assert res["modes"]["M1"]["status"] == "FLAGGED"


def test_empirical_type_keeps_quantitative_modes_on(tmp_path):
    res = _run(tmp_path, {"results.md": "Accuracy of 1.00."}, {"c.json": "{}"},
               ptype="empirical-imrad")
    assert res["modes"]["M1"]["status"] == "FLAGGED"


# ---------- mode coverage contract ----------

def test_all_seven_modes_reported(tmp_path):
    res = _run(tmp_path, {"results.md": "Nothing notable here."})
    assert set(res["modes"]) == {"M1", "M2", "M3", "M4", "M5", "M6", "M7"}


def test_m2_delegated_and_m4_not_automated(tmp_path):
    res = _run(tmp_path, {"results.md": "Nothing notable."})
    assert res["modes"]["M2"]["status"] == "DELEGATED"
    assert "verify-citations" in res["modes"]["M2"]["reason"]
    assert res["modes"]["M4"]["status"] == "NOT_AUTOMATED"


def test_undecidable_modes_never_contribute_warnings(tmp_path):
    res = _run(tmp_path, {"results.md": "Nothing notable."})
    assert res["warnings"] == 0


# ---------- PROJECT.md type reading ----------

def test_type_read_from_project_md(tmp_path):
    (tmp_path / "PROJECT.md").write_text(
        "# P\n\n- **Type:** qualitative  <!-- enum comment -->\n", encoding="utf-8")
    assert fs.read_type(tmp_path / "PROJECT.md") == "qualitative"


def test_tbd_type_reads_as_unset(tmp_path):
    (tmp_path / "PROJECT.md").write_text("- **Type:** TBD\n", encoding="utf-8")
    assert fs.read_type(tmp_path / "PROJECT.md") is None


def test_missing_project_md_reads_as_unset(tmp_path):
    assert fs.read_type(tmp_path / "PROJECT.md") is None


# ---------- parsing robustness ----------

def test_code_fence_ignored(tmp_path):
    res = _run(tmp_path, {"results.md": "Text.\n\n```\naccuracy = 1.00\n```\n"},
               {"c.json": "{}"})
    assert res["modes"]["M1"]["findings"] == []


def test_heading_ignored(tmp_path):
    res = _run(tmp_path, {"discussion.md": "## Surprisingly strong results\n\nSee below.\n"})
    assert res["modes"]["M5"]["findings"] == []


# ---------- CLI contract ----------

def test_empty_project_exits_zero(run):
    code, out, _ = run("failure_scan.py")
    assert code == 0 and json.loads(out)["warnings"] == 0


def test_strict_exits_two_on_warning(run, tmp_path):
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "discussion.md").write_text(
        "Surprisingly, the effect reversed.", encoding="utf-8")
    code, out, _ = run("failure_scan.py", "--strict")
    assert code == 2 and json.loads(out)["warnings"] == 1


def test_type_flag_overrides_project_md(run, tmp_path):
    (tmp_path / "PROJECT.md").write_text("- **Type:** empirical-imrad\n", encoding="utf-8")
    code, out, _ = run("failure_scan.py", "--type", "theoretical")
    assert code == 0 and json.loads(out)["quantitative_modes_active"] is False


def test_path_outside_project_rejected(run):
    code, _, err = run("failure_scan.py", "--drafts", "../elsewhere")
    assert code == 1 and "--drafts" in err


# ---------- grouped thousands are counts, not measurements ----------
# Regression: "1.572 kayıt" (Turkish grouping) and "1,572 records" (English) were
# read as the DECIMAL 1.572. That slipped past the "integers are counts and
# years" skip, so a PRISMA identification count was reported as an own result
# with no artefact behind it — while the artefact holding 1572 sat in analysis/.

import pytest  # noqa: E402


@pytest.mark.parametrize("tok,expected", [
    ("1.572", "1572"),        # Turkish grouping
    ("1,572", "1572"),        # English grouping
    ("12.345", "12345"),
    ("12,345.67", "12345.67"),  # English: comma groups, point decimates
    ("12.345,67", "12345.67"),  # Turkish: point groups, comma decimates
    ("0.87", "0.87"),         # a real decimal is untouched
    ("0,940", "0.94"),
    ("1572", "1572"),
])
def test_grouped_thousands_normalise_to_the_plain_integer(tok, expected):
    assert fs._norm(tok) == expected


def test_a_narrated_record_count_is_not_an_unbacked_result(tmp_path):
    res = _run(tmp_path,
               {"bulgular.md": "Uluslararası kolda tanımlanan 1.572 kaydın 1.328'i "
                               "elemede dışlandı.\n"},
               {"counts.json": '{"identified": 1572, "excluded_screening": 1328}'},
               "systematic-review")
    assert res["modes"]["M3"]["findings"] == []


def test_a_genuinely_unbacked_measurement_is_still_flagged(tmp_path):
    res = _run(tmp_path,
               {"bulgular.md": "Havuzlanmış duyarlılık 0.937 olarak bulunmuştur.\n"},
               {"counts.json": '{"identified": 1572}'},
               "systematic-review")
    vals = [f["value"] for f in res["modes"]["M3"]["findings"]]
    assert "0.937" in vals


# ---------- a cited metric is a literature number ----------

def test_a_cited_perfect_metric_is_not_this_papers_own_result(tmp_path):
    """A review's job includes REPORTING an implausible 1.0 someone published.

    Regression: a sentence naming another study's perfect score — and diagnosing
    the leakage in the next clause — was flagged as this paper's own constant
    leaking through. scan_m3 already exempts cited sentences for exactly this
    reason; M1 now does the same.
    """
    res = _run(tmp_path, {"bulgular.md":
                          "Bir çalışmada beş sınıfın tamamında duyarlılık 1,0 olarak "
                          "bildirilmiştir [@cavli2023yapay].\n"})
    assert res["modes"]["M1"]["findings"] == []


def test_an_uncited_perfect_metric_is_still_flagged(tmp_path):
    res = _run(tmp_path, {"bulgular.md":
                          "Modelimiz test kümesinde 1,0 duyarlılık elde etmiştir.\n"})
    hits = [f for f in res["modes"]["M1"]["findings"]
            if f["signal"] == "exact-round-metric"]
    assert len(hits) == 1


# ---------- M3/M6: a pool large enough to back anything cannot clear anything ----
def _saturating_analysis() -> dict:
    """An artefact set that starts with every two-decimal prefix.

    Not contrived: a real review's analysis/ directory holds tens of thousands
    of numbers (per-study cells, bootstrap draws, per-fold predictions), and
    backed() accepts any artefact number that STARTS WITH the prose value.
    """
    return {"big.csv": "v\n" + "\n".join("0.%02d99" % i for i in range(100)) + "\n"}


def test_saturated_pool_reports_insufficient_evidence_not_clear(tmp_path):
    """Regression for the defect this measure exists for: on a real manuscript
    the pool backed 100% of two-decimal values, so M3 reported CLEAR over a
    Discussion paragraph whose correlation, medians and p-values were produced
    by no script at all. The check was not wrong about any single number — it
    had lost the ability to be wrong."""
    res = _run(tmp_path, {"results.md": "The correlation was 0.22 overall."},
               _saturating_analysis())
    m3 = res["modes"]["M3"]
    assert m3["status"] == "INSUFFICIENT EVIDENCE"
    assert m3["backing_saturation"] == 1.0
    assert "NOT a pass" in m3["reason"]


def test_small_pool_still_reports_a_real_clear(tmp_path):
    """The measure must not turn every clean project into INSUFFICIENT
    EVIDENCE: a handful of artefacts backs almost nothing it did not produce."""
    res = _run(tmp_path, {"results.md": "Accuracy was 0.87 overall."},
               {"metrics.csv": "acc\n0.8712\n"})
    m3 = res["modes"]["M3"]
    assert m3["status"] == "CLEAR"
    assert m3["backing_saturation"] < fs.SATURATION_LIMIT


def test_saturation_never_hides_a_real_finding(tmp_path):
    """A saturated pool downgrades a CLEAR, never a FLAGGED: an unbacked number
    is still an unbacked number, and burying it under a caveat would be worse
    than the caveat's absence."""
    res = _run(tmp_path, {"results.md": "The delta was 12.4 points."},
               _saturating_analysis())
    m3 = res["modes"]["M3"]
    assert m3["status"] == "FLAGGED"
    assert [f["value"] for f in m3["findings"]] == ["12.4"]


def test_saturation_is_reported_for_m6_as_well(tmp_path):
    """M6 uses the same backed() rule against the same pool, so it inherits the
    same blindness and must inherit the same caveat."""
    res = _run(tmp_path, {"methods.md": "We report the setup in full."},
               _saturating_analysis())
    assert res["modes"]["M6"]["status"] == "INSUFFICIENT EVIDENCE"
    assert res["modes"]["M6"]["backing_saturation"] == 1.0


def test_backing_saturation_of_an_empty_pool_is_zero(tmp_path):
    assert fs.backing_saturation(set()) == 0.0


# ---------- an HTML comment is not prose ----------


def test_a_failure_tell_inside_an_html_comment_is_not_scanned(tmp_path):
    """The sentence was removed from the manuscript; it is still in the file.

    Scanning it reports a mode against text no reader will ever see, and the
    author cannot act on it without deleting a note they kept deliberately.
    """
    body = ("Sonuçlar tabloda sunulmuştur.\n\n"
            "<!-- eski cümle: our method achieves state-of-the-art results and "
            "significantly outperforms all baselines -->\n")
    clean = fs._clean(body)
    assert "state-of-the-art" not in clean
    assert "Sonuçlar tabloda sunulmuştur." in clean
