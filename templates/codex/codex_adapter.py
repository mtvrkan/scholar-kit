#!/usr/bin/env python3
"""codex_adapter.py — run the kit's enforcement hooks under OpenAI Codex.

The gates live in `.claude/hooks/` and are written against Claude Code's hook
payload. Codex speaks almost the same contract — same event names, same
`hookSpecificOutput.permissionDecision` reply, same `agent_type` field for a
subagent, and shell commands arrive as `tool_name: "Bash"` with
`tool_input.command` exactly as they do in Claude Code. Three things differ,
and this file is the whole of the difference:

  1. FILE EDITS. Codex has one editing tool, `apply_patch`, and its payload is
     `{"tool_name": "apply_patch", "tool_input": {"command": "<patch text>"}}`.
     There is no `file_path`. Every gate dispatches on `Write`/`Edit` +
     `file_path`, so an unadapted gate sees a tool name it does not know and
     answers with zero bytes — every file edit in the project ungated, and
     nothing anywhere saying so. The adapter reads the patch envelope's
     `*** Add File:` / `*** Update File:` / `*** Delete File:` / `*** Move to:`
     headers and asks the gate once per touched path, as a `Write` (added
     file) or `Edit` (everything else). One denial denies the whole patch.

  2. NO TOOL ALLOWLIST FOR SUBAGENTS. In Claude Code a read-only agent is
     read-only because its frontmatter grants no Write tool. A Codex custom
     agent inherits the session's tools; its file can only ask. So for
     `agent_write_scope` the adapter derives the same contract from the same
     frontmatter: an agent whose `.claude/agents/<name>.md` grants no
     Write/Edit/NotebookEdit and that the hook does not already scope is
     treated as read-only (empty scope). Nothing is invented here — the list
     is read from the files that define the agents.

  3. A SHELL COMMAND MAY ARRIVE AS A LIST. Normalised to the string the gates
     parse.

Everything else passes through byte for byte: the hook's stdout, stderr and
exit code are the adapter's. The gates themselves are not modified and are not
copied — a project carries one enforcement layer, used by both harnesses.

Fail-open, like every gate it fronts, and never silently: a patch whose
touched paths cannot be read is reported through `_degrade` as a check that
did not run, not answered with silence.

This file is the SOURCE. scripts/codex_sync.py copies it to
`codex/hooks/codex_adapter.py` in the kit and to `.codex/hooks/codex_adapter.py`
in a project; all three sit two levels below the directory that holds
`.claude/`, which is how the gates are found.

Usage (wired by the generated hooks.json):
    python .codex/hooks/codex_adapter.py <hook-name>     # payload on stdin

Change record: DECISIONS.md D-099. Behaviour is locked by
tests/test_codex_adapter.py — see `hooks` in tests/README.md.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shlex
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
HOOKS_DIR = PROJECT / ".claude" / "hooks"
AGENTS_DIR = PROJECT / ".claude" / "agents"

# The hooks a command line may name. A closed list, not "any file in the
# directory": the argument comes from a hooks.json a project can edit, and the
# adapter imports and runs what it is pointed at.
HOOKS = ("protect_data_files", "phase_gate", "agent_write_scope",
         "template_supremacy_gate", "cite_warn", "session_status",
         "enforcement_notice")

_PATCH_HEADER = re.compile(
    r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+?)\s*$", re.MULTILINE)
_WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}


def patch_paths(patch: str) -> list[tuple[str, str]]:
    """(claude_tool, path) for every file an apply_patch envelope touches.

    An added file is a `Write`; an update, a delete and a move destination are
    an `Edit`. The distinction is cosmetic for the gates (they treat the three
    write tools alike) and kept only so a denial message reads naturally.
    Order preserved, duplicates dropped.
    """
    seen, out = set(), []
    for kind, path in _PATCH_HEADER.findall(patch):
        path = path.strip()
        if not path or path in seen:
            continue
        seen.add(path)
        out.append(("Write" if kind == "Add File" else "Edit", path))
    return out


def shell_command_text(command) -> str | None:
    """The command as the single string the gates parse, or None if unusable.

    `["bash", "-lc", "<script>"]` yields the script itself — quoting it back
    into one argument would hide its redirects from the write-sink parser.
    """
    if isinstance(command, str):
        return command
    if isinstance(command, list) and command and all(isinstance(c, str) for c in command):
        if len(command) >= 3 and command[1] in ("-lc", "-c"):
            return command[2]
        return shlex.join(command)
    return None


def readonly_agents() -> set[str]:
    """Agents whose own frontmatter grants no file-writing tool."""
    names = set()
    try:
        files = sorted(AGENTS_DIR.glob("*.md"))
    except OSError:
        return names
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = re.match(r"﻿?---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            continue
        name = re.search(r"^name:\s*(\S+)\s*$", m.group(1), re.MULTILINE)
        tools = re.search(r"^tools:\s*(.+)$", m.group(1), re.MULTILINE)
        if not name or not tools:
            continue
        granted = {t.strip() for t in tools.group(1).split(",")}
        if not granted & _WRITE_TOOLS:
            names.add(name.group(1))
    return names


def load_hook(name: str):
    """Import a gate module without running it (its `main` is called later)."""
    sys.path.insert(0, str(HOOKS_DIR))
    spec = importlib.util.spec_from_file_location(
        f"scholar_kit_hook_{name}", HOOKS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if name == "agent_write_scope":
        scopes = getattr(module, "AGENT_SCOPES", None)
        if isinstance(scopes, dict):
            for agent in readonly_agents():
                scopes.setdefault(agent, ())
    return module


def run_hook(module, payload_text: str) -> tuple[int, str, str]:
    """Call a gate's main() on one payload. Returns (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    stdin = sys.stdin
    sys.stdin = io.StringIO(payload_text)
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                module.main()
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    finally:
        sys.stdin = stdin
    return code, out.getvalue(), err.getvalue()


