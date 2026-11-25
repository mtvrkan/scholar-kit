---
name: docx-output
description: "DOCX output & Word template compliance. Pandoc markdown → Word pipeline with CSL citation rendering, --reference-doc style mapping (Heading 1-4, Body Text, Block Text, Caption, Table styles); how template-profile.md constraints the build (TEMPLATE SUPREMACY rule — profile overrides kit defaults); figure/table numbering and captions in DOCX; bash scripts/docx_build.sh usage (execute, don't read); troubleshooting missing/broken styles, Turkish character/font issues, page-break control via raw OpenXML. Use when building thesis/paper to .docx, debugging styles/formatting, or preparing submission-ready Word documents."
---

> **Gate:** `docx_build.sh` writes into `build/`/`exports/`, which
> `.claude/hooks/phase_gate.py` enforces at the tool-call layer per CLAUDE.md
> Invariant 3 — verify-status.json must be PASS and the latest
> `reviews/round-N.md` must show Major issues: 0, or the hook denies the
> call regardless of what this skill says. Run `/verify-citations` and
> `/critique` (looping through `/revise` until Major=0) before building.
>
> **Gate:** `.claude/hooks/template_supremacy_gate.py` also enforces
> Invariant 8 (TEMPLATE SUPREMACY) at the tool-call layer: when
> `templates/ingested/template-profile.md` exists, `docx_build.sh`'s
> reference-doc argument MUST be `templates/ingested/reference.docx` (or
> `-` for an explicit draft-preview build) — any other path is denied. This
> covers only the reference-doc argument, not the LaTeX build path or
> `docx_style_check.py`'s own font/size drift check (still a non-fatal WARN).

## 1. Pandoc Pipeline Overview

The output is produced via `scripts/docx_build.sh` (execute it — never
hand-assemble the pandoc call), which runs:
```bash
pandoc --citeproc --csl templates/csl/<style>.csl \
  --bibliography bib/references.bib \
  --from markdown+smart --to docx \
  --reference-doc templates/ingested/reference.docx \
  --output build/thesis.docx \
  --metadata link-citations=true \
  <section1.md> [section2.md ...]
```

**Flow:**
1. **Input:** Markdown files + YAML metadata (title, author, date) + bibliography (`references.bib`)
2. **Citation processor:** `--citeproc` + CSL file render `[@key]` to formatted citations
3. **Reference doc:** Styles from `reference.docx` are APPLIED to all output headings, body text, etc.
4. **Output:** Institution-compliant .docx with intact styling, numbering, TOC

---

## 2. Markdown to Word Mapping

Pandoc maps Markdown to Word styles automatically:

| Markdown syntax | Maps to Word style | Example |
|---|---|---|
| `# Heading` | Heading 1 | Chapter titles |
| `## Heading` | Heading 2 | Section headings |
| `### Heading` | Heading 3 | Subsection headings |
| `#### Heading` | Heading 4 | Sub-subsection headings |
| Body paragraph (1st in a section) | **First Paragraph** | Normal prose, no first-line indent |
| Body paragraph (2nd+ in a section) | Body Text | Normal prose, first-line indent |
| `> quote text` | Block Text | Indented quotes (if present in ref.docx) |
| Table | Table | Standard table style (Pandoc references table style ID "Table" literally, not "Table Grid") |
| `![alt](path/image.png)` | Figure + caption | Image with captions (via Caption style) |

**Rule:** If Word style exists in reference.docx, Pandoc uses it. If not, Pandoc applies a sensible fallback. Undefined custom styles → **silently ignored** (style doesn't render; text appears in Normal, NOT Body Text — verified live: a reference.docx missing "First Paragraph" makes every section's opening paragraph fall back to bare Normal even when Body Text IS defined, since Pandoc treats "First Paragraph" and "Body Text" as two separate, both-required styles, not one style with a fallback name for the other).

---

## 3. Reference Document (template.docx)

### What it is:
A **template Word file** containing your desired styles (font, size, spacing, color, alignment) for Heading 1, Heading 2, Body Text, etc. Pandoc reads ONLY the style definitions, NOT the content.

### How to create one:

