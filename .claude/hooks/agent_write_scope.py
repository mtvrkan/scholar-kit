#!/usr/bin/env python3
"""PreToolUse hook — enforce per-subagent write-path isolation.

format-engineer/source-analyst/data-scientist's own .md descriptions each
claim a "by convention" write scope (build/+exports/+templates/ingested/,
evidence/extracts/, analysis/ respectively) — CLAUDE.md's subagent dispatch
section and their own frontmatter say so explicitly, but nothing enforced it:
settings.json's Write(./**)-family permissions are session-wide, not scoped
per agent identity, so any of the three could technically write into either
of the other two's directories, or anywhere else Write reaches (drafts/,
sources/, evidence/cards.jsonl's directory, etc. — the latter is separately
blocked by protect_data_files.py's filename-based check regardless of this
hook, but the directory-level isolation itself had no gate at all).

citation-verifier/literature-scout/qa-auditor are the mirror case: their own
.md frontmatter grants no Write/Edit/NotebookEdit at all and their contract
is "read-only, reports only" — but they DO hold Bash, so a stray shell
write-sink (redirect/tee/cp/mv) from one of them was constrained by nothing
but role convention. Scoping them to an EMPTY prefix tuple denies every
write destination; their legitimate script calls (e.g. literature-scout's
`python scripts/registry_db.py add ...`) are untouched since those are
subprocess invocations, not shell write-sink syntax this hook recognizes.

Hook input carries `agent_type` (the calling subagent's frontmatter `name`)
whenever a tool call happens inside a subagent context; it is ABSENT for the
main orchestrator session and for any subagent not listed in AGENT_SCOPES
below — both cases are intentionally left unrestricted by this hook (the
orchestrator legitimately writes drafts/outline/reviews/sources/evidence, and
every other subagent either holds no Write/Bash tool at all or isn't part of
this particular isolation claim).

Covers two tool surfaces per agent:
  - Write/Edit/NotebookEdit: file_path/notebook_path must fall under one of
    the agent's declared prefixes.
  - Bash: every write-sink DESTINATION (see _shell_write_sink.write_destinations
    — deliberately destination-only, not every cp/mv argument, so a normal
    `cp templates/x build/x` isn't flagged for its read-only source) must also
    fall under one of the agent's declared prefixes.

Change record: the narrative notes above are the point-of-use summary, not the
record. Full reasoning and rejected alternatives: DECISIONS.md (D-078, D-080,
D-081, D-083, D-084, D-091). Behaviour is locked by
tests/test_agent_write_scope_hook.py and the round suites listed under `hooks`
in tests/README.md.

Fail-open: malformed stdin, unknown agent_type, or an unexpected error while
evaluating the check never blocks the call — the same discipline every other
hook in this kit follows.
"""
import json
import posixpath
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _degrade import missing_tool_name, read_payload, report, report_contract
from _shell_write_sink import strip_heredocs, write_destinations

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

# Each value is the tuple of directory prefixes (relative to the project
# root, trailing slash) this agent may write under. Anything outside all of
# its own prefixes is denied. Agents that hold the Write tool AND make an
# explicit "by convention, only I write here" claim are listed with their
# real prefixes — see each agent's own .md frontmatter description for the
# source of each scope.
#
# citation-verifier/literature-scout/qa-auditor hold NO Write/Edit/
# NotebookEdit tool at all (their own .md frontmatter grants only Read/Bash/
# Grep/Glob/WebFetch/mcp__*) and their entire contract is read + report —
# "Read-only — writes nothing" / "reports discrepancies, never fixes them".
# That was previously enforced by role convention only: this hook only
# covered the three agents that legitimately write files, so a stray Bash
# write-sink (redirect/tee/cp/mv) from one of these three was constrained by
# nothing but the agent's own good behavior. An empty prefix tuple denies
# EVERY write destination for them (_in_scope() returns False for any path
# against an empty prefix list) — their sanctioned script calls (e.g.
# literature-scout's `python scripts/registry_db.py add ...`) are untouched
# because those are subprocess invocations, not shell write-sink syntax
# write_destinations() recognizes (no redirect/tee/cp/mv/open() literal in
# the command text), so this closes only the residual raw-shell-write gap.
AGENT_SCOPES = {
    "format-engineer": ("build/", "exports/", "templates/ingested/"),
    "source-analyst": ("evidence/extracts/",),
    "data-scientist": ("analysis/",),
    "citation-verifier": (),
    "literature-scout": (),
    "qa-auditor": (),
}

# The project root. Claude Code invokes every hook with cwd set to the
# project root (the same convention phase_gate.py relies on implicitly via
# its own bare relative paths like Path("outline/outline.md")), and the test
# suite replicates that by passing cwd=tmp_path — so Path.cwd() gives the
# right anchor in both production and tests, unlike deriving it from this
# hook file's own on-disk location (which is always the real repo root and
# can never equal a pytest tmp_path).
PROJECT_ROOT = Path.cwd().resolve()


def _norm_parts(path: str) -> tuple[str, ...]:
    return tuple(p for p in posixpath.normpath(path.replace("\\", "/")).split("/")
                 if p and p != ".")


