---
name: import-manuscript
description: "Bring a manuscript that already exists — a .docx from a supervisor, a LaTeX chapter, a PDF of last year's submission — into the project so the kit's own machinery applies to it. Converts and splits it into section files, reads its reference list as a list of DOIs (re-fetched from the authoritative record, never transcribed), and reports which references cannot be resolved. Nothing in the text is edited and no citation is rewritten. Use when the paper was NOT written here and the author wants it verified, reviewed, restyled or finished."
disable-model-invocation: true
argument-hint: "<file.docx|.tex|.pdf|.md> [--resolve]"
---

# /import-manuscript — The Paper That Already Exists

## What this command is, and is not

It **is** the on-ramp: a document becomes section files under `drafts/`, its
reference list becomes register entries with authoritative BibTeX, and from that
point `/verify-citations`, `/critique`, `/revise`, `/restyle` and `/submit-check`
work on it exactly as they would on a paper drafted here.

It is **not** a rewrite. Not one sentence of the author's text is changed by this
command, and no `[12]` becomes `[@key]` without the author looking at it. An
import that quietly edited the argument would make every later check circular —
the kit would be verifying its own edit.

## Gate: Abort if Failed

1. **Check:** `PROJECT.md` exists. If not: run `/new-project` first — the import
   writes into a project's `drafts/`, `sources/` and `bib/`, and those have to
   exist and belong to something.
2. **Check:** the file exists and is one of `.md .docx .tex .pdf .odt .rtf .html`.
   - `.docx` / `.tex` / `.odt` / `.rtf` need **pandoc**; `.pdf` needs
     **pymupdf4llm**. Both exit BLOCKED with the install line — the manuscript is
     never hand-parsed as a fallback, because a `.docx` read with a regex turns a
     table into a paragraph and a footnote into body text.
3. **Prefer the source over the PDF.** If the author has both, take the `.docx`
   or `.tex`. A PDF conversion loses the heading structure, and the import then
   produces one long file the author has to split by hand.

## Procedure

### Step 1: Plan, and show it before writing anything

```bash
python scripts/manuscript_import.py --file <path> --plan
```

Report to the author, in their language:

- the **sections** it found and the files they would become (this is where a bad
  conversion is visible: three sections from a 40-page thesis means the headings
  did not survive);
- the **word count** — against `PROJECT.md`'s budget if one is set;
- the **reference list**: how many entries, how many carry a DOI, how many do not;
- the **citation style** it detected (numeric / author-year / pandoc) — this
  decides what Step 3 can offer;
- any **warning**, verbatim. "No headings" is the important one.

If a target file already exists the command refuses and names it. Do not reach
for `--force` on the author's behalf: a section file that exists is a section
someone has been editing.

### Step 2: Import, then resolve the references

```bash
python scripts/manuscript_import.py --file <path>            # sections
python scripts/manuscript_import.py --file <path> --resolve  # + bibliography
```

`--resolve` sends every DOI in the reference list through `doi2bib.py` and
registers each entry as a **candidate** stamped
`metadata_source: "manuscript reference list (unverified)"`. Say plainly what
that means: the bibliography now holds the publisher's record, not the author's
typing, and the two are allowed to differ — that difference is a finding, not an
error to smooth over.

Entries **without a DOI** are listed in the report and are the author's next
piece of work. For each one:

```bash
python scripts/doi2bib.py --title-search "<title>" --year <year>
```

Never fill one in from memory. A reference that cannot be resolved stays
unresolved and `/verify-citations` will say so — which is the honest outcome and
occasionally the true one (a real book chapter with no DOI).

### Step 3: The citation rewrite is a proposal, not an edit

When the manuscript uses numeric citations, `drafts/citation-map.json` holds
`{"12": {"doi": …, "bib_key": …}}`. Offer the conversion to pandoc syntax
**section by section, with the author reading each mapping**, and only if they
want it. State the trade honestly:

- converting means `/verify-citations`, `claim_check.py` and `cite_audit.py` can
  see the citations at all — until then, most of the kit's citation machinery is
  blind to this manuscript;
- a mis-mapped `[12]` attributes a claim to the wrong paper, and once the number
  is gone the error is unrecoverable by inspection.

If the author declines, that is a legitimate end state. Record it and continue —
the register and the bibliography still improve every later step.

### Step 4: Bind the numbers, if this is an empirical paper

An imported manuscript's results have no `analysis/` behind them. Ask whether the
data and the scripts exist:

- data exists → `/analyze-data` or `/experiment` re-establishes the chain, and
  `analysis/counts.json` lets `consistency_check.py` reconcile prose against it;
- they do not → say so explicitly in the report. `failure_scan.py`'s M3 check and
  `experiment_db.py trace` will both come back empty, and the author should know
  that this is a property of the import, not a verdict on the paper.

### Step 5: Hand off to the normal pipeline

```bash
python scripts/cite_audit.py          # in-text ↔ bibliography, both directions
```

Then, in order: `/verify-citations` → `/critique` → `/revise` → `/submit-check`.
Nothing about the rest of the pipeline changes for an imported manuscript.

## Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 Makale içe aktarıldı — tez-taslak.docx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bölümler:  7 dosya · 8.412 kelime (bütçe: 10.000)
Atıf stili: numaralı · metinde 46 farklı numara
Kaynakça:  52 kayıt · 41 DOI'li (çekildi) · 11 DOI'siz (aşağıda)
Sicil:     SRC-0001…SRC-0041 (aday, "unverified" damgalı)
Eşleme:    drafts/citation-map.json — öneri, uygulanmadı

DOI'siz 11 kayıt: <ilk 5, ad ve yıl>
Sonraki: doi2bib --title-search ile çöz → /verify-citations
```

Never report an import as complete while entries are unresolved without naming
them. The count that matters to the author is not "41 fetched" — it is "11 that
nothing has checked".

## Notes

- **This is not `/import-library`.** That one takes a Zotero/Mendeley export —
  references only. This one takes the manuscript, and its reference list is a
  by-product. Running both is normal; the register dedups.
- **A PDF-only manuscript is a degraded import** and should be reported as one:
  no heading structure, a reference list mangled by column breaks, and often
  hyphenated line-ends inside the DOIs. The `.docx` behind it is almost always
  worth asking for.
- **Existing figures and tables** come across as pandoc's media folder; the
  import does not renumber them. `figure_check.py` will report numbering and
  caption problems once the sections are in place.
- **This writes `drafts/` before an outline exists, and that is not a gate
  bypass.** The outline gate stops the kit from *generating* prose with nothing
  behind it; an imported manuscript is prose that already exists and that the
  author wrote. What the gate still governs is unchanged: `/draft` on top of this
  project remains blocked until an outline is approved, so anything the kit adds
  to the imported text goes through the same door as always. If the author wants
  to keep working on it section by section, build the outline from the imported
  structure first — `/outline` will bind it to the evidence cards, which is the
  step the imported manuscript never had.

## Reference

- **Scripts:** `python scripts/manuscript_import.py` (`--plan`, `--resolve`,
  `--force`) · `python scripts/doi2bib.py --title-search` (unresolved entries) ·
  `python scripts/cite_audit.py`
- **Writes:** `drafts/<nn>-<slug>.md`, `drafts/citation-map.json`, and — through
  their own sanctioned writers — `sources/registry.jsonl` and `bib/references.bib`
- **Related:** `/import-library` (references only), `/verify-citations` (the point
  of doing this), `/translate` (if the target venue's language differs),
  `/retarget`, `/critique`

---
*An imported manuscript's reference list is a claim about 52 papers. Re-fetching them is how it becomes 52 records.*
