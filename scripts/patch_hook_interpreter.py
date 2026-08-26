#!/usr/bin/env python3
"""patch_hook_interpreter.py — rewrite .claude/settings.json hook commands to
invoke a specific Python interpreter (e.g. "python3 ..." -> "python ...").

This is the actual logic behind INSTALL.sh's patch_hooks() / INSTALL.ps1's
Update-HookInterpreter, extracted into a standalone script after the same
interpreter-drift bug (committed file says "python3" while the detected
interpreter is "python", or vice versa) recurred three times with zero
regression-test coverage each time (see DECISIONS.md D-017, D-027, D-041) —
bash heredocs and PowerShell cmdlets aren't unit-testable from pytest, but a
plain Python function is.

Usage:
  python scripts/patch_hook_interpreter.py --target python [--settings .claude/settings.json]
Exit codes: 0 always (missing settings.json is not an error — nothing to patch).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, file_lock, require_within_cwd, write_json_atomic

# Leading interpreter token to rewrite: python / python3 / python3.11 /
# python3.11.2 / py, optional .exe, then a space. An earlier fixed-string
# prefix list ("python3 "/"python "/"py ") silently no-oped on a versioned
# interpreter like `python3.11 ...` — a real interpreter-drift form on systems
# where that's the detected command. Matched case-insensitively for the
# Windows `Python`/`PY` spellings.
_LEADING_INTERP = re.compile(r"^(?:python3?(?:\.\d+)*|py)(?:\.exe)?\s+", re.IGNORECASE)
# --target is spliced verbatim into a hook "command" string persisted to
# settings.json and later executed by the shell on every hook invocation —
# an unvalidated value (shell metacharacters, whitespace, quotes) would
# persist a command-injection payload into the project's own config. Only
# allow a bare interpreter token/path: no whitespace, quotes, or shell
# metacharacters (;&|`$(){}<>!\n).
_SAFE_TARGET_RE = re.compile(r"^[A-Za-z0-9_./\\:-]+$")
# Character-safety alone isn't enough: this script is reachable through the
# already-allowed "Bash(python scripts/*)" permission with no confirmation
# prompt, so --target is effectively attacker/agent-controlled input. Without
# a further check, a syntactically-safe-but-arbitrary path like
# "C:\temp\evil.exe" would pass _SAFE_TARGET_RE and get spliced in as the
# interpreter for EVERY hook command, silently disabling the whole
# enforcement layer on the next hook invocation. Require the target's own
# basename to look like a real python/python3/py interpreter — this still
# accepts any path (venv interpreters, "/usr/bin/python3",
# "C:\Python311\python.exe" — see test_patch_hook_interpreter_accepts_plain_
# interpreter_tokens, an intentional prior-round contract), just not an
# arbitrarily-named binary.
_INTERP_BASENAME_RE = re.compile(r"^(?:python3?(?:\.\d+)*|py)(?:\.exe)?$", re.IGNORECASE)


def patch(cfg: dict, target: str) -> bool:
    """Rewrite every hook command's leading python/python3 to `target`, in place.
    Returns True if anything changed. Validates the settings.json hooks
    structure shape-by-shape (event -> array, entry -> object, .hooks ->
    array, each hook -> object) rather than trusting it, since a malformed
    file (a hook group persisted as a bare string, "hooks" persisted as a
    dict instead of a list, ...) used to crash with a raw AttributeError
    instead of this module's documented ERROR:/exit-1 contract."""
    if not isinstance(cfg, dict):
        die(f"settings.json must be a JSON object, got {type(cfg).__name__}")
    hooks = cfg.get("hooks") or {}
    if not isinstance(hooks, dict):
        die(f"settings.json's \"hooks\" key must be an object, got {type(hooks).__name__}")
    changed = False
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            die(f"settings.json hooks.{event} must be an array, got {type(groups).__name__}")
        for g in groups:
            if not isinstance(g, dict):
                die(f"settings.json hooks.{event}[] entry must be an object, got {type(g).__name__}")
            hook_list = g.get("hooks", [])
            if not isinstance(hook_list, list):
                die(f"settings.json hooks.{event}[].hooks must be an array, got {type(hook_list).__name__}")
            for h in hook_list:
                if not isinstance(h, dict):
                    die(f"settings.json hooks.{event}[].hooks[] entry must be an object, "
                        f"got {type(h).__name__}")
                c = h.get("command", "")
                if not isinstance(c, str):
                    continue
                m = _LEADING_INTERP.match(c)
                if m:
                    new = f"{target} " + c[m.end():]
                    if new != c:
                        h["command"] = new
                        changed = True
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True,
                     help="interpreter command hooks should invoke, e.g. python/python3/py")
    ap.add_argument("--settings", default=".claude/settings.json")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    if not _SAFE_TARGET_RE.match(args.target):
        die(f"--target '{args.target}' is not a plain interpreter token/path "
            f"(no spaces, quotes, or shell metacharacters allowed)")
    basename = Path(args.target.replace("\\", "/")).name
    if not _INTERP_BASENAME_RE.match(basename):
        die(f"--target '{args.target}' does not look like a python/python3/py "
            f"interpreter (basename '{basename}' doesn't match) — refusing to "
            f"rewrite every hook command to an arbitrary binary")
    require_within_cwd(args.settings, "--settings")

    p = Path(args.settings)
    if not p.exists():
        emit({"changed": False, "reason": f"{p} not found"}, True)
        return
    try:
        with file_lock(p):
            cfg = json.loads(p.read_text(encoding="utf-8"))
            changed = patch(cfg, args.target)
            if changed:
                write_json_atomic(p, cfg)
    except json.JSONDecodeError as e:
        die(f"{p} is not valid JSON — {e.msg}")
    except UnicodeDecodeError as e:
        die(f"{p} is not valid UTF-8 ({e}) — fix the encoding before re-running")
    except TimeoutError as e:
        die(str(e))
    except OSError as e:
        die(f"failed to write {p} — {e}")
    emit({"changed": changed, "target": args.target, "settings": p.as_posix()}, True)


if __name__ == "__main__":
    main()
