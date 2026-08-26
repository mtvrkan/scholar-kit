# Measurement — what the kit measures about itself, and what it does not

A kit that makes judgements about a manuscript owes the reader an account of how
often it is right. This document is that account, including the parts where the
honest answer is "not measured".

## Two layers, measured differently

| Layer | What it is | How it is measured |
|---|---|---|
| **Deterministic checkers** | `claim_check.py`, `failure_scan.py`, `tr_style_check.py`, `temporal_check.py`, `consistency_check.py`, `figure_check.py` — scripts with no model call | Labeled gold sets under `eval/gold/`, scored precision / recall / F1 by `scripts/run_evals.py`, and the sets themselves mutation-checked (see below) |
| **Skill routing** | does a fresh model pick the right skill from name+description alone | `eval/golden-prompts.json` + a live model run — see [ROUTING-EVAL.md](ROUTING-EVAL.md) |
| **Reviewer accuracy** | does `reviewer-critic` decide the way a real venue did | `/critique --calibrate --gold <file>` against **your own** labelled papers, scored by `scripts/calibration_score.py` — the kit ships no gold set |
| **Reviewer stability** | is the reviewer's read of one draft consistent | `/critique --calibrate`, computed by `scripts/review_stability.py` over the 3 run reports — decision agreement, Major-issue count range, which sections the runs disagree about. Deterministic on purpose: a comparison the model performs on its own three outputs is not a measurement of that model. Stability is *not* accuracy: a reviewer that is consistently wrong scores perfectly |
| **Screening accuracy** | does the kit's title/abstract include/exclude match yours | `scripts/screening_score.py --gold <file>` against **your own** labelled sample — recall, precision, Cohen's κ, never accuracy. The kit ships no gold set; `--sample N` draws a **blinded** worksheet (the kit's own decision is not on it) and `--from-worksheet` turns it back into labels; see [screening/README.md](screening/README.md) |
| **Drafting stability** | do independent renderings of one section from one evidence set agree on which sources are cited, which quantities are reported, and how strongly each source is claimed | `scripts/draft_stability.py run-1.md run-2.md …` — needs no labels, because disagreement between two renderings of the same evidence is itself the finding. Accuracy still unmeasured: a stage that is consistently wrong scores 1.00 |
| **Synthesis stability** | do independent renderings of the synthesis from one evidence set agree | Same instrument, same limit: `scripts/draft_stability.py` reads any evidence-bound markdown, and a synthesis matrix rendered N times is exactly that. Accuracy unmeasured |
| **Everything else LLM-mediated** | the style audit (an edit list, not evidence-bound prose) | **Not measured.** No gold set exists and none is invented |

## Running it

```bash
python scripts/run_evals.py              # all gold sets, JSON report
python scripts/run_evals.py --task claim_strength
python scripts/run_evals.py --strict     # exit 2 if any threshold is missed
python scripts/run_evals.py --mutate     # also: would the cases notice a broken checker?
```

The shipped gold sets are also asserted by `tests/test_run_evals.py`, so every
`pytest` run — and therefore every CI run — gates on them. A checker whose
behaviour drifts below its declared threshold fails the build, and so does a
gold set that stops noticing its own checker breaking.

Nine checkers are covered, including the whole spine of the zero-fabrication
chain: `cite_audit.py` (the in-text/bibliography cross-diff the citation gate is
built on), `bib_doctor.py` (bibliography hygiene) and `evidence_funnel.py` (why
a card never reached the prose).

The rest of `scripts/` is not, and the honest reading of an uncovered checker is
the same as for an untested one: nobody has measured it. `word_budget.py` has
unit tests but no labelled gold set — it reports arithmetic rather than making
judgements, so precision/recall is a poor fit for it. `citation_triangulate.py`
is deliberately excluded: it asks a live second index (OpenAlex), and a gold set
scored against a network response measures the network.

## Current results

| Gold set | Cases | Positive / negative | Precision | Recall | Mutations caught |
|---|---|---|---|---|---|
| `bib_doctor` | 13 | 7 / 6 | 1.00 | 1.00 | 6 / 6 |
| `cite_audit` | 13 | 7 / 6 | 1.00 | 1.00 | 6 / 6 |
| `claim_strength` | 75 | 36 / 39 | 1.00 | 1.00 | 11 / 11 |
| `consistency` | 17 | 8 / 9 | 1.00 | 1.00 | 6 / 6 |
| `draft_integrity` | 16 | 11 / 5 | 1.00 | 1.00 | 6 / 6 |
| `evidence_funnel` | 16 | 7 / 9 | 1.00 | 1.00 | 8 / 8 |
| `failure_modes` | 40 | 21 / 19 | 1.00 | 1.00 | 6 / 6 |
| `figures` | 22 | 12 / 10 | 1.00 | 1.00 | 8 / 8 |
| `temporal` | 17 | 6 / 11 | 1.00 | 1.00 | 5 / 5 |
| `tr_style` | 40 | 16 / 24 | 1.00 | 1.00 | 13 / 13 |
| **total** | **269** | **131 / 138** | — | — | **75 / 75** |

Thresholds are P ≥ 0.95, R ≥ 0.95 on every set — see
[Why every set is held to 0.95](#why-every-set-is-held-to-095).
Re-generate this table with `python scripts/run_evals.py --mutate`; do not
hand-edit it.

Read the next section before quoting any of it. Nine perfect scores in a row is
the shape a suite takes when it is measuring its author's intent, which is
exactly what this one does. The last column is the one that is not free — see
the mutation section below for what it cost to make it read 54 / 54.

## The mutation check — measuring the measurement

Precision and recall answer "does the checker do what its author meant?" They
cannot answer the question one level down: **would these cases notice if it
stopped?** A negative case that stays silent however the code is broken scores
exactly like a case that measures something. That is the same undeserved-1.00-
by-omission problem the whole document is about, applied to the gold sets
themselves.

So every manifest declares `mutations`: named, source-level breakages of its own
checker. The set is credible to the extent that breaking the checker makes it
fail its thresholds.

```bash
python scripts/run_evals.py --mutate            # score + mutation report
python scripts/run_evals.py --mutate --strict   # exit 2 if any mutation survives
```

`tests/test_run_evals.py` asserts that every gold set declares mutations, that
each says in prose what it breaks, and that **none survives** — so this rides
into CI on the ordinary `pytest` run, alongside the threshold gate.

Substitution against the real source, not monkeypatching, on purpose: it mutates
the code the checker actually ships, and a mutation whose anchor no longer
appears **dies loudly** rather than silently testing nothing. That failure mode
— refactor the checker, the anchor string vanishes, the mutation "passes"
forever — is the one thing that would hollow this out, and it has its own test.

### What the first run found

Three of seventeen mutations survived, and two were in gold sets that had been
shipping at a perfect score for months:

| Survivor | What it meant |
|---|---|
| `claim_strength:artefact-pointer-allowance-removed` | One case covered "as Table 2 shows". Deleting the allowance entirely dropped precision only to 0.90 — exactly the threshold — so the suite passed with the behaviour gone. |
| `failure_modes:zero-variance-detector-disabled` | One case covered `± 0.00`. Removing the detector left recall at 0.92, above threshold. |
| `tr_style:first-person-exception-list-emptied` | The mutation itself was wrong (`set() or {…}` returns the right operand), so nothing was mutated. A broken mutation is a silent pass, which is why the no-op guard exists. |

Fixing the first two meant writing the cases that were missing — and case
`025-clean-equation-pointer`, written to hold the artefact allowance, **failed
against the real checker and found a bug**: `Eq.` was not in `claim_check`'s
sentence-splitter protection list even though `ARTEFACT_RE` recognises it, so
"the threshold is derived in Eq. 4 and equals 0.63" split at the abbreviation
and the fragment holding the statistic lost the pointer that exempts it. Any ML
paper writes that sentence. Following it up showed `ARTEFACT_RE` accepted the
English `Fig.` but none of the Turkish abbreviations (`Şek.`, `Denk.`, `Böl.`,
`Tbl.`) — the own-work allowance was quietly weaker in Turkish than in English,
in a kit whose central claim is that the two are equal targets. Both fixed.

That chain — mutation survives → write the missing case → the case fails →
a real defect, in the shipped code, in the language the project cares most about
— is the argument for the whole mechanism. Read it as one data point, not a
guarantee: 43 caught mutations bound the ways the author thought to break the
checkers, and nothing more.

### What extending coverage to the citation spine found

The same chain ran again when `cite_audit`, `bib_doctor` and `evidence_funnel`
were given gold sets, and this time it reached further into the code.

`cite_audit:code-fence-stripping-disabled` survived: deleting the fenced-block
strip changed no score at all. Chasing why exposed the actual reason — the
inline-code pattern `` `[^`]*` `` does not exclude newlines, so it was already
swallowing fenced blocks as a side effect, and the fence strip was dead weight
for citation extraction.

That is a defect, not a redundancy. The same pattern makes **two stray backticks
anywhere in ordinary prose** — a threshold written `5\``, a quoted keystroke —
pair up across the paragraphs between them and delete every `[@key]` in that
span. Those keys never enter `cited`, so a citation with no bibliography entry
is **never reported as missing** and `/verify-citations` passes a manuscript it
exists to stop. A false negative, in the one check that blocks, reachable from
prose nobody would look at twice.

`tr_style_check.py` already used the correct single-line form; the other five
copies (`cite_audit`, `claim_check`, `consistency_check`, `failure_scan`,
`figure_check`) did not. All now do, case
`012-stray-backticks-do-not-swallow-a-real-citation` holds it, and a mutation
restores the old pattern to prove the case notices.

Note what found it: not the precision column, which was already 1.00 and stayed
1.00, but a *surviving mutation* in a set that looked perfect. That is the
argument for the mutation column existing at all.

### What an adversarial pass found

The runs above extended coverage. This one tried to **break** two checkers:
seventeen cases written to fail — cases picked because there was a reason to
expect the checker to get them wrong, not because they demonstrate it working.
`claim_check` took twelve, `tr_style_check` five. Three results are worth
recording, in descending order of how uncomfortable they are.

**One probe disagreed with the checker, and the checker won.** A doubly hedged
Turkish sentence — *"…azaltabileceğini düşündürmektedir"*, two hedges stacked —
sitting on top of a card that reports only an association was written as a
negative case, on the assumption that so much hedging cannot be an overclaim.
It fired. The rule is that a hedge demotes one rung, so directional 4 − 1 = 3
is still above associative 1, and the rule is right: attributing a *direction*
to a source that reported a *correlation* is the overclaim reviewers write
comments about, however softly it is phrased. The case ships as a positive
(`034`), its English twin ships beside it (`035`), and three negatives now pin
the boundary from below (`036`–`038`) so the rule cannot later drift into
flagging properly qualified prose. The honest summary: the adversarial pass
found an error in the author's expectation, not in the code.

**The bilingual probes passed.** A thesis `ozet.md` holding Turkish decimals
(`0,81`) beside English ones (`0.81`), and a Turkish impersonal body beside a
first-person English abstract, are both *correct* — each half follows its own
convention — and a file-wide separator or voice count would have fired on every
bilingual manuscript this kit exists to produce. Neither fired. Those cases now
ship (`113`, `115`) with the controls that keep them from passing vacuously
(`114`, `116`).

**Adding a true positive silently disarmed a mutation.** Case `114` raised
`tr_style`'s tp from 8 to 9, which lifted the precision produced by
`first-person-exception-list-emptied` from 8/9 = 0.89 to 9/10 = 0.90 — exactly
the threshold — and the mutation started surviving. Nothing was broken and
nothing was reported; a set got *bigger* and measured *less*. This is a
structural property of threshold-based mutation catching, and the only defence
is arithmetic: a mutation needs enough cases to die on that no single addition
can lift it over the line. Case `117` supplies the second one (9/11 = 0.82,
caught again), and `--mutate --strict` is what surfaced the problem in the first
place.

### What probing outside the set found — nominalized claims

The adversarial pass above wrote cases designed to fail. This one asked a
different question: what shape of sentence had nobody written a case for at all?

`claim_check`'s ladder was built entirely from verbs. Formal academic prose
states the same relations as noun phrases at least as often — "the effect of X
on Y" asserts exactly what "X affects Y" asserts — and every nominal spelling
scored rung-`None`, which means *exempt from comparison*, not "weak". Six of six
nominal phrasings written over an associative card produced no warning, while
their verb twins all fired.

The gap was also **asymmetric**. English rung 5 caught its nominal ("the cause
of") by accident: `caus(e|al|ation)` happens to span noun and verb. Turkish had
no such accident, so `etkisi`, `nedeni`, `sebebiyle`, `kaynaklanmaktadır` and
`katkısı` all carried no rung whatsoever — the checker was quietly weaker in the
language this kit treats as a first-class target. That is the same class as the
`ARTEFACT_RE` finding recorded two sections up, one layer higher, and finding it
twice is the argument for keeping this document honest about coverage rather
than quoting the precision column.

Sixteen positives (four per behaviour: English framed nominals, `etkisi`,
nominal causation, `katkısı`) and eleven negatives now hold it. The negatives are
the ones that make the patterns safe to ship: this kit *generates*
meta-analysis vocabulary elsewhere, so "effect size", "random-effects model" and
"etki büyüklüğü" must never read as claims, and the Turkish privative `-siz`
(`etkisiz` = *without effect*) asserts the opposite of the rung it sits next to.

### Why every set is held to 0.95

All ten sets are scored at P ≥ 0.95, R ≥ 0.95. `claim_strength` was moved there
first, alone; the other eight followed.

Not a quality ranking — an arithmetic one. A single threshold applied to a
**pooled** set weakens as the set grows: a mutation that breaks one behaviour is
caught only while that behaviour's cases make up more than (1 − threshold) of
the whole. At 0.90 that meant four cases out of 38; the same four out of 71
stopped being enough, and adding the nominalization cases silently revived three
mutations — hedge, own-work and statistic — that had been dying comfortably for
months. Nothing was broken and nothing was reported, exactly as in the
`first-person-exception-list-emptied` episode above, but at four times the scale.

The two available answers were padding the set with cases written only to move a
denominator, or raising the bar. 0.95 is the stricter reading, it is one every
checker here already clears at 1.00, and it restores the margins.

Leaving the other eight at 0.90 was recorded at the time as a deliberate choice
rather than an oversight — the argument applied to them "the moment any of them
grows". The measurement says it had already applied. Under a 0.90 line
`tr_style:percent-detector-disabled` died at 0.8889, a margin of **0.011**: one
added positive case away from surviving, which is precisely how
`first-person-exception-list-emptied` was lost once already. Waiting for the
symptom means waiting for a mutation to go quiet, and a mutation going quiet is
the one event this harness cannot report.

Margins now, as the widest metric that still falls below the line (the number
above is this measure at the old threshold, so the two are comparable):

| Gold set | Closest mutation to the line | Margin |
|---|---|---|
| `tr_style` | 0.9412 (`keyword-list-continuation-removed`) | 0.009 |
| `failure_modes` | 0.9167 (`m1-citation-exemption-removed`) | 0.033 |
| `claim_strength` | 0.9000 (`ownwork-allowance-removed`) | 0.050 |
| `bib_doctor` | 0.8750 (`preprint-exemption-removed`) | 0.075 |
| `cite_audit` | 0.8750 (`code-fence-stripping-disabled`) | 0.075 |
| `evidence_funnel` | 0.8750 (`registry-id-to-bib-key-resolution-broken`) | 0.075 |
| `figures` | 0.8750 (`code-fence-stripping-removed`) | 0.075 |
| `temporal` | 0.8750 (`anachronism-gap-loosened`) | 0.075 |
| `consistency` | 0.8462 (`manifest-type-guard-removed`) | 0.104 |

`claim_strength` keeps the thinnest margin of the ten, and it is the largest
set — which is the property restated: **a fixed threshold over a pooled set is a
decaying guarantee**, and it decays without a symptom. The threshold is a floor,
not a ceiling; a set that grows past its margin needs cases per behaviour, not
another round of raising the line.

## The LLM layer: one more stage is now measurable

Screening — the include/exclude call on a title and abstract — joins reviewer
accuracy as a layer with an instrument (`scripts/screening_score.py`). It was
chosen ahead of the others for a reason that is not convenience: its errors are
the only ones in the pipeline that leave **no trace**. A wrongly excluded study
never reaches full text, never becomes a card, and never appears in
`cite_audit`, `evidence_funnel` or a `qa-auditor` report — all of which examine
what survived. The measurement has to come from outside, or not at all.

Three deliberate refusals in that script, each of which would otherwise produce
a number that reads better than it is:

- **No accuracy, ever.** At a 5–10% inclusion rate, excluding everything scores
  90–95%. The field's own statistic is Cohen's κ, which subtracts chance
  agreement and scores that screener 0 — and κ is reported as `null`, not 0,
  when either side used a single class, because 0 there would be
  indistinguishable from measured total disagreement.
- **No rates below 20 scored records.** Counts stand; recall does not. A recall
  figure over a handful of records is one or two studies wearing a percentage
  sign — the same call `calibration_score.py` makes for its `directional` tier.
- **No gold set ships.** Screening labels are a claim about *your* inclusion
  criteria on *your* topic. One written by the model whose decisions it scores
  measures agreement with itself; the mechanical half of that (labels reachable
  from the decisions file) is refused outright.

Still unmeasured, and stated rather than quietly narrowed: drafting, synthesis
and the style audit. They have no discrete correct answer to label, and a rubric
score produced by a model is not a measurement of a model.

## Reviewer calibration is user-supplied by design

The ten gold sets above ship with the kit because they score *scripts*, whose
correct behaviour the author can state. The reviewer gold set does not ship,
and will not: a label there is a claim about what a real venue actually decided,
and inventing those to produce a number would corrupt the one thing the mode
exists to provide. Protocol, the gold-label isolation rule, tier selection and
how to read FNR/FPR without inverting them:
`.claude/skills/critique/reference/calibration.md`.

## What these numbers do not mean

Read this section before quoting the table above.

**They measure intent, not coverage.** Each gold set was written by the same
person who wrote the checker it scores. It answers "does this checker do what
its author meant it to do", not "does it catch overclaims in the wild". A defect
class nobody thought to write a case for is invisible here — and scores an
undeserved 1.00 by omission, not by merit.

**A perfect score on a small set is a weak claim.** 269 cases across ten
checkers — 13 to 75 per set — are enough to catch regressions and to force the
author to state the intended behaviour precisely. They are not enough to
estimate a real-world error rate, and no confidence interval is offered because
none would be meaningful at this size. The mutation column is a stronger claim
than the precision column, and still a bounded one: it says the cases notice the
75 breakages someone thought to write down.

**Precision requires negatives.** A suite of positive cases alone measures only
recall; its precision is either undefined or vacuously 1.00. The shipped sets
carry 138 negatives against 131 positives deliberately, and
`test_shipped_gold_sets_carry_negatives` fails the build if a suite ever loses
them. The negatives are the near-miss shapes each detector must decline to fire
on — an ordinary metric value, a cited surprise, a corroborated hyperparameter,
an attributive participle, a section number that looks like a decimal, a
first-mention English parenthetical, a range mention of three figures at once, a
preprint that legitimately has no journal, two distinct papers whose titles share
most of their words, an own-result card that is uncited by design, and stray
backticks in prose that are not code.

**The gold sets are audited by the harness too.** Two cases in the first run
were wrong, not the code: one used a spelling of "±" no author would write, and
one accidentally tripped a second, legitimately-firing check. Both are fixed and
the second now carries a `comment` field explaining what it isolates. A gold set
is a claim about correct behaviour and can be wrong like any other claim.

**Nothing here validates the underlying research.** These are checks on a
manuscript and its stated process. A study built on fabricated data passes every
one of them if the fabrication is reported consistently. That boundary is not a
gap to be closed by more cases; it is where the tooling stops and human,
institutional and reproducibility review begin.

## Adding a gold set

1. `eval/gold/<task>/manifest.json` with `task`, `entrypoint` (a module in
   `scripts/` registered in `run_evals.ENTRYPOINTS`), `thresholds`, and `cases`.
2. Each case gets a unique `id`, fixture files (`drafts`, and optionally
   `analysis` / `cards` / `registry` / `type`), and an `expect` list.
3. `expect` entries are **subset matches** — name only the fields the case is
   really asserting. Pinning a message string makes the case fail on a reword,
   which teaches nothing.
4. Include negatives. A case with `"expect": []` asserts the checker stays
   quiet, and those are the cases that make precision mean something.
5. Declare `mutations` — at least one per behaviour the set claims to hold — and
   run `--mutate` until none survives. A case you cannot break the checker into
   failing is a case you have not written yet. This is enforced, not advised:
   a gold set with no mutations fails the test suite.
6. Prefer real prose over synthetic strings. The `±` case above is the reminder:
   a fixture no author would actually write measures nothing about real drafts.

## When to re-run

- After changing any checker's patterns or thresholds — the gold set is the
  acceptance test for that change.
- After adding a language or a new tell: add cases in the same commit, including
  at least one negative.
- Before publishing any accuracy claim about the kit anywhere.
