---
name: front-matter
description: "Produce a thesis's front matter and check it: inner cover, approval page, ethics declaration, acknowledgements, Özet and Abstract with matching keyword lists, table of contents, list of tables, list of figures, abbreviations — in the order YÖK and your institute require, with the contents and lists derived from the body rather than typed. A thesis is turned back at the institute's formal check far more often than at the defence, and this is where."
disable-model-invocation: true
argument-hint: "[--check] [--order <institute-order.json>]"
---

# /front-matter — The Pages the Institute Checks First

The science is defended in front of a committee. The front matter is checked by a
secretary, in one pass, against a list — and a missing ethics declaration or a
list of figures that stops at 11 while the body has 14 costs a resubmission cycle.

## Gate

1. **Check:** the project type is a thesis (`PROJECT.md` → `thesis-bsc |
   thesis-msc | thesis-phd | thesis-cumulative`). For an article, most of these
   pages do not exist; say so rather than producing them.
2. **Check:** `drafts/` holds the body. The contents and the lists are *derived*
   from it — writing them before the chapters exist means writing them twice.
3. **Read** `templates/ingested/template-profile.md` if it exists. **Its rules
   override everything below**, including the page order (TEMPLATE SUPREMACY).

## Step 1: Establish the required order — do not assume it

Ask which institute, then read its guideline if the author has it
(`/ingest-template` handles a PDF/DOCX guideline). The kit's default is the
YÖK-conventional sequence:

```
iç kapak → onay sayfası → etik beyan → teşekkür → Özet → Abstract →
İçindekiler → Tablo listesi → Şekil listesi → Kısaltmalar
```

Universities differ in real ways — some put the ethics declaration after the
acknowledgements, some require a Turkish and an English inner cover, some add a
dedication page. If the author's guideline differs, write the order to
`templates/institution/front-matter-order.json` and pass it as `--order`; the
guideline wins over the kit, always.

## Step 2: Write the pages — with the author, not for them

Into `drafts/00-front-matter.md`, one `#` heading per page.

- **İç kapak / Onay sayfası** — the institute's own template governs the layout
  down to the font size. Fill only what the author gives you: names, titles,
  dates, the jury. **Never invent a jury member, a date or a supervisor's title.**
- **Etik beyan** — the standard declaration that the work is the author's own and
  that sources are cited. Where the study involved human subjects or data
  collection, this is also where the ethics-board reference goes; take it from
  `PROJECT.md`'s *Ethics approval* field or `analysis/datasets.jsonl`, and if it
  is absent, ask rather than writing "gerekli değildir".
- **Teşekkür** — the author's own words. Offer a scaffold; do not write feelings
  on someone's behalf.
- **Özet / Abstract** — the same summary in two languages, with the **same
  keyword list** in each. `frontmatter_check.py` compares the counts; whether the
  two say the same thing is `tr_style_check.py`'s Özet↔Abstract equivalence check
  and, finally, the author's judgement.
- **İçindekiler / Tablo / Şekil listeleri** — derived from the body's actual
  headings and captions. Do not type them: a typed list is a list that goes stale
  the next time a chapter is renamed, and the format build (`latex_build.sh` /
  `docx_build.sh`) generates them from the document anyway. Write them here so
  the check can compare, and regenerate after every structural change.
- **Kısaltmalar** — every abbreviation the body defines, alphabetically.

## Step 3: Check

```bash
python scripts/frontmatter_check.py
python scripts/tr_style_check.py            # Özet↔Abstract equivalence, TR conventions
```

`frontmatter_check.py` reports: a required page missing, a page out of order, a
keyword-count mismatch between Özet and Abstract, a contents entry with no chapter
behind it (or a chapter with no entry), and a figure/table in the body that the
list does not carry.

## Step 4: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📑 Ön kısım
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sayfalar: 9/9 (Y÷K sırası) ✓
Özet ↔ Abstract: 5 / 5 anahtar kelime ✓
İçindekiler: gövdedeki 14 başlıkla eşleşiyor ✓
Şekil listesi: 14 şekil ✓ · Tablo listesi: 6 tablo ✓

Elle doldurulacak: jüri üyeleri (onay sayfası), savunma tarihi
```

What the author must fill by hand stays visibly empty. A plausible-looking jury
member on an approval page is a fabrication with a signature line under it.

## Reference

- **Scripts:** `python scripts/frontmatter_check.py` · `tr_style_check.py`
  (Özet↔Abstract) · `word_budget.py --rq-trace` (chapter↔RQ mapping)
- **Skill:** thesis-structure (the YÖK requirements this is built on)
- **Writes:** `drafts/00-front-matter.md`
- **Related:** `/ingest-template` (the institute guideline), `/submit-check`,
  `/defense-prep`

---
*The committee reads the science. The institute reads this page, and it reads it first.*
