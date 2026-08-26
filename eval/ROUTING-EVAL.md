# Skill Routing Evaluation

Live accuracy test for scholar-kit's skill descriptions — does a fresh model, given
ONLY the name+description catalog Claude Code preloads every session (skill bodies
load later, only after triggering), pick the right skill for a realistic user message?

Set size: **95 prompts / 54 skills**, every skill covered. That line is derived
from the artifacts by `tests/test_kit_meta_scripts.py`, not maintained by hand —
see *Coverage is a gate now* below for why it had to become one.

## Method

1. `python scripts/skill_routing_eval.py --require-full-coverage` — static check:
   every `eval/golden-prompts.json` entry's `expect` field names a real skill, and
   every skill in the catalog has at least one prompt. Exit 2 on either failure.
2. Live test: a **fresh** agent (no prior conversation, no access to skill bodies —
   only the extracted `{skill, description}` catalog from
   `scripts/extract_skill_descriptions.py`) is given all prompts and asked which
   skill it would invoke, exactly simulating Claude Code's own router. Reproduce with
   a fresh Agent/Task call fed the catalog JSON + `eval/golden-prompts.json`.

## Coverage is a gate now

The static check used to *report* uncovered skills without counting them as
problems, and the count in this document was typed rather than derived. Both
drifted the moment two skills shipped without prompts: `disclosures` and
`restyle` sat unrouted at 26/28 while this page still read "full coverage as of
this run". Neither had ever been put in front of a router, so neither had a
measured routing accuracy — and `restyle` is precisely the case that needs one,
because `citation-styles`' description also names *"switch citation style"*.

Two changes, so the same drift cannot recur silently: `--require-full-coverage`
makes an uncovered skill exit 2, and a test asserts the shipped set passes under
that flag and that the set size stated above matches the files.

## Results

| Run | Accuracy | Notes |
|---|---|---|
| 1 (initial) | 41/42 (97.6%) | 1 miss: prompt #8 ("what's the difference between SCI-E/SSCI/ESCI/Scopus") predicted `journal-check` instead of `literature-review` — a conceptual question about index *classes* got matched by keyword overlap (WoS/Scopus/indexing) against journal-check's description, which is meant for looking up ONE named venue. |
| 2 (after fix) | 4/4 (100%) targeted re-test | Sharpened both descriptions: journal-check now states explicitly "Use when a SPECIFIC journal is named... For a CONCEPTUAL question... use literature-review instead"; literature-review gained trigger phrases 'what is SCIE/ESCI/Scopus', 'quartile meaning', 'predatory journal signs'. Re-tested with 4 prompts spanning both the original miss and 3 controls (2 correctly-routed journal-check cases + 1 new conceptual predatory-flags question) — all 4 correct. |
| 3 (post-/slr additions) | 44/44 (100%) FULL live re-run | After adding /slr (+2 prompts, 26 skills) and the lit-review vs literature-review disambiguation (an /slr spot-check had exposed their "execute" overlap), the complete 44-prompt set was re-run with a fresh agent: all correct, including both /slr prompts and the previously-missed conceptual index question. |

| 4 (coverage closure) | 45/48 (93.8%) FULL live re-run | The first live scoring of the 48-prompt set, blind: the agent was given the extracted catalog and the prompts with `expect` **stripped**. Three misses, each at self-reported `medium` confidence while all 45 hits were `high` — the router flagged its own two collisions. (a) #5 and #6 ("systematic literature review…" / "…sistematik olsun") went to `slr` instead of `lit-review`: `slr`'s description opened on the word *systematic* while `lit-review`'s never used it, so the only sharp token in the prompt pointed at the heavier pipeline. (b) #32 ("APA'dan IEEE stiline nasıl geçerim, referanslarımı yeniden mi yazmam lazım?") went to `restyle` instead of `citation-styles` — **the pair this document named in advance as the one to watch**, and it missed in the predicted direction: a question about what switching involves, answered by the command that performs it. |
| 5 (after fix) | **48/48 (100%)** FULL live re-run | Four descriptions sharpened on the criterion the misses exposed, not on keywords. `lit-review` now states that a review merely *called* systematic belongs to it and that `/slr` is chosen by its ARTEFACTS (named databases, downloaded PDFs, per-database Excel, JSON extraction); `slr` says the same from its side. `citation-styles` now declares itself the QUESTION side (including "whether the references have to be rewritten — they do not") and points the action at `/restyle`; `restyle` declares itself the INSTRUCTION side and points questions back. A second fresh agent, same blind protocol, scored 48/48 — the three fixed prompts plus all 45 previously-correct ones, so the sharpening created no new collision. |
| 6 (full set) | **95/95 (100%)** FULL live re-run | The first live scoring of the complete 95-prompt / 54-skill set, blind: a fresh agent was given the extracted catalog and the prompts with `expect` stripped, told to read nothing else, and wrote its predictions to a scratch file scored afterwards. All 95 correct, including the 47 prompts and 26 skills that had never faced a router — the grant, ethics, DMP, referee, dossier, teaching and empirical-chain axes, whose descriptions had until now been measured only by the static coverage check. |

