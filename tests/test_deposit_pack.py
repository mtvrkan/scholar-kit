"""The preprint deposit and the correction (scripts/deposit_pack.py).

The preprint half pins the refusal: no server's character limit is recalled, and
the licence/category/policy questions are surfaced as questions rather than
answered — a posted licence is effectively irreversible.

The corrigendum half pins the thing that is actually hard about a correction:
not the letter, but the list of everywhere else the wrong number went — drafts,
figures named beside it, run records, evidence cards.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import deposit_pack as dp  # noqa: E402

LIMITS = {"server": "arXiv", "source_url": "https://info.arxiv.org/help/",
          "read_on": "2026-08-15", "abstract_max_chars": 1920,
          "title_max_chars": 240, "categories": ["eess.SP", "cs.LG"]}

ERROR = {"source_url": "https://doi.org/10.1234/published",
         "wrong_value": 0.91, "correct_value": 0.87,
         "what_happened": "the held-out split was reported before the leakage fix"}

DRAFT_RESULTS = """# Results

The model reaches 0.91 F1 on the held-out split (Table 2).

Figure 3 shows the same 0.91 across seeds.

The baseline reaches 0.75.
"""

RUNS = [{"id": "RUN-0007", "dataset": "DS-0001", "seed": 1, "metrics": {"f1": 0.91}},
        {"id": "RUN-0008", "dataset": "DS-0001", "seed": 2, "metrics": {"f1": 0.75}}]

CARDS = [{"id": "EV-0090", "type": "own-result", "claim": "F1 reaches 0.91",
          "metrics": {"F1": 0.91}}]


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "deposit_pack.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, limits=LIMITS, error=ERROR, abstract="A short abstract.\n",
             results=DRAFT_RESULTS, runs=RUNS, cards=CARDS):
    (tmp_path / "drafts").mkdir(exist_ok=True)
    (tmp_path / "analysis").mkdir(exist_ok=True)
    (tmp_path / "evidence").mkdir(exist_ok=True)
    (tmp_path / "exports" / "deposit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "PROJECT.md").write_text("**Title (working):** A short title\n",
                                         encoding="utf-8")
    (tmp_path / "drafts" / "abstract.md").write_text(
        abstract + "\nKeywords: a, b, c, d\n", encoding="utf-8")
    (tmp_path / "drafts" / "results.md").write_text(results, encoding="utf-8")
    (tmp_path / "analysis" / "runs.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    (tmp_path / "evidence" / "cards.jsonl").write_text(
        "".join(json.dumps(c) + "\n" for c in cards), encoding="utf-8")
    if limits is not None:
        (tmp_path / "exports" / "deposit" / "server-limits.json").write_text(
            json.dumps(limits), encoding="utf-8")
    if error is not None:
        (tmp_path / "exports" / "deposit" / "erratum.json").write_text(
            json.dumps(error), encoding="utf-8")
    return tmp_path


# ---------- preprint ----------

def test_the_licence_and_policy_questions_are_asked_never_answered(tmp_path):
    report = json.loads(_run(_project(tmp_path), "--preprint", "arxiv", expect=2).stdout)
    keys = [q["key"] for q in report["open_questions"]]
    assert "licence" in keys and "target_journal_policy" in keys
    policy = next(q for q in report["open_questions"] if q["key"] == "target_journal_policy")
    assert "not recalled here" in policy["question"]
    assert policy["answer"] is None


def test_undecided_questions_are_findings_not_a_printed_list(tmp_path):
    """Printing the five and exiting 0 made an undecided deposit read the same
    as a checked one."""
    report = json.loads(_run(_project(tmp_path), "--preprint", "arxiv", expect=2).stdout)
    assert set(report["undecided"]) == {q["key"] for q in report["open_questions"]}
    assert any("irreversible" in p for p in report["problems"])


def test_recording_the_decisions_clears_them(tmp_path):
    decided = dict(LIMITS, decisions={
        "target_journal_policy": "Elsevier permits the submitted version",
        "licence": "CC-BY-4.0", "category": "eess.SP",
        "version_posted": "submitted manuscript", "coauthor_consent": "yes, 2026-08-15"})
    report = json.loads(_run(_project(tmp_path, limits=decided),
                             "--preprint", "arxiv").stdout)
    assert report["result"] == "OK"
    assert report["undecided"] == []


def test_no_server_limits_file_reports_unchecked_not_ok(tmp_path):
    report = json.loads(_run(_project(tmp_path, limits=None), "--preprint", "arxiv",
                             expect=2).stdout)
    assert report["result"] == "UNCHECKED"
    assert "will not recall a character limit" in report["note"]
    assert report["measured"]["abstract_chars"] > 0  # measured, just not checked


def test_an_abstract_over_the_servers_own_limit_is_a_finding(tmp_path):
    project = _project(tmp_path, limits=dict(LIMITS, abstract_max_chars=10))
    report = json.loads(_run(project, "--preprint", "arxiv", expect=2).stdout)
    assert report["checked"]["abstract_chars"]["over"] is True
    assert any("arXiv allows 10" in p for p in report["problems"])


def test_the_disclosure_sentence_is_produced_with_visible_blanks(tmp_path):
    report = json.loads(_run(_project(tmp_path), "--preprint", "arxiv", expect=2).stdout)
    assert report["disclosure_sentence"]
    assert "<server>" in report["disclosure_sentence"]
    assert "<licence>" in report["disclosure_sentence"]


def test_a_limits_file_with_no_source_is_refused(tmp_path):
    project = _project(tmp_path, limits={"abstract_max_chars": 1920})
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "deposit_pack.py"), "--preprint", "arxiv"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "source_url" in proc.stderr


# ---------- corrigendum ----------

def test_the_correction_finds_every_place_the_wrong_number_went(tmp_path):
    report = json.loads(_run(_project(tmp_path), "--corrigendum", expect=2).stdout)
    assert len(report["found_in_drafts"]) == 2
    assert sorted(report["artefacts_named_nearby"]) == ["Figure 3", "Table 2"]
    assert [r["run"] for r in report["run_records"]] == ["RUN-0007"]
    assert [c["id"] for c in report["evidence_cards"]] == ["EV-0090"]


def test_a_run_record_holding_the_wrong_value_is_its_own_finding(tmp_path):
    report = json.loads(_run(_project(tmp_path), "--corrigendum", expect=2).stdout)
    assert any("replication package disagree" in p for p in report["problems"])


def test_the_value_is_matched_across_decimal_conventions(tmp_path):
    project = _project(tmp_path, results="# Bulgular\n\nModel 0,91 F1'e ulaşır.\n",
                       runs=[], cards=[])
    report = json.loads(_run(project, "--corrigendum", expect=0).stdout)
    assert len(report["found_in_drafts"]) == 1


def test_a_value_that_appears_nowhere_is_reported_rather_than_assumed(tmp_path):
    project = _project(tmp_path, error=dict(ERROR, wrong_value=0.42), runs=[], cards=[])
    report = json.loads(_run(project, "--corrigendum", expect=2).stdout)
    assert report["found_in_drafts"] == []
    assert any("was not found" in p for p in report["problems"])


def test_the_letter_skeleton_asks_what_does_not_change(tmp_path):
    """A reader's first question is whether the conclusion survives."""
    report = json.loads(_run(_project(tmp_path), "--corrigendum", expect=2).stdout)
    assert any("does NOT change" in step for step in report["letter_skeleton"])
    assert any("Who found it" in step for step in report["letter_skeleton"])


