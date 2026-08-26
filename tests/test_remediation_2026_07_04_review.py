"""Regression tests for the independent review on 2026-07-04 (4 fresh agents:
security/hooks, script correctness, skill/agent consistency, docs/test quality —
see DECISIONS.md for the corresponding D-0xx entries). Covers gaps none of the
prior review passes caught: a `set -u` crash in latex_build.sh, a non-string
hook `command` value crashing patch_hook_interpreter.py, and validate_kit.py
not detecting an unresolvable hook interpreter (the exact fail-open failure
mode D-017/D-027/D-041 warn about).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import validate_kit  # noqa: E402


def _bash_runs(bash: str) -> bool:
    """Whether that bash can execute anything — a partial Git for Windows
    install leaves `bin\\bash.exe` on disk with an empty `usr\\bin\\` behind it,
    and an existence check calls that a working shell."""
    try:
        return subprocess.run([bash, "-c", "exit 0"],
                              capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _find_git_bash() -> str:
    """Plain "bash" on this Windows box resolves to the WSL launcher shim in
    System32 (which fails with no WSL distro installed) before Git Bash gets
    a chance — locate the real Git Bash explicitly, same one the dev
    environment's Bash tool uses."""
    for cand in (r"C:\Program Files\Git\bin\bash.exe",
                 r"C:\Program Files\Git\usr\bin\bash.exe",
                 shutil.which("bash")):
        if cand and Path(cand).exists() and _bash_runs(cand):
            return cand
    pytest.skip("no working bash executable available")


# ---------- latex_build.sh: must not crash under `set -u` without LOCALAPPDATA ----------

def test_latex_build_blocked_message_not_unbound_variable_crash(tmp_path):
    """Regression: the winget-MiKTeX PATH probe referenced a bare $LOCALAPPDATA
    (Windows-only env var) inside a `set -u` script. On any host where it's
    unset — every macOS/Linux box, and this test's own sandboxed env — bash
    aborted with 'LOCALAPPDATA: unbound variable' instead of the intended
    friendly 'BLOCKED: latexmk not installed' message."""
    bash = _find_git_bash() if sys.platform == "win32" else "bash"
    main_tex = tmp_path / "main.tex"
    main_tex.write_text(r"\documentclass{article}\begin{document}x\end{document}",
                        encoding="utf-8")

    env = dict(os.environ)
    env.pop("LOCALAPPDATA", None)
    # Force the "latexmk not found" branch regardless of what's installed on
    # the machine running this test, without stripping unrelated PATH entries
    # (basename/dirname/mkdir must still resolve).
    env["PATH"] = os.pathsep.join(
        p for p in env.get("PATH", "").split(os.pathsep) if "miktex" not in p.lower())

    proc = subprocess.run(
        [bash, "scripts/latex_build.sh", str(main_tex), str(tmp_path / "build")],
        cwd=ROOT, capture_output=True, text=True, env=env)

    assert "unbound variable" not in proc.stderr, proc.stderr
    assert proc.returncode == 3, (proc.returncode, proc.stdout, proc.stderr)
    assert "BLOCKED" in proc.stdout


# ---------- patch_hook_interpreter.py: a non-string command must not crash ----------

def test_patch_hook_interpreter_ignores_non_string_command(run, tmp_path):
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()
    settings_path = settings_dir / "settings.json"
    settings_path.write_text(json.dumps({
        "hooks": {"PreToolUse": [{"hooks": [
            {"command": None},
            {"command": "python3 hooks/foo.py"},
        ]}]}
    }, indent=2) + "\n", encoding="utf-8")

    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                          "--settings", ".claude/settings.json")
    assert code == 0, err
    rep = json.loads(out)
    assert rep["changed"] is True
    cfg = json.loads(settings_path.read_text(encoding="utf-8"))
    hooks = cfg["hooks"]["PreToolUse"][0]["hooks"]
    assert hooks[0]["command"] is None  # untouched, not crashed
    assert hooks[1]["command"] == "python hooks/foo.py"


# ---------- validate_kit.py: unresolvable hook interpreter must be flagged ----------

def test_validate_kit_flags_unresolvable_hook_interpreter(tmp_path, monkeypatch, capsys):
    # validate_kit.ROOT is computed from its own __file__, not CWD, so a
    # subprocess `run` fixture invocation can't be redirected to a sandboxed
    # settings.json — monkeypatch the module constant directly instead.
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [{"hooks": [
            {"command": "python3 hooks/foo.py"},
        ]}]}
    }, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setattr(validate_kit, "ROOT", tmp_path)
    monkeypatch.setattr(validate_kit.shutil, "which", lambda cmd: None)
    monkeypatch.setattr(sys, "argv", ["validate_kit.py", "--json"])
    with pytest.raises(SystemExit):
        validate_kit.main()

    # Not filtering out the many other "missing" problems a bare sandbox kit
    # produces — just confirming THIS problem class is among them.
    rep = json.loads(capsys.readouterr().out)
    assert any("interpreter" in p and "not found on PATH" in p for p in rep["problems"]), rep


def test_validate_kit_real_kit_hook_interpreters_resolve():
    """The kit's own committed settings.json must reference an interpreter
    that's actually resolvable — otherwise every hook fails open silently."""
    proc = subprocess.run([sys.executable, "scripts/validate_kit.py", "--json"],
                          cwd=ROOT, capture_output=True, text=True)
    rep = json.loads(proc.stdout)
    assert not any("interpreter" in p and "not found on PATH" in p for p in rep["problems"]), rep
