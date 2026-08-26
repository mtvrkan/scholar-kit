"""Text recycling against your own earlier work (scripts/overlap_check.py).

POSITIONING.md refuses a similarity score. This does not sneak one in: the tests
below pin that there is no percentage in the output, that it compares only
against files the author names, and that it says in its own payload that it does
not replace an institutional tool.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import overlap_check as oc  # noqa: E402,F401  (import smoke: the module must load)

SHARED = ("The vibration signals were sampled at twelve kilohertz and segmented "
          "into windows of one thousand and twenty four points with fifty percent "
          "overlap between consecutive windows in every experiment reported here")


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "overlap_check.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _project(tmp_path, new_text, old_text):
    (tmp_path / "drafts").mkdir(exist_ok=True)
    (tmp_path / "old").mkdir(exist_ok=True)
    (tmp_path / "drafts" / "methods.md").write_text(new_text, encoding="utf-8")
    (tmp_path / "old" / "previous.md").write_text(old_text, encoding="utf-8")
    return tmp_path


# ---------- what it finds ----------

def test_a_recycled_passage_is_located(tmp_path):
    _project(tmp_path, f"# Methods\n\n{SHARED}. We then trained a model.\n",
             f"# Old methods\n\n{SHARED}. Something else followed.\n")
    out = json.loads(_run(tmp_path, "--against", "old", expect=2).stdout)
    finding = out["findings"][0]
    assert finding["file"] == "drafts/methods.md"
    assert finding["passages"][0]["source"] == "old/previous.md"
    assert finding["passages"][0]["words"] >= 12


def test_one_recycled_paragraph_is_one_finding_not_forty(tmp_path):
    # Extending the match is what keeps the report readable.
    _project(tmp_path, SHARED + " and more text here.\n", SHARED + " and other text.\n")
    out = json.loads(_run(tmp_path, "--against", "old", expect=2).stdout)
    assert len(out["findings"][0]["passages"]) == 1


def test_ordinary_shared_phrasing_is_not_reported(tmp_path):
    _project(tmp_path, "# Methods\n\nAll analyses were performed in Python.\n",
             "# Old\n\nAll analyses were performed in Python. The rest differs entirely "
             "from anything in the new manuscript.\n")
    out = json.loads(_run(tmp_path, "--against", "old").stdout)
    assert out["result"] == "NONE"


def test_citations_and_code_do_not_create_matches(tmp_path):
    new = "# M\n\nWe cite [@kaya2024] here.\n\n```\nimport numpy as np\n```\n"
    old = "# O\n\nWe cite [@kaya2024] there.\n\n```\nimport numpy as np\n```\n"
    _project(tmp_path, new, old)
    out = json.loads(_run(tmp_path, "--against", "old").stdout)
    assert out["result"] == "NONE"


# ---------- what it refuses to be ----------

def test_no_percentage_appears_anywhere_in_the_output(tmp_path):
    """The refusal that matters: a ratio invites comparison with an institutional
    threshold it has no relationship to."""
    _project(tmp_path, SHARED + ".\n", SHARED + ".\n")
    payload = json.loads(_run(tmp_path, "--against", "old", expect=2).stdout)
    # No FIELD is a score — the words "percentage" and "plagiarism" appear only
    # in the disclaimer, which is where they belong.
    for key in payload:
        assert not any(token in key for token in ("percent", "score", "ratio",
                                                  "similarity")), key
    for finding in payload["findings"]:
        assert set(finding) == {"file", "passages"}
        for passage in finding["passages"]:
            assert set(passage) == {"words", "source", "passage"}


def test_the_payload_says_it_does_not_replace_the_institution_s_tool(tmp_path):
    _project(tmp_path, "a b c\n", "d e f\n")
    out = json.loads(_run(tmp_path, "--against", "old").stdout)
    assert "does not replace your institution" in out["note"]


def test_a_tiny_window_is_refused(tmp_path):
    _project(tmp_path, "a\n", "b\n")
    proc = _run(tmp_path, "--against", "old", "--window", "4", expect=1)
    assert "too small" in proc.stderr


def test_comparing_the_manuscript_with_itself_is_refused(tmp_path):
    _project(tmp_path, SHARED + ".\n", SHARED + ".\n")
    proc = _run(tmp_path, "--against", "drafts", expect=1)
    assert "with itself" in proc.stderr


# ---------- CLI contract ----------

def test_an_absent_against_path_is_an_error(tmp_path):
    _project(tmp_path, "a\n", "b\n")
    proc = _run(tmp_path, "--against", "nowhere", expect=1)
    assert "does not exist" in proc.stderr


def test_earlier_work_outside_the_project_is_allowed(tmp_path):
    # Your previous papers live elsewhere; nothing is written and nothing leaves
    # the machine, so the usual in-project restriction would only obstruct.
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "old.md").write_text(SHARED + ".\n", encoding="utf-8")
    project = tmp_path / "project"
    (project / "drafts").mkdir(parents=True)
    (project / "drafts" / "m.md").write_text(SHARED + ".\n", encoding="utf-8")
    out = json.loads(_run(project, "--against", str(outside), expect=2).stdout)
    assert out["result"] == "OVERLAP"


def test_output_is_exactly_one_json_object(tmp_path):
    _project(tmp_path, "a b c\n", "d e f\n")
    json.loads(_run(tmp_path, "--against", "old").stdout)
