"""Regression tests for .claude/hooks/session_status.py — a SessionStart hook
that prints the first 15 lines of drafts/STATUS.md so every new session
resumes with project context. Previously had no test coverage.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"


def _run_hook(payload, cwd):
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "session_status.py")],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return proc


def test_prints_status_md_when_present(tmp_path):
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "STATUS.md").write_text(
        "# Status\nIntro: drafted\nMethods: pending\n", encoding="utf-8")
    proc = _run_hook({"cwd": str(tmp_path)}, tmp_path)
    assert proc.returncode == 0
    assert "Intro: drafted" in proc.stdout
    assert "scholar-kit STATUS" in proc.stdout


def test_silent_when_no_status_md(tmp_path):
    proc = _run_hook({"cwd": str(tmp_path)}, tmp_path)
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_truncates_to_first_15_lines(tmp_path):
    (tmp_path / "drafts").mkdir()
    lines = [f"line {i}" for i in range(30)]
    (tmp_path / "drafts" / "STATUS.md").write_text("\n".join(lines), encoding="utf-8")
    proc = _run_hook({"cwd": str(tmp_path)}, tmp_path)
    assert "line 14" in proc.stdout
    assert "line 15" not in proc.stdout


def test_fails_open_on_garbage_stdin(tmp_path):
    proc = subprocess.run([sys.executable, str(HOOKS / "session_status.py")],
                          input="not json", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0


def test_uses_payload_cwd_not_process_cwd(tmp_path):
    other = tmp_path / "other_project"
    (other / "drafts").mkdir(parents=True)
    (other / "drafts" / "STATUS.md").write_text("From other project\n", encoding="utf-8")
    # Run with the *process* cwd set to tmp_path (no STATUS.md there) but the
    # payload's "cwd" field pointing at `other` — the hook must honor the
    # payload's cwd, matching cite_warn.py/phase_gate.py's convention.
    proc = _run_hook({"cwd": str(other)}, tmp_path)
    assert proc.returncode == 0
    assert "From other project" in proc.stdout
