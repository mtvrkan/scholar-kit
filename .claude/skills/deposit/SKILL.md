---
name: deposit
description: "Two moments either side of publication. --preprint assembles an arXiv/SSRN/TechRxiv/OSF deposit: title and abstract against the SERVER's own limits, the licence/category/journal-policy/version/co-author decisions recorded rather than guessed, and the preprint disclosure sentence the cover letter will need. --corrigendum takes an error found in a published paper and lists everywhere that number went — drafts, the figures and tables named beside it, the run records, the evidence cards — then gives the letter's skeleton. Use before posting a preprint, or when a mistake surfaces after publication."
disable-model-invocation: true
argument-hint: "--preprint <arxiv|ssrn|techrxiv|osf|biorxiv> | --corrigendum"
---

# /deposit — posting it early, and fixing it late

## A. The preprint

```bash
python scripts/deposit_pack.py --preprint arxiv
```

### The limits file, and the five decisions

```json
{
  "server": "arXiv",
  "source_url": "https://info.arxiv.org/help/",
  "read_on": "2026-08-15",
  "title_max_chars": 240,
  "abstract_max_chars": 1920,
  "categories": ["eess.SP", "cs.LG"],
  "decisions": {
    "target_journal_policy": "…",
    "licence": "…",
    "category": "…",
    "version_posted": "…",
    "coauthor_consent": "…"
  }
}
```

The limits come from the server's own help page. The five `decisions` are the
questions the kit asks and will not answer:

1. **Does the target journal permit this?** Read the journal's own preprint
   policy. It differs between imprints of the same publisher, and it is not
   recalled here. Some venues treat a posted preprint as prior publication.
2. **Which licence?** CC-BY permits redistribution and adaptation with
   attribution; CC-BY-NC forbids commercial reuse; arXiv's non-exclusive licence
   permits distribution only. **A posted licence is effectively irreversible** —
   servers do not un-license a paper.
3. **Which category?** Wrong classification is the most common reason a preprint
   is quietly unread.
4. **Which version** — submitted, accepted, or published? Usually only one of the
   three is permitted.
5. **Have all co-authors agreed?** Posting is a publication act.

Leaving one undecided is a **finding**, not a note: exit 2 until each is recorded.
Printing five questions and exiting 0 would make an undecided deposit read
exactly like a checked one.

### After posting

The command produces the disclosure sentence with visible blanks:

> A preprint of this manuscript has been posted at `<server>` under `<licence>`
> (`<URL>`). 

Fill it and add it to `exports/submission/cover-letter.md` — most venues require
the letter to say a preprint exists, and `/submission-pack` will ask.

## B. The corrigendum

Describe the error first — the letter is the easy half:

```json
{
  "source_url": "https://doi.org/10.1234/published",
  "wrong_value": 0.91,
  "correct_value": 0.87,
  "what_happened": "the held-out split was reported before the leakage fix"
}
```

```bash
python scripts/deposit_pack.py --corrigendum
```

### What it actually gives you

The hard half of a correction is the question nobody asks in the right order:
**what else did that number touch.**

```
found_in_drafts        results.md:3, results.md:5
artefacts_nearby       Table 2, Figure 3
run_records            RUN-0007 (f1=0.91, DS-0001, seed 1)
evidence_cards         EV-0090 "F1 reaches 0.91"
```

Values are matched **across decimal conventions**, so `0,91` in a Turkish section
and `0.91` in an English one are one value, not two misses.

A run record still holding the wrong value is its own finding: a corrigendum that
leaves the register saying the old number makes the replication package disagree
with the correction — and the package is what a reader checks.

### The letter

The skeleton the command prints has six steps; two of them are the ones authors
skip:

- **What does *not* change.** State it. A reader's first question is whether the
  conclusion survives, and silence reads as "they are not saying".
- **Who found it.** If a reader did, say so.

### After the letter

```bash
python scripts/experiment_db.py trace 0.87      # the run that produced the right number
python scripts/consistency_check.py             # narrated vs presented, re-run
python scripts/replication_pack.py --build      # the deposit, rebuilt from the corrected register
```

## What this does not do

- **It does not decide that a correction is needed, or that it is enough.**
  Corrigendum, erratum or retraction is between the authors and the editor.
- **It does not know a server's limits or a journal's policy.** Both are files
  you fill.
- **It does not post anything.** No upload, no API token, no account.

## Reference

- **Script:** `python scripts/deposit_pack.py` (`--preprint <server>`,
  `--corrigendum --error <file>`)
- **Reads:** `drafts/`, `PROJECT.md`, `analysis/runs.jsonl`, `evidence/cards.jsonl`
- **Writes:** nothing — the files you fill live in `exports/deposit/`
- **Related:** `/submission-pack` (the disclosure it needs), `/replication-package`
  (the deposit of code and data), `/journal-check` (the venue whose policy decides
  the preprint question)

---
*A preprint licence is a decision you make once and cannot revisit. A correction is a decision you would rather have made earlier. Both are worth a checklist.*
