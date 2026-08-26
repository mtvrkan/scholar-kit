"""Regression tests for .claude/hooks/template_supremacy_gate.py — a PreToolUse
hook enforcing a narrow, mechanically-checkable slice of CLAUDE.md's
Invariant 8 (TEMPLATE SUPREMACY):
  - DOCX: when templates/ingested/template-profile.md exists, a
    scripts/docx_build.sh invocation's reference-doc argument must be
    templates/ingested/reference.docx (or "-" for an explicit draft-preview
    build), never a stale kit-default path.
  - LaTeX: when a template is registered AND the ingested file is a .cls/.sty
    (not .docx-only), a scripts/latex_build.sh invocation's main.tex must
    \\documentclass or \\usepackage the ingested class somewhere in its text.
Neither check verifies full content compliance (every extracted margin/
heading/spacing rule) or touches docx_style_check.py's existing font/size
drift WARN — see the hook's own module docstring and DECISIONS.md D-079 for
scope.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"


def _run_hook(payload, cwd):
    return subprocess.run(
        [sys.executable, str(HOOKS / "template_supremacy_gate.py")],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def _bash_payload(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _register_template(tmp_path):
    d = tmp_path / "templates" / "ingested"
    d.mkdir(parents=True)
    (d / "template-profile.md").write_text("# extracted rules", encoding="utf-8")


# ---------- template registered: wrong reference doc denied ----------

def test_wrong_reference_doc_denied_when_template_registered(tmp_path):
    _register_template(tmp_path)
    cmd = "bash scripts/docx_build.sh build/paper.docx templates/csl/apa.csl templates/paper/reference.docx drafts/intro.md"
    proc = _run_hook(_bash_payload(cmd), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "templates/ingested/reference.docx" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_direct_invocation_without_interpreter_prefix_also_denied(tmp_path):
    _register_template(tmp_path)
    cmd = "./scripts/docx_build.sh build/paper.docx templates/csl/apa.csl templates/paper/reference.docx drafts/intro.md"
    proc = _run_hook(_bash_payload(cmd), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------- template registered: correct usage allowed ----------

def test_ingested_reference_doc_allowed_when_template_registered(tmp_path):
    _register_template(tmp_path)
    cmd = "bash scripts/docx_build.sh build/paper.docx templates/csl/apa.csl templates/ingested/reference.docx drafts/intro.md"
    proc = _run_hook(_bash_payload(cmd), tmp_path)
    assert proc.stdout.strip() == ""


def test_dash_draft_preview_allowed_when_template_registered(tmp_path):
    _register_template(tmp_path)
    cmd = "bash scripts/docx_build.sh build/preview.docx templates/csl/apa.csl - drafts/intro.md"
    proc = _run_hook(_bash_payload(cmd), tmp_path)
    assert proc.stdout.strip() == ""


# ---------- no template registered: kit defaults are correct, never gated ----------

def test_kit_default_reference_doc_allowed_when_no_template_registered(tmp_path):
    cmd = "bash scripts/docx_build.sh build/paper.docx templates/csl/apa.csl templates/paper/reference.docx drafts/intro.md"
    proc = _run_hook(_bash_payload(cmd), tmp_path)
    assert proc.stdout.strip() == ""


# ---------- unrelated commands / other build scripts never gated ----------

def test_unrelated_command_not_gated(tmp_path):
    _register_template(tmp_path)
    proc = _run_hook(_bash_payload("pytest tests/ -x -q"), tmp_path)
    assert proc.stdout.strip() == ""


def test_bare_mention_not_gated(tmp_path):
    _register_template(tmp_path)
    proc = _run_hook(_bash_payload("cat scripts/docx_build.sh"), tmp_path)
    assert proc.stdout.strip() == ""


def test_latex_build_not_covered_when_no_cls_ingested(tmp_path):
    # Documented scope limitation, not a bug: a template-profile.md with no
    # ingested .cls/.sty (e.g. a .docx-only registration) has no LaTeX class
    # claim to check.
    _register_template(tmp_path)
    proc = _run_hook(_bash_payload("bash scripts/latex_build.sh main.tex build"), tmp_path)
    assert proc.stdout.strip() == ""


# ---------- LaTeX path: ingested .cls/.sty must be referenced ----------

def _register_latex_template(tmp_path, filename="ieee-template.cls"):
    d = tmp_path / "templates" / "ingested"
    d.mkdir(parents=True, exist_ok=True)
    (d / "template-profile.md").write_text("# extracted rules", encoding="utf-8")
    (d / filename).write_text("% latex class stub", encoding="utf-8")


def test_latex_main_tex_not_referencing_ingested_class_denied(tmp_path):
    _register_latex_template(tmp_path)
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\\end{document}\n", encoding="utf-8")
    proc = _run_hook(_bash_payload("bash scripts/latex_build.sh main.tex build"), tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "ieee-template" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_latex_main_tex_referencing_ingested_documentclass_allowed(tmp_path):
    _register_latex_template(tmp_path)
    (tmp_path / "main.tex").write_text(
        "\\documentclass{ieee-template}\n\\begin{document}\\end{document}\n", encoding="utf-8")
    proc = _run_hook(_bash_payload("bash scripts/latex_build.sh main.tex build"), tmp_path)
    assert proc.stdout.strip() == ""


def test_latex_main_tex_referencing_ingested_usepackage_allowed(tmp_path):
    _register_latex_template(tmp_path, filename="thesis-style.sty")
    (tmp_path / "main.tex").write_text(
        "\\documentclass{report}\n\\usepackage{thesis-style}\n\\begin{document}\\end{document}\n",
        encoding="utf-8")
    proc = _run_hook(_bash_payload("bash scripts/latex_build.sh main.tex build"), tmp_path)
    assert proc.stdout.strip() == ""


def test_latex_no_template_registered_never_gated(tmp_path):
    (tmp_path / "main.tex").write_text("\\documentclass{article}\n", encoding="utf-8")
    proc = _run_hook(_bash_payload("bash scripts/latex_build.sh main.tex build"), tmp_path)
    assert proc.stdout.strip() == ""


def test_latex_missing_main_tex_file_not_gated(tmp_path):
    # Let latex_build.sh itself report the missing-file error, not this hook.
    _register_latex_template(tmp_path)
    proc = _run_hook(_bash_payload("bash scripts/latex_build.sh main.tex build"), tmp_path)
    assert proc.stdout.strip() == ""


# ---------- fail-open ----------

def test_hook_fails_open_on_garbage_stdin(tmp_path):
    # Fail-OPEN is the contract and is unchanged: exit 0, no permissionDecision,
    # the call proceeds. What changed is that it is no longer SILENT — a
    # degradation notice that the gate did not run is emitted, because exit-0
    # with no output is byte-identical to "checked, nothing to gate" and made a
    # broken gate indistinguishable from a passing one.
    proc = subprocess.run([sys.executable, str(HOOKS / "template_supremacy_gate.py")],
                          input="not json", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert "permissionDecision" not in proc.stdout, "a degraded gate must not deny"
    assert payload["systemMessage"].startswith("⚠ Scholar-Kit gate degraded")
    assert "template_supremacy_gate" in payload["systemMessage"]
    assert "ALLOWED" in payload["systemMessage"]


def test_hook_is_silent_on_empty_stdin(tmp_path):
    # The asymmetry is deliberate. A harness probing the hook with no payload
    # is not a broken gate, and warning on every such call would train the
    # author to ignore the warning that matters.
    proc = subprocess.run([sys.executable, str(HOOKS / "template_supremacy_gate.py")],
                          input="", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    assert proc.stderr.strip() == ""


def test_degradation_notice_carries_no_payload_content(tmp_path):
    # A hook sees draft prose, paths and shell commands. The notice reports the
    # exception TYPE and origin only — never str(exc) — so manuscript content
    # cannot ride out into a session-visible warning and the transcript.
    secret = "PATIENT-COHORT-ENROLMENT-1998"
    proc = subprocess.run([sys.executable, str(HOOKS / "template_supremacy_gate.py")],
                          input="{not json " + secret, cwd=tmp_path,
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert secret not in proc.stdout
    assert secret not in proc.stderr


def test_non_bash_tool_not_gated(tmp_path):
    _register_template(tmp_path)
    payload = {"tool_name": "Write", "tool_input": {"file_path": "build/paper.docx"}}
    proc = _run_hook(payload, tmp_path)
    assert proc.stdout.strip() == ""
