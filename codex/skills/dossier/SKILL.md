---
name: dossier
description: "Compute a promotion / doçentlik / atama dossier's points table from a publication export you supply and a criteria table you fill from ÜAK's or your university's own published document — and re-verify every publication's index claim against the venue cache, because the most common way a dossier entry is struck out is an ESCI paper entered under SCI-E. Also renders an academic CV from the same list. Keeps nothing between runs. Use at a promotion application or when auditing your own record; /journal-check profiles a single venue."
disable-model-invocation: true
argument-hint: "--publications <export.bib|.json|.csv> [--cv]"
---

# /dossier — arithmetic, and the index claim nobody re-checks

A promotion file is a points table: each publication lands in a criterion, each
criterion carries a value, the values sum. All of it is arithmetic, and all of it
gets done by hand at midnight against a PDF of criteria.

The error that costs a file is not the addition. It is the index claim — a paper
in an ESCI journal entered under the SCI-E criterion, usually **honestly**: the
journal was SCIE when the work started, or the publisher's own page said so. A
reviewer checks it against the Master Journal List and the entry falls.

## What this keeps between runs: nothing

There is no ledger, no publication history, no profile. Every run starts from the
two files you pass, and the script writes only where `--write` points, inside the
project directory.

`POSITIONING.md` refuses cross-paper memory, and this looked like the feature
that would finally have to move that line. It did not — the value here was never
in remembering. It is in the arithmetic and the re-verification, neither of which
needs a history.

## Step 1: export your publications

ORCID and Scopus both export BibTeX; so does Web of Science, Zotero and Mendeley.
Put it in `dossier/publications.bib`.

`.json` (a plain array) and `.csv` (with a header) also work. **ORCID's own JSON
is deliberately not parsed** — its schema is deep and versioned, and a parser
that silently mis-reads half a record is worse than an export step.

Fields that matter: `title`, `year`, `type` (`article` / `conference` /
`chapter` / `book` / `thesis` / `patent`), `venue`, `issn`, `doi`, and optionally
`authorship` (`first` / `corresponding` / `co`) and `index` (what you *claim*,
which is what gets checked).

## Step 2: the criteria table, from its own document

```json
{
  "authority": "ÜAK 2026 Doçentlik Temel Alan Ölçütleri — Mühendislik",
  "source_url": "https://uak.gov.tr/…",
  "read_on": "2026-08-15",
  "minimum_total": 100,
  "criteria": [
    {"id": "A1", "label": "SCI-E/SSCI/AHCI makale", "points": 20,
     "match": {"type": "article", "index": ["SCIE", "SSCI", "AHCI"]}, "min_count": 2},
    {"id": "A5", "label": "ESCI makale", "points": 10,
     "match": {"type": "article", "index": ["ESCI"]}},
    {"id": "A8", "label": "TR Dizin makale", "points": 8,
     "match": {"type": "article", "index": ["TR_DIZIN"]}},
    {"id": "B1", "label": "Bildiri", "points": 5,
     "match": {"type": "conference"}, "max_count": 4}
  ]
}
```

**Read the values off the table itself.** They differ by temel alan, by
university, and by year. The kit will not recall "doçentlik için 100 puan" — that
is the authority-file rule, and a dossier built on a remembered point value is
built on the same error class as a remembered DOI.

Order matters: a publication scores against the **first** criterion it matches,
which is your declaration of precedence.

## Step 3: fill the venue cache

Verification reads `sources/venues.jsonl` — this project's own cache. A venue
that is not in it is **not** counted:

```bash
python scripts/venue_check.py --issn 0888-3270
python scripts/venue_check.py --title "Journal of Emerging Things"
```

## Step 4: score

```bash
python scripts/dossier_score.py --publications dossier/publications.bib
```

Three buckets, kept apart on purpose:

| Bucket | Meaning |
|---|---|
| **counted** | the venue was verified and the publication matched a criterion |
| **pending verification** | it would match, but its venue is not in the cache — points reported separately, neither added nor dropped |
| **unmatched** | no criterion fits: either the criteria file is incomplete, or these do not count |

And the findings:

```
index_mismatches:
  "Transfer learning under load"  claimed SCIE  verified ESCI  (checked 2026-08-01)
```

A criterion with a `max_count` reports **which** publications fell outside it, by
name. The order it counted in is your export's order, which is no order at all —
if a different paper should take the slot, move it up in the export.

The mismatched paper then scores against **ESCI**, not against the claim. Every
verified row carries the date its index was checked, because a WoS class is a
fact with a date on it.

## Step 5: the CV

```bash
python scripts/dossier_score.py --publications dossier/publications.bib --cv \
    --write dossier/cv.md
```

Grouped by the criteria table's own categories, newest first, each line carrying
the verified index. No "selected publications" judgement, no invented
affiliation, title or date — every line comes from the export.

## What this does not do

- **It does not decide the file is sufficient.** It reports counted points
  against the minimum the criteria file declares, and stops. That decision
  belongs to a committee.
- **It does not recall a criterion, a point value or a threshold.**
- **It does not improve an index.** A claim the cache does not confirm is a
  mismatch, reported with the date of the check.
- **It does not fill YÖKSİS.** No portal is touched and no credential is held.

## Reference

- **Script:** `python scripts/dossier_score.py --publications <file> [--criteria]
  [--venues] [--cv] [--write]`
- **Reads:** your export, `dossier/criteria.json`, `sources/venues.jsonl`
- **Writes:** only `--write`, inside the project
- **Related:** `/journal-check` (fills the venue cache), `/import-library` (turns
  a reference library into a register), `/submission-pack`

---
*A dossier is not judged on its total. It is judged on whether every line in it survives being looked up.*
