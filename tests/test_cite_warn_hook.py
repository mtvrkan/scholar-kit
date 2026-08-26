"""Regression tests for .claude/hooks/cite_warn.py — a PostToolUse hook that
runs cite_audit.py --quick after every Write/Edit to drafts/*.md, surfacing
undefined citation keys / [CITATION NEEDED] tags via stderr + exit 2 (never
blocks; the tool call already completed by the time PostToolUse fires).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"

sys.path.insert(0, str(HOOKS))
import cite_warn  # noqa: E402


def test_is_draft_md_matches_regardless_of_case():
    assert cite_warn._is_draft_md("Drafts/intro.md") is True
    assert cite_warn._is_draft_md("DRAFTS/Intro.MD") is True


def test_is_draft_md_status_exemption_is_case_insensitive():
    assert cite_warn._is_draft_md("Drafts/Status.md") is False
    assert cite_warn._is_draft_md("drafts/STATUS.md") is False


def test_is_draft_md_still_rejects_file_merely_ending_in_status_md():
    assert cite_warn._is_draft_md("drafts/oldSTATUS.md") is True
    assert cite_warn._is_draft_md("Drafts/OldStatus.md") is True


def _run_hook(payload, cwd):
    # See test_phase_gate_hook.py's note: the hook no-ops outside a kit project.
    Path(cwd, "PROJECT.md").touch()
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "cite_warn.py")],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return proc


def _payload(tmp_path, rel):
    return {"tool_name": "Write", "tool_input": {"file_path": rel}, "cwd": str(tmp_path)}


def test_status_md_itself_is_exempt(tmp_path):
    proc = _run_hook(_payload(tmp_path, "drafts/STATUS.md"), tmp_path)
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_status_md_exemption_is_case_insensitive(tmp_path):
    proc = _run_hook(_payload(tmp_path, "drafts/status.md"), tmp_path)
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_file_merely_ending_in_status_md_is_not_exempt(tmp_path):
    # Regression: `norm.endswith("STATUS.md")` wrongly matched "oldSTATUS.md",
    # "resultsSTATUS.md" etc., silently skipping the citation check on a real
    # draft file just because its name happens to end with those characters.
    (tmp_path / "drafts").mkdir(parents=True)
    (tmp_path / "drafts" / "oldSTATUS.md").write_text(
        "Some text with an undefined citation [@nonexistent2020].\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "cite_audit.py").write_text(
        "import sys\nprint('MISSING: nonexistent2020')\nsys.exit(0)\n", encoding="utf-8")
    proc = _run_hook(_payload(tmp_path, "drafts/oldSTATUS.md"), tmp_path)
    # Must NOT be silently exempted — cite_audit.py (our stub) ran and its
    # non-"clean" output was surfaced via exit 2 + stderr.
    assert proc.returncode == 2
    assert "MISSING" in proc.stderr


def test_non_draft_file_not_gated(tmp_path):
    proc = _run_hook(_payload(tmp_path, "PROJECT.md"), tmp_path)
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_non_markdown_file_not_gated(tmp_path):
    proc = _run_hook(_payload(tmp_path, "drafts/notes.txt"), tmp_path)
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_missing_cite_audit_script_exits_clean(tmp_path):
    (tmp_path / "drafts").mkdir(parents=True)
    proc = _run_hook(_payload(tmp_path, "drafts/intro.md"), tmp_path)
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_hook_fails_open_on_garbage_stdin(tmp_path):
    proc = subprocess.run([sys.executable, str(HOOKS / "cite_warn.py")],
                          input="not json", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0


def test_clean_cite_audit_output_does_not_trigger_feedback(tmp_path):
    (tmp_path / "drafts").mkdir(parents=True)
    (tmp_path / "drafts" / "intro.md").write_text("All citations present.\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "cite_audit.py").write_text(
        "print('clean')\n", encoding="utf-8")
    proc = _run_hook(_payload(tmp_path, "drafts/intro.md"), tmp_path)
    assert proc.returncode == 0
    assert proc.stderr == ""


# ---------- Bash surface (independent review, 2026-07-04) ----------
# Regression: this hook used to only fire on tool_name in ("Write", "Edit"),
# so `echo ... > drafts/intro.md` via Bash left a real draft's citations
# completely unchecked — the exact same blind spot phase_gate.py had for its
# outline/verify gates.

def _bash_payload(tmp_path, command):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(tmp_path)}


def test_bash_write_to_drafts_triggers_citation_check(tmp_path):
    (tmp_path / "drafts").mkdir(parents=True)
    (tmp_path / "drafts" / "intro.md").write_text(
        "Some text with an undefined citation [@nonexistent2020].\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "cite_audit.py").write_text(
        "import sys\nprint('MISSING: nonexistent2020')\nsys.exit(0)\n", encoding="utf-8")
    proc = _run_hook(_bash_payload(tmp_path, "echo 'x' > drafts/intro.md"), tmp_path)
    assert proc.returncode == 2
    assert "MISSING" in proc.stderr


def test_bash_write_to_drafts_status_md_still_exempt(tmp_path):
    proc = _run_hook(_bash_payload(tmp_path, "echo 'x' > drafts/STATUS.md"), tmp_path)
    assert proc.returncode == 0
    assert proc.stderr == ""


def test_bash_unrelated_command_not_gated(tmp_path):
    proc = _run_hook(_bash_payload(tmp_path, "pytest tests/ -x -q"), tmp_path)
    assert proc.returncode == 0
    assert proc.stderr == ""
