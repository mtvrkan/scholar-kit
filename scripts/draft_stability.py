#!/usr/bin/env python3
"""draft_stability.py — measure the drafting stage without a gold set.

WHY THIS EXISTS
`eval/MEASUREMENT.md` splits the kit in two: the deterministic checkers are
scored against labelled gold sets, and everything LLM-mediated — drafting,
synthesis, the style audit — is recorded as **not measured**, because no gold set
exists and the kit refuses to invent one (POSITIONING.md). That refusal is right
and it is not going to change: a fabricated label makes the number worse than
absent, since it is then believed.

But "no labels" rules out ACCURACY, not measurement. There is one property of a
drafting stage that needs no ground truth at all: render the same section from
the same evidence twice, and the things that must not vary — which sources are
cited, which numbers are reported, how strongly each source is claimed — either
agree or they do not. Where they disagree, at least one rendering put something
in the text that did not come from the evidence, and no reference answer is
needed to know that.

This is the same instrument `/critique --calibrate` already applies to the
reviewer, pointed at the stage that produces the manuscript. It closes the
architectural half of the gap: every LLM-mediated stage in the kit now has at
least one measurement that can actually be run, rather than a paragraph
explaining why it cannot.

WHAT IT CANNOT TELL YOU — read before quoting any number it prints
Stability is not accuracy. A drafting stage that cites the same wrong source
every single time scores 1.00 here. MEASUREMENT.md states this for the reviewer
and it is no weaker in this direction: agreement is evidence about VARIANCE, and
variance is only one of the two ways a stage is wrong. A perfect score here means
"this section is reproducible from its evidence", never "this section is right".

It also cannot see prose. Two honest renderings differ in every sentence, which
is why nothing here compares wording, sentence count or length: those disagree by
construction, and a metric that punished them would measure the language, not the
work.

WHAT ELSE IT MEASURES
Nothing here is specific to a drafted section: the three dimensions are
properties of any prose written FROM a fixed evidence set. A synthesis (the
matrix `/lit-review` produces) is the other stage with that shape, and rendering
it N times and comparing with this tool is what `eval/MEASUREMENT.md` means by
"stability measurable" on that row. What the tool cannot cover is a stage with
no evidence-bound text at all — the style audit returns an edit list, and
`review_stability.py` handles the reviewer's own output.

USAGE
Produce N independent renderings of ONE section from the SAME evidence (run
`/draft <section>` N times into separate files — the runs must not see each
other), then:

  python scripts/draft_stability.py runs/methods-1.md runs/methods-2.md [more...]
  python scripts/draft_stability.py --strict runs/*.md      # exit 2 below --min

Exit codes: 0 ok · 1 error · 2 --strict and agreement fell below --min.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cite_audit import extract_citations
from claim_check import cited_keys, rung_of, split_sentences
from lib_common import die, emit, require_within_cwd

# A reported quantity: digits with an optional decimal separator (either
# convention — the kit's Turkish half writes 0,81 where its English half writes
# 0.81), optionally a percent sign. Deliberately NOT a general number grab:
#
#  - a bare four-digit year is excluded, because it is almost always part of a
#    citation or a sentence about the literature, and it varies with phrasing
#    rather than with what the draft reports;
#  - an ordinal in prose ("the first of three stages") is not matched, since it
#    carries no digits.
#
# What remains is the class this measurement is about: a metric, a sample size,
# a proportion — the numbers that must come from the evidence and cannot be
# reworded into existence.
_NUMBER_RE = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(%?)")
_YEAR_RE = re.compile(r"^(1[89]|20)\d\d$")


def numbers_in(text: str) -> set[str]:
    out = set()
    for value, pct in _NUMBER_RE.findall(text):
        if not pct and _YEAR_RE.match(value):
            continue
        # Normalised to a single decimal convention so 0,81 and 0.81 are the
        # same reported quantity — a run that differs only in decimal separator
        # disagrees about typography, not about what it measured, and
        # tr_style_check.py is where that belongs.
        out.add(value.replace(",", ".") + pct)
    return out


def claim_rungs(text: str) -> dict[str, int]:
    """The strongest claim rung asserted alongside each cited key.

    Strongest, not per mention: a source cited five times is claimed as strongly as
    its strongest sentence, which is exactly what claim_check.py compares against
    the evidence cards. Sentences with a citation but no ladder verb contribute
    nothing (rung_of returns None) rather than a zero — "no claim verb" is not
    "the weakest claim".
    """
    rungs: dict[str, int] = {}
    for sentence in split_sentences(text):
        rung, _ = rung_of(sentence)
        if rung is None:
            continue
        for key in cited_keys(sentence):
            rungs[key] = max(rungs.get(key, rung), rung)
    return rungs


def agreement(sets: list[set]) -> tuple[float, list]:
    """Share of observed items present in EVERY run, plus the ones that are not.

    Public because `review_stability.py` measures a different stage with the same
    rule, and two implementations of one definition drift — this repository has
    watched that happen three times in one much smaller place (D-017/D-027/D-041).

    Intersection over union across all runs at once, not a pairwise average: with
    three runs, an item that two of them agree on is still an item one of them
    invented or dropped, and a pairwise mean would report that as two-thirds
    agreement instead of one disagreement. Returns 1.0 for no observations at
    all — a section that reports no numbers is perfectly consistent about it, and
    calling that 0.0 would flag every qualitative draft in the kit.
    """
    union = set().union(*sets) if sets else set()
    if not union:
        return 1.0, []
    common = set.intersection(*sets) if sets else set()
    return len(common) / len(union), sorted(union - common)


def compare(texts: list[str]) -> dict:
    citations = [extract_citations(t) for t in texts]
    numbers = [numbers_in(t) for t in texts]
    rung_maps = [claim_rungs(t) for t in texts]

    cite_score, cite_unstable = agreement(citations)
    num_score, num_unstable = agreement(numbers)

    # Claim strength is compared only for keys EVERY run cited: a key one run
    # never mentioned has already been counted as a citation disagreement, and
    # counting it again here would report one defect as two.
    shared_keys = set.intersection(*[set(m) for m in rung_maps]) if rung_maps else set()
    rung_conflicts = []
    for key in sorted(shared_keys):
        observed = sorted({m[key] for m in rung_maps})
        if len(observed) > 1:
            rung_conflicts.append({"key": key, "rungs": observed})
    rung_score = 1.0 if not shared_keys else 1 - len(rung_conflicts) / len(shared_keys)

    return {
        "runs": len(texts),
        "citations": {"agreement": round(cite_score, 4), "unstable": cite_unstable},
        "numbers": {"agreement": round(num_score, 4), "unstable": num_unstable},
        "claim_strength": {"agreement": round(rung_score, 4),
                           "compared_keys": len(shared_keys),
                           "conflicts": rung_conflicts},
        "lowest_agreement": round(min(cite_score, num_score, rung_score), 4),
        "note": ("stability, not accuracy: a stage that is consistently wrong "
                 "scores 1.00 here — see eval/MEASUREMENT.md"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="*", help="2+ independent renderings of ONE section")
    ap.add_argument("--min", type=float, default=1.0,
                    help="with --strict: the agreement floor (default 1.0 — the "
                         "cited sources and reported numbers of one section drafted "
                         "from one evidence set have no honest reason to vary)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 when the lowest agreement falls below --min")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    if len(args.runs) < 2:
        die("give at least 2 rendering files — stability is a property of a set "
            "of runs, and one run has none")
    texts = []
    for rel in args.runs:
        require_within_cwd(rel, "runs")
        p = Path(rel)
        if not p.is_file():
            die(f"{rel} does not exist")
        texts.append(p.read_text(encoding="utf-8", errors="replace"))

    result = compare(texts)
    result["files"] = [Path(r).as_posix() for r in args.runs]
    emit(result, args.json_out)
    if args.strict and result["lowest_agreement"] < args.min:
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a rendering — {e}")
    except UnicodeDecodeError as e:
        die(f"a rendering is not valid UTF-8 — {e}")