def _json_lines(text: str) -> list[dict]:
    objs = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict):
            objs.append(obj)
    return objs


def _is_deny(obj: dict) -> bool:
    specific = obj.get("hookSpecificOutput")
    return isinstance(specific, dict) and specific.get("permissionDecision") == "deny"


def merge(results: list[tuple[int, str, str]]) -> tuple[int, str, str]:
    """Fold the per-path answers of one patch into a single hook answer.

    A denial for any path is the answer for the patch. Otherwise the notices
    (`systemMessage`) are kept, de-duplicated; stderr is concatenated and the
    highest exit code wins, so cite_warn's exit-2 feedback survives a patch
    that also touched a clean file.
    """
    code = max((r[0] for r in results), default=0)
    err_parts, messages, deny = [], [], None
    for _, out, err in results:
        if err.strip() and err.strip() not in err_parts:
            err_parts.append(err.strip())
        for obj in _json_lines(out):
            if deny is None and _is_deny(obj):
                deny = obj
            msg = obj.get("systemMessage")
            if isinstance(msg, str) and msg and msg not in messages:
                messages.append(msg)
    stderr = "\n".join(err_parts) + ("\n" if err_parts else "")
    if deny is not None:
        return code, json.dumps(deny) + "\n", stderr
    if messages:
        return code, json.dumps({"systemMessage": "\n".join(messages)}) + "\n", stderr
    return code, "", stderr


def translate(payload: dict, degrade, hook: str) -> list[dict] | None:
    """Claude-shaped payloads for one Codex payload; None means pass it as is."""
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if tool == "apply_patch":
        patch = tool_input.get("command") if isinstance(tool_input, dict) else tool_input
        paths = patch_paths(patch) if isinstance(patch, str) else []
        if not paths:
            # Shape only, never the patch text: it is manuscript content.
            degrade.report_contract(
                f"{hook} (codex adapter)",
                "apply_patch payload names no touched file")
            return []
        return [{**payload, "tool_name": claude_tool, "tool_input": {"file_path": path}}
                for claude_tool, path in paths]
    if tool == "Bash" and isinstance(tool_input, dict) \
            and not isinstance(tool_input.get("command"), str):
        text = shell_command_text(tool_input.get("command"))
        if text is not None:
            return [{**payload, "tool_input": {**tool_input, "command": text}}]
    return None


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in HOOKS:
        print(f"usage: codex_adapter.py <{'|'.join(HOOKS)}>", file=sys.stderr)
        return 0  # a mis-wired command must not block the tool call
    hook = sys.argv[1]
    raw = sys.stdin.read()
    try:
        module = load_hook(hook)
        import _degrade as degrade  # the hooks' own reporter; on sys.path now
    except Exception as exc:  # the gate could not even be loaded
        text = (f"⚠ Scholar-Kit gate degraded: {hook} could not be loaded by the "
                f"Codex adapter ({type(exc).__name__}). The call was ALLOWED — "
                f"this check did not run.")
        print(json.dumps({"systemMessage": text}))
        print(text, file=sys.stderr)
        return 0

    payloads = None
    try:
        parsed = json.loads(raw) if raw.strip() else None
        if isinstance(parsed, dict):
            payloads = translate(parsed, degrade, hook)
    except ValueError:
        payloads = None  # unparseable: let the gate report it in its own words

    try:
        if payloads is None:
            code, out, err = run_hook(module, raw)
        else:
            code, out, err = merge(
                [run_hook(module, json.dumps(p)) for p in payloads])
    except Exception as exc:
        degrade.report(f"{hook} (codex adapter)", "the hook", exc)
        return 0
    sys.stdout.write(out)
    sys.stderr.write(err)
    return code


if __name__ == "__main__":
    sys.exit(main())
