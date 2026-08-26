#!/usr/bin/env python3
"""PostToolUse hook — instant citation warning after a draft edit.

Fires on Write|Edit of drafts/*.md, AND on any Bash command that writes there
via redirect/tee/cp/mv/python one-liners/PowerShell cmdlets (see
_shell_write_sink.py) — `cat <<'EOF' > drafts/intro.md` used to leave this
hook entirely blind, since only Write/Edit was recognized, letting a
Bash-authored draft skip the citation check every Write/Edit gets. Runs
cite_audit.py --quick on each touched drafts/*.md file. Non-blocking
visibility: undefined keys / [CITATION NEEDED] tags are surfaced to the model
via exit 2 + stderr (tool already ran; this is feedback, not a block).
Fail-open on any unexpected input.

Change record: full reasoning and rejected alternatives live in DECISIONS.md
(D-065, D-074, D-075, D-077, D-080, D-081, D-091). Behaviour is locked by
tests/test_cite_warn_hook.py — see `hooks` in tests/README.md.
"""
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _degrade import missing_tool_name, read_payload, report_contract
from _project_scope import is_kit_project
from _shell_write_sink import write_targets


def _is_draft_md(path: str) -> bool:
    # Lowercased before the component/suffix checks — phase_gate.py's parallel
    # gate does the same, since Windows/macOS treat "Drafts/intro.md" and
    # "drafts/intro.md" as the identical file; a case-sensitive check here let
    # a citation-bearing draft skip the citation check just by capitalization.
    norm = path.replace("\\", "/").lower()
    # basename equality, not endswith("status.md") — the latter also matches
    # "drafts/oldstatus.md" or "drafts/resultsstatus.md", wrongly exempting
    # any draft file that merely ends with those characters from the citation
    # check it should actually get.
    is_status_file = norm.rsplit("/", 1)[-1] == "status.md"
    return "/drafts/" in f"/{norm}" and norm.endswith(".md") and not is_status_file


def _candidate_paths(payload) -> list[str]:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if tool in ("Write", "Edit"):
        path = tool_input.get("file_path", "")
        return [path] if path else []
    if tool == "Bash":
        command = tool_input.get("command", "")
        return write_targets(command) if command else []
    return []


def main():
    # Fail-open on any unusable stdin, and never with a traceback: empty input
    # stays silent, input that will not parse — or that parses into something
    # other than an object — is reported. See _degrade.py.
    payload = read_payload('cite_warn', sys.stdin.read())
    if payload is None:
        sys.exit(0)
    project_dir = payload.get("cwd") or "."
    # `drafts/*.md` is an ordinary path outside this kit. The scripts/ check
    # below already no-ops in someone else's repo, but only by accident of
    # layout; state the intent so a future plugin layout that ships scripts/
    # alongside the hooks cannot silently start auditing unrelated drafts.
    # Checked BEFORE the tool_name branch below so the contract notice cannot
    # fire in a directory this kit was never gating.
    if not is_kit_project(project_dir):
        sys.exit(0)
    if missing_tool_name(payload):
        report_contract('cite_warn', "no 'tool_name' key")
        sys.exit(0)
    if payload.get("tool_name") not in ("Write", "Edit", "Bash"):
        sys.exit(0)
    script = Path(project_dir) / "scripts" / "cite_audit.py"
    if not script.exists():
        sys.exit(0)

    warnings = []
    for path in _candidate_paths(payload):
        if not _is_draft_md(path):
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(script), "--quick", "--file", path],
                capture_output=True, text=True, cwd=project_dir, timeout=30,
                encoding="utf-8", errors="replace")
        except Exception:
            continue
        out = (proc.stdout or "").strip()
        if out and "clean" not in out:
            warnings.append(out)

    if warnings:
        print("\n".join(warnings), file=sys.stderr)
        sys.exit(2)  # PostToolUse: stderr goes to the model as feedback
    sys.exit(0)


if __name__ == "__main__":
    main()