**Live-scored: 95 of 95 prompts (run 6).** Every prompt in the shipped set has
now been scored live under the blind protocol, and every one was routed
correctly. Read that with three limits attached. It is **one agent, one run** —
runs 4 and 5 used two independent agents, and this one has not yet been
replicated. It measures the *catalog*, not the kit: a correct pick from
name+description says nothing about whether the skill body then does the right
thing. And 100% on a set whose prompts were written by the same person who wrote
the descriptions is the same kind of number as a gold set scoring 1.00 against
its own checker — see `eval/MEASUREMENT.md`, "What these numbers do not mean",
which applies here word for word.

Six prompts came back at `medium` confidence, all of them correct: #5
(`lit-review` over `slr`, the systematic-without-artefacts case this page
sharpened in run 5), #12 and #13 (`analyze-data` over `experiment` — data in
hand versus a run worth registering), #36 (`thesis-structure` over
`front-matter` — the knowledge question versus producing the thing), #41 and #42
(`comparative-analysis` over `ml-research` and `academic-writing`). Those five
pairs are where the catalog is thinnest, and they are the first place to look if
a later run does miss. Note what this run did to run 4's observation that
confidence predicted misses: with no misses to predict, six mediums went
unfalsified rather than confirmed. It stays an observation.

### Why this line is worded so carefully

Until run 6 this page carried a claim it had stopped being entitled to:

> Current measured accuracy: 48 of 48 (run 5). Every prompt in the shipped set
> has now been scored live, including the four that had never faced a router.

That was true the day it was written, at 48 prompts over 28 skills. It was
false at the first of the five set-growths that followed, and it stayed on the
page through all five — 50/29, 54/31, 56/32, 65/39, 95/54 — so across five set
revisions the document asserted that prompts and skills had been measured when
not one of them had.

The failure is worth naming precisely, because this document had already built
a gate against it: when two skills
shipped without prompts, `--require-full-coverage` was added and a test was
wired to the *set-size* line. Both worked — the size line is derived and correct
at 95/54. What nothing watched was the **scope of the accuracy claim**, one
sentence below. A gate on the denominator does not gate the sentence that uses
it. `tests/test_routing_eval_currency.py` now parses the "Live-scored: N of M"
line above, requires M to equal the shipped set, and refuses any full-coverage
wording while N is below M. The page earned that wording back in run 6 — but it
earned it by running the eval, which is the only way the check can ever be
satisfied.

Two things are worth keeping from run 4 rather than filing away: the collision
this page *predicted* is the one that fired, which is evidence the pair-level
reasoning works; and confidence was a usable signal — every miss carried
`medium`, every hit `high`. Neither is measured over enough runs to be a claim,
so they are recorded as observations, not as properties of the router.

## Reproducing

```bash
python scripts/skill_routing_eval.py           # static coverage check
python scripts/extract_skill_descriptions.py   # regenerate the catalog fed to the live test
```

Then spawn a fresh agent (Task/Agent tool, `general-purpose`, no shared context) with
the catalog JSON + the prompts, and ask it to predict per-prompt; score against
`expect` afterwards.

**Strip `expect` before the prompts reach the agent, and tell it to read nothing
else.** `eval/golden-prompts.json` carries the answer beside every question, so
handing that file over measures reading comprehension; so does letting the agent
open this repository, where the answers are also in this document. Write a
labels-removed `[{id, prompt}]` file to a scratch directory and pass that path.
The same rule as `calibration_score.py`'s refusal to score label-contaminated
verdicts, one layer down.

Investigate any miss by checking whether the two competing
skills' descriptions genuinely overlap in wording — sharpen the loser's description
with an explicit disambiguator (as done for journal-check/literature-review above)
rather than reflexively adding keywords, which can create new collisions elsewhere.

## When to re-run

- After adding, removing, or renaming any skill.
- After editing any skill's `description:` field.
- Periodically as the golden set grows — add new prompts for edge cases discovered
  during real use (misrouted requests are the best source of new golden prompts).
