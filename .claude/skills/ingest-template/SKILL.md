---
name: ingest-template
description: "Register a journal or institute template (.docx reference document or .cls/.sty LaTeX file) as the formatting authority for your project. Analyzes the template structure (styles, margins, heading hierarchy, captions), extracts rules into templates/ingested/template-profile.md, and establishes TEMPLATE SUPREMACY: all future builds override kit defaults with your template's rules. Use this once per project when you have a venue-provided or institute-mandated template."
disable-model-invocation: true
argument-hint: "<file-path>"
---

# /ingest-template — Register Template as Formatting Authority

## Gate: Abort if Failed

1. **Check:** The file specified in `<file-path>` exists.
   - If missing: abort with "File not found: <file-path>. Provide the full path to your template (.docx or .cls/.sty file)."

2. **Check:** File extension is `.docx`, `.cls`, `.sty`, or `.tex`.
   - If unsupported: abort with "Unsupported template format. Provide a .docx reference document or .cls/.sty LaTeX file."

## Procedure

### Step 1: Create templates/ingested/ Directory

1. **Check:** Directory `templates/ingested/` exists.
   - If missing: create it (this is where ingested templates live).

### Step 2: Copy Template to templates/ingested/

1. **Copy** the file from `<file-path>` into `templates/ingested/`.
   - Example: `/ingest-template journal-template.docx` → copies to `templates/ingested/journal-template.docx`
   - Preserve original filename.

2. **Record the file path** for the analysis step.

### Step 3: Dispatch format-engineer Subagent (Template-Analysis Mode)

Provide this input contract to the agent:

- **What to build:** `template-analysis` (not pdf/docx/xlsx — just analyze)
- **Template file path:** The copied file in `templates/ingested/[filename]`
- **PROJECT.md path:** The project's `PROJECT.md` (so the agent understands the target document type and language)
- **Analysis output:** Write `templates/ingested/template-profile.md` (the agent's responsibility)

The agent will:

1. **For .docx files:**
   - Unzip the .docx and read `word/styles.xml` (document styles)
   - Extract heading hierarchy (Heading1, Heading2, Heading3 styles with font size, weight, spacing)
   - Extract body text style (font family, size, line spacing, paragraph spacing)
   - Extract caption style (used for figure/table captions)
   - Extract bibliography/citation style (if a CSL or BibTeX reference is embedded)
   - Read `word/document.xml` sectPr element to extract:
     - Page margins (top, bottom, left, right)
     - Page size (Letter, A4, etc.)
     - Orientation (portrait/landscape)
   - Extract color scheme (if a color scheme is defined in theme.xml)

2. **For .cls/.sty or .tex files:**
   - Parse the LaTeX file for:
     - `\documentclass` options (article, book, report, etc.; one/two-sided; font size, paper size)
     - Required packages (e.g., \usepackage{geometry}, \usepackage{fancyhdr})
     - Heading formatting commands (\section, \subsection style definitions)
     - Bibliography style commands (\bibliographystyle{}, \usepackage{biblatex} options)
     - Custom preamble code relevant to formatting

3. **Generate `templates/ingested/template-profile.md`** documenting:
   - Heading hierarchy (Heading1: 16pt bold, spacing: 12pt before/after; etc.)
   - Body text: font, size, line spacing
   - Caption format (e.g., "Figure 1: Description")
   - Margins and page layout
   - Bibliography style name (if present)
   - Color scheme (if present)
   - Any custom rules (two-column layout, specific table formats, etc.)
   - Which kit defaults each rule overrides

4. **Append the machine-readable rules block** to `template-profile.md`. The prose
   above it is for the human reviewing the analysis; this block is what
   `scripts/template_compliance.py` compares every build against. Without it the
   profile's rules are unenforceable and the checker reports `unbound`.

   ````markdown
   ```json template-rules
   {
     "source_template": "journal-template.docx",
     "target": "docx",
     "page": {"size": "A4", "margins_mm": {"top": 25.4, "bottom": 25.4, "left": 30, "right": 20}},
     "body": {"font": "Times New Roman", "size_pt": 12, "line_spacing": 1.5},
     "headings": {"Heading 1": {"font": "Times New Roman", "size_pt": 16, "bold": true}},
     "caption": {"style_name": "Caption", "label_format": "Figure 1. "},
     "bibliography": {"style": "ieee", "csl": "templates/csl/ieee.csl"},
     "latex": {"documentclass": null, "class_options": [], "required_packages": []}
   }
   ```
   ````

   **`null` is mandatory for anything the template does not state.** Do not fill a
   field with a plausible default, a kit default, or a value inferred from a
   sibling field — a fabricated rule is checked against the build and reported as
   a mismatch or, worse, as compliance with something the venue never required.
   The checker treats `null` as *unchecked* and says so; that is the honest
   outcome, and it is the same discipline as `verified:false` in the bibliography.
   `target` is `"docx"`, `"latex"`, or `"both"`; fill the `latex` object only for
   `.cls`/`.sty`/`.tex` templates.

5. **For .docx templates only, regenerate `templates/ingested/reference.docx`**
   from the values extracted in step 1 — replaces manual style copy-paste in Word:
   ```bash
   python scripts/make_reference_docx.py --out templates/ingested/reference.docx \
     --font "<extracted body font>" --size <extracted body size> --spacing <extracted line spacing>
   ```

### Step 4: Confirm Template Profile was Created

1. **Check:** File `templates/ingested/template-profile.md` exists and is not empty.
   - If missing: abort with "Template analysis failed. format-engineer did not create template-profile.md. Check the template file format and try again."

2. **Read the first 20 lines** of `template-profile.md` to verify it contains valid rules.

3. **Check:** the file contains a ```json template-rules block and it parses.
   Verify by running the checker against any existing build, or with no build at
   all — it reports `"status": "unbound"` when the block is missing or malformed:

   ```bash
   python scripts/template_compliance.py --built build/paper.docx
   ```

   If `unbound`: the analysis produced prose only. Send it back to
   format-engineer rather than accepting it — TEMPLATE SUPREMACY that no build
   can be checked against is a claim, not a guarantee.

### Step 5: Report to User and Establish Template Supremacy

Display:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Template Ingested
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Template file: templates/ingested/[filename]
Profile: templates/ingested/template-profile.md

Extracted rules:
  • Headings: [Heading1 style], [Heading2 style], ...
  • Body text: [font], [size], [line spacing]
  • Margins: [top] / [right] / [bottom] / [left]
  • Page size: [Letter / A4 / custom]
  • Caption style: [format]
  • Bibliography: [style name or CSL reference]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 TEMPLATE SUPREMACY ACTIVATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

All future builds (/submit-check, format-engineer) will:
  1. Read template-profile.md FIRST
  2. Apply every rule in the profile
  3. Override kit defaults with template rules
  4. Report any template rule that cannot be honored

If you need to:
  • Switch templates: ingest a new one (overwrites profile)
  • Disable template: delete templates/ingested/template-profile.md
  • Refine template rules: edit template-profile.md directly

Next step: /draft sections or /submit-check to build with the new template.
```

### Step 6: Optional — Validate Template Compliance

Offer to run a preview build:

```
Would you like to test-build a sample section with this template? [y/n]
  
  y → Builds a 1-page preview (first 500 words of introduction or methods)
      to verify the template renders correctly
  n → Skip; template is ready for full builds
```

If yes, run:
```bash
# For .docx templates (reference doc = the ingested file; CSL from PROJECT.md style):
bash scripts/docx_build.sh build/template-preview.docx templates/csl/<style>.csl   templates/ingested/<file>.docx drafts/<any-section>.md

# For LaTeX templates (main .tex assembled with the ingested class/preamble):
bash scripts/latex_build.sh <main.tex> build
```

Both build scripts run `template_compliance.py` themselves when a profile exists
and print a `WARN:` block for every rule the build contradicts — the preview is
therefore also the first compliance measurement, not just a visual check. To read
the full per-rule verdict (including which rules could NOT be verified, which is
never the same as compliance):

```bash
python scripts/template_compliance.py --built build/template-preview.docx
```

Report: "✅ Preview built at [path]. Check formatting before full build."
If the report contains mismatches, fix the reference doc / preamble and rebuild —
do NOT edit `template-rules` to match the build, which would make the checker
agree with whatever was produced and measure nothing.

## Reference

- **Subagent:** format-engineer (sonnet model, template analysis + rule extraction)
- **Input files:** 
  - User's template file (any path)
  - `PROJECT.md` (for context on document type and language)
- **Output artifacts:**
  - `templates/ingested/[template-filename]` (the template copy)
  - `templates/ingested/template-profile.md` (extracted rules — this is the key file)
- **Downstream:** All builds via `/submit-check` and format-engineer will honor this profile
- **Related skills:** latex-thesis, docx-output (kit defaults that the profile overrides)

---
*Once a template is ingested, its rules are law. Kit defaults apply only to documents without templates/ingested/template-profile.md.*
