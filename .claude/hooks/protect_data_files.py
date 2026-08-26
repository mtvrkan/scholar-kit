#!/usr/bin/env python3
"""PreToolUse hook — block direct writes to script-owned data files.

registry.jsonl, cards.jsonl, venues.jsonl, search-log.jsonl, references.bib,
and verify-status.json may only be mutated through scripts/ (Invariant 6:
data integrity via scripts — verify-status.json joined this list once
write_verify_status.py existed as a sanctioned writer; previously it had no
script-owned protection at all, since citation-verifier itself holds no
Write tool and the orchestrator wrote it directly).
This hook enforces it deterministically for ANY path shape (the settings.json
deny list only covers project-relative literals) across TWO tool surfaces:
  - Write/Edit/NotebookEdit: blocked by file_path name (as before).
  - Bash: most agents hold Bash and could otherwise redirect/tee/python -c
    their way around the Write/Edit block entirely — this was a real gap
    (Invariant 6 was enforced only for Write|Edit|NotebookEdit). Best-effort
    pattern match on shell redirection / tee / cp/mv / rm/del/Remove-Item /
    sed/awk/perl -i / PowerShell cmdlets / Python one-liners (open(), shutil,
    pathlib) writing to a protected filename; NOT a sandbox — a sufficiently
    obfuscated command (variable indirection, base64, etc.) can still slip
    through. cp/mv check EVERY argument, not just the destination — moving a
    protected file away from its required path is data loss even though
    nothing is "written" to it, and an earlier version only checked the last
    token (the destination), missing `mv registry.jsonl /tmp/out.bak`.
    An earlier version of this hook trusted any command that merely
    mentioned a sanctioned script's filename ANYWHERE (even in an unrelated
    echo string or comment) — that was a one-token bypass, not "deliberate
    evasion." This version has no such blanket trust list: it matches
    precisely on write-sink SYNTAX (redirect operators, tee, cp/mv, in-place
    editors, PowerShell write cmdlets, open()/shutil/pathlib write calls),
    which is what actually distinguishes a write from a read/argument
    mention — `python scripts/registry_db.py --file sources/registry.jsonl
    stats` is correctly allowed (no write-sink syntax present) without
    needing to special-case the script name at all.
Fail-open: unexpected stdin → exit 0.

NOT THE ONLY LAYER, as of the OS-permission change: `scripts/lib_common.py`
marks these six files read-only after every sanctioned write, so `>`, `tee`,
`Set-Content` and `open(p, "w")` are refused by the filesystem regardless of
what this hook recognised. The division of labour is deliberate and neither
half is redundant:
  - the permission bit stops WRITES without needing to parse anything, which
    is what makes it immune to the evasion class this file keeps discovering;
  - this hook stops `rm`/`del`/`Remove-Item -Force` and `mv`, which the
    permission bit CANNOT stop (deletion and rename are governed by the
    directory's permission, not the file's), and it explains itself in the
    denial message where a bare EACCES would not.
A change that weakens either half should say which half is now carrying the
case it dropped.

Change record: the "an earlier version…" notes above are the point-of-use
summary — kept here on purpose, because a bypass that has already been shipped
once is exactly what a reader editing this file needs in front of them. They are
NOT the record. The full reasoning, the review pass that found each defect and
the alternatives rejected live in DECISIONS.md (D-065, D-066, D-068..D-073,
D-075, D-077, D-078, D-080, D-081, D-083, D-091); the behaviour is locked by
tests/test_protect_data_files_hook.py and the round suites listed under `hooks`
in tests/README.md. If the two ever disagree, DECISIONS.md is authoritative for
*why* and the tests are authoritative for *what*.
"""
import fnmatch
import json
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
from _degrade import missing_tool_name, read_payload, report, report_contract
from _project_scope import is_kit_project
from _shell_write_sink import write_targets

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

