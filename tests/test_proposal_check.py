"""The grant proposal's arithmetic and graph (scripts/proposal_check.py).

A proposal is rejected for two kinds of reason. The first — the idea did not
convince anyone — is untouched here. The second is the one reviewers find every
round and that is entirely mechanical: an objective no work package serves, a
deliverable outside the project's own duration, budget lines that do not sum, and
a personnel figure that does not follow from the person-months.

These tests pin the four, plus the refusal: no call-fields file ⇒ UNCHECKED.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import proposal_check as pc  # noqa: E402

CALL = {"call": "Example 1001", "source_url": "https://example.org/call-2026",
        "read_on": "2026-08-15", "duration_months": 24,
        "fields": [{"name": "summary", "max_words": 300},
                   {"name": "state_of_the_art"},
                   {"name": "method"}]}

WPS = {
    "duration_months": 24,
    "objectives": [{"id": "O1", "text": "Build the model"},
                   {"id": "O2", "text": "Validate on field data"}],
    "workpackages": [
        {"id": "WP1", "title": "Data", "start_month": 1, "end_month": 6,
         "objectives": ["O1"], "person_months": {"researcher": 6},
         "deliverables": [{"id": "D1.1", "title": "Dataset", "month": 6}],
         "milestones": [{"id": "M1", "title": "Data ready", "month": 6}]},
        {"id": "WP2", "title": "Model", "start_month": 5, "end_month": 18,
         "objectives": ["O1", "O2"], "person_months": {"researcher": 12, "pi": 3},
         "deliverables": [{"id": "D2.1", "title": "Trained model", "month": 18}]},
    ],
}

BUDGET = {"currency": "TRY", "total": 400000,
          "lines": [{"item": "Personel", "amount": 300000, "justification": "18 ay araştırmacı"},
                    {"item": "Sarf malzeme", "amount": 100000, "justification": "Sensörler"}],
          "personnel_rate_per_month": {"researcher": 16666.6667, "pi": 0}}

NARRATIVE = """# Proposal

## Summary
A short but real summary of the project.

## State of the art
Prior work is reviewed here.

