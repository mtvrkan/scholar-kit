"""Tests for consistency_check.py — the numeric "narrated ≠ presented" lint.

Motivated by a real defect in the first end-to-end paper run: prose stated a
count (findings/models) that disagreed with what was actually presented. The
checker reconciles prose numbers against analysis/counts.json (manifest) and
flags the same quantity stated with different numbers across sections.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import consistency_check as cc  # noqa: E402


def _project(tmp_path, files: dict, manifest: dict | None):
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    for name, text in files.items():
        (drafts / name).write_text(text, encoding="utf-8")
    if manifest is not None:
        (tmp_path / "analysis").mkdir()
        (tmp_path / "analysis" / "counts.json").write_text(
            json.dumps(manifest), encoding="utf-8")
    return drafts, tmp_path / "analysis" / "counts.json"


# ---------- find_bound_numbers: digit + word numbers, modifier window ----------

def test_digit_number_bound_to_noun():
    assert cc.find_bound_numbers("we used 21 features", cc.NOUN_MAP["n_features"]) == [21]


def test_word_number_bound_to_noun():
    assert cc.find_bound_numbers("we trained four models", cc.NOUN_MAP["n_models"]) == [4]


def test_modifier_words_between_number_and_noun():
    got = cc.find_bound_numbers("four machine learning models", cc.NOUN_MAP["n_models"])
    assert got == [4]


def test_number_not_bound_to_unrelated_noun():
    assert cc.find_bound_numbers("50 of the patients recovered", cc.NOUN_MAP["n_models"]) == []


# ---------- manifest reconciliation ----------

def test_manifest_mismatch_flagged(tmp_path):
    drafts, manifest = _project(
        tmp_path,
        {"results.md": "We present 99 findings across four models."},
        {"n_findings": 80, "n_models": 4})
    res = cc.check(drafts, manifest)
    quantities = {m["quantity"] for m in res["manifest_mismatch"]}
    assert "n_findings" in quantities
    assert "n_models" not in quantities  # 4 == 4, correct
    assert res["warnings"] >= 1


def test_manifest_match_no_warning(tmp_path):
    drafts, manifest = _project(
        tmp_path,
        {"results.md": "We present 80 findings across four models."},
        {"n_findings": 80, "n_models": 4})
    res = cc.check(drafts, manifest)
    assert res["manifest_mismatch"] == []


def test_no_manifest_skips_reconciliation_but_runs_drift(tmp_path):
    drafts, manifest = _project(
        tmp_path,
        {"a.md": "four models", "b.md": "three models"},
        None)
    res = cc.check(drafts, manifest)
    assert res["manifest_present"] is False
    assert res["manifest_mismatch"] == []
    assert any(d["quantity"] == "n_models" for d in res["cross_section_drift"])


# ---------- cross-section drift ----------

def test_cross_section_drift_flagged(tmp_path):
    drafts, manifest = _project(
        tmp_path,
        {"abstract.md": "We compare four models.",
         "results.md": "Only three models were retained."},
        {"n_models": 4})
    res = cc.check(drafts, manifest)
    drift = [d for d in res["cross_section_drift"] if d["quantity"] == "n_models"]
    assert drift and set(drift[0]["values"]) == {3, 4}


def test_consistent_across_sections_no_drift(tmp_path):
    drafts, manifest = _project(
        tmp_path,
        {"abstract.md": "four models", "results.md": "the four models"},
        None)
    res = cc.check(drafts, manifest)
    assert res["cross_section_drift"] == []


# ---------- CLI contract ----------

def _run(cwd, *args):
    p = subprocess.run([sys.executable, str(SCRIPTS / "consistency_check.py"), *args],
                       cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    return p.returncode, p.stdout, p.stderr


def test_cli_default_never_blocks_even_with_warnings(tmp_path):
    _project(tmp_path, {"results.md": "99 findings"}, {"n_findings": 80})
    code, out, err = _run(tmp_path)
    assert code == 0  # WARN-only by default
    assert json.loads(out)["warnings"] >= 1


def test_cli_strict_blocks_on_warnings(tmp_path):
    _project(tmp_path, {"results.md": "99 findings"}, {"n_findings": 80})
    code, out, err = _run(tmp_path, "--strict")
    assert code == 2


def test_cli_strict_clean_passes(tmp_path):
    _project(tmp_path, {"results.md": "80 findings"}, {"n_findings": 80})
    code, out, err = _run(tmp_path, "--strict")
    assert code == 0


# --- table totals -----------------------------------------------------------
# A disposition table in the reference manuscript summed to 67 while its own
# prose said 68, and its caption claimed the numbers were register-derived.
# Every other guard here checks prose against data; nothing checked a table
# against itself.

def _md(tmp_path, text: str) -> Path:
    f = tmp_path / "t.md"
    f.write_text(text, encoding="utf-8")
    return f


def test_total_row_that_does_not_sum_is_flagged(tmp_path):
    f = _md(tmp_path, "| X | A | B | Toplam |\n|---|---|---|---|\n"
                      "| r1 | 4 | 0 | 4 |\n| r2 | 17 | 7 | 24 |\n"
                      "| Toplam | 22 | 7 | 29 |\n")
    hits = cc.check_table_totals([f])
    assert any(h["kind"] == "table-total-row" and h["stated"] == 22
               and h["sums_to"] == 21 for h in hits)


def test_total_row_that_sums_is_silent(tmp_path):
    f = _md(tmp_path, "| X | A | B | Toplam |\n|---|---|---|---|\n"
                      "| r1 | 4 | 0 | 4 |\n| r2 | 18 | 7 | 25 |\n"
                      "| Toplam | 22 | 7 | 29 |\n")
    assert cc.check_table_totals([f]) == []


def test_total_column_that_does_not_sum_is_flagged(tmp_path):
    f = _md(tmp_path, "| X | A | B | Total |\n|---|---|---|---|\n"
                      "| r1 | 4 | 1 | 9 |\n")
    hits = cc.check_table_totals([f])
    assert any(h["kind"] == "table-total-column" and h["sums_to"] == 5 for h in hits)


def test_bold_markup_in_total_cells_still_compared(tmp_path):
    """The total row is exactly where an author bolds the number."""
    f = _md(tmp_path, "| X | A | Toplam |\n|---|---|---|\n"
                      "| r1 | **17** | **17** |\n| **Toplam** | **18** | **18** |\n")
    assert any(h["stated"] == 18 and h["sums_to"] == 17
               for h in cc.check_table_totals([f]))


def test_non_numeric_columns_are_skipped_not_guessed(tmp_path):
    """Ranges, percentages and QUADAS marks must not be summed."""
    f = _md(tmp_path, "| Çalışma | Duyarlılık | Toplam |\n|---|---|---|\n"
                      "| A | %87,0–99,3 | n/d |\n| B | `+` | — |\n"
                      "| Toplam | 5 | 5 |\n")
    assert cc.check_table_totals([f]) == []


def test_cells_carrying_words_are_skipped(tmp_path):
    """"18 kayıt" may count something other than the column's unit."""
    f = _md(tmp_path, "| X | A | Toplam |\n|---|---|---|\n"
                      "| r1 | 4 kayıt | 4 |\n| r2 | 5 kayıt | 5 |\n"
                      "| Toplam | 9 kayıt | 9 |\n")
    assert cc.check_table_totals([f]) == []


