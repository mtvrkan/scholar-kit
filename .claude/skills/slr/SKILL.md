---
name: slr
description: "Run the full Systematic Literature Review pipeline. Chosen by its ARTEFACTS, not by the word 'systematic' alone — a systematic review with no artefacts named is /lit-review --systematic. The artefacts: user-selected databases (Scopus, WoS, IEEE, Wiley, PubMed, Google Scholar; default Scholar) with advanced title+abstract+keyword queries, screening (automatic + manual), local PDF folder tree, lossless PDF→Markdown conversion, striking-section extraction to JSON with in-paper references, detailed SLR Excel (queries sheet + per-database sheets), and a back-step qa-auditor double-checking every stage. All references bib-backed and verified. Gate: PROJECT.md complete."
disable-model-invocation: true
argument-hint: "[--db scopus,wos,ieee,wiley,pubmed,scholar] [--fast]"
---

# /slr — Systematic Literature Review pipeline (hocamdan contract)

"hocamdan" ("from my professor/advisor," Turkish) is this kit's shorthand for
the specific SLR deliverable format an academic advisor handed down as a
requirement — the per-database Excel sheets, the PDF→Markdown conversion, the
back-step qa-auditor double-check. Referenced elsewhere in this kit
(pdf2md.py, xlsx_export.py, advanced-search.md, qa-auditor.md) as a shared
provenance tag for that same original spec, not a technical term.

Runs the 7-step SLR pipeline end to end. Transparency rule: after EVERY stage,
report to the user what was produced (counts + artifact paths) BEFORE moving on,
and dispatch **qa-auditor** on that stage. **Gate (operationalized):** parse the
agent's returned JSON — if `"verdict":"DISCREPANCIES"` and any element of
`discrepancies[]` has `"severity":"blocker"`, STOP: show the blocker list to the
user and do NOT start the next stage until each is resolved (fixed, or the user
explicitly accepts the risk). `"severity":"warn"` items alone never block
(çift göz — the trailing verification agent).

## GATE (check first, abort with explanation in the user's language)
- PROJECT.md exists and has no TBD in topic/RQs/type. If missing → suggest /new-project.

## Stage 1 — Advanced search (per-database)
1. Parse `--db` (comma list). If absent, ask once; if the user doesn't care, default
   to `scholar` (Google Scholar) per the pipeline contract.
2. Dispatch **literature-scout** with: topic + RQs + inclusion criteria + the chosen
   databases + the per-DB query syntax rules from
   literature-review/reference/advanced-search.md (TITLE-ABS-KEY for Scopus, TS= for
   WoS, [tiab] for PubMed, ...). The scout must:
   - build concept-block queries (title+abstract+keyword scope; author search when
     the user names authors),
   - log EVERY executed query: `python scripts/registry_db.py log-query --db <db>
     --query "..." --hits N`,
   - set the `db` field on every registry record it adds,
   - report per-DB hit counts + the refinement trail.
   The scout has no Write tool — write its returned narrative to
   `sources/search-log.md` now.
3. QA: dispatch qa-auditor (stage: search). Present per-DB table to the user.

## Stage 2 — Screening (automatic + manual)
1. Scout's relevance-ranked shortlist → present to the user with one-line reasons
   and venue flags. The user may include/exclude ANY record (manual overrides are
   first-class; record them with `--reason "user decision: ..."`).
2. Apply decisions via `python scripts/registry_db.py set-status <id> included|excluded
   --reason "..." --stage screening`.
3. QA: qa-auditor (stage: screening).

## Stage 3 — Local folder tree + PDFs
1. Ensure the project tree (already created by /new-project): `sources/pdf/` (PDFs),
   `sources/md/` (converted markdown), `evidence/extracts/` (section JSONs),
   `analysis/figures/`, `analysis/tables/`, `drafts/`.
2. For each included record: if an open-access PDF is reachable (paper-search MCP /
   OA link), fetch it to `sources/pdf/<bib_key>.pdf`. Otherwise list the paywalled
   papers and ask the user to download them via institutional access into that folder
   (the kit NEVER bypasses paywalls). If a report stays out of reach, give it its own
   PRISMA box rather than a verdict it never received:
   `set-status <id> unretrieved --stage fulltext --reason "<where you looked, what blocked it>"`
   — `excluded` would claim an eligibility judgement you never made, and `candidate`
   would let prisma_flow.py count it as assessed at full text. Fetch BibTeX now:
   `python scripts/doi2bib.py --doi <doi> --append bib/references.bib` and bind
   `set-field <id> bib_key <key>` — every included paper gets a verified bib entry
   BEFORE reading (reference accuracy is the spine of the whole pipeline).

## Stage 4 — Lossless PDF → Markdown
1. `python scripts/pdf2md.py --all` → `sources/md/<key>/<key>.md` + `img/` + meta.json
   (all text, tables as markdown, figures as PNG — no data loss).
2. QA: qa-auditor (stage: conversion) — page/image counts re-derived from the PDFs,
   spot-reads for truncation.

