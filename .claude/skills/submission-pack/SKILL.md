---
name: submission-pack
description: "Produce everything the journal's submission portal asks for besides the manuscript: the cover letter to the editor, title/abstract/keywords checked against the venue's own limits, highlights (3-5 bullets, character-checked), the ethics/funding/competing-interests/CRediT/data-availability statements, and suggested reviewers derived from your own reference list. Writes exports/submission/. Use after /submit-check passes; the limits come from a file you fill from the venue's author guidelines, never from the model's memory."
disable-model-invocation: true
argument-hint: "[--venue <name>] [--letter-only] [--check]"
---

# /submission-pack — The Second Document Nobody Talks About

The manuscript is finished, and then there is the form: title length, abstract
word count, keywords, highlights, five declarations, a cover letter, suggested
reviewers. Every one of those has a limit the venue publishes and an editorial
assistant checks before any reviewer sees the paper. A desk rejection there costs
weeks for a reason that took ten seconds to check.

## Gate: Abort if Failed

1. **Check:** `verify-status.json` exists with `result: PASS`.
   - If not: "Önce `/verify-citations`. Kapak mektubu, doğrulanmamış atıflar
     taşıyan bir makale için yazılmaz."
2. **Check:** at least one file in `drafts/`.
3. **Recommend (do not block):** `/submit-check` first. This command assembles the
   form; that one checks the manuscript.

## Step 1: The limits file — the one thing the kit will not remember

```bash
cat exports/submission/limits.json   # if it does not exist, create it WITH the author
```

```json
{
  "venue": "Mechanical Systems and Signal Processing",
  "source_url": "https://www.<venue>/guide-for-authors",
  "read_on": "2026-08-14",
  "title_max_chars": 120,
  "abstract_max_words": 250,
  "keywords": {"min": 4, "max": 6},
  "highlights": {"count_min": 3, "count_max": 5, "max_chars": 85},
  "manuscript_max_words": 8000,
  "required_statements": ["ethics", "funding", "competing_interests",
                          "data_availability", "credit", "ai_disclosure"]
}
```

**Ask the author to read these off the venue's own author-guidelines page and
paste them.** Do not fill this file from memory, and do not offer to: "Elsevier
abstracts are 250 words" is a remembered limit, it is wrong often enough to cause
the exact desk rejection this command exists to prevent, and it is the same error
class as a remembered DOI. If the author does not have the page open, say so in
the report — `submission_pack.py` returns `UNCHECKED` (exit 2) rather than a
comfortable `OK`, because "nothing was checked" and "no problems" must not read
the same.

## Step 2: Check what exists

```bash
python scripts/submission_pack.py --check
```

Reports title characters, abstract words, keyword count, highlights (count and
per-item characters), total manuscript words, and which required statements are
missing — each with the command that produces it.

## Step 3: The statements — each from its own source

```bash
python scripts/compliance_gen.py availability          # from the dataset + run registers
python scripts/compliance_gen.py credit --authors '[…]'
python scripts/compliance_gen.py funding --grants '[…]'      # or --none, explicitly
python scripts/compliance_gen.py ai-disclosure --tool "…" --uses "…"
```

Write them to `exports/submission/statements.md`.

Two of these have to be handled carefully:

- **Data availability** is generated from `analysis/datasets.jsonl` and
  `analysis/runs.jsonl`. If a dataset has no citation DOI or no recorded licence,
  the script writes **no sentence for it** — and you must not write one either.
  "Available from the corresponding author on reasonable request" is the sentence
  most often found to be untrue after publication; if that is genuinely the
  arrangement, the author writes it themselves, knowing what they are promising.
- **Competing interests** is never assumed absent. Ask. "The authors declare no
  competing interests" is a claim about the authors' finances and relationships,
  and nothing in this project knows those.

## Step 4: Highlights

3-5 bullets, each ≤ the venue's character limit, each a *finding* rather than a
topic ("A CNN reaches 0.94 ROC-AUC on CWRU under variable load" — not "We study
bearing faults"). No citations: highlights are read standalone and `[@key]`
renders as literal text in the form.

```bash
python scripts/submission_pack.py --highlights
```

## Step 5: The cover letter

Write `exports/submission/cover-letter.md`. Structure, in the editor's reading
order — they spend under a minute on it:

1. **What the paper reports**, in one sentence, in the venue's vocabulary.
2. **Why this venue** — the specific fit, ideally naming work the journal has
   published that this extends. `python scripts/venue_fit.py` derives candidates
   from your own reference list, and how many of your citations are already in
   this venue is the honest version of that paragraph.
3. **What is new**, bound to the manuscript's own claims — never a stronger claim
   in the letter than in the paper. An editor who reads "we prove" in the letter
   and "our results suggest" in the abstract has learned something about the
   authors.
4. **The declarations the venue requires in the letter itself**: original work,
   not under consideration elsewhere, all authors approved, ethics approval where
   applicable, any preprint already posted.
5. **Suggested / opposed reviewers**, if the venue asks.

**Suggested reviewers come from your own reference list**, not from the model's
memory of who works on this topic: run `venue_fit.py` and the registry, pick the
authors of the sources this manuscript actually engages with, and exclude anyone
with a conflict (same institution, recent co-authorship, supervisor/student).
Never invent an e-mail address — leave it for the author to fill; a wrong address
in a portal is worse than an empty field. State the conflict rule you applied in
the report so it is visible.

## Step 6: Assemble and report

```bash
python scripts/submission_pack.py --manifest
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📮 Gönderim paketi — <venue>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Başlık:     104/120 karakter ✓
Özet:       238/250 kelime ✓
Anahtar:    5 (4-6) ✓
Highlights: 4 madde, en uzunu 81/85 ✓
Metin:      7 640/8 000 kelime ✓

Beyanlar:   etik ✓ · fon ✓ · çıkar çatışması ✓ · CRediT ✓
            veri erişilebilirliği ✓ (DS-0001, CC-BY-4.0, DOI ile)
            AI beyanı ✓

Kapak mektubu: exports/submission/cover-letter.md
Önerilen hakem: 3 (kendi kaynak listenizden; e-posta alanları boş)

Açık kalan: <her biri tek satır, boş bırakılmışsa nedeni>
```

Everything still open is listed. A field the author must fill (an ORCID, a
funder's grant number, a reviewer's e-mail) stays visibly empty rather than
plausibly filled.

## Notes

- **`--letter-only`** regenerates just the cover letter — the common case when
  retargeting after a rejection (`/retarget`).
- **The letter never claims more than the paper.** If the abstract hedges and the
  letter does not, the letter is wrong, not the abstract.
- **Preprint disclosure**: if the manuscript is already on arXiv/SSRN/OSF, most
  venues require the letter to say so. Ask; do not assume it is not.

## Reference

- **Scripts:** `python scripts/submission_pack.py` (limits, counts, manifest) ·
  `python scripts/compliance_gen.py` (four statements, one of them derived) ·
  `python scripts/venue_fit.py` (the venue-fit paragraph and reviewer candidates)
- **Writes:** `exports/submission/` — `cover-letter.md`, `highlights.md`,
  `statements.md`, `metadata.md`, and the `limits.json` you filled
- **Related:** `/submit-check` (the manuscript), `/journal-check` (choosing the
  venue), `/retarget` (after a rejection), `/disclosures`

---
*The form is not paperwork around the paper. For the first week after submission it is the only thing anyone reads.*
