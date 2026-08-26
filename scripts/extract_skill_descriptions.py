#!/usr/bin/env python3
"""extract_skill_descriptions.py — dump name+description of every SKILL.md as JSON.

Used by the routing eval harness to build the exact catalog Claude Code sees when
choosing a skill (skill metadata is preloaded every session; bodies load on trigger).

Usage: python scripts/extract_skill_descriptions.py [--json]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import emit, parse_frontmatter as frontmatter  # noqa: E402

ROOT = Path(__file__).parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", dest="json_out", action="store_true", default=True)
    ap.parse_args()  # output is always JSON; the flag is accepted for consistency
    out = []
    for p in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        # Per-file guard: one unreadable/malformed SKILL.md must not abort the
        # whole catalog dump the routing eval depends on. A skipped skill still
        # carries its name, so the eval flags it as uncovered rather than
        # crashing with a raw traceback.
        try:
            fm = frontmatter(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            out.append({"skill": p.parent.name, "description": "", "is_command": False,
                        "error": str(e)})
            continue
        out.append({"skill": p.parent.name, "description": fm.get("description", ""),
                    "is_command": fm.get("disable-model-invocation") == "true"})
    emit(out, True)


if __name__ == "__main__":
    main()