def _scope_parts(path: str) -> tuple[str, ...]:
    """Return the path's components, reduced to project-relative form so the
    scope prefix can be anchored at the START of the path, not matched as a
    subsequence anywhere.

    An earlier version normalized every path and matched the scope prefix as a
    contiguous subsequence ANYWHERE in the components, to tolerate the absolute
    paths Write's file_path usually arrives as. That let a nested lookalike
    escape the gate — found live: format-engineer (scoped to templates/ingested/)
    could write evidence/templates/ingested/evil.md, and data-scientist (scoped
    to analysis/) could write sources/analysis/evil.md, because the scope name
    still appeared somewhere in the path. Anchoring the project-relative form at
    index 0 closes that: sources/analysis/... starts with "sources", not
    "analysis", so it no longer matches.

    An absolute path that can't be resolved under PROJECT_ROOT at all (points
    genuinely outside the project, or is an unresolvable UNC path) returns ()
    — never in scope for any non-empty prefix, i.e. denied. A prior version
    fell back to the subsequence match in this case, which let an
    out-of-project absolute path like C:\\Users\\Public\\build\\evil.dll match
    the "build/" scope purely because "build" appeared as a component
    somewhere in it."""
    raw = path.replace("\\", "/")
    p = Path(raw)
    if p.is_absolute():
        try:
            return _norm_parts(p.resolve().relative_to(PROJECT_ROOT).as_posix())
        except (ValueError, OSError):
            return ()
    return _norm_parts(raw)


# A sanctioned kit script's own primary-output flag. write_destinations() sees
# only shell write-sink SYNTAX (redirect/tee/cp/mv/open()), never the write a
# script performs internally through openpyxl/python-docx/etc. — so a scoped
# agent could smuggle a write past this hook via `xlsx_export.py --out <path>`.
_OUT_FLAG = re.compile(
    r"(?:^|\s)(?:--out|--output|--out-dir)(?:=|\s+)"
    r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\";|&]+))")


def _script_out_destinations(command: str) -> list[str]:
    """Primary-output paths a `scripts/…` invocation is directed at via an
    explicit --out/--output/--out-dir flag.

    Applied ONLY to the read-only (empty-scope) agents: they must write
    NOTHING, there is no legitimate --out usage for them, and the script's own
    subprocess write is invisible to write_destinations(). The WRITER agents
    are deliberately excluded — they have documented, in-scope --out flows
    (xlsx_export.py --out exports/…, make_reference_docx.py --out
    templates/…) that a blunt flag scan would risk false-denying, and their
    script writes already stay inside the project via each script's own
    require_within_cwd() guard. Heredoc bodies are stripped first so a report
    an agent authors via `cat <<EOF … EOF` that merely MENTIONS --out isn't
    read as an invocation."""
    if "scripts/" not in command and "scripts\\" not in command:
        return []
    command = strip_heredocs(command)
    return [next(g for g in m.groups() if g is not None)
            for m in _OUT_FLAG.finditer(command)]


def _in_scope(path: str, prefixes: tuple[str, ...]) -> bool:
    parts = _scope_parts(path)
    for prefix in prefixes:
        prefix_parts = tuple(p for p in prefix.rstrip("/").split("/") if p)
        if parts[:len(prefix_parts)] == prefix_parts:
            return True
    return False


def _reason(agent_type: str, path: str, prefixes: tuple[str, ...]) -> str:
    allowed = ", ".join(prefixes) if prefixes else "no path (read-only agent)"
    return (f"write-scope isolation: {agent_type} is scoped to {allowed} — "
            f"\"{path}\" falls outside its declared write scope.")


def main():
    # Fail-open on any unusable stdin, and never with a traceback: empty input
    # stays silent, input that will not parse — or that parses into something
    # other than an object — is reported. See _degrade.py.
    payload = read_payload('agent_write_scope', sys.stdin.read())
    if payload is None:
        sys.exit(0)

    agent_type = payload.get("agent_type")
    if agent_type not in AGENT_SCOPES:
        sys.exit(0)  # main session, or a subagent with no scope claim to enforce
    prefixes = AGENT_SCOPES[agent_type]

    # A recognized scoped agent whose payload carries no `tool_name` is the
    # harness contract having moved: `agent_type` still resolved, so this is
    # not somebody else's session, and the write scope simply stopped being
    # evaluated. Silence here would read as "in scope". See _degrade.py.
    if missing_tool_name(payload):
        report_contract(f'agent_write_scope ({agent_type})', "no 'tool_name' key")
        sys.exit(0)

    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    reason = None
    try:
        if tool in ("Write", "Edit", "NotebookEdit"):
            path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
            if isinstance(path, str) and path and not _in_scope(path, prefixes):
                reason = _reason(agent_type, path, prefixes)
        elif tool == "Bash":
            command = tool_input.get("command", "")
            if isinstance(command, str) and command:
                targets = list(write_destinations(command))
                if not prefixes:  # read-only agent: also close the script --out escape
                    targets += _script_out_destinations(command)
                for target in targets:
                    if not _in_scope(target, prefixes):
                        reason = _reason(agent_type, target, prefixes)
                        break
    except Exception as exc:
        # Fail-open backstop, matching phase_gate.py/protect_data_files.py:
        # an unexpected error while evaluating the check must never block
        # every Write/Edit/Bash call for the affected agent — but it must also
        # not look like a clean pass, which is the one thing a scope check
        # silently returning None cannot be told apart from. See _degrade.py.
        report(f"agent_write_scope ({agent_type})", "this subagent's write scope", exc)
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
