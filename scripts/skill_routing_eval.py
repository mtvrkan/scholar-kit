#!/usr/bin/env python3
"""skill_routing_eval.py — structural checks for eval/golden-prompts.json.

Verifies every golden prompt's "expect" field names a real skill, and that the
set covers a reasonable share of the catalog. This is the STATIC half of the
routing eval; live accuracy (does a fresh model actually pick the right skill
given only name+description, the way Claude Code's own router does) requires
an actual model call and is run out-of-band (see ROUTING-EVAL.md for the most
recent live result — reproduce it with a fresh Agent/Task call fed
scripts/extract_skill_descriptions.py's output + eval/golden-prompts.json).

Usage: python scripts/skill_routing_eval.py [--json]
Exit codes: 0 clean · 2 problems found.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd  # noqa: E402,F401 (utf-8 guard via lib_common)

ROOT = Path(__file__).parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prompts", default="eval/golden-prompts.json")
    ap.add_argument("--require-full-coverage", action="store_true",
                    help="treat a skill with no golden prompt as a problem (exit 2). "
                         "Off by default because a caller may legitimately score a "
                         "partial file; ON for the shipped set, gated by "
                         "tests/test_governance_docs.py")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    # Validate the path this script ACTUALLY reads (ROOT / args.prompts), not
    # args.prompts on its own: the read target and the traversal-guard target
    # used to diverge — require_within_cwd(args.prompts) resolved against cwd
    # while the read resolved against ROOT, so a relative --prompts run from a
    # subdirectory was validated as one file and then silently read as another.
    # Guarding the real read target keeps them identical (and, for the absolute
    # paths the tests pass, `ROOT / abs` == abs, so behavior there is unchanged).
    prompts_path = ROOT / args.prompts
    require_within_cwd(str(prompts_path), "--prompts")
    if not prompts_path.exists():
        die(f"{args.prompts} not found")
    try:
        prompts = json.loads(prompts_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{args.prompts} is not valid JSON — {e.msg}")
    if not isinstance(prompts, list):
        die(f"{args.prompts} must be a JSON array of prompt objects, got "
            f"{type(prompts).__name__}")

    try:
        skills_raw = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "extract_skill_descriptions.py")],
            capture_output=True, text=True, encoding="utf-8", cwd=ROOT, timeout=60)
    except subprocess.TimeoutExpired:
        die("extract_skill_descriptions.py timed out (>60s)")
    if skills_raw.returncode != 0:
        die(f"extract_skill_descriptions.py failed (exit {skills_raw.returncode}) — {skills_raw.stderr.strip()}")
    try:
        catalog = {s["skill"] for s in json.loads(skills_raw.stdout)}
    except json.JSONDecodeError as e:
        die(f"extract_skill_descriptions.py did not emit valid JSON — {e.msg}")

    problems = []
    covered = set()
    for i, p in enumerate(prompts):
        if not isinstance(p, dict):
            die(f"{args.prompts} entry {i} is not a JSON object, got {type(p).__name__}")
        if not p.get("prompt"):
            problems.append(f"entry {i}: missing 'prompt'")
        expect = p.get("expect")
        if not expect:
            problems.append(f"entry {i}: missing 'expect'")
        elif expect not in catalog:
            problems.append(f"entry {i}: expect='{expect}' is not a real skill")
        else:
            covered.add(expect)

    # A skill with no golden prompt is a skill whose description has never been
    # put in front of a router. That was reported and not counted: the shipped
    # set drifted to 26 of 28 covered (disclosures, restyle) while
    # ROUTING-EVAL.md still read "full coverage", because nothing failed when a
    # new skill arrived without a prompt. Adding a skill is exactly the moment
    # the gap opens, so the check belongs on the same run that adds it.
    uncovered = catalog - covered
    if args.require_full_coverage and uncovered:
        problems.append(
            "skills with no golden prompt: " + ", ".join(sorted(uncovered)) +
            " — every skill in the catalog needs at least one prompt, or its "
            "description is unrouted and unmeasured")
    result = {
        "total_prompts": len(prompts),
        "skills_in_catalog": len(catalog),
        "skills_covered_by_eval": len(covered),
        "skills_uncovered": sorted(uncovered),
        "problems": problems,
    }
    emit(result, True)
    sys.exit(2 if problems else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a kit file — {e}")
    except UnicodeDecodeError as e:
        die(f"a kit file is not valid UTF-8 — {e}")
