---
name: review-paper
description: "Write the referee report for SOMEONE ELSE'S manuscript that a journal asked you to review — from the notes you take while reading it, because the paper itself never enters the kit. Structures your notes into summary/significance/numbered Major and Minor comments/confidential note/recommendation, then audits the report: unanchored comments, broken numbering, a recommendation outside the journal's own option set, and the phrases with which an anonymous referee accidentally signs it. Use when you have accepted a review invitation. Not /critique (that simulates a review of YOUR draft) and not /respond-review (that answers a decision letter about your own paper)."
disable-model-invocation: true
argument-hint: "[--scaffold|--check] [<report-file>]"
---

# /review-paper — the kit never reads the paper

A manuscript sent to you for review arrives under a confidentiality undertaking.
Elsevier, Springer and NIH state it explicitly: uploading it to a tool is a
breach — **the referee's breach, not the author's** — and no amount of report
quality undoes it.

So this command does the opposite of the obvious thing. **You read the paper.**
That was never the hard part. The hard part, and the part that actually costs the
evening, is writing it up so that:

- the authors can respond to it point by point,
- each comment names a place in the text,
- the recommendation is one the portal actually offers,
- and the report does not quietly identify you.

None of that needs the manuscript, and all four are checkable.

## Hard rule for this session

**Do not read, summarise, quote or accept the manuscript under review.** Not as
a PDF, not as pasted text, not "just the abstract". If the user offers it,
decline once, briefly, and continue with their notes — that is CLAUDE.md
invariant 10, and `referee_report.py` refuses a `.pdf`/`.docx`/`.tex` path
before it opens the file.

## Step 1: the journal's own form

```bash
cat reviews/referee/review-form.json
```

```json
{
  "journal": "Example Transactions",
  "source_url": "https://example.org/reviewer-guidelines",
  "read_on": "2026-08-15",
  "recommendations": ["Accept", "Minor revision", "Major revision", "Reject"],
  "max_words": 1200
}
```

Read the options off the invitation e-mail or the reviewer portal. "Minor
revision" exists at most venues and not all; a recommendation the portal does not
offer means the editor has to come back and ask again. No file ⇒ `UNCHECKED`.

## Step 2: the reading checklist, before you read

Load the reporting guideline for the paper's type — `reporting-guidelines` skill:
CONSORT for an RCT, STROBE for observational, PRISMA for a systematic review,
CARE for a case report, COREQ/SRQR for qualitative. For an ML paper, the
`ml-research` skill's extraction schema is the same list in a different order:
baselines, splits, seeds, ablations, leakage, significance, reproducibility.

Read with the checklist beside you. What it catches is what a referee otherwise
notices only in the third paper of the evening.

## Step 3: scaffold, then write

```bash
python scripts/referee_report.py --scaffold reviews/referee/report.md
```

Then fill it in — this is the drafting the session helps with, working from what
**you** report about the paper:

- **Summary** in your own words. Authors read it first to find out whether you
  understood them; a summary that could describe any paper in the field tells
  them you did not.
- **Significance** — is the question worth answering, and does this answer move
  it? Separate from correctness, and editors weigh it separately.
- **Major comments**, numbered, each anchored (`Section 3.2`, `Table 2`,
  `line 145`) and each stating **what would resolve it**. "The evaluation is
  weak" is a verdict; "the split is random over recordings from the same bearing,
  so a group-aware split is needed" is a comment.
- **Minor comments**, numbered separately.
- **Confidential note to the editor** — suspected overlap, a conflict you only
  noticed on reading, a limit to your own expertise. Leave it empty rather than
  filling it.
- **Recommendation** — one of the journal's own options, consistent with the
  Major list. Four Majors and "Minor revision" is a report the editor will not
  be able to act on.

## Step 4: audit

```bash
python scripts/referee_report.py --check reviews/referee/report.md
```

| Check | Why it matters |
|---|---|
| Numbering 1..n, no bullets | authors answer point by point; an unnumbered comment gets no reply, and `--coverage` on their side cannot find it |
| Every Major anchored | a comment with no place in the paper is an opinion |
| Recommendation ∈ the journal's set | otherwise the editor re-requests it |
| Word limit | some forms have one |
| **Self-identification** | "as we showed in our previous work", "kendi çalışmamızda" — an anonymous report that points at its author's own work is signed |

## What this does not do

- **It does not read, and will not be persuaded to.** There is no flag.
- **It does not judge your comments.** Whether a criticism is fair, correct or
  proportionate is peer review's actual substance and is entirely yours.
- **It does not decide the paper.** The recommendation is your judgement; the
  script only checks it is one the journal offers.
- **It does not detect plagiarism, image manipulation or fabrication.** If you
  suspect any of those, that is a confidential note to the editor, not a check.

## Reference

- **Script:** `python scripts/referee_report.py` (`--scaffold`, `--check`, `--form`)
- **Writes:** `reviews/referee/report.md` and the `review-form.json` you filled
- **Related:** `reporting-guidelines` and `ml-research` (the reading checklists),
  `/critique` (a simulated review of **your** draft), `/respond-review` (answering
  a letter about your own paper), `/journal-check` (the venue you are refereeing for)

---
*The report an author remembers is the one that told them what to do next. Everything else is a grade.*
