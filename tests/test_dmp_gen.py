"""The Data Management Plan (scripts/dmp_gen.py), derived rather than templated.

What these pin is the refusal, because that is the whole difference between this
and a downloaded template: FAIR is reported letter by letter with the record that
evidences it, and a dataset with no verified licence or no citation DOI gets no
sentence written for it at all.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import dmp_gen as dg  # noqa: E402

COMPLETE = {
    "id": "DS-0001", "name": "cwru-bearing", "source": "uci", "version": "1.2",
    "license": "CC-BY-4.0", "license_verified": True,
    "citation": {"doi": "10.1234/abcd"},
    "url": "https://example.org/cwru",
    "files": [{"path": "analysis/data/a.csv", "sha256": "ab" * 32, "bytes": 2048}],
}

NO_DOI = dict(COMPLETE, id="DS-0002", name="local-vib", citation={})
PROPRIETARY = dict(COMPLETE, id="DS-0003", name="lab-runs",
                   files=[{"path": "analysis/data/x.mat", "sha256": "cd" * 32}])
OWN_SURVEY = dict(COMPLETE, id="DS-0004", name="student-survey", source="own-survey")


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "dmp_gen.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, datasets=(COMPLETE,), runs=()):
    (tmp_path / "analysis").mkdir(exist_ok=True)
    (tmp_path / "analysis" / "datasets.jsonl").write_text(
        "".join(json.dumps(d) + "\n" for d in datasets), encoding="utf-8")
    (tmp_path / "analysis" / "runs.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in runs), encoding="utf-8")
    return tmp_path


# ---------- FAIR, letter by letter ----------

def test_a_complete_record_evidences_all_four_letters():
    fair = dg.fair_for(COMPLETE)
    assert all(state["evidenced"] for state in fair.values())
    assert "10.1234/abcd" in fair["F"]["because"]


def test_a_missing_doi_leaves_findable_unevidenced_and_says_how_to_fix_it():
    fair = dg.fair_for(NO_DOI)
    assert fair["F"]["evidenced"] is False
    assert "dataset_db.py" in fair["F"]["because"]
    assert fair["A"]["evidenced"] is True  # the other letters are independent


def test_a_proprietary_format_is_what_decides_interoperability():
    fair = dg.fair_for(PROPRIETARY)
    assert fair["I"]["evidenced"] is False
    assert ".mat" in fair["I"]["because"]


def test_an_unverified_licence_blocks_accessible_and_reusable():
    fair = dg.fair_for(dict(COMPLETE, license_verified=False))
    assert fair["A"]["evidenced"] is False
    assert fair["R"]["evidenced"] is False
    assert fair["F"]["evidenced"] is True


# ---------- the refusal ----------

def test_no_sentence_is_written_for_a_dataset_missing_its_doi():
    report = dg.build([NO_DOI], [], dg.CORE_SECTIONS, False)
    assert report["availability_sentences"] == []
    assert report["no_sentence_written_for"][0]["dataset"] == "local-vib"
    assert "citation DOI" in report["no_sentence_written_for"][0]["missing"]


def test_the_rendered_plan_names_the_gap_rather_than_hiding_it():
    md = dg.render_markdown(dg.build([NO_DOI], [], dg.CORE_SECTIONS, False))
    assert "Datasets no sentence was written for" in md
    assert "local-vib" in md


def test_the_plan_never_claims_the_project_follows_fair_principles():
    md = dg.render_markdown(dg.build([COMPLETE], [], dg.CORE_SECTIONS, False))
    assert "follows FAIR" not in md
    assert "FAIR-compliant" not in md
    assert "evidenced" in md


def test_own_collected_data_is_named_as_not_redistributable():
    summary = dg.summarise_dataset(OWN_SURVEY)
    assert summary["redistributable"] is False
    sentence = dg._sentence(summary)
    assert "not redistributable" in sentence
    assert "access is by application" in sentence


def test_resource_and_storage_sections_carry_blanks_rather_than_invented_costs():
    report = dg.build([COMPLETE], [], dg.CORE_SECTIONS, False)
    blanks = report["body"]["resources"]["blank"]
    assert any("cost" in b for b in blanks)
    md = dg.render_markdown(report)
    assert "TODO:" in md


# ---------- the funder's own section list ----------

def test_a_funder_section_list_replaces_the_generic_core(tmp_path):
    project = _project(tmp_path)
    (project / "sections.json").write_text(
        json.dumps({"sections": ["data_summary", "our_funder_specific_question"]}),
        encoding="utf-8")
    report = json.loads(_run(project, "--sections", "sections.json", expect=0).stdout)
    assert report["sections"] == ["data_summary", "our_funder_specific_question"]
    unknown = report["body"]["our_funder_specific_question"]
    assert "answer it yourself" in unknown["blank"][0]


def test_a_missing_sections_file_is_an_error_not_a_silent_fallback(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "dmp_gen.py"), "--sections", "nope.json"],
        cwd=_project(tmp_path), capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "does not exist" in proc.stderr


# ---------- end to end ----------

def test_a_complete_register_writes_a_plan_and_exits_clean(tmp_path):
    project = _project(tmp_path)
    proc = _run(project, "--write", "dmp.md", expect=0)
    report = json.loads(proc.stdout)
    assert report["result"] == "OK"
    md = (project / "dmp.md").read_text(encoding="utf-8")
    assert "10.1234/abcd" in md
    assert "CC-BY-4.0" in md


def test_check_mode_reports_only_the_gaps(tmp_path):
    proc = _run(_project(tmp_path, datasets=(COMPLETE, NO_DOI)), "--check", expect=2)
    report = json.loads(proc.stdout)
    assert report["result"] == "GAPS"
    assert report["unevidenced_by_dataset"] == {"local-vib": ["F"]}
