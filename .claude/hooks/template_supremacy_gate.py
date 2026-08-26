#!/usr/bin/env python3
"""PreToolUse hook — mechanical (partial) enforcement of CLAUDE.md's
Invariant 8, TEMPLATE SUPREMACY ("if templates/ingested/template-profile.md
exists, its rules override all default formatting").

Previously this invariant relied entirely on format-engineer's own procedure
step ("Read template-profile.md first if present") — nothing re-checked it at
the tool-call layer, the same class of gap Invariant 3 (phase_gate.py) and
Invariant 6 (protect_data_files.py) already closed for their own claims.

Scope, deliberately narrow: this hook catches two concrete, discrete,
unambiguous mistakes, not full TEMPLATE SUPREMACY enforcement:
  - DOCX: invoking scripts/docx_build.sh with a reference-doc argument that is
    neither "-" (the documented, exempt draft-preview convention: docx-output/
    SKILL.md and docx_build.sh's own header both say so) nor
    templates/ingested/reference.docx, while a template IS registered.
  - LaTeX: invoking scripts/latex_build.sh on a main.tex that never references
    the ingested .cls/.sty at all (no documentclass or usepackage command
    naming it), while a template IS registered AND the ingested file is a .cls/.sty
    (not a .docx-only registration, which has no LaTeX claim to check). This
    is still not full content compliance — it only catches "the ingested
    class is never incorporated anywhere", not "every extracted margin/
    heading/spacing rule from template-profile.md is honored".
    That second question is now answered, one layer later and by a different
    mechanism: `scripts/template_compliance.py` compares the BUILT document
    against a machine-readable `template-rules` block that /ingest-template
    writes into template-profile.md, and both build scripts run it as a
    non-fatal WARN (D-089). It is a post-build report, not a pre-tool block,
    so it does not replace this hook: this one refuses a build that ignores
    the template outright, that one grades a build that ran.
  - docx_style_check.py's own font/size drift detection (already wired into
    docx_build.sh as a non-fatal WARN, D-071c) is left exactly as-is; this
    hook does not touch that WARN-vs-hard-fail decision.
This closes the cheap, careless version of the bypass (format-engineer simply
forgetting a template is registered and building from a kit-default reference
doc / main.tex that never incorporates it), not every version.

Change record: the narrative notes above are the point-of-use summary, not the
record. Full reasoning and rejected alternatives: DECISIONS.md (D-079, D-080,
D-081, D-084, D-091). Behaviour is locked by
tests/test_template_supremacy_gate_hook.py and the round suites listed under
`hooks` in tests/README.md.

Fail-open: unexpected stdin, no template registered, unreadable main.tex, or
a build invocation this hook can't confidently parse -> allowed, never a crash.
"""
import json
import posixpath
import re
import shlex
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
from _degrade import missing_tool_name, read_payload, report, report_contract
# Imported for the contract notice only, never to widen or narrow what this
# hook gates: the notice must stay inside kit projects for the same reason the
# other hooks' gating does — a plugin install runs it in every session.
from _project_scope import is_kit_project

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

_INTERPRETER_RE = re.compile(r"^(bash|sh|zsh|source)(\.exe)?$", re.IGNORECASE)
INGESTED_REFDOC = "templates/ingested/reference.docx"
TEMPLATE_PROFILE = "templates/ingested/template-profile.md"


def _build_script_args(command: str, script_name: str) -> list[str] | None:
    """Return scripts/<script_name>'s positional args if this (sub-)command
    invokes it directly or via bash/sh/zsh/source/'.', else None for each
    sub-command — mirrors phase_gate.py's _invokes_build_script token-position
    logic, but also captures the arguments that follow (that function only
    needs "was this invoked", not "with what args"). Shared by the docx and
    latex gates below — they differ only in which script name they look for
    and how they interpret the returned args."""
    for sub in re.split(r"&&|\|\||;|\||\n", command):
        try:
            tokens = shlex.split(sub, posix=True)
        except ValueError:
            tokens = sub.split()
        i = 0
        while i < len(tokens) and re.match(r"^[A-Za-z_]\w*=", tokens[i]):
            i += 1  # skip leading FOO=bar env-var assignments
        if i >= len(tokens):
            continue
        first = tokens[i].strip("'\"")
        if first == ".":
            if i + 1 < len(tokens):
                name = PurePosixPath(tokens[i + 1].strip("'\"").replace("\\", "/")).name
                if name.lower() == script_name:
                    return tokens[i + 2:]
            continue
        first_name = PurePosixPath(first.replace("\\", "/")).name
        if _INTERPRETER_RE.match(first_name):
            if i + 1 < len(tokens):
                name = PurePosixPath(tokens[i + 1].strip("'\"").replace("\\", "/")).name
                if name.lower() == script_name:
                    return tokens[i + 2:]
            continue
        # Case-insensitive, matching phase_gate.py's BUILD_SCRIPTS check: both
        # primary platforms have a case-insensitive filesystem, so
        # `bash scripts/DOCX_BUILD.SH ...` runs the identical real script while
        # an exact-case comparison let it skip this template-supremacy gate.
        if first_name.lower() == script_name:
            return tokens[i + 1:]
    return None