PROTECTED = {
    "registry.jsonl": "python scripts/registry_db.py",
    "cards.jsonl": "python scripts/evidence_db.py",
    "venues.jsonl": "python scripts/venue_check.py",
    "search-log.jsonl": "python scripts/registry_db.py log-query",
    # All three verbs, deliberately: the message is the only thing a blocked
    # user reads, and naming only the two that ADD entries is what sent an
    # author holding a freshly-detected fabricated citation into a hand-edit
    # this hook then refused, with nowhere left to go.
    "references.bib": ("python scripts/doi2bib.py --append / bib_doctor.py --fix / "
                       "bib_doctor.py --retract <key>"),
    "verify-status.json": "python scripts/write_verify_status.py",
    # Append-only by construction: the sanctioned writer only ever adds a record
    # whose `prev` names the current tail. An Edit is therefore not a smaller
    # version of a legitimate operation here, it is the one operation the ledger
    # exists to make impossible to do quietly.
    "provenance.jsonl": "python scripts/provenance.py --record <event> --path <file>",
    "datasets.jsonl": "python scripts/dataset_db.py add / attach / set-field",
    "runs.jsonl": "python scripts/experiment_db.py add",
}


def _protected_name(path_str: str) -> str | None:
    name = PurePosixPath(path_str.replace("\\", "/")).name.lower()
    if name in PROTECTED:
        return name
    # A glob target (`mv sources/*.jsonl /tmp/`, `Move-Item sources/*.jsonl ...`)
    # never equals a protected basename literally — the wildcard IS the literal
    # last path component — so the exact-match check above always missed it,
    # even though the shell would actually expand it to include a protected
    # file. fnmatch each protected name against the wildcard pattern: it's the
    # same match direction a shell glob would perform.
    if any(ch in name for ch in "*?["):
        for prot in PROTECTED:
            if fnmatch.fnmatch(prot, name):
                return prot
    return None


def _bash_target(command: str) -> str | None:
    """Best-effort: does this shell command write/move/delete a protected
    file? Returns the protected filename if any detected write-sink target
    matches, else None."""
    for target in write_targets(command):
        hit = _protected_name(target)
        if hit:
            return hit
    return None


def main():
    # Fail-open on any unusable stdin, and never with a traceback: empty input
    # stays silent, input that will not parse — or that parses into something
    # other than an object — is reported. See _degrade.py.
    payload = read_payload('protect_data_files', sys.stdin.read())
    if payload is None:
        sys.exit(0)
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    # `references.bib` is in essentially every LaTeX repository ever written.
    # Installed as a plugin this hook runs in every session, so without this
    # check it would deny edits to an unrelated project's bibliography and
    # tell the author to use a script they do not have. See _project_scope.py.
    if not is_kit_project():
        sys.exit(0)

    # Scoped to a real kit project, a payload with no `tool_name` cannot be an
    # ordinary call: it is the harness contract having moved. Announced rather
    # than exited on, because "no branch matched" and "this gate no longer
    # understands its input" are otherwise the same zero bytes. See _degrade.py.
    if missing_tool_name(payload):
        report_contract('protect_data_files', "no 'tool_name' key")
        sys.exit(0)

    name = None
    try:
        if tool in ("Write", "Edit", "NotebookEdit"):
            # NotebookEdit's payload key is "notebook_path", not "file_path" — the
            # matcher in settings.json includes NotebookEdit, but reading only
            # "file_path" left this branch permanently dead for it.
            path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
            if isinstance(path, str) and path:
                name = _protected_name(path)
        elif tool == "Bash":
            command = tool_input.get("command", "")
            if isinstance(command, str) and command:
                name = _bash_target(command)
    except Exception as exc:
        # This evaluation used to run unguarded, so a raise here left the hook
        # exiting on a traceback: still fail-open in effect (a non-blocking
        # error), but reported as a crash rather than as a check that did not
        # run, and inconsistent with the other three gates. Same contract as
        # theirs now — allowed, and said out loud. See _degrade.py.
        report(f"protect_data_files ({tool})", "data-file protection", exc)
        sys.exit(0)

    if name:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"{name} is script-owned (Invariant 6) — mutate it via: "
                    f"{PROTECTED[name]}. Direct edits corrupt the evidence chain."),
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    main()
