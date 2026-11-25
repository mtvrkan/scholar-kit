---
name: respond-review
description: "Work through a REAL journal decision letter — the editor's e-mail with two or three reviewers and their numbered comments — rather than the kit's own simulated critique. Parses the letter into structured comments, plans an edit or a reasoned refusal for each, applies them through the drafts, and produces a point-by-point response letter whose coverage is checked mechanically: every comment answered, none invented. Use /revise for /critique's own findings; use this when a journal has replied."
disable-model-invocation: true
argument-hint: "<letter-file> [--round 1]"
---

# /respond-review — The Letter a Journal Actually Sent

`/critique` simulates a review and `/revise` works through its findings. This
takes the document an author receives: an editor's decision with three reviewers
and forty numbered comments, where the work is not "what should I fix" but
"have I answered every one, and can the editor see that I have".

## Gate: Abort if Failed

1. **Check:** the letter file exists inside the project (`reviews/`).
   - Not there yet: "Editörün mektubunu `reviews/decision-letter.md` olarak
     kaydedin (e-postadan yapıştırmanız yeterli). PDF ise:
     `python scripts/pdf2md.py --pdf <file>`."
2. **Check:** `drafts/` holds the manuscript the letter is about.
   - If the drafts have moved on since submission, say so: the reviewers read a
     specific version, and a response written against a different one produces
     answers to line numbers that no longer exist.

## Step 1: Parse the letter — do not read it into prose

```bash
python scripts/review_letter.py --parse reviews/decision-letter.md
```

Returns one record per comment: reviewer, number, text. Numbering restarts per
reviewer in nearly every real letter, so the ids are `Reviewer 2.3`, not `3`.

If a block came back `unnumbered`, the letter did not number it — the script
refuses to split a paragraph into invented comments. Number them **with the
author**, in the response, and say in the letter that you have done so
("R2 raised three points in a single paragraph; we address them as R2.a-c").

## Step 2: Classify each comment before touching the manuscript

Go through them one at a time and assign exactly one of four:

| Class | Meaning | What the response says |
|---|---|---|
| **Do** | the reviewer is right | what changed, and where (section + what the new text says) |
| **Do differently** | the concern is valid, the proposed fix is not | the concern, the alternative, why it addresses the same problem |
| **Cannot** | out of scope, impossible with this data, would require a new study | why, plainly, plus what *was* done instead (a limitation paragraph, a caveat) |
| **Disagree** | the reviewer is mistaken | the evidence, courteously, and never more than the evidence supports |

**"Disagree" and "Cannot" are legitimate and both must be visible.** An author
who silently ignores a comment is read as evading it; an author who says "we
could not do this because the cohort is retrospective, and we have added this to
the limitations" is read as honest. Never fake a change to close a comment, and
never claim an analysis was run that was not — `/verify-citations` and
`experiment_db.py trace` will catch it later, and a reviewer often catches it
sooner.

Present the classification table to the author and get approval **before** any
edit. This is the one place where a wrong call is expensive: an unnecessary
re-analysis costs weeks.

## Step 3: Apply the edits

Route each **Do** / **Do differently** through the existing machinery — the same
discipline as `/revise`:

- edits go into the section file, never into a copy;
- a new claim needs a card (`evidence_db.py`) and a new citation needs
  `doi2bib.py`; the phase gates still apply;
- a new number needs a run behind it (`/experiment`, then
  `experiment_db.py trace` to confirm the number in the text matches a record);
- log every change to `reviews/changelog-round-N.md` as you go, with the comment
  id — that log is what the response letter is written from, so writing it later
  means writing it from memory.

After the edits:

```bash
python scripts/cite_audit.py          # citations still resolve
python scripts/consistency_check.py            # prose numbers still agree
python scripts/claim_check.py                  # nothing got stronger than its card
```

## Step 4: Write the response letter

`reviews/response-round-N.md`, in the format every editor expects:

```markdown
# Response to Reviewers — Round 1

We thank the editor and the reviewers. Changes are marked in the revised
manuscript; reviewer comments are reproduced in italics.

## Reviewer 1

**1.** *"The sample size is not justified in Section 3."*

We agree. Section 3.2 now reports the power analysis (n=128 for d=0.5 at
80% power) and states the assumption it rests on. **Manuscript p. 7, ¶2.**

**2.** *"Figure 2 is unreadable at print size."*
...
```

Three rules that matter more than the wording:

- **Quote the comment, do not paraphrase it.** A paraphrase always shades the
  comment toward what is easy to answer, and the editor has the original open.
- **Point at the change**, by section and paragraph. "We have revised the text"
  with no location is the single most common cause of a second revision round.
- **Answer in the reviewer's numbering**, even when you group. The editor reads
  down the list.

## Step 5: Coverage — the check the editor runs first

```bash
python scripts/review_letter.py --parse reviews/decision-letter.md \
    --coverage reviews/response-round-N.md
```

Exit 2 means either a comment has no response, or the response answers a comment
the letter never made (usually a mis-numbering — and to the editor it reads worse
than a gap). Fix and re-run until it exits 0.

The script matches on **numbers, not wording**: a paragraph that echoes the
reviewer's phrasing without answering by number does not count, because from the
editor's side it does not either. And it says plainly what it does not check —
whether an answer is *adequate*. That is the reviewer's call, and no script has it.

## Step 6: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📨 Hakem yanıtı — Round 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mektup:   3 hakem · 27 yorum (Editör 1 · R1 9 · R2 11 · R3 6)
Sınıflar: 19 uygulandı · 4 farklı biçimde · 3 yapılamadı · 1 katılmıyoruz
Kapsama:  27/27 ✓ (review_letter.py --coverage)

Denetimler: cite_audit ✓ · consistency ✓ · claim_check ✓
Yeni kaynak: 4 (hepsi doi2bib ile doğrulandı)
Yeni koşu:   6 (RUN-0031…0036, tohumlarıyla kayıtlı)

Yapılamayanlar ve gerekçeleri (mektupta açıkça yazılı):
  • R2.7 — prospektif kohort gerektirir; sınırlılıklara eklendi
  • R3.2 — veri lisansı paylaşımı engelliyor; DS-0001 lisansı alıntılandı
```

Always list the **Cannot** and **Disagree** items in the report, not just the
count. They are the parts of the response the author has to be comfortable
defending, and they should never reach the editor without being read aloud once.

## Notes

- **Rounds are files, not overwrites.** `decision-letter-r2.md`,
  `response-round-2.md`. A second-round letter refers to the first response, and
  an editor checks consistency between them.
- **A rejection is not this command.** If the decision is Reject, the work is
  `/retarget` — a different venue, a re-scoped paper — not a response letter.
- **`/critique` is still useful here**: run it on the revised manuscript before
  resubmitting, so the next reviewer's first objection is one you have already seen.

## Reference

- **Scripts:** `python scripts/review_letter.py` (`--parse`, `--coverage`) ·
  `cite_audit.py` · `consistency_check.py` · `claim_check.py` ·
  `experiment_db.py trace` (a new number must have a run behind it)
- **Writes:** `reviews/response-round-N.md`, `reviews/changelog-round-N.md`
- **Related:** `/revise` (the kit's own critique), `/critique` (a fresh read of
  the revision), `/submission-pack` (the resubmission's cover letter),
  `/retarget` (after a rejection)

---
*Answering every comment is not the same as agreeing with every comment. The first is required; the second never was.*