def test_table_totals_reach_the_warning_count(tmp_path):
    drafts, manifest = _project(
        tmp_path,
        {"a.md": "| X | A | Toplam |\n|---|---|---|\n"
                 "| r1 | 4 | 4 |\n| Toplam | 9 | 9 |\n"},
        None)
    out = cc.check(drafts, manifest, tmp_path / "sources" / "registry.jsonl")
    assert out["table_totals"]
    assert out["warnings"] >= len(out["table_totals"])


# --- grouped thousands, both conventions -------------------------------------
# Regression: _NUM had no provision for a thousands separator, so it matched only
# the tail of a grouped number. "1,572 records" bound 572; "12,345 records" bound
# 345; and — worst, because this checker's first language is Turkish — "1.572
# kayıt" bound the DECIMAL 1.572. A checker that exists to catch a number stated
# two ways cannot itself misread the number: it would report a manifest mismatch
# that does not exist, or silently agree with a figure nobody wrote.

import pytest  # noqa: E402


@pytest.mark.parametrize("text,expected", [
    ("1,572 records identified", 1572),      # English grouping
    ("1.572 kayıt records", 1572),           # Turkish grouping
    ("12,345 records", 12345),
    ("12.345 records", 12345),
    ("1572 records", 1572),                  # ungrouped still works
])
def test_grouped_thousands_are_read_whole(text, expected):
    assert cc.find_bound_numbers(text, cc.NOUN_MAP["n_samples"]) == [expected]


