"""The plugin-install gap, made loud instead of documented.

`.claude/hooks/enforcement_notice.py` fires at session start when a directory
has a PROJECT.md but not the layer that enforces it — the state a user lands in
by installing the plugin and never running `/new-project`. Everything here is
about the two ways this could fail as a mechanism: staying silent when the gap
is real, and crying wolf when it is not.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOK = ROOT / ".claude" / "hooks" / "enforcement_notice.py"
PLUGIN_DIR = ROOT / ".claude-plugin"


def _run(cwd, stdin=None):
    payload = json.dumps({"cwd": str(cwd)}) if stdin is None else stdin
    p = subprocess.run([sys.executable, str(HOOK)], input=payload,
                       capture_output=True, text=True, encoding="utf-8", timeout=30)
    return p.returncode, p.stdout or "", p.stderr or ""


def _materialise(root: Path, scripts=True, hooks=True, project=True):
    if project:
        (root / "PROJECT.md").write_text("# Paper\n", encoding="utf-8")
    if scripts:
        (root / "scripts").mkdir(exist_ok=True)
        (root / "scripts" / "registry_db.py").write_text("", encoding="utf-8")
    if hooks:
        (root / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (root / ".claude" / "hooks" / "phase_gate.py").write_text("", encoding="utf-8")


# ---------- fires exactly when the gap is real ----------

def test_reports_the_gap_in_a_project_with_no_runtime(tmp_path):
    _materialise(tmp_path, scripts=False, hooks=False)
    code, out, _ = _run(tmp_path)
    assert code == 0
    assert "ENFORCEMENT ABSENT" in out
    assert "scripts/registry_db.py" in out and ".claude/hooks/phase_gate.py" in out
    assert "/new-project" in out, "the notice must name the fix, not just the problem"


def test_names_only_what_is_actually_missing(tmp_path):
    """A half-materialised project is the confusing case: reporting both layers
    would send the user looking for a file that is right there."""
    _materialise(tmp_path, scripts=True, hooks=False)
    code, out, _ = _run(tmp_path)
    assert code == 0
    assert ".claude/hooks/phase_gate.py" in out
    assert "scripts/registry_db.py" not in out


def test_the_notice_says_which_guarantees_are_not_in_force(tmp_path):
    # The point is not "something is missing" — it is which specific promise the
    # user is currently NOT getting. Without this the notice is unactionable.
    _materialise(tmp_path, scripts=False, hooks=False)
    _, out, _ = _run(tmp_path)
    for claim in ("/verify-citations", "outline", "registry.jsonl"):
        assert claim in out, f"the notice does not say what {claim} no longer guarantees"


# ---------- stays silent everywhere else ----------

def test_silent_in_a_fully_materialised_project(tmp_path):
    _materialise(tmp_path)
    code, out, _ = _run(tmp_path)
    assert code == 0 and out.strip() == ""


def test_silent_without_project_md_even_with_no_runtime(tmp_path):
    """Somebody else's repository. A plugin's hooks run in EVERY session, so a
    notice that fired here would be noise in every unrelated project the user
    opens — and noise is how a warning stops being read."""
    (tmp_path / "drafts").mkdir()
    code, out, _ = _run(tmp_path)
    assert code == 0 and out.strip() == ""


def test_silent_and_clean_on_a_broken_payload(tmp_path):
    for bad in ("", "not json", "[]"):
        code, out, err = _run(tmp_path, stdin=bad)
        assert code == 0, f"payload {bad!r} produced exit {code}"
        assert out.strip() == "" and "Traceback" not in err


def test_always_exits_zero_so_the_interpreter_fallback_cannot_double_print(tmp_path):
    """hooks.json runs `python … || python3 …`. A non-zero exit from a notice
    that RAN would make the fallback run it a second time, printing the same
    warning twice — so exit 0 is load-bearing, in the firing case too."""
    _materialise(tmp_path, scripts=False, hooks=False)
    code, out, _ = _run(tmp_path)
    assert code == 0 and "ENFORCEMENT ABSENT" in out


# ---------- the wiring ----------

def test_plugin_manifest_registers_the_hooks_file():
    manifest = json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))
    rel = manifest.get("hooks")
    assert rel, "plugin.json declares no hooks file — the notice ships dead"
    assert rel.startswith("./") and rel.endswith(".json")
    assert (ROOT / rel.removeprefix("./")).is_file()


def test_the_hooks_file_declares_only_hook_event_names():
    """The manifest schema constrains this file's top-level keys to hook event
    names, so there is nowhere in it to explain itself — which is why a `hooks`
    file carrying a `$comment` key was removed rather than kept as
    documentation. The explanation lives in the script's own docstring; this
    test is what stops it from being re-added.
    """
    hooks = json.loads((PLUGIN_DIR / "hooks.json").read_text(encoding="utf-8"))
    events = {"PreToolUse", "PostToolUse", "SessionStart", "SessionEnd", "Stop",
              "SubagentStop", "UserPromptSubmit", "Notification", "PreCompact"}
    assert set(hooks) <= events, f"non-event keys in hooks.json: {set(hooks) - events}"

    doc = (ROOT / ".claude" / "hooks" / "enforcement_notice.py").read_text(encoding="utf-8")
    assert "python3" in doc, (
        "the interpreter-fallback reasoning has no home if it is neither in "
        "hooks.json nor in the script's docstring")


def test_the_hooks_file_wires_the_notice_to_session_start():
    hooks = json.loads((PLUGIN_DIR / "hooks.json").read_text(encoding="utf-8"))
    commands = [h["command"] for entry in hooks["SessionStart"] for h in entry["hooks"]]
    assert commands, "hooks.json registers no SessionStart command"
    joined = " ".join(commands)
    assert "enforcement_notice.py" in joined
    assert "${CLAUDE_PLUGIN_ROOT}" in joined, (
        "a plugin hook must resolve against the plugin root, not the project's cwd")
    assert "python3" in joined, (
        "no python3 fallback — the hook would be silent on a macOS/Linux box "
        "whose only interpreter is python3, which is most of them")


def test_every_script_path_named_in_the_plugin_hooks_file_exists():
    text = (PLUGIN_DIR / "hooks.json").read_text(encoding="utf-8")
    for name in ("enforcement_notice.py",):
        assert (ROOT / ".claude" / "hooks" / name).is_file()
        assert name in text
