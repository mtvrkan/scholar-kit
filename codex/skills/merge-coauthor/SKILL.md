---
name: merge-coauthor
description: "Read what a co-author or supervisor changed in the file they sent back — a tracked-changes .docx, a revised .tex, a returned .md — as a structured report rather than a wall of coloured text: which sections moved, which citation keys were added or removed, which numbers changed or appeared with no run behind them, which claims moved up the strength ladder, and every Word comment they left. Nothing is merged automatically. Use when a draft comes back from a co-author; use /import-manuscript to bring in a manuscript the kit has never seen, and /respond-review for a journal's decision letter."
disable-model-invocation: true
argument-hint: "<returned-file.docx|.tex|.md|.pdf>"
---

# /merge-coauthor — the three changes a read-through misses

Word's track-changes view answers *which words moved*. That is the one question
whose answer is already obvious, and it is what hides the three that are not:

- a **citation key disappeared** while the sentence it supported stayed
- a **number changed**, or a new one appeared that no recorded run produced
- a **claim moved up the ladder** — "our results suggest" became "we prove"

All three look like the paper, which is why they survive being read. They are
extracted mechanically here, and the prose diff is reported as counts underneath
them.

## Gate

`drafts/` must hold the version you sent. That is the comparison baseline — if
the co-author is returning something that was never in the kit, use
`/import-manuscript` instead.

## Step 1: run the comparison

```bash
python scripts/coauthor_diff.py --returned inbox/paper-supervisor.docx
```

`.docx` and `.tex` convert through pandoc, `.pdf` through pymupdf4llm — the same
converters `/import-manuscript` uses, never a hand-written parser. A missing
converter exits `BLOCKED` (3) naming what to install, rather than degrading into
a regex.

## Step 2: read the flags first

```
flags:
  citation_removed        Results   @kaya2023deep
  claim_strengthened      Results   "we prove"  (was: predictive)
  number_not_in_run_register        0.91  (as written: "0.91")
```

Each one is *"this changed, look at it"* — never *"this is wrong"*:

| Flag | What to do |
|---|---|
| `citation_removed` | Read the sentence that kept the claim. If the claim stands, it needs a source; if it does not, it needs cutting. |
| `claim_strengthened` | Compare against the evidence: `python scripts/claim_check.py`. A co-author's stronger sentence is sometimes the right one — but it has to be earned in the same revision. |
| `number_not_in_run_register` | `python scripts/experiment_db.py trace <number>`. Either a run was never registered, or the number was typed. Both are worth knowing before submission. |

## Step 3: read the comments

Word comments are pulled out of the `.docx` itself, because pandoc drops them and
they are frequently the only place the supervisor said **why**:

```
comments:
  Prof. Yılmaz (2026-08-15) — "Bu iddia için kaynak gerekiyor."
```

## Step 4: apply, by hand

Nothing was written into `drafts/`. Work through the report section by section
and apply what you accept — this is the part with a person behind it, and a tool
that merged for you would have made those calls silently.

After applying:

```bash
python scripts/cite_audit.py                 # keys still resolve
python scripts/consistency_check.py          # narrated vs presented numbers
python scripts/claim_check.py                # claim strength vs evidence
```

## What is deliberately not compared

**Prose.** Two honest edits of one paragraph share no wording, so a similarity
score over them measures nothing but the length of the paragraph. What is
compared is citation keys, quantities, claim strength and word counts — four
things with an unambiguous before and after.

**Whether a change is an improvement.** That is a judgement about the argument,
and it is yours and your co-author's.

## Reference

- **Script:** `python scripts/coauthor_diff.py --returned <file> [--drafts drafts]
  [--runs analysis/runs.jsonl]`
- **Reads:** `drafts/*.md`, the returned file, `analysis/runs.jsonl`
- **Writes:** nothing
- **Related:** `/import-manuscript` (a manuscript the kit has not seen),
  `/respond-review` (a journal's letter), `/revise` (`/critique`'s own findings),
  `/translate` (whose quantity comparison this reuses)

---
*The dangerous edit is never the one you can see in red. It is the sentence that still reads like yours.*
