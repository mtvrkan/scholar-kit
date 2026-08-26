"""Deterministic reading of `/critique --calibrate` (scripts/review_stability.py).

The stability half of --calibrate used to be computed by the model reading its
own three reports. These tests pin the script that replaced that: what counts as
a decision, what counts as an issue, which parts of the draft a Major issue is
taken to point at — and, by name, that a consistently wrong reviewer scores 1.00.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import review_stability as rs  # noqa: E402


def report(decision="Major Revision", major=("Methods: the sample is not described",),
           minor=("Typo in the abstract",)):
    return (
        "## RUBRIC SCORES\n\nNovelty: 3/5\n\n"
        "## MAJOR ISSUES\n\n"
        + "".join(f"{i}. {m}\n" for i, m in enumerate(major, 1))
        + "\n## MINOR ISSUES\n\n"
        + "".join(f"{i}. {m}\n" for i, m in enumerate(minor, 1))
        + f"\n## DECISION\n\n{decision} — the sampling has to be stated.\n")


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "review_stability.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _files(tmp_path, *texts):
    names = []
    for i, text in enumerate(texts, 1):
        p = tmp_path / f"run-{i}.md"
        p.write_text(text, encoding="utf-8")
        names.append(p.name)
    return names


# ---------- the three dimensions ----------

def test_three_identical_reviews_agree_completely(tmp_path):
    out = json.loads(_run(tmp_path, *_files(tmp_path, report(), report(), report())).stdout)
    assert out["decision"]["unanimous"] is True
    assert out["lowest_agreement"] == 1.0


def test_a_split_decision_is_reported_as_the_modal_share(tmp_path):
    out = json.loads(_run(tmp_path, *_files(
        tmp_path, report(), report(), report("Minor Revision"))).stdout)
    assert out["decision"]["modal"] == "Major Revision"
    assert round(out["decision"]["agreement"], 2) == 0.67
    assert out["decision"]["unanimous"] is False


def test_major_revision_is_not_read_as_a_bare_major_or_an_accept(tmp_path):
    # "Major Revision" contains "Major"; "Accept" appears in half the rubrics
    # ever written. Ordering is the whole reason the parse is trustworthy.
    assert rs.decision_in("Major Revision — resubmit") == "Major Revision"
    assert rs.decision_in("Accept with no changes") == "Accept"


def test_the_issue_count_range_is_reported_not_averaged(tmp_path):
    out = json.loads(_run(tmp_path, *_files(
        tmp_path,
        report(major=("Methods: no sample",)),
        report(major=("Methods: no sample", "Results: no CI", "Discussion: overclaims")),
    )).stdout)
    assert out["major_issues"]["per_run"] == [1, 3]
    assert out["major_issues"]["min"] == 1 and out["major_issues"]["max"] == 3


def test_the_sections_the_reviews_disagree_about_are_named(tmp_path):
    out = json.loads(_run(tmp_path, *_files(
        tmp_path,
        report(major=("Methods: no sample description",)),
        report(major=("Methods: no sample description", "Discussion: overclaims")),
    )).stdout)
    assert out["flagged_sections"]["unstable"] == ["discussion"]
    assert out["flagged_sections"]["agreement"] == 0.5


def test_turkish_section_names_map_to_the_same_section(tmp_path):
    out = json.loads(_run(tmp_path, *_files(
        tmp_path,
        report(major=("Yöntem: örneklem tanımlanmamış",)),
        report(major=("Methods: the sample is not described",)),
    )).stdout)
    assert out["flagged_sections"]["agreement"] == 1.0


def test_an_issue_naming_no_section_is_counted_visibly(tmp_path):
    # Dropping it silently would make the section agreement look better than the
    # evidence for it.
    out = json.loads(_run(tmp_path, *_files(
        tmp_path,
        report(major=("The framing is unclear throughout",)),
        report(major=("The framing is unclear throughout",)),
    )).stdout)
    assert out["flagged_sections"]["unattributed_per_run"] == [1, 1]


# ---------- parsing the report format /critique writes ----------

def test_bulleted_issues_count_the_same_as_numbered_ones():
    parsed = rs.read_report("## MAJOR ISSUES\n\n- Methods: a\n- Results: b\n\n"
                            "## DECISION\n\nReject\n")
    assert parsed["major"] == 2 and parsed["decision"] == "Reject"


def test_the_word_reject_inside_an_issue_is_not_the_decision():
    parsed = rs.read_report(
        "## MAJOR ISSUES\n\n1. The paper says reviewers would reject this design\n\n"
        "## DECISION\n\nMinor Revision\n")
    assert parsed["decision"] == "Minor Revision"


def test_a_report_with_no_countable_issues_reports_zero_not_a_guess():
    parsed = rs.read_report("## MAJOR ISSUES\n\nNone.\n\n## DECISION\n\nAccept\n")
    assert parsed["major"] == 0


# ---------- the limit, asserted by name ----------

def test_a_consistently_wrong_reviewer_scores_perfectly():
    """The sentence /critique already prints, now bound to a number: three runs
    agreeing says nothing about whether any of them is right."""
    out = rs.compare([report(), report(), report()])
    assert out["lowest_agreement"] == 1.0
    assert "not accuracy" in out["note"]


# ---------- CLI contract ----------

def test_one_report_is_refused(tmp_path):
    _run(tmp_path, *_files(tmp_path, report()), expect=1)


def test_a_file_that_is_not_a_review_says_so(tmp_path):
    proc = _run(tmp_path, *_files(tmp_path, "# Notes\n\nSome prose.\n",
                                  "# Notes\n\nOther prose.\n"), expect=1)
    assert "DECISION" in proc.stderr


def test_strict_exits_two_below_the_floor(tmp_path):
    _run(tmp_path, "--strict", "--min", "1.0",
         *_files(tmp_path, report(), report("Reject")), expect=2)


def test_output_is_exactly_one_json_object(tmp_path):
    json.loads(_run(tmp_path, *_files(tmp_path, report(), report())).stdout)