def test_the_script_does_not_decide_between_corrigendum_and_retraction(tmp_path):
    report = json.loads(_run(_project(tmp_path), "--corrigendum", expect=2).stdout)
    assert "between the authors and the editor" in report["note"]


def test_a_missing_erratum_file_names_the_shape_it_wants(tmp_path):
    project = _project(tmp_path, error=None)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "deposit_pack.py"), "--corrigendum"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "wrong_value" in proc.stderr and "what_happened" in proc.stderr


def test_a_non_numeric_correction_is_handed_back(tmp_path):
    project = _project(tmp_path, error=dict(ERROR, wrong_value="the wrong citation"))
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "deposit_pack.py"), "--corrigendum"],
        cwd=project, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "write the letter by hand" in proc.stderr


# ---------- mode selection ----------

def test_exactly_one_mode_is_required(tmp_path):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "deposit_pack.py")],
                          cwd=_project(tmp_path), capture_output=True, text=True,
                          encoding="utf-8")
    assert proc.returncode == 1
    assert "pick exactly one" in proc.stderr


def test_the_open_questions_list_is_stable_and_covers_the_five(tmp_path):
    assert len(dp.OPEN_QUESTIONS) == 5
    assert {k for k, _ in dp.OPEN_QUESTIONS} == {
        "target_journal_policy", "licence", "category", "version_posted",
        "coauthor_consent"}
