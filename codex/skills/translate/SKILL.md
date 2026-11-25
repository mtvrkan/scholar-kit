---
name: translate
description: "Translate the manuscript between Turkish and English — section by section, with the terminology fixed in advance and a deterministic check that the citations, the quantities and the cross-references survived. Produces the target-language draft beside the source one, never on top of it. Use when a Turkish thesis becomes an English submission, when an English draft becomes a Turkish thesis chapter, or when a journal's language differs from the one the work was written in."
disable-model-invocation: true
argument-hint: "[tr-en|en-tr] [<section file or 'all'>]"
---

# /translate — The Same Paper in the Other Language

## What this command is, and is not

It **is** a translation with the invariants enforced: the same sources cited, the
same quantities reported, the same figure pointed at, the same term used for the
same concept throughout. Those four are what a reader of only the target text
cannot check and what `translation_check.py` checks mechanically.

It is **not** a machine-translation button. The translation happens here, one
section at a time, because the failure mode of a whole-document pass is a
paragraph quietly dropped — and a dropped paragraph that carried no citation, no
number and no cross-reference is invisible to every check in this kit. The length
ratio in the report exists for exactly that gap.

## Gate: Abort if Failed

1. **Check:** at least one section file exists under `drafts/`.
2. **Check:** `PROJECT.md` states the output language. If the translation target
   is the new output language, update `PROJECT.md` **after** the translation is
   accepted — not before, or every subsequent check will judge the source draft
   against the wrong language's conventions.
3. **Decide where it lands:** `drafts/en/` for tr→en, `drafts/tr/` for en→tr. The
   source is never overwritten. Two languages of one paper are two documents, and
   the moment one replaces the other, the ability to check them against each other
   is gone.

## Procedure

### Step 1: Fix the terminology before translating a word

Read the project's own glossary (`templates/tr-terminology.json`, copied in by
`/new-project`), and build the term table for **this** paper: every domain term
that appears more than twice, with the single rendering it will have in the
target language.

Present it to the author before starting. Two reasons this comes first:

- a term decided mid-translation means the first half and the second half of the
  paper use different words for one concept, and that reads as two authors;
- Turkish academic vocabulary is genuinely contested (`veri seti` / `veri kümesi`,
  `öznitelik` / `özellik`, `duyarlılık` / `anma`). The kit does not pick — the
  author does, once, here. `tr_style_check.py` and `translation_check.py` then
  both enforce the choice rather than a preference.

Terms with no accepted Turkish equivalent stay in English, italicised, with the
Turkish gloss at first mention — and then consistently in that form.

### Step 2: Translate one section, in this session

Drafting is never delegated, and translation is drafting. Per section, in the
target language's academic register (academic-writing skill: `turkish-academic.md`
or `english-academic.md`):

**Carry across unchanged:**
- every citation key, byte for byte — `[@yilmaz2020derin]` is not translated;
- every quantity, at the precision the source reports it. Re-rounding is not a
  translation decision; if `0,8091` should be `0.81`, it should be 0.81 in both
  versions, and that is an edit to make in both;
- evidence card ids (`EV-####`), equation numbers, and the identity of every
  figure and table (`Şekil 3` ↔ `Figure 3` — the *number* never moves).

**Change deliberately:**
- the decimal separator, to the target language's convention (`0,85` ↔ `0.85`)
  and the thousands separator with it;
- the cross-reference word (`Tablo` ↔ `Table`), never its number;
- figure captions and axis labels — regenerate them rather than editing the
  image: `python scripts/results_figure.py --lang en …` writes the caption in the
  target language from the same register.

**Never do:**
- translate the title of a cited work inside the bibliography. A Turkish source
  keeps its Turkish title; the target style's rule for a bracketed translation is
  the citation-styles skill's, and `references.bib` is written by `doi2bib.py`
  alone in any case;
- translate a direct quotation without marking it. A translated quotation is a
  paraphrase of a translation: mark it (`[çeviri bize aittir]` / `[author's
  translation]`) or quote the original and translate in a footnote;
- carry a hedge across at a different strength. `may contribute` is not
  `katkı sağlamaktadır`. The claim-strength ladder is language-independent and
  `claim_check.py` reads the target text, not the source.

