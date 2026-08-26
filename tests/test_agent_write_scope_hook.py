"""Regression tests for .claude/hooks/agent_write_scope.py — a PreToolUse hook
enforcing per-subagent write-path isolation. format-engineer/source-analyst/
data-scientist each claim (in their own .md frontmatter description) a
"by convention" write scope, but nothing enforced it: settings.json's
Write(./**)-family permissions are session-wide, not scoped per agent
identity. This hook reads the `agent_type` field Claude Code adds to hook
input when a tool call happens inside a subagent context and denies any
Write/Edit/NotebookEdit/Bash-write destination outside that agent's declared
scope. citation-verifier/literature-scout/qa-auditor are scoped to an EMPTY
prefix tuple — they hold no Write/Edit tool at all, so any raw shell
write-sink from their Bash tool is denied, while their sanctioned script
subprocess calls (not shell write-sink syntax) stay unaffected.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"


def _run_hook(payload, cwd):
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "agent_write_scope.py")],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return proc


def _write_payload(agent_type, path):
    return {"agent_type": agent_type, "tool_name": "Write", "tool_input": {"file_path": path}}


# ---------- format-engineer ----------

def test_format_engineer_write_to_build_allowed(tmp_path):
    proc = _run_hook(_write_payload("format-engineer", str(tmp_path / "build" / "paper.pdf")), tmp_path)
    assert proc.stdout.strip() == ""


def test_format_engineer_write_to_exports_allowed(tmp_path):
    proc = _run_hook(_write_payload("format-engineer", str(tmp_path / "exports" / "out.xlsx")), tmp_path)
    assert proc.stdout.strip() == ""


def test_format_engineer_write_to_templates_ingested_allowed(tmp_path):
    proc = _run_hook(
        _write_payload("format-engineer", str(tmp_path / "templates" / "ingested" / "template-profile.md")),
        tmp_path)
    assert proc.stdout.strip() == ""


def test_format_engineer_write_to_drafts_denied(tmp_path):
    proc = _run_hook(_write_payload("format-engineer", str(tmp_path / "drafts" / "intro.md")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "format-engineer" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_format_engineer_write_to_analysis_denied(tmp_path):
    proc = _run_hook(_write_payload("format-engineer", str(tmp_path / "analysis" / "foo.py")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_format_engineer_write_to_evidence_extracts_denied(tmp_path):
    proc = _run_hook(
        _write_payload("format-engineer", str(tmp_path / "evidence" / "extracts" / "smith2024.json")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------- source-analyst ----------

def test_source_analyst_write_to_evidence_extracts_allowed(tmp_path):
    proc = _run_hook(
        _write_payload("source-analyst", str(tmp_path / "evidence" / "extracts" / "smith2024.json")), tmp_path)
    assert proc.stdout.strip() == ""


def test_source_analyst_write_to_build_denied(tmp_path):
    proc = _run_hook(_write_payload("source-analyst", str(tmp_path / "build" / "sneaky.tex")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_source_analyst_write_to_evidence_root_denied(tmp_path):
    # evidence/ itself (not evidence/extracts/) is out of scope — cards.jsonl's
    # directory, not the sanctioned extracts subdirectory.
    proc = _run_hook(_write_payload("source-analyst", str(tmp_path / "evidence" / "notes.md")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------- data-scientist ----------

def test_data_scientist_write_to_analysis_allowed(tmp_path):
    proc = _run_hook(_write_payload("data-scientist", str(tmp_path / "analysis" / "01_eda.py")), tmp_path)
    assert proc.stdout.strip() == ""


def test_data_scientist_write_to_drafts_denied(tmp_path):
    proc = _run_hook(_write_payload("data-scientist", str(tmp_path / "drafts" / "results.md")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_data_scientist_write_to_evidence_extracts_denied(tmp_path):
    proc = _run_hook(
        _write_payload("data-scientist", str(tmp_path / "evidence" / "extracts" / "x.json")), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------- unrestricted actors ----------

def test_main_session_no_agent_type_unrestricted(tmp_path):
    # No agent_type field at all == the main orchestrator session — this hook
    # must not restrict it (drafts/outline/reviews/sources/evidence are all
    # legitimately its own to write).
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}
    proc = _run_hook(payload, tmp_path)
    assert proc.stdout.strip() == ""


def test_unscoped_agent_type_unrestricted(tmp_path):
    # methodology-advisor holds no Write/Bash tool and makes no write-scope
    # claim — not in AGENT_SCOPES, so this hook must not restrict it either.
    proc = _run_hook(_write_payload("methodology-advisor", str(tmp_path / "build" / "x.tex")), tmp_path)
    assert proc.stdout.strip() == ""


# ---------- read-only-by-design agents (empty scope) ----------

def test_literature_scout_bash_redirect_denied(tmp_path):
    # literature-scout holds Bash but no Write/Edit tool at all — its
    # contract is search + report, never a raw shell write.
    payload = {"agent_type": "literature-scout", "tool_name": "Bash",
               "tool_input": {"command": "echo '{\"fake\":1}' > sources/registry.jsonl"}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_literature_scout_sanctioned_script_call_allowed(tmp_path):
    # Its real, sanctioned workflow is a subprocess call into registry_db.py —
    # not a shell redirect/tee/cp/mv write_destinations() can see — so an
    # empty write scope must not block this.
    payload = {"agent_type": "literature-scout", "tool_name": "Bash",
               "tool_input": {"command": "python scripts/registry_db.py add --json '{\"title\":\"x\"}'"}}
    proc = _run_hook(payload, tmp_path)
    assert proc.stdout.strip() == ""


def test_citation_verifier_bash_tee_denied(tmp_path):
    payload = {"agent_type": "citation-verifier", "tool_name": "Bash",
               "tool_input": {"command": "echo ok | tee verify-status.json"}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_qa_auditor_bash_cp_denied(tmp_path):
    payload = {"agent_type": "qa-auditor", "tool_name": "Bash",
               "tool_input": {"command": "cp drafts/methods.md reviews/sneaky.md"}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_qa_auditor_read_only_bash_allowed(tmp_path):
    payload = {"agent_type": "qa-auditor", "tool_name": "Bash",
               "tool_input": {"command": "python scripts/qa_inspect.py --stage screening"}}
    proc = _run_hook(payload, tmp_path)
    assert proc.stdout.strip() == ""


# ---------- NotebookEdit ----------

def test_notebook_edit_uses_notebook_path_key(tmp_path):
    payload = {"agent_type": "data-scientist", "tool_name": "NotebookEdit",
               "tool_input": {"notebook_path": str(tmp_path / "build" / "sneaky.ipynb")}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------- Bash surface ----------

def test_bash_redirect_outside_scope_denied(tmp_path):
    payload = {"agent_type": "format-engineer", "tool_name": "Bash",
               "tool_input": {"command": "echo 'x' > drafts/results.md"}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_redirect_inside_scope_allowed(tmp_path):
    payload = {"agent_type": "format-engineer", "tool_name": "Bash",
               "tool_input": {"command": "echo 'x' > build/tmp.tex"}}
    proc = _run_hook(payload, tmp_path)
    assert proc.stdout.strip() == ""


def test_bash_cp_destination_outside_scope_denied(tmp_path):
    payload = {"agent_type": "format-engineer", "tool_name": "Bash",
               "tool_input": {"command": "cp templates/paper/main.tex drafts/leak.tex"}}
    proc = _run_hook(payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_cp_readonly_source_outside_scope_not_a_false_positive(tmp_path):
    # The whole point of using write_destinations() (not write_targets()):
    # copying FROM templates/ (outside format-engineer's declared scope, but
    # only being READ here) INTO build/ (in scope) must be allowed — the
    # source argument is not itself a write.
    payload = {"agent_type": "format-engineer", "tool_name": "Bash",
               "tool_input": {"command": "cp templates/paper/main.tex build/main.tex"}}
    proc = _run_hook(payload, tmp_path)
    assert proc.stdout.strip() == ""


def test_bash_unrelated_read_command_not_blocked(tmp_path):
    payload = {"agent_type": "data-scientist", "tool_name": "Bash",
               "tool_input": {"command": "cat drafts/results.md"}}
    proc = _run_hook(payload, tmp_path)
    assert proc.stdout.strip() == ""


# ---------- fail-open ----------

def test_hook_fails_open_on_garbage_stdin(tmp_path):
    # Fail-OPEN is the contract and is unchanged: exit 0, no permissionDecision,
    # the call proceeds. What changed is that it is no longer SILENT — a
    # degradation notice that the gate did not run is emitted, because exit-0
    # with no output is byte-identical to "checked, nothing to gate" and made a
    # broken gate indistinguishable from a passing one.
    proc = subprocess.run([sys.executable, str(HOOKS / "agent_write_scope.py")],
                          input="not json", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert "permissionDecision" not in proc.stdout, "a degraded gate must not deny"
    assert payload["systemMessage"].startswith("⚠ Scholar-Kit gate degraded")
    assert "agent_write_scope" in payload["systemMessage"]
    assert "ALLOWED" in payload["systemMessage"]


def test_hook_is_silent_on_empty_stdin(tmp_path):
    # The asymmetry is deliberate. A harness probing the hook with no payload
    # is not a broken gate, and warning on every such call would train the
    # author to ignore the warning that matters.
    proc = subprocess.run([sys.executable, str(HOOKS / "agent_write_scope.py")],
                          input="", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    assert proc.stderr.strip() == ""


def test_degradation_notice_carries_no_payload_content(tmp_path):
    # A hook sees draft prose, paths and shell commands. The notice reports the
    # exception TYPE and origin only — never str(exc) — so manuscript content
    # cannot ride out into a session-visible warning and the transcript.
    secret = "PATIENT-COHORT-ENROLMENT-1998"
    proc = subprocess.run([sys.executable, str(HOOKS / "agent_write_scope.py")],
                          input="{not json " + secret, cwd=tmp_path,
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert secret not in proc.stdout
    assert secret not in proc.stderr


# ---------- L2: read-only agents can't smuggle a write via a script --out flag ----------
# (2026-07-05 audit) write_destinations() sees only shell write-sink SYNTAX,
# never the write a sanctioned script performs internally. A read-only
# (empty-scope) agent could therefore escape its "writes nothing" contract via
# `xlsx_export.py --out <path>`. Closed for empty-scope agents only; writer
# agents keep their documented in-scope --out flows.

def test_readonly_agent_script_out_flag_denied(tmp_path):
    payload = {"agent_type": "literature-scout", "tool_name": "Bash",
               "tool_input": {"command": "python scripts/xlsx_export.py --out exports/x.xlsx"}}
    out = json.loads(_run_hook(payload, tmp_path).stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_readonly_agent_script_out_dir_flag_denied(tmp_path):
    payload = {"agent_type": "qa-auditor", "tool_name": "Bash",
               "tool_input": {"command": "python scripts/prisma_flow.py --registry sources/registry.jsonl --out-dir outline"}}
    out = json.loads(_run_hook(payload, tmp_path).stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_readonly_agent_script_without_out_flag_still_allowed(tmp_path):
    # The sanctioned registry_db.py add path has no --out flag — must not be
    # caught by the --out scan (regression guard for the L2 fix).
    payload = {"agent_type": "literature-scout", "tool_name": "Bash",
               "tool_input": {"command": "python scripts/registry_db.py add --json '{\"title\":\"x\"}'"}}
    assert _run_hook(payload, tmp_path).stdout.strip() == ""


def test_writer_agent_out_flag_not_scanned_preserves_documented_flow(tmp_path):
    # format-engineer's documented make_reference_docx.py --out templates/paper/
    # flow (docx-output SKILL) must NOT be denied by the --out scan — writer
    # agents are deliberately excluded from _script_out_destinations.
    payload = {"agent_type": "format-engineer", "tool_name": "Bash",
               "tool_input": {"command": "python scripts/make_reference_docx.py --out templates/paper/reference.docx"}}
    assert _run_hook(payload, tmp_path).stdout.strip() == ""
