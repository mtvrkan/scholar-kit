"""Regression tests for .claude/hooks/protect_data_files.py — a PreToolUse hook
enforcing CLAUDE.md's Invariant 6 (registry/cards/venues/search-log/bib/
verify-status are script-owned; no direct Write/Edit/NotebookEdit/Bash mutation).
This hook previously had no test coverage despite being central to the
anti-fabrication chain (a direct hand-edit of registry.jsonl or cards.jsonl
would silently defeat doi2bib.py's verified-DOI discipline and
evidence_db.py's registry cross-check).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"


def _run_hook(payload, cwd):
    # See test_phase_gate_hook.py's note: the hook no-ops outside a kit project
    # (references.bib exists in every LaTeX repo), so the fixture declares one.
    Path(cwd, "PROJECT.md").touch()
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "protect_data_files.py")],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return proc


def _write_payload(path):
    return {"tool_name": "Write", "tool_input": {"file_path": path}}


# ---------- Write/Edit/NotebookEdit surface ----------

def test_direct_write_to_registry_blocked(tmp_path):
    proc = _run_hook(_write_payload(str(tmp_path / "sources" / "registry.jsonl")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "registry_db.py" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_direct_write_to_cards_blocked(tmp_path):
    proc = _run_hook(_write_payload(str(tmp_path / "evidence" / "cards.jsonl")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "evidence_db.py" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_direct_write_to_verify_status_blocked(tmp_path):
    proc = _run_hook(_write_payload(str(tmp_path / "verify-status.json")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "write_verify_status.py" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_write_to_unprotected_file_allowed(tmp_path):
    proc = _run_hook(_write_payload(str(tmp_path / "drafts" / "intro.md")), tmp_path)
    assert proc.stdout.strip() == ""


def test_notebook_edit_uses_notebook_path_key(tmp_path):
    # Regression: NotebookEdit's payload key is "notebook_path", not
    # "file_path" — a hook reading only "file_path" leaves this branch
    # permanently dead even though NotebookEdit is in settings.json's matcher.
    payload = {"tool_name": "NotebookEdit",
               "tool_input": {"notebook_path": str(tmp_path / "sources" / "registry.jsonl")}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------- Bash surface ----------

def test_bash_redirect_to_registry_blocked(tmp_path):
    payload = {"tool_name": "Bash",
               "tool_input": {"command": "echo '{}' > sources/registry.jsonl"}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_mv_of_protected_file_blocked(tmp_path):
    # mv registry.jsonl away from its required path is data loss even though
    # nothing is "written" to it — every argument must be checked, not just
    # the destination.
    payload = {"tool_name": "Bash",
               "tool_input": {"command": "mv sources/registry.jsonl /tmp/out.bak"}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_merely_reading_protected_file_not_blocked(tmp_path):
    payload = {"tool_name": "Bash",
               "tool_input": {"command": "python scripts/registry_db.py --file sources/registry.jsonl stats"}}
    proc = _run_hook(payload, tmp_path)
    assert proc.stdout.strip() == ""


def test_bash_unrelated_command_not_blocked(tmp_path):
    payload = {"tool_name": "Bash", "tool_input": {"command": "pytest tests/ -x -q"}}
    proc = _run_hook(payload, tmp_path)
    assert proc.stdout.strip() == ""


def test_bash_quoted_target_with_space_blocked(tmp_path):
    # Regression companion to the _shell_write_sink.py whitespace fix: a
    # protected filename doesn't need a space in ITS name to matter here, but
    # confirms the shared write_targets() plumbing still surfaces a real
    # protected-file hit through this hook after that fix.
    payload = {"tool_name": "Bash",
               "tool_input": {"command": 'cp "backup copy.jsonl" sources/registry.jsonl'}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_rename_item_of_protected_file_blocked(tmp_path):
    payload = {"tool_name": "Bash", "tool_input": {"command": "Rename-Item sources/registry.jsonl old.bak"}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_pipeless_tee_of_protected_file_blocked(tmp_path):
    payload = {"tool_name": "Bash", "tool_input": {"command": 'tee sources/registry.jsonl <<< "x"'}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_os_remove_of_protected_file_blocked(tmp_path):
    payload = {"tool_name": "Bash",
               "tool_input": {"command": "python -c \"import os; os.remove('sources/registry.jsonl')\""}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_os_rename_of_protected_file_blocked(tmp_path):
    payload = {"tool_name": "Bash",
               "tool_input": {"command": "python -c \"import os; os.rename('sources/registry.jsonl', 'x.bak')\""}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------- fail-open ----------

def test_hook_fails_open_on_garbage_stdin(tmp_path):
    # Fail-OPEN is the contract and is unchanged: exit 0, no permissionDecision,
    # the call proceeds. What changed is that it is no longer SILENT — a
    # degradation notice that the gate did not run is emitted, because exit-0
    # with no output is byte-identical to "checked, nothing to gate" and made a
    # broken gate indistinguishable from a passing one.
    proc = subprocess.run([sys.executable, str(HOOKS / "protect_data_files.py")],
                          input="not json", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert "permissionDecision" not in proc.stdout, "a degraded gate must not deny"
    assert payload["systemMessage"].startswith("⚠ Scholar-Kit gate degraded")
    assert "protect_data_files" in payload["systemMessage"]
    assert "ALLOWED" in payload["systemMessage"]


def test_hook_is_silent_on_empty_stdin(tmp_path):
    # The asymmetry is deliberate. A harness probing the hook with no payload
    # is not a broken gate, and warning on every such call would train the
    # author to ignore the warning that matters.
    proc = subprocess.run([sys.executable, str(HOOKS / "protect_data_files.py")],
                          input="", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    assert proc.stderr.strip() == ""


def test_degradation_notice_carries_no_payload_content(tmp_path):
    # A hook sees draft prose, paths and shell commands. The notice reports the
    # exception TYPE and origin only — never str(exc) — so manuscript content
    # cannot ride out into a session-visible warning and the transcript.
    secret = "PATIENT-COHORT-ENROLMENT-1998"
    proc = subprocess.run([sys.executable, str(HOOKS / "protect_data_files.py")],
                          input="{not json " + secret, cwd=tmp_path,
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert secret not in proc.stdout
    assert secret not in proc.stderr
