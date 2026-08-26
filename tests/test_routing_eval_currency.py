"""ROUTING-EVAL.md may not claim more live coverage than it has.

The document already had a gate, and the gate held: when two skills shipped
without prompts, `--require-full-coverage` started exiting 2 and
`test_routing_eval_doc_numbers_match_the_artifacts` pinned the "N prompts / M
skills" line to the files. At the time of writing that line reads 95/54 and is
correct.

One sentence below it, the accuracy claim read:

    Current measured accuracy: 48 of 48 (run 5). Every prompt in the shipped
    set has now been scored live.

True the day it was written, at 48/28. The set then grew through 50/29, 54/31,
56/32 and 65/39 to 95/54 — and the sentence did not move. A gate on the
denominator does not gate the sentence that uses it: the size line was derived
and honest while the claim built on it silently became a statement that 47
prompts and 26 skills had been measured when none of them had.

So this file gates the CLAIM, not the number. The accuracy value itself is
still deliberately unpinned, for the reason the older test gives: it comes from
a model run, and pinning it would only pin the last time somebody typed it.
What is checkable is scope — how many of the shipped prompts that figure covers,
and whether the prose oversells it. Three checks:

  - the "Live-scored: N of M prompts" line exists and M is the real set size,
    so growing the set forces the line to be revisited;
  - N never exceeds M;
  - while N < M, no full-coverage wording may appear in the page's own prose.

The third check reads the page with blockquotes stripped. A page that records
why its own claim went stale has to be able to quote the retired sentence, and
a checker that cannot tell `> Every prompt ... has now been scored live` from
an assertion of the same words is the "lint that fires on correct prose" this
repository refuses elsewhere. The rule is therefore positional and simple:
inside `>`, it is history; outside `>`, it is a claim.

Re-running the live eval is what clears this: score the whole set under the
blind protocol in "Reproducing", then set N to what was actually scored.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
DOC = ROOT / "eval" / "ROUTING-EVAL.md"

# Wordings that assert the whole shipped set has been measured. Each is a real
# phrasing this page has used or would plausibly reach for; the point is that
# "we measured everything" cannot be said while the counts disagree.
FULL_COVERAGE_CLAIMS = [
    r"every prompt in the shipped set has (?:now )?been scored",
    r"every prompt (?:has|had) (?:now )?been scored live",
    r"the (?:whole|entire|full|complete) (?:shipped )?set has (?:now )?been scored",
    r"all \d+ prompts (?:have|had) been scored",
    r"full live coverage",
]


def _doc() -> str:
    return DOC.read_text(encoding="utf-8")


def _doc_prose() -> str:
    """The page minus its blockquotes — what it asserts, not what it quotes."""
    kept = [ln for ln in _doc().splitlines() if not ln.lstrip().startswith(">")]
    return "\n".join(kept)


def _shipped_set_size() -> int:
    """The set size as the static checker derives it — never as prose states it."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "skill_routing_eval.py")],
        capture_output=True, text=True, cwd=ROOT,
    )
    return json.loads(proc.stdout)["total_prompts"]


def _live_scored() -> tuple[int, int]:
    m = re.search(r"Live-scored:\s*\*?\*?\s*(\d+)\s+of\s+(\d+)\s+prompts", _doc())
    assert m, (
        "ROUTING-EVAL.md no longer carries a 'Live-scored: N of M prompts' line. "
        "That line is how this page states how much of the shipped set its "
        "accuracy figure actually covers, and removing it removes the only "
        "machine-checkable version of that claim. Restore it, or replace this "
        "test with one that gates whatever states the same thing."
    )
    return int(m.group(1)), int(m.group(2))


def test_the_live_scored_line_names_the_real_set_size():
    """Growing the golden set must force the coverage claim to be revisited."""
    scored, of = _live_scored()
    shipped = _shipped_set_size()
    assert of == shipped, (
        f"ROUTING-EVAL.md says the accuracy figure covers {scored} of {of} "
        f"prompts, but the shipped golden set now holds {shipped}. The set grew "
        "and the coverage claim did not follow — the exact drift this file "
        f"exists to stop. Either re-run the live eval over all {shipped} and "
        f"update both numbers, or set the line to 'Live-scored: {scored} of "
        f"{shipped} prompts' and say which ones were never scored."
    )


def test_no_more_prompts_are_claimed_scored_than_the_set_holds():
    scored, of = _live_scored()
    assert scored <= of, (
        f"ROUTING-EVAL.md claims {scored} prompts scored out of a set of {of}."
    )


@pytest.mark.parametrize("claim", FULL_COVERAGE_CLAIMS)
def test_full_coverage_is_not_claimed_while_the_set_is_partly_unscored(claim):
    scored, of = _live_scored()
    if scored >= of:
        pytest.skip("the whole set is live-scored; full-coverage wording is earned")
    hit = re.search(claim, _doc_prose(), re.IGNORECASE)
    assert not hit, (
        f"ROUTING-EVAL.md states {scored} of {of} prompts have been live-scored, "
        f"yet the page also asserts, outside any blockquote: {hit.group(0)!r}. "
        "That is the sentence that "
        "went stale before — a full-coverage claim outliving the set it was "
        "true for. Remove it, or re-run the eval so it becomes true again."
    )