## Stage 5 — Striking-section extraction to JSON
For each converted paper dispatch **source-analyst** with the md path (NOT the PDF);
besides its normal evidence cards it writes `evidence/extracts/<bib_key>.json`:
```json
{"key":"kaya2023deep","registry_id":"SRC-0001",
 "sections":{"abstract":"...","methods":"...","results":"...","findings":"...",
             "suggestions":"..."},
 "fields":{"<project-specific column>":"<value>", "...":"..."},
 "key_references":[{"text":"<ref as cited>","doi":"10...","bib_key":null,
                    "why":"foundational for RQ1"}],
 "figures":["sources/md/kaya2023deep/img/....png"],
 "tables_md":["|Input|F1|...|"]}
```
- `fields` columns come from PROJECT.md's extraction schema: on first run, propose a
  domain-appropriate column set (like the professor's example: Alan, Klinik Görev,
  Veri Türü, Veri Seti, Örneklem, Modalite, Model Türü, Baseline, Yöntemler,
  Değerlendirme, Metrikler, İnsan Değerlendirmesi, Özet Bulgular, Notlar — adapt to
  THIS project's domain), get user approval, and record it in PROJECT.md.
- `key_references`: the paper's own most-cited-worthy references — verbatim as cited,
  plus DOI when findable. When such a reference later enters our registry, bind its
  bib_key. NEVER invent DOIs; leave null and mark for doi2bib --title-search.
- Sequential by default; parallel 3-5× only under `--fast` (cost decision, tell the user).
- QA: qa-auditor (stage: extraction) — values traced back into the md verbatim.

## Stage 6 — Detailed SLR Excel
1. `python scripts/xlsx_export.py --sheet all` — includes: screening, extraction,
   matrix, venues, prisma, **queries** (from search-log.jsonl), **slr** (core +
   dynamic fields + Dahil/Hariç + notes) and **per-database sheets** (db-scopus,
   db-wos, ...), matching the professor's workbook layout.
2. `python scripts/prisma_flow.py --registry sources/registry.jsonl`.
3. QA: qa-auditor (stage: excel) — row counts and partitions re-checked.

## Stage 6b — Quantitative synthesis (ONLY if the review supports it)

Skip this stage by default. Run it only when the user asks to pool results, or
when the extraction table already holds comparable effect data.

**The gate is a judgement, not a statistic.** Before computing anything, dispatch
**methodology-advisor** in **POOLABILITY** mode with the extracted PICO/PECO rows.
It returns `pool` | `pool-with-subgroups` | `do-not-pool`, the specific
incomparability behind each exclusion, and the decisions that must be
pre-registered NOW (model, effect measure, subgroups) rather than chosen after
seeing output. On `do-not-pool`, say so and stop — a pooled number from
incomparable studies is worse than no number because it looks like an answer, and
a narrative synthesis is a legitimate result. Record the decision and its reason
for the Methods section either way.

1. Build the effect table from `evidence/extracts/*.json` into
   `analysis/effects.csv`. Required columns depend on the measure:
   - binary outcome → `study,e1,n1,e2,n2` (events/total per arm)
   - continuous outcome → `study,m1,sd1,n1,m2,sd2,n2`
   - already-computed effects → `study,yi,sei`
   Every value must be traceable to an extract. A cell you cannot trace is a
   `[CITATION NEEDED]`, not an estimate.
2. Pool:
   ```bash
   python scripts/meta_analysis.py --input analysis/effects.csv --measure or --json
   python scripts/meta_analysis.py --input analysis/effects.csv --measure or --forest
   ```
   `--measure`: `or` `rr` `rd` `md` `smd` `precomputed`.
3. Report to the user, in this order: k and the excluded rows **with reasons**,
   both models, Q/I²/tau², the prediction interval, and Egger (or the explicit
   reason it was not run). Reproduce the `caveats` array — it is part of the
   result, not decoration.
4. **The model is chosen before the numbers, not after.** If the protocol did not
   specify one, say that in Methods and report both. Never present the model with
   the smaller p-value as "the" result.
5. QA: qa-auditor (stage: extraction) re-checks every effect-table cell against
   its extract. A transposed SD is invisible to the pooling maths.

Interpretation limits to carry into the write-up verbatim:
- I² describes variation beyond sampling error. It does **not** license pooling,
  and it is imprecise with few studies.
- Egger's test is not run below 10 studies; below that a null result means
  nothing. Funnel asymmetry has causes other than publication bias.
- A continuity correction was applied to any zero-cell study (see per-study
  `notes`) — it biases toward the null and must be disclosed.

## Stage 7 — Writing with full provenance
Continue with the standard gated pipeline — /outline → /draft → /verify-citations →
/critique → /submit-check — with these SLR-specific rules:
- Drafting pulls from cards AND extracts (md files stay on disk; only the needed
  slices load).
- EVERY reference in the manuscript is bib-backed: pandoc [@key] keys only, entries
  machine-fetched via doi2bib, `verified={true}` enforced; citation-verifier must
  PASS (fabrication/retraction check) before /critique. No exceptions — reference
  accuracy is a hard gate, not a style preference.
- Figures/tables reused from papers are cited with source + page; own figures live
  in analysis/figures with caption drafts.
- QA: qa-auditor (stage: draft-numbers) after each drafted section.

## Output to the user (each stage, transparently)
Stage name → what ran → counts → artifact paths → qa-auditor verdict → next step.
Keep each stage report ≤10 lines; the artifacts carry the detail.