**Option A: Ingest your institution's template:**
```bash
/ingest-template templates/ingested/your-university-template.docx
```

This creates `template-profile.md` documenting all styles found in your template.
format-engineer also regenerates `templates/ingested/reference.docx` from those
extracted values automatically (no manual style copy-paste in Word):
```bash
python scripts/make_reference_docx.py --out templates/ingested/reference.docx \
  --font "<extracted font>" --size <extracted size> --spacing <extracted line spacing>
```

**Option B: Generate a baseline via script, then adjust:**
```bash
python scripts/make_reference_docx.py --out templates/paper/reference.docx --font "Times New Roman" --size 12 --spacing 1.5
```
This creates Title, Heading 1-4, First Paragraph, Body Text, Block Text,
Table, Caption, and Bibliography styles pre-populated with sensible defaults
(Table is cloned from Word's built-in "Table Grid" borders under the style
ID "Table," since that's the literal ID Pandoc's docx writer references —
defining a style named "Table Grid" instead would go unused). Open the
result in Word and adjust only what your institution's template requires.

**Option C: Manual style configuration in Word (from scratch):**
1. Open Word, create `reference.docx`.
2. Define each style: Home → Styles → Modify.
   - **Heading 1:** Arial 14pt bold, 12pt space before, 0pt after, left-aligned
   - **Heading 2:** Arial 12pt bold, 6pt space before, 0pt after
   - **Body Text:** Times New Roman 12pt, 1.5 line spacing, justified
   - **Block Text:** Times New Roman 11pt, gray background (optional), left indent 0.5" (Pandoc uses this style for `>` blockquotes, not "Block Quote")
   - **Table:** create/rename a table style to the literal name "Table" (not "Table Grid") — Pandoc's docx writer references this exact style ID for every generated table
   - **Caption:** Times New Roman 10pt, gray text (optional)
3. Create one paragraph in each style (so Pandoc reads the style definition).
4. Save as `reference.docx`.

**Critical:** Pandoc imports style *definitions* from reference.docx. Content is ignored.

---

## 4. Template-Profile Supremacy Rule

If `templates/ingested/template-profile.md` exists (created by `/ingest-template`), **its rules override all kit defaults.**

### Example template-profile.md:
```markdown
# Template Profile: University of Istanbul

## Detected styles
- Heading 1: Arial 14pt, bold, 12pt space before
- Heading 2: Arial 12pt, bold, 6pt space before
- Body Text: Calibri 11pt, 1.15 line spacing
- Table: No alternating rows
- Caption: Calibri 9pt, gray

## Institution requirements
- Margins: 2.5 cm (T/B/L), 2.0 cm (R)
- Page numbering: footer, right-aligned, start at 1 on page 1
- Headings: capitalize first word only (not all caps)
- Tables: no colored headers
- Figures: caption below; table: caption above
- Language: Turkish thesis → Heading 1 in Turkish; Abstract section in English (separate page if required)

## Overrides
- Default kit Heading 1: Times New Roman 16pt → OVERRIDE to Arial 14pt
- Default kit Body Text: 1.5 spacing → OVERRIDE to 1.15
- Default kit table style (no grid) → OVERRIDE to gridlines on
```

When this profile exists:
- `docx_build.sh` uses **only** the styles defined in reference.docx.
- Kit defaults are **ignored completely**.
- If a required heading style is missing from reference.docx, the build **warns** but does not fail.

---

## 5. Bibliography & Citation Rendering

### CSL files (Citation Style Language):
Pandoc + `--citeproc` renders in-text `[@key]` citations using a CSL file
from `templates/csl/`:

```bash
pandoc ... --csl templates/csl/apa.csl --bibliography bib/references.bib ...
```