def gate_reason_for_bash(command: str) -> str | None:
    args = _build_script_args(command, "docx_build.sh")
    if not args or len(args) < 3:
        return None  # not a docx_build.sh invocation, or too malformed to safely judge
    if not Path(TEMPLATE_PROFILE).exists():
        return None  # no template registered — kit defaults ARE the correct choice
    reference = args[2].strip("'\"")
    if reference == "-":
        return None  # explicit, documented draft-preview convention — exempt
    normalized = posixpath.normpath(reference.replace("\\", "/"))
    if normalized == INGESTED_REFDOC:
        return None
    return (f"TEMPLATE SUPREMACY (Invariant 8): {TEMPLATE_PROFILE} exists — a template is "
            f"registered and its rules override kit defaults. Build with "
            f"--reference-doc {INGESTED_REFDOC} (or pass \"-\" for an explicit "
            f"draft-preview build), not \"{reference}\".")


def _ingested_latex_class_stem() -> str | None:
    """Basename (no extension) of the .cls/.sty file registered under
    templates/ingested/, if any — the LaTeX analogue of INGESTED_REFDOC.
    None when no such file was ingested (only a .docx template registered, or
    no template at all), meaning the LaTeX gate below has nothing to check."""
    ingested_dir = Path("templates/ingested")
    if not ingested_dir.is_dir():
        return None
    for pattern in ("*.cls", "*.sty"):
        for f in sorted(ingested_dir.glob(pattern)):
            return f.stem
    return None


def gate_reason_for_latex(command: str) -> str | None:
    args = _build_script_args(command, "latex_build.sh")
    if not args:
        return None  # not a latex_build.sh invocation
    if not Path(TEMPLATE_PROFILE).exists():
        return None  # no template registered — kit defaults ARE the correct choice
    stem = _ingested_latex_class_stem()
    if not stem:
        return None  # registered template is .docx-only — no LaTeX class to check
    main_tex = Path(args[0].strip("'\""))
    if not main_tex.is_file():
        return None  # let latex_build.sh itself report the missing-file error
    try:
        text = main_tex.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if re.search(r"\\(?:documentclass|usepackage)(?:\[[^\]]*\])?\{[^}]*\b"
                 + re.escape(stem) + r"\b[^}]*\}", text):
        return None
    return (f"TEMPLATE SUPREMACY (Invariant 8): {TEMPLATE_PROFILE} exists and "
            f"templates/ingested/{stem}.cls/.sty is the registered class — {main_tex} "
            f"never \\documentclass{{}}s or \\usepackage{{}}s it. Incorporate the "
            f"ingested class before building, or point at a main.tex that does.")


def main():
    # Fail-open on any unusable stdin, and never with a traceback: empty input
    # stays silent, input that will not parse — or that parses into something
    # other than an object — is reported. See _degrade.py.
    payload = read_payload('template_supremacy_gate', sys.stdin.read())
    if payload is None:
        sys.exit(0)
    # A payload with SOME other tool_name is ordinary (the matcher may widen);
    # a payload with NONE is the contract having moved, and this gate would
    # then never fire again while looking exactly like a gate that passed.
    if missing_tool_name(payload) and is_kit_project():
        report_contract('template_supremacy_gate', "no 'tool_name' key")
        sys.exit(0)
    if payload.get("tool_name") != "Bash":
        sys.exit(0)
    command = (payload.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str) or not command:
        sys.exit(0)

    try:
        reason = gate_reason_for_bash(command) or gate_reason_for_latex(command)
    except Exception as exc:
        # Fail-open backstop, matching every other hook in this kit — and, like
        # them, no longer silent about it. See _degrade.py.
        report("template_supremacy_gate", "the ingested template's constraints", exc)
        sys.exit(0)

    if reason:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
