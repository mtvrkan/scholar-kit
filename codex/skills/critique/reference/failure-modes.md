# AI-Research Failure Modes — 7-Mode Checklist

**Source:** Lu et al. (2026), *Towards end-to-end automation of AI research*,
Nature 651:914–919 — Limitations, Figure 2, Supplementary A.2.9. Lu et al. built
the first autonomous AI research system to pass blind peer review, and their
Limitations section enumerates the failure modes it produced. Most apply just as
much to a human-in-the-loop workflow like this kit's.

**Why a checklist at all:** these failures are dangerous precisely because they
**read like competent work**. A hallucinated result reads exactly like a real
one. A shortcut-driven finding reads exactly like a generalization. A Methods
section describing a run that never happened reads exactly like a faithful one.
Nothing in the prose signals the defect — which is why it has to be asked about
explicitly rather than noticed.

**Two halves.** `scripts/failure_scan.py` decides the part a machine can decide
and reports the rest as explicitly un-decided. This document is the other half:
the questions a human — or `reviewer-critic` — has to answer. Never treat a
`CLEAR` from the script as clearance of the mode; it clears the *tell*, not the
mode.

---

## Paper-type pre-filter

M1, M3 and M6 assume the manuscript reports its own measurements. On a
`theoretical`, `narrative-review`, `qualitative` or `case-report` manuscript
they would fire on participant counts and worked examples, so the scanner
switches them off for those types — and **reports the skip**. If you see a
SKIPPED status you did not expect, check `PROJECT.md`'s `- **Type:**` bullet
before assuming the manuscript is clean. An unknown or missing type keeps every
mode ON: failing toward more scanning is the safe direction.

---

## M1 — Implementation bug passing self-review

The analysis code has a defect (off-by-one, wrong variable, silent divide, wrong
flag) that produces numerically plausible but scientifically wrong results.
Nothing looks obviously wrong, so the number enters the paper.

*Scanner tells:* metric reported as exactly 1.00 / 0.50 / 0.00; one value
standing in for three or more different metrics; zero dispersion.

**Ask:**
- For every number in the draft: is there a saved log, notebook or script run
  that produced it? Did it exit 0, with no warnings?
- Do confidence intervals and error bars actually *vary* across conditions, or
  are they suspiciously alike?
- Was any metric computed on a different split than the one Methods describes?

## M2 — Hallucinated citation

A reference that does not exist, is miscited, or is credited with a finding it
does not contain.

**Fully covered elsewhere and deliberately not re-checked here:**
`/verify-citations` is a hard gate (fabrication + retraction + DOI
cross-checking), and `claim_check.py` covers the harder half — a *real* citation
carrying a claim stronger than its source supports. Re-implementing a weaker
version of either inside this checklist would only blur that boundary.

## M3 — Hallucinated experimental result

A number that corresponds to no actual run: averaged differently than claimed,
taken from a crashed run, or invented to fit the narrative.

*Scanner tell:* a decimal narrated as an own result in a result-bearing section,
appearing in no `analysis/` artefact. Prose rounding is accepted (a table's
0.8712 may be written 0.87); prose *more precise* than any artefact is flagged,
because that is precision from nowhere.

**Ask:**
- Does every table in the draft match a saved CSV, log or run directory?
- Does "we ran N seeds" match the number of run directories that exist?
- If `analysis/` is absent the mode is SKIPPED, not clear — with no artefacts
  there is nothing to check against, and that is itself worth fixing.

## M4 — Shortcut reliance

The result is real, but the model achieved it by exploiting a spurious feature
rather than learning the intended relationship. The canonical case: a
colour-biased MNIST model scoring 99% by reading the background, not the digit.

