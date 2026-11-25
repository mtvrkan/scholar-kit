"""Tests for templates/codex/codex_adapter.py — the kit's gates under OpenAI Codex.

Codex edits files with one tool, `apply_patch`, whose payload carries the patch
text and no `file_path`. Unadapted, every gate in the kit answers such a call
with zero bytes: the tool name matches no branch. These tests lock the property
that matters — a Codex file edit is refused exactly where the same edit made by
Claude Code's Write/Edit is refused — and the two properties that keep the
adapter from becoming a new failure mode: it is transparent for everything it
does not translate, and it never fails closed or silent.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
ADAPTER = ROOT / "templates" / "codex" / "codex_adapter.py"
HOOKS = ROOT / ".claude" / "hooks"


def _project(tmp_path: Path) -> Path:
    (tmp_path / "PROJECT.md").write_text("<!-- scholar-kit-project -->\n", encoding="utf-8")
    return tmp_path


def _patch(*headers: str) -> str:
    body = "\n".join(f"*** {h}\n+x" for h in headers)
    return f"*** Begin Patch\n{body}\n*** End Patch"


def _codex(hook: str, payload, cwd: Path):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, str(ADAPTER), hook], input=raw,
                          capture_output=True, text=True, cwd=cwd, encoding="utf-8")


def _claude(hook: str, payload: dict, cwd: Path):
    return subprocess.run([sys.executable, str(HOOKS / f"{hook}.py")],
                          input=json.dumps(payload), capture_output=True, text=True,
                          cwd=cwd, encoding="utf-8")


def _apply_patch(*headers: str, **extra) -> dict:
    return {"hook_event_name": "PreToolUse", "tool_name": "apply_patch",
            "tool_input": {"command": _patch(*headers)}, **extra}


def _decision(proc) -> str | None:
    for line in proc.stdout.splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        specific = obj.get("hookSpecificOutput") or {}
        if "permissionDecision" in specific:
            return specific["permissionDecision"]
    return None


# ---------- parity: the same edit is refused in both harnesses ----------

PROTECTED = ["sources/registry.jsonl", "evidence/cards.jsonl", "bib/references.bib",
             "verify-status.json", "provenance.jsonl", "analysis/runs.jsonl"]


@pytest.mark.parametrize("path", PROTECTED)
@pytest.mark.parametrize("header", ["Add File", "Update File", "Delete File"])
def test_protected_file_is_denied_for_every_patch_operation(tmp_path, path, header):
    cwd = _project(tmp_path)
    proc = _codex("protect_data_files", _apply_patch(f"{header}: {path}"), cwd)
    assert proc.returncode == 0
    assert _decision(proc) == "deny", proc.stdout


def test_denial_reason_is_the_gates_own(tmp_path):
    cwd = _project(tmp_path)
    codex = _codex("protect_data_files",
                   _apply_patch("Update File: sources/registry.jsonl"), cwd)
    claude = _claude("protect_data_files",
                     {"tool_name": "Edit",
                      "tool_input": {"file_path": "sources/registry.jsonl"}}, cwd)
    assert json.loads(codex.stdout) == json.loads(claude.stdout)


def test_one_protected_path_denies_a_multi_file_patch(tmp_path):
    cwd = _project(tmp_path)
    proc = _codex("protect_data_files",
                  _apply_patch("Add File: notes.md", "Update File: evidence/cards.jsonl",
                               "Add File: other.md"), cwd)
    assert _decision(proc) == "deny"
    assert "cards.jsonl" in proc.stdout


def test_move_destination_is_checked(tmp_path):
    cwd = _project(tmp_path)
    patch = ("*** Begin Patch\n*** Update File: scratch.bib\n"
             "*** Move to: bib/references.bib\n@@\n-a\n+b\n*** End Patch")
    proc = _codex("protect_data_files",
                  {"tool_name": "apply_patch", "tool_input": {"command": patch}}, cwd)
    assert _decision(proc) == "deny"


def test_unprotected_patch_is_allowed_silently(tmp_path):
    cwd = _project(tmp_path)
    proc = _codex("protect_data_files", _apply_patch("Add File: notes.md"), cwd)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")


def test_phase_gate_blocks_a_draft_before_outline_approval(tmp_path):
    cwd = _project(tmp_path)
    codex = _codex("phase_gate", _apply_patch("Add File: drafts/intro.md"), cwd)
    claude = _claude("phase_gate", {"tool_name": "Write",
                                    "tool_input": {"file_path": "drafts/intro.md"}}, cwd)
    assert _decision(claude) == "deny", "precondition: the gate itself denies this"
    assert json.loads(codex.stdout) == json.loads(claude.stdout)


def test_outside_a_kit_project_nothing_is_gated(tmp_path):
    # No PROJECT.md: references.bib is somebody else's bibliography.
    proc = _codex("protect_data_files",
                  _apply_patch("Update File: references.bib"), tmp_path)
    assert (proc.returncode, proc.stdout) == (0, "")


# ---------- subagent write scope ----------

def test_scoped_agent_is_held_to_its_scope(tmp_path):
    cwd = _project(tmp_path)
    inside = _codex("agent_write_scope",
                    _apply_patch("Add File: analysis/fig.py", agent_type="data-scientist"), cwd)
    outside = _codex("agent_write_scope",
                     _apply_patch("Add File: drafts/x.md", agent_type="data-scientist"), cwd)
    assert _decision(inside) is None
    assert _decision(outside) == "deny"


@pytest.mark.parametrize("agent", ["reviewer-critic", "style-auditor",
                                   "methodology-advisor", "dataset-scout"])
def test_agents_without_a_write_tool_are_read_only_under_codex(tmp_path, agent):
    """Claude enforces these by granting no Write tool. Codex has no tool
    allowlist, so the adapter derives the same contract from the frontmatter."""
    cwd = _project(tmp_path)
    proc = _codex("agent_write_scope",
                  _apply_patch("Add File: notes.md", agent_type=agent), cwd)
    assert _decision(proc) == "deny"
    assert "read-only" in proc.stdout


def test_read_only_derivation_matches_the_agent_files():
    sys.path.insert(0, str(ADAPTER.parent))
    try:
        import codex_adapter
    finally:
        sys.path.pop(0)
    derived = codex_adapter.readonly_agents()
    expected = set()
    for md in (ROOT / ".claude" / "agents").glob("*.md"):
        head = md.read_text(encoding="utf-8").split("\n---\n", 1)[0]
        tools = next(l for l in head.splitlines() if l.startswith("tools:"))
        granted = {t.strip() for t in tools.split(":", 1)[1].split(",")}
        if not granted & {"Write", "Edit", "NotebookEdit"}:
            expected.add(md.stem)
    assert derived == expected
    assert {"data-scientist", "format-engineer", "source-analyst"}.isdisjoint(derived)


def test_main_session_is_not_scoped(tmp_path):
    cwd = _project(tmp_path)
    proc = _codex("agent_write_scope", _apply_patch("Add File: notes.md"), cwd)
    assert (proc.returncode, proc.stdout) == (0, "")


# ---------- transparency for what is not translated ----------

BASH_CASES = [
    ("protect_data_files", "echo x > evidence/cards.jsonl"),
    ("protect_data_files", "python scripts/registry_db.py stats"),
    ("phase_gate", "cat notes.md"),
    ("template_supremacy_gate", "bash scripts/docx_build.sh"),
]


@pytest.mark.parametrize("hook,command", BASH_CASES)
def test_bash_payload_passes_through_unchanged(tmp_path, hook, command):
    cwd = _project(tmp_path)
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": command}}
    codex, claude = _codex(hook, payload, cwd), _claude(hook, payload, cwd)
    assert (codex.returncode, codex.stdout, codex.stderr) == \
           (claude.returncode, claude.stdout, claude.stderr)


def test_bash_command_given_as_a_list_is_still_gated(tmp_path):
    cwd = _project(tmp_path)
    payload = {"tool_name": "Bash",
               "tool_input": {"command": ["bash", "-lc", "echo x > evidence/cards.jsonl"]}}
    assert _decision(_codex("protect_data_files", payload, cwd)) == "deny"


def test_session_status_passes_through(tmp_path):
    cwd = _project(tmp_path)
    (cwd / "drafts").mkdir()
    (cwd / "drafts" / "STATUS.md").write_text("phase: outline\n", encoding="utf-8")
    proc = _codex("session_status", {"hook_event_name": "SessionStart", "cwd": str(cwd)}, cwd)
    assert "phase: outline" in proc.stdout


# ---------- PostToolUse feedback survives ----------

def test_cite_warn_feedback_reaches_codex(tmp_path):
    cwd = _project(tmp_path)
    (cwd / "scripts").mkdir()
    for name in ("cite_audit.py", "lib_common.py"):
        (cwd / "scripts" / name).write_bytes((ROOT / "scripts" / name).read_bytes())
    (cwd / "drafts").mkdir()
    (cwd / "drafts" / "intro.md").write_text(
        "A claim [@nobody2099missing].\n", encoding="utf-8")
    payload = {"hook_event_name": "PostToolUse", "cwd": str(cwd),
               **_apply_patch("Add File: notes.md", "Update File: drafts/intro.md")}
    codex = _codex("cite_warn", payload, cwd)
    claude = _claude("cite_warn", {"tool_name": "Edit", "cwd": str(cwd),
                                   "tool_input": {"file_path": "drafts/intro.md"}}, cwd)
    assert claude.returncode == 2, "precondition: cite_warn flags this draft"
    assert codex.returncode == 2
    assert codex.stderr.strip() == claude.stderr.strip()


# ---------- never closed, never silent ----------

@pytest.mark.parametrize("command", ["not a patch", "", None, 123, ["a", "b"]])
def test_unreadable_patch_is_allowed_and_announced(tmp_path, command):
    cwd = _project(tmp_path)
    proc = _codex("phase_gate",
                  {"tool_name": "apply_patch", "tool_input": {"command": command}}, cwd)
    assert proc.returncode == 0
    assert _decision(proc) is None
    assert "gate degraded" in proc.stdout and "ALLOWED" in proc.stdout


def test_degradation_notice_never_quotes_the_patch(tmp_path):
    cwd = _project(tmp_path)
    proc = _codex("phase_gate",
                  {"tool_name": "apply_patch",
                   "tool_input": {"command": "SECRET-MANUSCRIPT-SENTENCE"}}, cwd)
    assert "SECRET-MANUSCRIPT-SENTENCE" not in proc.stdout + proc.stderr


@pytest.mark.parametrize("raw", ["", "{not json", "[]", '"x"'])
def test_malformed_stdin_behaves_as_the_gate_itself_does(tmp_path, raw):
    cwd = _project(tmp_path)
    codex = _codex("protect_data_files", raw, cwd)
    claude = subprocess.run([sys.executable, str(HOOKS / "protect_data_files.py")],
                            input=raw, capture_output=True, text=True, cwd=cwd,
                            encoding="utf-8")
    assert codex.returncode == claude.returncode == 0
    assert codex.stdout == claude.stdout


@pytest.mark.parametrize("argv", [[], ["no_such_hook"], ["../../etc/passwd"],
                                  ["phase_gate", "extra"]])
def test_a_miswired_command_never_blocks(tmp_path, argv):
    proc = subprocess.run([sys.executable, str(ADAPTER), *argv],
                          input=json.dumps(_apply_patch("Add File: drafts/x.md")),
                          capture_output=True, text=True, cwd=_project(tmp_path),
                          encoding="utf-8")
    assert proc.returncode == 0
    assert proc.stdout == ""


def test_adapter_names_only_hooks_that_exist():
    sys.path.insert(0, str(ADAPTER.parent))
    try:
        import codex_adapter
    finally:
        sys.path.pop(0)
    for hook in codex_adapter.HOOKS:
        assert (HOOKS / f"{hook}.py").is_file(), hook
