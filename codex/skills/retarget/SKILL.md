---
name: retarget
description: "Move a manuscript to a different venue after a rejection or a change of plan: check the new venue's index status and fit, re-derive the word budget and section structure, switch the citation style, ingest the new template, regenerate the cover letter and submission pack, and list what the previous reviewers said that the new submission should address first. One pass over everything a venue change touches."
disable-model-invocation: true
argument-hint: "<new venue name|issn>"
---

# /retarget — The Same Work, a Different Venue

A rejection is not a verdict on the work, but it is a decision point, and the
mechanical part of moving venues is where a week disappears: a different style,
a different word limit, a different structure, a different template, a cover
letter that still names the old journal.

## Gate

1. `PROJECT.md` exists with a target venue set (the one being left).
2. If the decision letter exists (`reviews/decision-letter*.md`), read it — step 4
   depends on it. If the paper was desk-rejected with no reviews, say so; there is
   nothing to carry over except the editor's stated reason.

## Step 1: Is the new venue the right one?

```bash
python scripts/venue_check.py --title "<new venue>"
python scripts/venue_fit.py                       # candidates from your OWN reference list
```

Report index status (SCIE/SSCI/ESCI/Scopus/TR Dizin, quartile), and the predatory
heuristic's finding. **If the venue is flagged, stop and say so plainly.** A
rejection makes an author more willing to accept a venue they would otherwise
refuse, and that is exactly when this check matters.

`venue_fit.py` derives candidates from the reference list this manuscript already
cites — the honest version of "which journal wants this paper".

## Step 2: What the new venue changes

Ask for the new venue's author guidelines and record them in
`exports/submission/limits.json` (the same file `/submission-pack` uses, rewritten
for the new venue — the old limits are now wrong in every field).

Then work through, in this order:

| Change | Command |
|---|---|
| Citation style | `/restyle <apa7\|ieee\|vancouver\|…>` — drafts and bibliography are never hand-edited |
| Template | `/ingest-template <new template file>` — its rules then override the kit's defaults |
| Word budget | `python scripts/word_budget.py` against the new total; re-plan per section |
| Structure | paper-types skill — a venue may want a different section set (e.g. a Methods-last format, or a structured abstract) |
| Cover letter + form | `/submission-pack` — regenerate; never edit the old letter |

## Step 3: The structural gap, if there is one

If the new venue's structure differs (a short-paper format, a different section
set, an unstructured abstract where the old one was structured), do **not**
reshape the manuscript by deleting text. Re-outline (`/outline`) against the new
type, then move content into it — the evidence chain has to survive the move, and
a section deleted to fit a word limit takes its citations with it.

Re-run afterwards:

```bash
python scripts/cite_audit.py
python scripts/word_budget.py
python scripts/submission_pack.py --check
```

## Step 4: Carry the previous reviews forward — this is the part people skip

If the paper was reviewed before rejection, those reviews are the cheapest peer
review it will ever get. Go through the previous decision letter
(`review_letter.py --parse`) and classify each comment:

- **Fixed** — the revision already addresses it;
- **Should fix now** — valid, and the next reviewer will see it too;
- **Venue-specific** — mattered to the old venue, not to this one (a scope
  objection, a format demand);
- **Disagree** — recorded, with the reason, so it is answered consistently if it
  comes up again.

Write this to `reviews/carried-forward.md`. A comment that two independent
reviewers raise is not a matter of opinion any more.

## Step 5: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Hedef değişikliği: <eski> → <yeni>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Yeni mekân: SCIE · Q2 · SJR 0.84 · şüpheli bayrak yok
Stil:       APA7 → IEEE (restyle ✓, künye elle değişmedi)
Bütçe:      8 000 → 6 000 kelime · şu an 7 640 → 1 640 fazla
Şablon:     yeni şablon alındı, kurallar geçerli
Önceki hakem: 11 madde → 6 çözülmüş · 3 şimdi çözülmeli · 2 mekâna özgü

Sonraki: /submission-pack (kapak mektubu ve form yeniden üretilecek)
```

## Notes

- **Do not resubmit the same PDF to a new journal.** The style, the template and
  the cover letter all name the old venue; editors notice, and it is read as
  carelessness about their journal specifically.
- **Simultaneous submission is not this.** One venue at a time; the cover letter
  declares it, and the declaration has to be true.
- **A preprint changes nothing here** except that the cover letter must disclose it.

## Reference

- **Scripts:** `venue_check.py` · `venue_fit.py` · `word_budget.py` ·
  `review_letter.py --parse` · `submission_pack.py --check` · `cite_audit.py`
- **Related:** `/journal-check`, `/restyle`, `/ingest-template`,
  `/submission-pack`, `/respond-review` (if the new venue reviews it)

---
*Changing venue is a mechanical task with one judgement in it: whether the new venue is a place you would have chosen before the rejection.*
