# Advanced Search — per-database query construction

The user may name the database(s) to search ("Scopus'ta ara", "WoS ve IEEE'de tara");
when none is named, default to Google Scholar (hocamdan pipeline step 1). Searches
target **title + abstract + keywords** unless the user narrows the field, and support
author search. Every executed query is logged (see Logging below) — reproducibility
is non-negotiable for SLRs.

## Query construction discipline

1. Parse the user's topic into CONCEPT BLOCKS (2-4), each expanded with synonyms,
   abbreviations, and variant spellings (use the bilingual keyword matrix from
   bilingual-search.md — TR concepts get their own blocks when TR databases are in scope).
2. Within a block: OR. Between blocks: AND. Phrases in quotes; truncation `*` where
   the database supports it (diagnos* → diagnosis/diagnostic/diagnostics).
3. Start broad, then tighten with the database's field codes below. Record hit counts
   at each refinement (the professor's QUERIES sheet pattern: query → hits → refined
   query → new hits).

## Database syntax cheat-sheet

| Database | Field-scoped query pattern | Author search | Notes |
|---|---|---|---|
| **Scopus** | `TITLE-ABS-KEY((blockA1 OR blockA2) AND (blockB1 OR blockB2))` | `AUTH("Kaya, A.")` / `AUTHOR-NAME(kaya)` | `AND NOT` for exclusions; `PUBYEAR > 2019`; `DOCTYPE(ar)` articles only; `LIMIT-TO(SRCTYPE, "j")` |
| **Web of Science** | `TS=((blockA) AND (blockB))` — TS = topic (title+abstract+keywords) | `AU=(Kaya A*)` | `TI=` title-only, `AB=` abstract-only; `PY=2020-2026`; indexes chosen in UI (SCI-E/SSCI/ESCI) |
| **IEEE Xplore** | `("Document Title":term OR "Abstract":term OR "Author Keywords":term)` | `"Authors":kaya` | Command search box; wildcard `*`; `AND/OR/NOT` uppercase |
| **Wiley Online Library** | Advanced search fields: "title", "abstract", "keywords" combined with AND/OR dropdowns | author field | No single-string field syntax; document the field-value pairs used |
| **PubMed** | `term[tiab]` (title/abstract) · `term[MeSH Terms]` · `(a[tiab] OR b[tiab]) AND c[MeSH Terms]` | `kaya a[Author]` | MeSH expansion is PubMed's superpower — map concepts to MeSH first |
| **Google Scholar** | plain quoted phrases + OR (uppercase); `intitle:term`; `author:"a kaya"` | `author:"..."` | No abstract/keyword fields; use as default & recall-oriented sweep; hit counts approximate |
| **Semantic Scholar / paper-search MCP** | structured params (query, year, fields) — see the MCP tool schemas | supported | preferred programmatic route when MCPs are connected |
| **TR Dizin / DergiPark / YÖK Tez** | site-scoped WebSearch patterns — see turkish-databases.md | limited | no API; provenance recorded per turkish-databases.md |

## Paywall reality (hocamdan.txt §1)

Web scraping reaches only open-access full texts; most journal PDFs sit behind
paywalls. The workflow therefore:
- Screens on title+abstract (always retrievable via the databases above).
- For included papers, asks the USER to download PDFs through their institutional
  access into `sources/pdf/<bib_key>.pdf` — the kit never bypasses paywalls.
- Open-access copies are fetched automatically when the paper-search MCP or
  Unpaywall-style links surface them.
- Every included paper's PDF is converted losslessly to markdown:
  `python scripts/pdf2md.py --all` → `sources/md/<key>/<key>.md` (execute, don't read).

## Logging (feeds the QUERIES sheet and PRISMA)

Machine-readable — one line per executed query, appended by the scout:
```
python scripts/registry_db.py log-query --db scopus --query "TITLE-ABS-KEY(...)" --hits 78 [--note "refined: +XAI block"]
```
This writes `sources/search-log.jsonl` ({"db","query","hits","date","note"}) and is
exported to the Excel `queries` sheet by xlsx_export. The human-readable
`search-log.md` narrative (what was tried, why refined) is kept alongside for the
manuscript's search-strategy section.