@pytest.mark.parametrize("token,expected", [
    ("1.5", 1.5),        # no three-digit group: a decimal
    ("0.809", 0.809),    # leading zero: never a thousands group
])
def test_real_decimals_are_still_decimals(token, expected):
    """Asked of the parser, because the binder no longer returns fractions.

    The separator disambiguation is what these two cases are about and it is
    still worth pinning; it just does not survive a trip through
    find_bound_numbers any more, which drops anything that is not a whole
    number. Testing it here keeps the property covered without asking the
    binder to return something no manifest key can hold.
    """
    assert cc._to_num(token) == expected


@pytest.mark.parametrize("token,expected", [
    ("12,345.67", 12345.67),   # English: comma groups, point decimates
    ("12.345,67", 12345.67),   # Turkish: point groups, comma decimates
])
def test_grouped_number_with_a_decimal_tail(token, expected):
    assert cc._to_num(token) == expected


@pytest.mark.parametrize("text", [
    "61.5-76.2 records",      # the far end of an interval
    "61.5\u201376.2 records",  # the same, with the en dash a typesetter uses
    "%76,2 records",          # a percentage, Turkish sign-first convention
    "1.5 records",            # a fraction of a thing that does not come in halves
    "COVID-19 records",       # a name that ends in digits
    "T2-weighted records",    # and one that carries them in the middle
])
def test_a_number_that_cannot_be_a_count_is_not_reported_as_one(text):
    """The manifest holds counts, so a fractional or borrowed digit is a misread.

    `61.5-76.2 records` bound **76.2** as the sample size next to a manifest
    saying **76**, and the script reported the manuscript as inconsistent for
    saying two true things. Every case here is a sentence a real review writes;
    none of them states how many of anything there were.
    """
    assert cc.find_bound_numbers(text, cc.NOUN_MAP["n_samples"]) == []


def test_a_plain_count_still_binds():
    """The guard above must not be silence dressed up as precision."""
    assert cc.find_bound_numbers("we screened 76 records", cc.NOUN_MAP["n_samples"]) == [76]
    assert cc.find_bound_numbers("1,572 records", cc.NOUN_MAP["n_samples"]) == [1572]
    assert cc.find_bound_numbers("four machine learning models",
                                 cc.NOUN_MAP["n_models"]) == [4]


def test_a_grouped_number_reaches_the_manifest_comparison(tmp_path):
    """The whole point: the manifest must be compared against 1572, not 572."""
    drafts, manifest = _project(tmp_path,
                       {"bulgular.md": "In total 1,572 records were screened.\n"},
                       {"n_samples": 1572})
    out = cc.check(drafts, manifest)
    assert out["manifest_mismatch"] == []


def test_a_grouped_number_still_catches_a_real_mismatch(tmp_path):
    drafts, manifest = _project(tmp_path,
                       {"bulgular.md": "In total 1,572 records were screened.\n"},
                       {"n_samples": 1600})
    out = cc.check(drafts, manifest)
    assert len(out["manifest_mismatch"]) == 1
    assert out["manifest_mismatch"][0]["stated"] == 1572


# ---------- "records" belongs to the PRISMA flow when a flow is being checked ----------
#
# A two-arm review states 1,572 records identified in one arm and 68 records held
# for the other, and both sentences are true. The n_samples drift check read
# "records" as one dataset-size quantity and reported the manuscript as
# inconsistent. Where a flow IS being checked, the word has an owner; where it is
# not, it goes back to meaning sample size.

_COUNTS = {
    "identified": 1572, "duplicates": 0, "screened": 1572,
    "excluded_screening": 1328, "sought": 244, "not_retrieved": 94,
    "fulltext": 150, "excluded_fulltext": 53, "included": 97,
}