PROJECT.md's `- **Citation style:**` bullet holds an enum key (`apa7`,
`ieee`, ...), not a filename — resolve it via the citation-styles skill's
"CSL File Mapping" table before calling `docx_build.sh` (its 2nd argument is
the resolved `templates/csl/*.csl` path, and it errors cleanly if the file
doesn't exist — it does not accept the enum key directly). Do not invent a
`bib/<style>.csl` path; no such copy step exists.

**In-text citation patterns:**
```markdown
Direct citation: [@Smith2020] renders as (Smith 2020) or [1] depending on CSL.
Narrative: Smith [-@Smith2020] says → "Smith (2020) says" (cite-only, no author in brackets)
Multiple: [@Smith2020; @Jones2021] → (Smith 2020; Jones 2021)
```

### Bibliography section:
Add at the end of your markdown:
```markdown
# References
```

Pandoc auto-appends the full bibliography after this heading.

---

## 6. Figures, Tables & Captions in DOCX

### Figures (inserted via Pandoc):
```markdown
![Figure caption: Results of experiment A.](figures/results_a.png)
```

**Output behavior:**
- Image inserted.
- Caption text becomes a separate "Caption" paragraph in Word.
- Figure numbering: Word auto-numbers (Figure 1, Figure 2, …) if the Caption style is used.

**Spacing:** Adjust in reference.docx Caption style (margins, font size).

### Tables (Markdown syntax):

```markdown
| Method | Accuracy | F1 |
|--------|----------|-----|
| Baseline | 85% | 0.82 |
| Ours | **92%** | **0.91** |

Table: Table 1. Results comparison.
```

**Output behavior:**
- Table inserted with the "Table" style (from reference.docx; Pandoc references this exact style ID, not "Table Grid").
- Caption "Table 1. Results comparison." rendered below table.
- Numbering: Word auto-numbers if Caption style in reference.docx applies to tables.

**Best practice:** Keep markdown tables simple; complex formatting (merged cells, colors) → export from script or use raw OpenXML (Section 8).

---

## 7. Building & Executing

### Execute (don't read):
```bash
bash scripts/docx_build.sh build/thesis.docx templates/csl/<style>.csl \
  templates/ingested/reference.docx drafts/introduction.md drafts/methods.md ...
```
4 required positional args, in order: output path, CSL file (resolve
PROJECT.md's citation-style enum key via citation-styles/SKILL.md's "CSL File
Mapping" table first — don't pass the enum key itself), reference.docx path
(or `-` for a pandoc-defaults draft preview), then one or more section
markdown files. It errors immediately with a clear message if any required
arg is missing or the CSL/reference-doc file doesn't exist.

This runs the Pandoc pipeline, checks for undefined styles (logs warnings), and outputs the file named in the first argument. Only **error summary** returns (no full Pandoc output) to save tokens.

### Output location:
```
build/thesis.docx
```

Open in Word to verify formatting, page breaks, TOC generation (Ctrl+A → F9 to update fields in Word).

---

## 8. Troubleshooting

### Issue: Styles not applying (text in default format)

**Check 1: Style name mismatch**
- Markdown `# Heading` → Pandoc looks for Word style named "Heading 1"
- If your reference.docx has "Heading1" (no space), Pandoc fails silently
- Fix: Verify reference.docx has styles named exactly: "Heading 1", "Heading 2", "First Paragraph", "Body Text", "Caption"
- **Common miss:** "First Paragraph" specifically — a reference.docx that only defines "Body Text" still renders every section's OPENING paragraph in unstyled "Normal" (Pandoc treats these as two separate required styles, not a fallback pair). If the first line under every heading looks unformatted but everything after it looks right, this is the cause.

**Check 2: Missing reference doc**
- Run: `ls -la templates/ingested/reference.docx`
- If missing, copy from institution template or create manually (Section 3)

### Issue: Turkish characters garbled (ç, ğ, ı, ş, ü)

**Cause:** Encoding mismatch or font doesn't support Turkish.

**Fix:**
1. In reference.docx, set Body Text font to a Unicode-capable font: Calibri, Arial, Times New Roman (all modern versions support Turkish).
2. Re-run: `bash scripts/docx_build.sh build/thesis.docx templates/csl/<style>.csl templates/ingested/reference.docx drafts/*.md`
3. If still broken: Check `bib/references.bib` — ensure UTF-8 encoding (no BOM). Open in plain-text editor, verify. Regenerate with `doi2bib.py` if needed.

### Issue: Page breaks in wrong places

Pandoc doesn't natively support page breaks in Markdown. Workaround: Insert raw OpenXML:

```markdown
[Page break: Insert raw XML]

<w:br w:type="page"/>

[Rest of content]
```

**Better solution:** Use Word's Find & Replace or insert breaks manually after export.

### Issue: TOC not auto-generating

Word requires explicit TOC field. After opening .docx:
1. Place cursor where TOC should appear.
2. References → Table of Contents → (choose style)
3. Word auto-generates from Heading 1–3 styles.

If headings don't appear in TOC, verify they use the correct Word style (Heading 1, Heading 2, etc.).

### Issue: Undefined citation key (shows as [citation needed])

**Check:** `bib/references.bib` contains the key?

Example: Markdown has `[@Smith2020]` but .bib file has no entry with key `Smith2020`.

**Fix:**
1. Run: `python scripts/doi2bib.py --verify --bib bib/references.bib` (`--verify` is a flag, not a value — the bib path always goes through `--bib`, never positionally)
2. Add missing entry via `doi2bib.py --doi 10.1234/example` or manually to .bib
3. Re-run: `bash scripts/docx_build.sh build/thesis.docx templates/csl/<style>.csl templates/ingested/reference.docx drafts/*.md`

### Issue: Images not embedding (broken image placeholders)

**Check:** Image paths are relative to Pandoc's working directory.

```markdown
![Caption](../figures/image.png)  # Relative path: correct
![Caption](/abs/path/figures/image.png)  # Absolute: risky
```

**Fix:**
1. Use relative paths: `figures/image.png` (assumes Pandoc runs from project root)
2. Verify file exists: `ls figures/image.png`
3. Ensure image format is supported: PNG, JPG, GIF (not TIFF by default in Pandoc)

---

## 9. Word Style Inspection (Debug Script)

`docx_build.sh` now runs this automatically after every successful build that
passes a real reference doc (not `-`), and prints a `WARN` line if styles
drift — it never fails the build over this, so re-run manually for the full
report when you see that warning. To run the compliance checker directly —
it compares font/size per style between the built doc and reference.docx and
reports mismatches (exit 0 compliant, 2 mismatches found):

```bash
python scripts/docx_style_check.py --built build/thesis.docx --reference templates/ingested/reference.docx --json
```

For manual inspection beyond what the script compares (raw XML), fall back to:

```bash
python -m zipfile -l build/thesis.docx | grep styles
# Extract and inspect XML (use a project-local scratch dir — /tmp doesn't exist on Windows):
python -m zipfile -e build/thesis.docx build/_docx_unzip
cat build/_docx_unzip/word/styles.xml | grep -E '<w:name|<w:rStyle' | head -20
```

---

## 10. Best Practices Checklist

- [ ] reference.docx contains styles: Heading 1, 2, 3, 4; First Paragraph; Body Text; Caption; Table.
- [ ] template-profile.md exists (from `/ingest-template`) and is reviewed.
- [ ] Markdown headings use `#`, `##`, `###`, `####` (no custom heading macros).
- [ ] All images use relative paths: `figures/name.png`.
- [ ] In-text citations use `[@key]` format (or `[-@key]` for narrative).
- [ ] Bibliography section marked with `# References` or `# Bibliography`.
- [ ] Table captions use format: `Table: Table N. Caption text.`
- [ ] No hardcoded page breaks in Markdown; insert via Word afterward if needed.
- [ ] Turkish characters tested in reference.docx (font supports ç, ğ, ı, ş, ü).
- [ ] After export, open in Word and update fields (Ctrl+A → F9) for TOC/page numbers.

---

## References
- **Build & execute:** `bash scripts/docx_build.sh <out.docx> <csl> <refdoc|-> <sections...>` (digested errors only)
- **Style compliance check:** `python scripts/docx_style_check.py --built <doc> --reference <ref> --json`
- **Reference-doc generation:** `python scripts/make_reference_docx.py --out <path> --font ... --size ... --spacing ...`
- **Template ingestion:** `/ingest-template` command (creates template-profile.md)
- **Pandoc documentation:** pandoc.org/MANUAL.html
- **CSL reference:** citationstyles.org (browse csl.json directory for available styles)
- **Citation troubleshooting:** `/verify-citations` command (checks all keys exist in .bib)