**Not automatable — no scanner tell exists.** This needs an ablation judgement,
and it is the single most valuable question to put to `reviewer-critic`
(especially the devil's-advocate persona under `--panel`).

**Ask:**
- Is there a controlled ablation ruling out the most obvious shortcut feature?
- Does the ablation section ablate the *claimed mechanism*, or only incidental
  hyperparameters?
- Is the baseline strong enough that beating it requires the proposed mechanism
  rather than just more compute or more data?
- Would the result survive on a variant of the dataset with the suspected
  shortcut removed?

## M5 — Implementation bug reframed as novel insight

The compound failure: a bug (M1) produces an unexpected result, and the writing
stage builds a story around it. The paper reads *more* interesting than a
bug-free version would have.

*Scanner tell:* "surprisingly" / "unexpectedly" / "beklenenin aksine" with
nothing cited nearby. A result is only surprising **relative to a published
expectation** — an unanchored surprise is also exactly the shape of a bug being
retold as a finding.

**Ask:**
- For each surprising claim: which source would have predicted the opposite?
  If none can be named, on what basis is it surprising?
- Did the surprise appear on the first run, or only after many debugging
  iterations? First-run surprises are the higher risk.
- Has it been reproduced from scratch in a clean environment?

## M6 — Methodology fabrication

Methods describes hyperparameters, datasets or procedures that are not what
actually ran — a plausible account of what a reasonable version *would* have
looked like, drifting from what happened.

*Scanner tell:* a hyperparameter stated in a Methods file whose value appears in
no `analysis/` artefact.

**Ask:**
- Does every Methods number (learning rate, batch size, epochs, split, seed)
  appear in the actual run config?
- Does Methods describe any preprocessing step with no counterpart in the code?
- Is anything written in the past tense that was never actually run?

## M7 — Frame-lock

A commitment made early (research question framing, method choice, direction)
that later stages are structurally downstream of and cannot back out of. The
paper ends up well-executed while answering the wrong question.

*Scanner tell:* hindsight phrasing ("in hindsight", "sonradan fark ettik").
Orphaned research questions — stated in the introduction, never answered — are
covered separately by `word_budget.py --rq-trace`.

**Ask:**
- Knowing what you know now, would you still choose this RQ and this method?
- Is the contribution better explained *by* the chosen framing, or *despite* it?
- If a reframing would improve the paper, is it still cheap enough to do?

---

## Verdicts

Use three, per mode — the middle one is the point of the exercise:

| Verdict | Meaning |
|---|---|
| **CLEAR** | There is positive evidence the mode does not apply. Record what it was. |
| **SUSPECTED** | A tell fired, or a question got a concerning answer. Surface it. |
| **INSUFFICIENT EVIDENCE** | Cannot be ruled in or out without material nobody has provided (logs, configs, run directories). |

INSUFFICIENT EVIDENCE is not a pass. For M1, M3, M5 and M6 it means the
artefacts that would settle the question do not exist — which is a finding about
the work's reproducibility, not a gap in the checklist.

A SUSPECTED mode is resolved by fixing it, by producing the missing evidence, or
by the author recording **why the flag is a false positive**. That reasoning
belongs in `reviews/round-N.md` — an override nobody wrote down is
indistinguishable from an override nobody thought about.

---

## Running it

```bash
python scripts/failure_scan.py             # WARN-only, all modes
python scripts/failure_scan.py --strict    # exit 2 on any tell
python scripts/failure_scan.py --type theoretical   # override PROJECT.md
```

The scanner reports every mode with a status — `CLEAR`, `FLAGGED`, `SKIPPED`
(with reason), `DELEGATED` (M2), or `NOT_AUTOMATED` (M4) — so the shape of what
was and was not checked is visible in the output rather than assumed.

## Related

- `/verify-citations` — M2's gate
- `scripts/claim_check.py` — claims stronger than their source (M2's harder half)
- `scripts/consistency_check.py` — narrated ≠ presented counts (M1/M3 neighbour)
- `word_budget.py --rq-trace` — orphaned RQs (M7 neighbour)
- `ml-research` skill — ablation design, leakage checks, seed discipline (M4)