### Step 3: Check what must not have changed

```bash
python scripts/translation_check.py --source drafts/03-yontem.md \
    --target drafts/en/03-methods.md --source-lang tr --target-lang en
```

Findings, and what each one actually means:

| Finding | Read it as |
|---|---|
| `citation_lost` | a paragraph was dropped, or a citation was silently merged |
| `citation_added` | a source appeared in translation — find out where from |
| `number_missing` / `number_added` | a digit moved, or a sentence was reformulated away from its number |
| `number_rounded` | legitimate, but now the two versions report different digits — fix one |
| `crossref_mismatch` | figure/table numbering shifted between versions |
| `term_unity` | one concept, two renderings in the target — Step 1's table was not applied |
| `untranslated_lines` | a passage was pasted, not translated |
| `section_count` | a heading was lost or added |

Resolve every finding before moving to the next section. A backlog of findings
across ten sections is how a translation ends up with a bibliography that does
not match its text.

Then the shape line: a length ratio far from ~1.0–1.3 (tr→en usually shortens
slightly; en→tr usually lengthens) is the only signal the kit has for a dropped
paragraph that carried nothing checkable. Look at it.

### Step 4: Register, then the language's own conventions

- `style-auditor` on the target text — register, hedging balance, tense
  discipline in the target language, not the source's.
- Turkish target: `python scripts/tr_style_check.py` — term unity, voice mixing,
  and the Özet↔Abstract equivalence.
- Thesis: `/front-matter --check` — Özet and Abstract must carry the **same
  number of keywords**, and the same claims. A translated abstract that gained a
  sentence is the single most common finding at the institute's formal check.

### Step 5: What the translation does not inherit

State these plainly when handing back:

- `verify-status.json` refers to the draft it was run on. Re-run
  `/verify-citations` against the translated draft — the citation keys should be
  identical, which makes this cheap, and if it is not cheap something moved.
- Review rounds (`reviews/round-N.md`) refer to the source draft's line numbers.
- `word_budget.py` targets are language-specific; an English 8.000-word limit is
  not a Turkish 8.000-word limit.

## Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 Çeviri tamamlandı — tr → en · 03-yontem
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hedef:     drafts/en/03-methods.md · 1.180 kelime (kaynak 1.040 · oran 1.13)
Değişmezler: atıf 14/14 ✓ · nicelik 22/22 ✓ · çapraz gönderme 6/6 ✓
Terim tablosu: 11 terim sabitlendi · karışım yok ✓
Kalan bulgu: yok

Sonraki bölüm: 04-bulgular  ·  Bitince: /verify-citations (çeviri taslağına karşı)
```

Never report a section as translated while `translation_check.py` still returns
findings, and never report the invariants as "✓" from reading the text — that
line comes from the script or it does not appear.

## Notes

- **Özet is not a translation of the Abstract**, and vice versa — but they must
  make the same claims and carry the same keyword count. Write the second one from
  the first, then check with `/front-matter --check`, not by eye.
- **Both languages, kept in sync, is a maintenance cost** the author is taking on
  knowingly: every later revision has to be made twice, and `translation_check.py`
  is the only thing that will notice when it was made once. Say this out loud at
  the start, not at the end.
- **A translated manuscript is still the author's work** and the AI-use disclosure
  should say translation assistance explicitly — `/disclosures ai` has the field.

## Reference

- **Scripts:** `python scripts/translation_check.py` (`--source`, `--target`,
  `--source-lang`, `--target-lang`, `--glossary`) · `python scripts/tr_style_check.py`
  · `python scripts/results_figure.py --lang` · `python scripts/word_budget.py`
- **Subagent:** style-auditor (register in the target language; returns an edit
  list, never a rewrite)
- **Skills:** academic-writing (`turkish-academic.md`, `english-academic.md`),
  citation-styles (how a translated title is cited), thesis-structure (Özet↔Abstract)
- **Writes:** `drafts/<lang>/<section>.md`
- **Related:** `/import-manuscript` (bring the other language's draft in first),
  `/retarget` (a venue change is what usually triggers this), `/front-matter`

---
*Two honest translations of one paragraph share no sentence. They share every citation, every number, and every figure they point at — which is why those are the ones a machine checks.*
