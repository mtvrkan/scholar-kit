---
name: dmp
description: "Produce the Data Management Plan a funder asks for (Horizon Europe, TÜBİTAK, an institutional policy) — derived from this project's dataset and run registers rather than filled into a downloaded template. Reports FAIR letter by letter with the record that evidences each, and writes no sentence for a dataset whose licence or citation DOI is not recorded. Use when a call requires a DMP, at a project's data-management review, or before depositing. Triggers on: 'veri yönetim planı', 'data management plan', 'DMP', 'FAIR plan', 'open data requirement'."
disable-model-invocation: true
argument-hint: "[--write exports/dmp.md] [--check] [--sections <funder-sections.json>]"
---

# /dmp — the plan, generated from what the project already recorded

Most data management plans are written the same way: download the template, fill
each box with a sentence that sounds like compliance, submit, never read it
again. The reason is that the facts a DMP asks for — what data, which licence,
which format, where it lives, who may have it — are scattered across a filesystem
and a memory.

This project keeps them in two script-owned registers already. So the plan is
**derived**, and what cannot be derived is left as an explicit blank rather than
written over.

## Gate

None. But the plan is only worth the registers behind it:

```bash
python scripts/dataset_db.py verify        # is the record complete, and do the bytes still match
python scripts/dmp_gen.py --check          # which FAIR letters are unevidenced
```

With an empty `analysis/datasets.jsonl` the result is `UNCHECKED`, not `OK`: a
plan written before the data is registered describes data nobody can verify.

If `analysis/datasets.jsonl` is empty, the plan will say so rather than describe
data that does not exist. Register the data first (`/find-dataset`,
`/collect-data`).

## Step 1: the gaps, before the document

```bash
python scripts/dmp_gen.py --check
```

```json
{"result": "GAPS",
 "unevidenced_by_dataset": {"local-vib": ["F", "R"]},
 "no_sentence_written_for": [{"dataset": "local-vib",
                              "missing": ["citation DOI", "verified licence"]}]}
```

Fix these in the register, not in the prose:

```bash
python scripts/dataset_db.py set-field DS-0002 citation '{"doi": "10.5281/zenodo.123"}'
python scripts/dataset_db.py set-field DS-0002 license "CC-BY-4.0"
python scripts/dataset_db.py verify --id DS-0002
```

A licence typed into the DMP but not into the register is a licence that will
disagree with the paper's availability statement six weeks later, because
`/submission-pack` reads the register and this document would not.

## Step 2: build

```bash
python scripts/dmp_gen.py --write exports/dmp.md
```

Section structure is the **Science Europe core** (a public, funder-neutral
standard): data summary · FAIR ×4 · resources · security and storage · ethical
aspects · other policies.

If your funder publishes its own section list, put it in a file and pass it:

```bash
python scripts/dmp_gen.py --sections proposal/dmp-sections.json --write exports/dmp.md
```

```json
{"funder": "…", "source_url": "…", "read_on": "2026-08-15",
 "sections": ["data_summary", "fair_findable", "…"]}
```

Sections the registers cannot answer come back as *"answer it yourself"* rather
than as a generated paragraph.

## Step 3: fill the blanks that are genuinely yours

Everything marked `TODO:` in the rendered file is a **commitment**, and only you
can make it:

- storage cost over the project's lifetime, and after it ends
- the person responsible for data management
- where working copies live, how they are backed up, who has write access
- the repository the final deposit goes to
- your institution's data policy and the funder's embargo terms
- the ethics approval reference — **once your board has issued it**

## How FAIR is reported, and why not as a score

Each letter is either evidenced by a record or not, with the reason:

```
- cwru-bearing — evidenced: citation DOI 10.1234/abcd
- local-vib    — NOT evidenced: no citation DOI in the register
```

Three out of four is not "75% FAIR" — it is a dataset nobody can reuse. The
document never contains the sentence "this project follows FAIR principles",
because that sentence is available to anyone regardless of what they did.

## What this does not do

- **It does not know your funder's template.** The generic core ships; your
  funder's section list is a file you fill.
- **It does not invent a cost, a volume or a repository name.** A plausible
  commitment nobody made is worse than a blank.
- **It does not describe data the register does not hold.** A dataset with no
  verified licence or no DOI gets no sentence — the gap is listed under its own
  heading, so a reviewer sees an honest absence rather than a confident lie.

## Reference

- **Script:** `python scripts/dmp_gen.py` (`--check`, `--write`, `--sections`)
- **Reads:** `analysis/datasets.jsonl`, `analysis/runs.jsonl`,
  `analysis/collection-protocol.md`
- **Writes:** wherever `--write` points (`exports/dmp.md` by convention)
- **Related:** `/find-dataset` and `/collect-data` (which fill the register),
  `/ethics-application` (the board's version of the same facts),
  `/replication-package` (the deposit this plan promises), `/proposal` (the call
  that asked for the DMP)

---
*A data management plan is a promise about the future written in the present tense. The only part worth writing is the part something on disk can still check next year.*
