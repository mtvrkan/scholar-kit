---
name: supervision
description: "Prepare a thesis monitoring committee report (TİK raporu) or a supervision progress review from the thesis project's own records — chapter word counts against the budget, RQ↔chapter traceability, evidence-card and run statistics, what changed since the last report — plus the committee's standing questions and the decisions the meeting has to record. Ships no script: it reads the registers the thesis already keeps. Use before a TİK meeting or a progress review; /defense-prep is for the defence itself."
disable-model-invocation: true
argument-hint: "[--period <n>] [--since <YYYY-MM-DD>]"
---

# /supervision — the six-month report, from what the thesis already recorded

A Turkish PhD requires a thesis monitoring committee (TİK) report twice a year,
and most institutes require the same shape for MSc progress reviews. The report
is written the night before, from memory of six months, and it is the document
that decides whether a student's registration continues.

The facts it needs are already on disk. This command assembles them and then gets
out of the way — the judgement in a TİK report is the supervisor's and the
student's, and none of it is derivable.

## What ships: no script

Like `/retarget` and `/present`, this is orchestration over tools that already
exist. That is deliberate: a supervision report has no arithmetic of its own, and
a script that invented one would be inventing the wrong thing.

## Step 1: where the thesis actually is

```bash
python scripts/word_budget.py                # per chapter, against the budget
python scripts/word_budget.py --rq-trace     # does every RQ still land in a chapter
python scripts/evidence_db.py stats          # cards, by chapter and strength
python scripts/experiment_db.py stats        # runs, seeds, datasets
python scripts/dataset_db.py verify          # is the data still the data
```

…and `/status` for the twenty-line digest.

The `--rq-trace` output is the one a committee reacts to. A research question
with no chapter behind it after eighteen months is the finding the meeting exists
to surface, and it is better surfaced by the student than by a member.

## Step 2: what changed since the last report

```bash
python scripts/provenance.py --verify        # the attestation chain, intact or not
git log --since="2026-02-15" --oneline       # if the thesis is under version control
```

Compare against the previous report in `reviews/supervision/`. The three
questions a committee actually asks:

1. What was **promised** last time?
2. What **happened**?
3. What **changed in the plan**, and why?

A period where nothing changed in the plan is either a period with no findings or
a report that is not saying. Committees know this.

## Step 3: write the report

`reviews/supervision/tik-<n>.md`, in the institute's own order if it publishes
one. The sections every version has:

- **Thesis title and stage** — and whether the title still describes the work.
  A title that drifted is a routine, recoverable finding at month 18 and an
  expensive one at submission.
- **Work completed this period**, bound to what the registers show: chapters
  drafted, sources screened, experiments run, data collected. Numbers from step 1,
  never from memory.
- **Findings so far**, at the claim strength the evidence supports —
  `python scripts/claim_check.py` before the meeting, not after it.
- **Deviations from the plan**, stated before they are explained.
- **The next period's plan**, with what would falsify the current direction.
- **Support needed** — access, equipment, funding, a co-supervisor, an ethics
  approval that has not moved. This section is the one students leave empty and
  the one committees exist for.
- **Publications and outputs** from `sources/registry.jsonl` and `drafts/`.

## Step 4: the questions to arrive prepared for

The committee's standing set, generated against this thesis's own claims — the
same machinery as `/defense-prep`, aimed at a mid-course meeting rather than a
defence:

- Which of your research questions is currently unanswerable, and what would
  change that?
- What did you find that you did not expect, and what did you do about it?
- Which result would you drop if you had to submit in three months?
- What is the weakest link between your data and your main claim?

## Step 5: what the meeting must record

A TİK report is a decision document. State plainly, in the minutes:

- the decision (continue / continue with conditions / warning), and the condition
  in words the student can act on,
- the date of the next meeting,
- anything the department owes the student.

A condition nobody wrote down is a condition nobody can be shown to have met.

## What this does not do

- **It keeps no student records.** Everything comes from the thesis project
  directory you are in. There is no roster, no history across students, and
  nothing is written outside the project.
- **It does not evaluate the student.** Progress against a plan is arithmetic;
  whether it is enough is the committee's judgement.
- **It does not know your institute's form.** If it publishes one, its section
  order wins — the same `/ingest-template` and authority-file discipline as
  everywhere else.
- **It is not a defence.** `/defense-prep` for that.

## Reference

- **Scripts (all existing):** `word_budget.py --rq-trace` · `evidence_db.py stats` ·
  `experiment_db.py stats` · `dataset_db.py verify` · `claim_check.py` ·
  `provenance.py --verify`
- **Writes:** `reviews/supervision/tik-<n>.md`
- **Related:** `/status`, `/defense-prep`, `/front-matter` (the institute's formal
  check), `/project-report` (the funder's version of the same exercise)

---
*The committee meeting a student dreads is the one where a member says out loud what the RQ trace has said for a year.*
