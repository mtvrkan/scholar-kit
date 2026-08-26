---
name: project-report
description: "Write the progress (gelişme) or final (sonuç) report a funder requires for a running project: planned work packages and deliverables against what actually happened, with the actual side derived from this project's own run, dataset and source registers. Slippage is stated as a table, never explained away, and an unreported deliverable is reported as 'not reported' rather than as complete. Use at a reporting deadline for a funded project; use /proposal for the application that started it."
disable-model-invocation: true
argument-hint: "[--period <n>] [--final]"
---

# /project-report — planned against actual, in that order

The report a funder asks for is the proposal's own work plan with a second
column. What makes it painful is that the second column lives in six places: a
folder of results, a mail thread, a student's thesis, two conference
acknowledgements, and a memory of which month things slipped.

Three of those six are already registers in this project.

## Gate

`proposal/workpackages.json` must exist — the report is the plan with an outcome
attached, and without the plan there is nothing to report against. If the
proposal was written outside the kit, transcribe its work plan into that file
first; it is the same file `/proposal` checks.

## Step 1: declare what is done

The registers know what was *produced*. Only you know which deliverable that
satisfies, and when. `proposal/progress.json`:

```json
{
  "period": 1,
  "deliverables": {
    "D1.1": {"month": 9, "evidence": "analysis/data/, DS-0001 in the register"},
    "D2.1": {"status": "in progress", "expected_month": 20}
  }
}
```

A deliverable absent from this file comes back as **`not reported`** — never as
complete. Those are different claims, and a report where they read the same is
the kind a funder's auditor finds interesting.

## Step 2: run it

```bash
python scripts/proposal_check.py --report
```

```
D1.1  WP1  Curated dataset   planned m6   completed m9   slippage +3
D2.1  WP2  Trained model     planned m18  not reported

derived_from_registers:
  runs_recorded 42 · datasets_registered 2 · sources_registered 61 · draft_files 7
```

The derived block is evidence you can point at, not a substitute for the
declaration: 42 recorded runs is a fact about `analysis/runs.jsonl`, and whether
they constitute D2.1 is your judgement.

## Step 3: write the report

Section by section, in this session. What the numbers do not give you:

- **Why a deliverable slipped.** The script states the gap and writes no reason —
  a report that explains slippage before stating it is the one nobody believes.
  State the slippage, then the reason, then what changed in the plan.
- **What was learned that changed the plan.** A funded project that ran exactly
  as written either had no findings or is not saying. Reviewers of final reports
  read this section first.
- **Publications and outputs.** Derived from `sources/registry.jsonl` and the
  drafts, but the acknowledgement wording and the grant number are yours:
  `python scripts/compliance_gen.py funding --grants '[…]'`.
- **Budget realisation.** The kit checks the *proposed* budget's arithmetic; what
  was actually spent comes from your institution's finance system and is not
  guessed here.

## Step 4: for a final report

```bash
python scripts/replication_pack.py --build
python scripts/dmp_gen.py --check
python scripts/experiment_db.py stats
```

A final report is the last moment the data management plan's promises can still
be kept. `--check` naming an unevidenced FAIR letter here is worth more than the
same finding six months after the project closes.

## What this does not do

- **It does not explain a gap.** It states one.
- **It does not know your funder's report template.** Section names come from
  `proposal/call-fields.json` — the same file the application used, extended with
  the reporting sections if they differ.
- **It does not read your finance system.** Spend is not derivable from anything
  in this project.

## Reference

- **Script:** `python scripts/proposal_check.py --report`
- **Reads:** `proposal/workpackages.json`, `proposal/progress.json`,
  `analysis/runs.jsonl`, `analysis/datasets.jsonl`, `sources/registry.jsonl`, `drafts/`
- **Related:** `/proposal`, `/dmp`, `/replication-package`, `/disclosures`

---
*The plan is a promise made before the work. The report is the only place anyone finds out which promises the work kept.*
