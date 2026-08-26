#!/usr/bin/env python3
"""SessionStart hook — print the first 15 lines of drafts/STATUS.md so every session
resumes with project context for pennies. Silent when no STATUS.md exists.

Change record: DECISIONS.md (D-065, D-075, D-091). Behaviour is locked by
tests/test_session_status_hook.py — see `hooks` in tests/README.md."""
import sys

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

import json
import sys
from pathlib import Path


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    # Valid JSON that is not an object (`[]`, `"x"`, `123`) parses fine and then
    # raises AttributeError on `.get` — outside the try, so this hook answered a
    # shape change with a traceback. It stays SILENT rather than reporting like
    # the gates do: this hook prints status, it does not enforce anything, and a
    # degradation notice for a cosmetic no-op is noise. See _degrade.py.
    if not isinstance(payload, dict):
        payload = {}
    project_dir = Path(payload.get("cwd") or ".")
    status = project_dir / "drafts" / "STATUS.md"
    if not status.exists():
        sys.exit(0)
    lines = status.read_text(encoding="utf-8", errors="replace").splitlines()[:15]
    print("=== scholar-kit STATUS (drafts/STATUS.md) ===")
    print("\n".join(lines))
    sys.exit(0)


if __name__ == "__main__":
    main()
