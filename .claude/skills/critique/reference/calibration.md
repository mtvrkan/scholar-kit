# Reviewer Calibration — measuring the reviewer's error profile

## Why

`reviewer-critic` returns an absolute rubric score and a decision. Neither is
interpretable without knowing how the reviewer errs. Two drafts can both be
scored "Major Revision" by a reviewer that is systematically harsh on
cross-disciplinary work and systematically lenient on weak methodology — nothing
in the score reveals which, and the reviewer cannot tell you, because a reviewer
that knew where it was wrong would not be wrong there.

Calibration mode measures that profile against papers whose real outcome you
already know. It does not make the reviewer better. It makes the reviewer's
imperfections legible, so a Major Revision can be read as "this reviewer, whose
over-harsh rate is 0.3, said Major" rather than as a verdict.

## The gold set is yours

The kit ships **no** labelled papers, and will not. A gold label is a claim about
what a real venue actually decided; inventing those for the sake of a number
would corrupt the one thing this mode exists to provide. Build the set from your
own history: papers you submitted and whose outcome you know, papers you
reviewed, your lab's past submissions.

`gold.jsonl`, one object per line:

```json
{"id": "p01", "label": "minor_revision", "venue": "IEEE Access", "note": "R1 wanted ablations"}
```

`label` ∈ `accept` · `minor_revision` · `major_revision` · `reject`.

Keep the file out of the drafts tree. It is an answer key.

## Gold-label isolation — the rule that makes the numbers mean anything

A reviewer that can see the expected outcome is not being measured; it is being
led. The isolation is structural: labels live in a file the reviewer never
receives, verdicts are frozen to disk, and `calibration_score.py` is the only
place the two meet — afterwards.

Concretely, during the panel phase:

- **Do not** read the gold file into the session before the panels run.
- **Do not** name the expected outcome, the venue's actual decision, or "this
  one was accepted" in any dispatch brief.
- **Do not** run the papers in label order, or in any batching a reader could
  infer the label from.
- **Do** write verdict records carrying only `id`, `run`, `decision`, and
  optionally `major_issues`.

`calibration_score.py` refuses to score any verdict record containing a
label-shaped field (`label`, `gold`, `goldLabel`, `expected`, `ground_truth`,
`truth`, `answer` — compared with punctuation and case folded away). That
refusal is a backstop against one specific accident, not a licence to be casual
about the rest: nothing can detect a label that reached the reviewer through a
dispatch brief and left no trace in the record.

## Two tiers

| | `full` | `directional` |
|---|---|---|
| Papers | 5–20 (10–15 recommended) | exactly 3 |
| Runs per paper | 3 or 5, majority-voted | exactly 1, never ensembled |
| Reports | confusion matrix, balanced accuracy, FNR/FPR with bootstrap CIs | raw direction counts only |
| Cost | high | low |

`directional` is a spot check. It **refuses to emit FNR/FPR at all** — three
single draws cannot estimate a rate, and printing one would be precisely the
overclaim this whole mode exists to make visible. Use it to see whether the
reviewer leans harsh or lenient at the Minor/Major boundary, nothing more.

Never silently substitute `directional` because `full` is expensive. If the user
asked for a profile and only has three papers, say that three papers cannot
produce one.

## Reading the output

**The positive class is fixed** and printed in every report:

```
positive = accept + minor_revision      negative = major_revision + reject
```

Under that convention:

| Metric | Reads as |
|---|---|
| **FNR** | the **over-harsh** rate — a publishable paper sent back |
| **FPR** | the **lenient** rate — a flawed paper waved through |

Reversing the positive class inverts both readings while leaving the formulas
unchanged, which is exactly how these numbers get misquoted. Never write "FNR =
missed rejects" or "FPR = over-rejection" with this script's output.

**Anchor for what to expect.** Lu et al. (2026, *Nature* 651:914–919, Table 1)
measured an LLM automated reviewer at balanced accuracy 0.65 against human
0.67–0.73 on 500 ICLR papers — comparable overall, with a *dramatically*
different error shape: FNR 0.17 vs human 0.52, FPR 0.50 vs human 0.17–0.34. The
machine reviewer was far more willing to let a weak paper through and far less
willing to reject a decent one. If your measured profile looks like that, it is
the expected shape, not a bug in your gold set.

**The boundary sub-matrix** is reported separately whenever the gold set holds
both `minor_revision` and `major_revision`. That boundary is the highest-traffic
decision in practice and the binary split collapses it entirely.

**Ties break conservative.** A reviewer split evenly between Minor and Major is
recorded as Major: it has not established the friendlier verdict, and resolving
ties optimistically would flatter the profile being measured.

**Unstable papers are named.** A paper whose runs disagreed contributes a
majority vote, and the report says so — part of the profile rests on a reviewer
that read those papers inconsistently.

## Limits, stated

- **Domain-specific.** A profile measured on machine-learning venues says
  nothing about qualitative education research. Error profiles do not transfer.
- **Session-scoped.** Nothing is cached across sessions. Re-run, or paste a
  prior report in as context. The alternative — a stored profile silently
  applied to a different domain months later — is worse than re-measuring.
- **n < 10 is directional.** The script emits this caveat itself; it is not
  removable by ignoring it.
- **Bootstrap CIs use a fixed seed** so a reported interval is reproducible
  rather than redrawn on each run. They quantify sampling noise in your gold
  set, not the reviewer's variance across model versions.
- **This measures the reviewer, not the kit.** A well-calibrated reviewer says
  nothing about whether the citations are real (`/verify-citations`) or the
  claims match their sources (`claim_check.py`).

## Related

- `eval/MEASUREMENT.md` — what the kit measures about itself overall, and what
  it leaves unmeasured
- `scripts/calibration_score.py` — the scorer; `--help` restates the conventions
- `--panel` in the parent skill — a different instrument: multiple perspectives
  on one draft, not accuracy against known outcomes
