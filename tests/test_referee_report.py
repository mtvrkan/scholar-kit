"""Refereeing, built as a refusal (scripts/referee_report.py).

The first test is the load-bearing one: pointed at a manuscript, the script
stops. A paper sent to you for review arrives under a confidentiality
undertaking, and a tool with an override flag for that is a tool whose refusal is
decoration.

The rest pin what CAN be checked without the paper — numbering, anchoring, the
journal's own recommendation set, and the phrases with which an anonymous
referee accidentally signs the report.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import referee_report as rr  # noqa: E402

FORM = {"journal": "Example Transactions",
        "source_url": "https://example.org/reviewer-guidelines",
        "read_on": "2026-08-15",
        "recommendations": ["Accept", "Minor revision", "Major revision", "Reject"],
        "max_words": 1200}

GOOD = """# Referee report — MS-2026-0417

## Summary
The paper proposes a convolutional model for bearing fault diagnosis and
evaluates it on two public datasets.

## Significance
The question matters and the evaluation is broader than most prior work.

## Major comments
1. (Section 3.2) The train/test split is described as random, but the recordings
   come from the same bearings; a group-aware split is needed.
2. (Table 2) Baselines are reported without variance across seeds.

## Minor comments
1. (line 145) The acronym SNR is used before it is defined.

## Confidential comments to the editor
The overlap with the authors' conference paper should be checked.

## Recommendation
Major revision
"""


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "referee_report.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, report=GOOD, form=FORM):
    (tmp_path / "reviews" / "referee").mkdir(parents=True, exist_ok=True)
    if report is not None:
        (tmp_path / "reviews" / "referee" / "report.md").write_text(report, encoding="utf-8")
    if form is not None:
        (tmp_path / "reviews" / "referee" / "review-form.json").write_text(
            json.dumps(form), encoding="utf-8")
    return tmp_path


# ---------- the refusal ----------

def test_pointing_it_at_the_manuscript_stops_the_run(tmp_path):
    project = _project(tmp_path, report=None)
    (project / "reviews" / "referee" / "submitted.pdf").write_bytes(b"%PDF-1.4\n")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "referee_report.py"),
         "--check", "reviews/referee/submitted.pdf"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "confidentiality undertaking" in proc.stderr
    assert "no flag that overrides" in proc.stderr


def test_every_manuscript_format_is_refused_by_extension(tmp_path):
    """Refused before the file is opened — a check that happens after the read
    is not a check."""
    project = _project(tmp_path, report=None)
    for suffix in (".pdf", ".docx", ".doc", ".tex", ".odt", ".rtf"):
        target = project / "reviews" / "referee" / f"ms{suffix}"
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "referee_report.py"),
             "--check", target.relative_to(project).as_posix()],
            cwd=project, capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 1, suffix
        assert "manuscript" in proc.stderr, suffix
        assert not target.exists(), f"{suffix} was created rather than refused"


# ---------- what can be checked without the paper ----------

def test_a_major_comment_with_no_place_in_the_paper_is_a_finding():
    report = GOOD.replace("(Section 3.2) The train/test split",
                          "The train/test split")
    result = rr.check_report(report, FORM)
    assert result["major"]["unanchored"] == [1]
    assert any("name no place" in p for p in result["problems"])


def test_bulleted_comments_are_reported_because_nobody_can_answer_them():
    report = GOOD.replace("1. (Section 3.2)", "- (Section 3.2)")
    result = rr.check_report(report, FORM)
    assert result["major"]["as_bullets"] == 1
    assert any("bullets" in p for p in result["problems"])


def test_broken_numbering_is_reported():
    report = GOOD.replace("2. (Table 2)", "3. (Table 2)")
    result = rr.check_report(report, FORM)
    assert any("numbering is [1, 3]" in p for p in result["problems"])


def test_a_recommendation_outside_the_journals_options_is_a_finding():
    report = GOOD.replace("Major revision", "Revise and resubmit")
    result = rr.check_report(report, FORM)
    assert result["recommendation_valid"] is False
    assert any("not one of the journal's options" in p for p in result["problems"])


def test_a_report_over_the_forms_word_limit_is_a_finding():
    result = rr.check_report(GOOD, dict(FORM, max_words=20))
    assert any("the form allows 20" in p for p in result["problems"])


def test_a_missing_section_is_named():
    report = GOOD.split("## Recommendation")[0]
    result = rr.check_report(report, FORM)
    assert "recommendation" in result["sections_missing"]


# ---------- the signature nobody meant to leave ----------

def test_pointing_at_your_own_work_in_the_first_person_is_flagged():
    report = GOOD.replace("a group-aware split is needed.",
                          "a group-aware split is needed, as we showed in our previous work.")
    result = rr.check_report(report, FORM)
    assert result["self_identification"]
    assert any("signed" in p for p in result["problems"])


def test_the_turkish_form_of_the_same_signature_is_flagged():
    report = GOOD.replace("The question matters",
                          "Kendi çalışmamızda gösterdiğimiz gibi, soru önemlidir")
    result = rr.check_report(report, FORM)
    assert result["self_identification"]


def test_citing_work_impersonally_is_not_flagged():
    """Recommending a paper is normal refereeing; recommending YOUR paper in the
    first person is the signature."""
    report = GOOD.replace("a group-aware split is needed.",
                          "a group-aware split is needed (see Zhang et al., 2024).")
    result = rr.check_report(report, FORM)
    assert result["self_identification"] == []


# ---------- the authority file ----------

def test_no_review_form_reports_unchecked_not_ok(tmp_path):
    proc = _run(_project(tmp_path, form=None), "--check", "reviews/referee/report.md",
                expect=2)
    result = json.loads(proc.stdout)
    assert result["result"] == "UNCHECKED"
    assert "NOT checked" in result["form_note"]


def test_a_review_form_with_no_source_is_refused(tmp_path):
    project = _project(tmp_path, form={"recommendations": ["Accept"]})
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "referee_report.py"),
         "--check", "reviews/referee/report.md"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "source_url" in proc.stderr


# ---------- scaffold and end to end ----------

def test_scaffold_writes_headings_and_refuses_to_overwrite(tmp_path):
    project = _project(tmp_path, report=None)
    _run(project, "--scaffold", "reviews/referee/report.md")
    text = (project / "reviews" / "referee" / "report.md").read_text(encoding="utf-8")
    assert "## Major comments" in text
    assert "confidentiality undertaking" in text
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "referee_report.py"),
         "--scaffold", "reviews/referee/report.md"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "refusing to overwrite" in proc.stderr


def test_a_complete_report_passes(tmp_path):
    result = json.loads(_run(_project(tmp_path), "--check",
                             "reviews/referee/report.md").stdout)
    assert result["result"] == "OK", result["problems"]
    assert result["recommendation"] == "Major revision"
    assert result["confidential_to_editor"]["present"] is True