## Method
The method is described here.
"""


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "proposal_check.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, call=CALL, wps=WPS, budget=BUDGET, narrative=NARRATIVE,
             progress=None):
    (tmp_path / "proposal").mkdir(exist_ok=True)
    for name, obj in (("call-fields.json", call), ("workpackages.json", wps),
                      ("budget.json", budget), ("progress.json", progress)):
        if obj is not None:
            (tmp_path / "proposal" / name).write_text(json.dumps(obj), encoding="utf-8")
    if narrative is not None:
        (tmp_path / "proposal" / "proposal.md").write_text(narrative, encoding="utf-8")
    return tmp_path


# ---------- the objective ↔ work-package graph ----------

def test_an_objective_no_work_package_serves_is_a_finding():
    spec = json.loads(json.dumps(WPS))
    spec["workpackages"][1]["objectives"] = ["O1"]
    result = pc.check_workpackages(spec, 24)
    assert result["orphan_objectives"] == ["O2"]
    assert any("served by no work package" in p for p in result["problems"])


def test_a_work_package_serving_no_objective_is_a_finding():
    spec = json.loads(json.dumps(WPS))
    spec["workpackages"][0]["objectives"] = []
    result = pc.check_workpackages(spec, 24)
    assert any("serves no objective" in p for p in result["problems"])


def test_a_work_package_with_no_deliverable_cannot_be_reported_on():
    spec = json.loads(json.dumps(WPS))
    spec["workpackages"][0]["deliverables"] = []
    result = pc.check_workpackages(spec, 24)
    assert any("no deliverable" in p for p in result["problems"])


def test_a_zero_person_month_work_package_is_a_finding():
    spec = json.loads(json.dumps(WPS))
    spec["workpackages"][0]["person_months"] = {"researcher": 0}
    result = pc.check_workpackages(spec, 24)
    assert any("zero person-months" in p for p in result["problems"])


def test_an_unknown_objective_reference_is_named():
    spec = json.loads(json.dumps(WPS))
    spec["workpackages"][0]["objectives"] = ["O9"]
    result = pc.check_workpackages(spec, 24)
    assert any("unknown objective" in p for p in result["problems"])


# ---------- the calendar ----------

def test_a_deliverable_past_the_projects_own_duration_is_a_finding():
    spec = json.loads(json.dumps(WPS))
    spec["workpackages"][1]["end_month"] = 30
    spec["workpackages"][1]["deliverables"][0]["month"] = 30
    result = pc.check_workpackages(spec, 24)
    assert any("the project lasts 24 months" in p for p in result["problems"])
    assert any("outside the project's 24 months" in p for p in result["problems"])


def test_a_deliverable_outside_its_own_work_packages_months_is_a_finding():
    spec = json.loads(json.dumps(WPS))
    spec["workpackages"][0]["deliverables"][0]["month"] = 12
    result = pc.check_workpackages(spec, 24)
    assert any("outside WP1's months 1-6" in p for p in result["problems"])


def test_a_work_package_that_ends_before_it_starts_is_a_finding():
    spec = json.loads(json.dumps(WPS))
    spec["workpackages"][0]["start_month"] = 9
    result = pc.check_workpackages(spec, 24)
    assert any("starts in month 9 and ends in month 6" in p for p in result["problems"])


def test_repeated_deliverable_ids_are_a_finding():
    spec = json.loads(json.dumps(WPS))
    spec["workpackages"][1]["deliverables"][0]["id"] = "D1.1"
    result = pc.check_workpackages(spec, 24)
    assert any("ids repeated: ['D1.1']" in p for p in result["problems"])


# ---------- the budget ----------

def test_budget_lines_that_do_not_sum_to_the_total_are_a_finding():
    result = pc.check_budget(dict(BUDGET, total=450000), 21)
    assert any("difference 50000" in p for p in result["problems"])


def test_an_unjustified_budget_line_is_the_first_one_cut():
    budget = json.loads(json.dumps(BUDGET))
    budget["lines"][1]["justification"] = ""
    result = pc.check_budget(budget, 21)
    assert any("no justification" in p for p in result["problems"])


def test_the_personnel_line_is_checked_against_the_person_months():
    """The inconsistency reviewers reliably find: two numbers describing
    different projects."""
    budget = json.loads(json.dumps(BUDGET))
    budget["lines"][0]["amount"] = 120000
    result = pc.personnel_consistency(WPS, budget)
    assert result["checked"] is True
    assert any("describing a different project" in p for p in result["problems"])


def test_person_months_at_the_stated_rates_reconcile_when_they_agree():
    result = pc.personnel_consistency(WPS, BUDGET)
    assert result["problems"] == []
    assert result["person_months_by_role"] == {"researcher": 18, "pi": 3}


def test_a_role_with_no_rate_is_named_rather_than_priced():
    budget = json.loads(json.dumps(BUDGET))
    del budget["personnel_rate_per_month"]["pi"]
    result = pc.personnel_consistency(WPS, budget)
    assert result["roles_with_no_rate"] == ["pi"]


def test_no_rates_at_all_means_the_check_did_not_run(tmp_path):
    budget = json.loads(json.dumps(BUDGET))
    del budget["personnel_rate_per_month"]
    result = pc.personnel_consistency(WPS, budget)
    assert result["checked"] is False
    assert "not assumed" in result["why"]


# ---------- the narrative against the call ----------

def test_a_section_over_the_calls_word_limit_is_a_finding():
    call = json.loads(json.dumps(CALL))
    call["fields"][0]["max_words"] = 3
    result = pc.check_narrative(NARRATIVE, call)
    assert any("the call allows 3" in p for p in result["problems"])


def test_a_missing_section_is_named():
    result = pc.check_narrative(NARRATIVE.split("## Method")[0], CALL)
    assert any("no section for 'method'" in p for p in result["problems"])


def test_a_placeholder_left_in_a_section_is_a_finding():
    result = pc.check_narrative(NARRATIVE.replace("The method is described here.",
                                                  "<TODO>"), CALL)
    assert any("still holds a placeholder" in p for p in result["problems"])


# ---------- the refusal ----------

def test_no_call_fields_file_reports_unchecked_not_ok(tmp_path):
    report = json.loads(_run(_project(tmp_path, call=None), "--check", expect=2).stdout)
    assert report["result"] == "UNCHECKED"
    assert "will not recall a funder's limits" in report["note"]


def test_a_call_fields_file_with_no_source_is_refused(tmp_path):
    project = _project(tmp_path, call={"fields": ["summary"], "duration_months": 24})
    proc = subprocess.run([sys.executable, str(SCRIPTS / "proposal_check.py"), "--check"],
                          cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "source_url" in proc.stderr


# ---------- Gantt ----------

def test_the_markdown_gantt_marks_each_work_packages_months(tmp_path):
    out = _run(_project(tmp_path), "--gantt", "markdown").stdout
    assert "| WP1 | Data |" in out
    wp1 = next(line for line in out.splitlines() if line.startswith("| WP1"))
    assert wp1.count("█") == 6


def test_the_latex_gantt_declares_the_package_it_needs(tmp_path):
    out = _run(_project(tmp_path), "--gantt", "latex").stdout
    assert "pgfgantt" in out
    assert "\\ganttbar{WP1: Data}{1}{6}" in out


# ---------- the report ----------

def test_an_unreported_deliverable_is_not_reported_never_complete(tmp_path):
    report = json.loads(_run(_project(tmp_path), "--report", expect=2).stdout)
    ids = [d["id"] for d in report["deliverables"]]
    assert ids == ["D1.1", "D2.1"]
    assert any("'not reported' is not 'complete'" in p for p in report["problems"])


def test_slippage_is_stated_and_not_explained(tmp_path):
    progress = {"deliverables": {"D1.1": {"month": 9, "evidence": "analysis/data/"},
                                 "D2.1": {"month": 18}}}
    report = json.loads(_run(_project(tmp_path, progress=progress), "--report").stdout)
    d11 = next(d for d in report["deliverables"] if d["id"] == "D1.1")
    assert d11["slippage_months"] == 3
    assert "No reason is written for a gap" in report["note"]


def test_the_report_derives_what_the_registers_hold(tmp_path):
    project = _project(tmp_path, progress={"deliverables": {"D1.1": {"month": 6},
                                                            "D2.1": {"month": 18}}})
    (project / "analysis").mkdir(exist_ok=True)
    (project / "analysis" / "runs.jsonl").write_text(
        '{"id": "RUN-0001"}\n{"id": "RUN-0002"}\n', encoding="utf-8")
    report = json.loads(_run(project, "--report").stdout)
    assert report["derived_from_registers"]["runs_recorded"] == 2


# ---------- end to end ----------

def test_a_consistent_proposal_passes(tmp_path):
    report = json.loads(_run(_project(tmp_path), "--check").stdout)
    assert report["result"] == "OK", report["problems"]
    assert report["workpackages"]["total_person_months"] == 21
