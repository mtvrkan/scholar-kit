---
name: export-excel
description: "Export literature registry, screening decisions, extracted data, PRISMA counts, search queries, and the detailed SLR sheet to a styled Excel workbook. Specify which sheet(s) to include: screening, extraction, synthesis matrix, venue quality checklist, prisma counts, search queries, the SLR sheet (+ per-database partitions), or all. Produces exports/literature-matrix.xlsx with auto-filters, frozen headers, and conditional formatting (e.g., quartile-based colors)."
disable-model-invocation: true
argument-hint: "[--sheet all|screening|extraction|matrix|venues|prisma|queries|slr]"
---

# /export-excel — Export Literature Registry to Styled Workbook

## Gate: Abort if Failed

1. **Check:** File `sources/registry.jsonl` exists and is not empty.
   - Read the first line to confirm it's valid JSONL.
   - If missing or empty: abort with "No sources in registry. Run `/lit-review` first to populate sources/registry.jsonl."

2. **Check:** File `evidence/cards.jsonl` exists (for extraction sheet, optional but recommended).
   - If missing: warn "No evidence cards found. Extraction sheet will be empty; proceed with other sheets."

## Procedure

### Step 1: Validate Arguments

1. **Parse the `--sheet` argument** (if provided):
   - Valid values: `all`, `screening`, `extraction`, `matrix`, `venues`,
     `prisma`, `queries`, `slr` (matches `xlsx_export.py`'s `--sheet` choices exactly)
   - Default (no argument): `all` (generate all available sheets)

2. **If invalid argument:** abort with "Invalid sheet option. Use: --sheet [all|screening|extraction|matrix|venues|prisma|queries|slr]"

### Step 2: Prepare Export Command

Build the command to run:

```bash
python scripts/xlsx_export.py --sheet <argument> [--out exports/literature-matrix.xlsx]
```

**Examples:**
- `/export-excel --sheet all` → all sheets
- `/export-excel --sheet screening` → screening decisions only
- `/export-excel` (no argument) → defaults to all

### Step 3: Run the Export Script

Execute the command. The script will:

1. **Read `sources/registry.jsonl`** and extract:
   - source ID, title, authors, year, venue, DOI, language
   - venue metadata (SCI-E / ESCI / Scopus / TR Dizin, quartile, SJR)
   - inclusion status (candidate / included / excluded)
   - exclusion reason (if excluded)

2. **Generate sheets based on argument:**

   **Sheet: Screening**
   - Columns: ID | Title | Authors | Year | Venue | Language | Status | Reason (if excluded)
   - All sources from registry, one row per source
   - Auto-filter on all columns
   - Frozen header row (first row)

   **Sheet: Extraction**
   - Read `evidence/cards.jsonl`
   - Columns: Card ID | Source ID | Claim | Detail | Page | Type (finding/method/quote/gap) | Strength (1–5) | Tags | Conflicts
   - One row per evidence card
   - Auto-filter on Type, Strength, Tags
   - Frozen header

   **Sheet: Synthesis Matrix**
   - Rows: RQs / research themes (extracted from evidence card tags)
   - Columns: research theme × source/evidence summary
   - Cell values: brief summary of how source addresses theme
   - Color-coded by strength (green=strong, yellow=moderate, gray=weak reference)

   **Sheet: Venue Quality**
   - Columns: Venue Name | ISSN | SCI-E | SSCI | AHCI | ESCI | Scopus | TR Dizin | Quartile | SJR | Predatory Flag | Checked Date
   - All unique venues from registry
   - Auto-filter on index columns
   - Conditional formatting: Q1 (dark green), Q2 (light green), Q3 (yellow), Q4 (orange), unclassified (gray)

   **Sheet: PRISMA**
   - PRISMA 2020 flow counts: records identified, per-status counts, excluded-with-reason breakdown
   - Read from `sources/registry.jsonl`; complements (does not replace) `prisma_flow.py`'s diagram output

   **Sheet: Queries**
   - One row per executed search query: date | database | query string | hit count | note
   - Read from `sources/search-log.jsonl` (written by `registry_db.py log-query`) — empty/omitted if no queries logged

   **Sheet: SLR** (detailed pipeline sheet, `/slr`-specific)
   - Core columns (registry_id, bib_key, title, year, venue, type, doi, db) + the
     union of per-project dynamic extraction fields (from `evidence/extracts/*.json`)
     + include/exclude + notes
   - PLUS one per-database partition sheet (`db-scopus`, `db-wos`, ...) — only
     generated when the registry has a `db` field set (i.e. sources came through `/slr`)

3. **Apply styling:**
   - Frozen header row (split pane at row 2)
   - Auto-filters on all columns
   - Font: 11pt, readable sans-serif (Calibri or Arial)
   - Header background: light gray (#D9D9D9)
   - Column widths: auto-fit, min 12 characters
   - Conditional formatting: quartile column (venue sheet) colored by rank

4. **Write output** to `exports/literature-matrix.xlsx` (create exports/ directory if missing).

### Step 4: Report Results to User

Display summary:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Excel Export Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output file: exports/literature-matrix.xlsx

Sheets generated:
  □ Screening (N sources)
    ├─ Included: M sources
    ├─ Excluded: K sources (reasons documented)
    └─ Filters on: Status, Language, Venue
  
  □ Extraction (P evidence cards)
    ├─ Findings: Q cards
    ├─ Methods: R cards
    ├─ Quotes: S cards
    └─ Filters on: Type, Strength, Tags
  
  □ Synthesis Matrix (T themes × sources)
    ├─ Themes identified: [list]
    └─ Color-coded by evidence strength
  
  □ Venue Quality (U unique venues)
    ├─ SCI-E indexed: V
    ├─ ESCI indexed: W
    ├─ Scopus-only: X
    ├─ TR Dizin: Y
    └─ Predatory flags: Z
  
Features:
  • Frozen header rows (first row fixed when scrolling)
  • Auto-filters on all columns
  • Conditional formatting: quartile colors (Q1-Q4)
  • Column widths auto-fitted for readability

Open the file in Excel, LibreOffice, or Google Sheets. 
You can now:
  • Filter by Venue to find all papers from a high-impact journal
  • Sort by Year to track methodological evolution
  • Review Extraction sheet to spot missing evidence cards
  • Share Screening sheet with co-reviewers for transparency
```

### Step 5: Optional Actions

1. **Filtering by year/index/etc. is done in Excel, not the script:**
   - `xlsx_export.py` has no `--year-min`/`--index`-style flags — it always exports
     the full dataset with auto-filter dropdowns already enabled on every column
     (frozen header row, `ws.auto_filter.ref` set per sheet). Point the user at
     the column's dropdown arrow in Excel/LibreOffice/Sheets instead of
     re-running the export.

2. **Remind about sheet maintenance:**
   ```
   💡 Tips:
     • Screening sheet: update Status column manually or via `python scripts/registry_db.py set-status <rec_id> <status>`
     • Extraction sheet: add new evidence cards via source-analyst or main session
     • Synthesis matrix: themes auto-generated from card tags; add tags via evidence_db.py
     • Venue quality: auto-refreshed from venue_check.py lookups (updated every 30 days)
   ```

## Reference

- **Script:** `python scripts/xlsx_export.py` (openpyxl-based, uses templated styling)
- **Input files:** 
  - `sources/registry.jsonl` (required)
  - `evidence/cards.jsonl` (for extraction sheet)
  - `sources/venues.jsonl` (for venue quality sheet)
- **Output artifact:** `exports/literature-matrix.xlsx`
- **Related skills:** literature-review (source registry structure), evidence-cards (card schema)

---
*Excel export is a read-only snapshot of your research data. Edit the spreadsheet for analysis; update the source files (registry.jsonl, cards.jsonl) to persist changes.*
