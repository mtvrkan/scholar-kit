---
name: import-library
description: "Import an existing reference library (Zotero, Mendeley, EndNote, or a .bib from an earlier paper) into the project's source register — without importing its bibliographic claims. The export is treated as a list of DOIs and a screening worksheet: DOI-bearing entries are re-fetched from the authoritative record by doi2bib.py, entries without a DOI are registered as candidates and reported, and not one field of the export ever reaches references.bib. Shows a plan and asks before writing anything."
disable-model-invocation: true
argument-hint: "[<export.bib|export.ris>] [--no-fetch] [--resolve] [--limit N]"
---

# /import-library — Bring an Existing Library In

## Gate: Abort if Failed

1. **Check:** `PROJECT.md` exists in the working directory.
   - If missing: abort with "No project here. Run `/new-project` first — the
     register this writes into is part of a project, not a loose file."

2. **Check:** the export file exists **inside the project**.
   - If the user names a path outside it (Downloads, Desktop): do not import.
     Say: "Copy the export into `sources/` first — the register has to be
     reproducible from the project directory alone, and a row whose origin was a
     file that no longer exists is not." Then stop and wait.
   - If no argument was given: list `sources/*.bib` and `sources/*.ris`. Exactly
     one match → use it. Several → ask which. None → say where to put it.

## What This Command Refuses

State this to the user once, before the import, in one sentence — it is the
reason the command is shaped the way it is:

> An exported `.bib` is bibliographic data of unknown provenance, so nothing in
> it is copied into `bib/references.bib`. Entries with a DOI are re-fetched from
> the authoritative record; entries without one are registered as candidates for
> you to resolve.

Never offer to "just copy the entries in to save time". That is Invariant 2, and
the fastest possible way to fill a bibliography with unverified references.

## Procedure

### Step 1: Plan (no writes, no network)

```bash
python scripts/library_import.py --file sources/<export> --plan
```

Report to the user, from the JSON:

```
Library: <file> — <parsed> records
  ├─ with DOI:    <with_doi>   → will be re-fetched from doi.org
  ├─ without DOI: <without_doi> → registered as candidates, bib left empty
  └─ languages:   <by_language>

First few: <sample titles>
```

If `parsed` is 0, the file is not a BibTeX or RIS export (a Zotero "Quick Copy"
text list is neither) — say so and stop.

### Step 2: Ask before writing

Ask once, plainly: import all `<parsed>` records now?

- **Yes** → Step 3.
- **A subset first** → `--limit N`. Recommend this above ~50 records: the fetch
  is one network call per DOI, and a small batch confirms the shape before the
  long run.
- **Offline** (no network right now, or the author wants to screen before
  spending the fetches) → Step 3 with `--no-fetch`, then Step 4 later.

### Step 3: Import

```bash
python scripts/library_import.py --file sources/<export> [--limit N]
# offline variant — register only, no bib writes:
python scripts/library_import.py --file sources/<export> --no-fetch
```

Progress prints one line per entry on stderr; the JSON summary is the last thing
on stdout. Exit 2 means "imported, but something is left to resolve" — that is a
normal outcome, not a failure.

### Step 4: Finish the bibliography (only after an offline import)

```bash
python scripts/library_import.py --resolve
```

Fetches and links every registered record that has a DOI and no bib key yet.

**Never re-run the import to finish the job** — the register would take the same
library a second time and mark all of it `duplicate`. `--resolve` exists for
precisely this.

### Step 5: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 Library imported
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Registered:  <n> new sources        (status: candidate)
Duplicates:  <n> already in the register — nothing overwritten
Bibliography: <n> entries fetched from the authoritative record

Left to resolve:
  • <n> without a DOI — `python scripts/doi2bib.py --title-search "<title>"`
  • <n> failed to fetch — <reason>, re-runnable with --resolve

Next: /lit-review to screen them, or /journal-check on a venue you don't know.
```

Then say what the import did **not** establish: these records are candidates
carrying the export's own unverified metadata (`metadata_source:
user-export (unverified)` on every row). Screening decides what is included;
the import decides nothing.

## Notes

- **Every record carries its provenance.** `db: import`, `import_source:
  <filename>`, `metadata_source: user-export (unverified)`. Six months later
  nothing else distinguishes an imported row from a screened one.
- **A failed fetch is not a fabricated entry.** If doi.org cannot resolve a DOI,
  the record is registered and the failure reported. Do not fall back to the
  export's fields, and do not write the entry by hand.
- **Turkish names survive the import.** BibTeX escapes (`Y{\i}lmaz`) are decoded
  through Unicode composition before the record is written — a name nobody can
  search for is a record nobody finds.

## Reference

- **Script:** `python scripts/library_import.py` (delegates every write to
  `registry_db.py` and `doi2bib.py` — it is not itself a writer of either file)
- **Writes:** `sources/registry.jsonl`, `bib/references.bib` (through those two)
- **Related:** `/lit-review` (screening the imported candidates), `/verify-citations`
  (what the fetched entries are checked against), evidence-cards skill

---
*An import brings sources in. It does not bring in the claim that they are right.*