def _counts_file(tmp_path, counts=None):
    d = tmp_path / "analysis"
    d.mkdir(exist_ok=True)
    f = d / "prisma-counts.json"
    f.write_text(json.dumps({"counts": counts or _COUNTS}), encoding="utf-8")
    return f


def test_two_arm_record_counts_are_not_drift_when_a_flow_is_checked(tmp_path):
    drafts, _ = _project(
        tmp_path,
        {"results.md": "1,572 records were identified. Of 68 Turkish-source records, "
                       "11 full texts were read."},
        None)
    res = cc.check(drafts, tmp_path / "analysis" / "counts.json",
                   tmp_path / "no-registry.jsonl", _counts_file(tmp_path))
    assert res["prisma"]["checked"] is True
    assert [d for d in res["cross_section_drift"] if d["quantity"] == "n_samples"] == []


def test_same_sentences_are_drift_when_no_flow_is_checked(tmp_path):
    # Mutation guard for the line above: without a flow, nothing owns "records"
    # and the drift check must still do its original job.
    drafts, _ = _project(
        tmp_path,
        {"results.md": "1,572 records were identified. Of 68 Turkish-source records, "
                       "11 full texts were read."},
        None)
    res = cc.check(drafts, tmp_path / "analysis" / "counts.json",
                   tmp_path / "no-registry.jsonl", None)
    assert res["prisma"]["checked"] is False
    assert [d for d in res["cross_section_drift"] if d["quantity"] == "n_samples"]


def test_giving_up_records_does_not_disarm_the_other_sample_words(tmp_path):
    drafts, _ = _project(
        tmp_path,
        {"a.md": "The cohort had 500 samples.", "b.md": "The cohort had 400 samples."},
        None)
    res = cc.check(drafts, tmp_path / "analysis" / "counts.json",
                   tmp_path / "no-registry.jsonl", _counts_file(tmp_path))
    assert [d for d in res["cross_section_drift"] if d["quantity"] == "n_samples"]


def test_mismatch_message_names_the_source_it_compared_against(tmp_path):
    # It used to say "the register-derived flow" even when --prisma-counts had
    # been used — a false statement about the check's own basis.
    drafts, _ = _project(
        tmp_path, {"results.md": "text <!-- PRISMA: included=42 -->"}, None)
    counts = _counts_file(tmp_path)
    res = cc.check(drafts, tmp_path / "analysis" / "counts.json",
                   tmp_path / "no-registry.jsonl", counts)
    (m,) = [x for x in res["prisma"]["mismatches"] if x["stage"] == "included"]
    assert "prisma-counts.json" in m["msg"]
    assert "register-derived" not in m["msg"]


# ---------- an HTML comment is not prose ----------


def test_a_number_inside_an_html_comment_is_not_a_narrated_quantity(tmp_path):
    """A revision leaves the old sentence in the file, commented out.

    Four sibling checkers read HTML comments as text until it was fixed; these
    three were never tested either way, and this one did read them. The stale
    number then argued with the manifest as if the author had written it, and
    the only way to silence the warning was to delete a comment that was there
    on purpose.
    """
    drafts, manifest = _project(tmp_path,
        {"bulgular.md": "In total 76 records were screened.\n\n"
                        "<!-- earlier draft: 5110 records were used -->\n"},
        {"n_samples": 76})
    out = cc.check(drafts, manifest)
    assert out["manifest_mismatch"] == []
    assert out["cross_section_drift"] == []


def test_a_prisma_binding_still_works_although_it_is_a_comment(tmp_path):
    """The one comment shape this script must read, and reads before stripping.

    `<!-- PRISMA: not_retrieved=35 -->` is the kit's own binding syntax. If
    comment-stripping ran first, the check that consumes it would go quietly
    blind — the failure mode a fix for false positives most easily creates.
    """
    text = "Otuz beş rapor elde edilemedi. <!-- PRISMA: not_retrieved=35 -->\n"
    (tmp_path / "b.md").write_text(text, encoding="utf-8")
    out = cc.check_prisma_narration([tmp_path / "b.md"], {"not_retrieved": 35})
    assert out["checked"] is True
    assert out["mismatches"] == []
    assert "not_retrieved" in out["bound"]
