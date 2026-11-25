# PRISMA 2020 Protocol — Systematic Review Workflow

PRISMA (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) is the gold standard for transparent, reproducible systematic reviews. This file documents the workflow and key flows.

## The PRISMA 2020 27-Item Checklist (Abbreviated)

Every systematic review should report (at minimum):

### Title & Abstract
1. **Title:** explicitly says "systematic review" or "meta-analysis"
2. **Abstract:** structured (objective, data sources, selection criteria, data extraction, synthesis, results, conclusions)

### Introduction
3. **Rationale:** clearly stated reason for review
4. **Objectives:** clearly stated objectives and explicit RQs

### Methods
5. **Protocol:** registered and where
6. **Eligibility criteria:** PICO or similar, inclusion/exclusion explicit
7. **Information sources:** databases, date range, language, other sources
8. **Search strategy:** full strategy reproducible (see search-log.md)
9. **Study selection:** process (who, how many, disagreement resolution)
10. **Data extraction:** form / process / extraction software
11. **Quality assessment:** tool used (e.g., Cochrane Risk of Bias, ROBINS-I)
12. **Effect measures:** what you're measuring (if meta-analysis)
13. **Synthesis methods:** how you're combining evidence (if meta-analysis)
14. **Reporting bias:** assessment methods (funnel plot, etc.; if applicable)
15. **Certainty:** quality of evidence (GRADE approach; if applicable)

### Results
16. **Study selection:** PRISMA flow diagram (counts at each stage)
17. **Study characteristics:** table of included studies
18. **Risk of bias:** summary per study or in text
19. **Results per study:** data extraction table
20. **Synthesis results:** combined evidence (narrative or quantitative)
21. **Certainty of evidence:** GRADE summary (if applicable)

### Discussion
22. **Summary:** main findings + alignment with other reviews
23. **Interpretation:** findings in light of existing evidence
24. **Limitations:** review limitations (not study limitations)
25. **Implications:** practical and research implications
26. **Author contributions:** who did what (transparency)

### Other
27. **Funding/conflicts:** declarations

---

## PRISMA Flow Diagram (The Visual)

The flow diagram tracks sources through four stages:

```
IDENTIFICATION
    ↓ (raw hits from databases)
[n = total hits across all databases]
    ↓ (remove duplicates)
    
SCREENING
[n = deduplicated records]
    ↓ (title/abstract assessment)
    ├─→ EXCLUDED [n = records not relevant]
    │
INCLUDED [n = full-text articles assessed]
    ↓ (full-text assessment)
    ├─→ EXCLUDED [n = studies with reason]
    │   (Reasons: out of scope, no full text, lower quality, etc.)
    
INCLUDED
[n = studies included in synthesis]
```

### Concrete Example (Bearing Fault Diagnosis)

```
IDENTIFICATION
[n = 1,247 records from Semantic Scholar
      + 234 from IEEE Xplore
      + 156 from arXiv
      = 1,637 total]

SCREENING (after dedup: 1,380 unique records)
[n = 1,380 records screened by title/abstract]
├─→ EXCLUDED [n = 1,157; reasons: geology/mechanics,
   not machine learning, not bearing-specific]

INCLUDED [n = 223 full-text articles assessed]
[n = 223 full-text articles assessed for eligibility]
├─→ EXCLUDED [n = 195; reasons: 
   - No empirical results (n=67)
   - Dataset unavailable (n=43)
   - Different application (not bearing) (n=52)
   - Conference abstract only (n=33)]

INCLUDED
[n = 28 studies included in synthesis]
```

---

## Search Log Documentation (search-log.md)

For every systematic review, create a **search-log.md** in the project root:

```markdown
# Search Log — [Project Title]
Date: 2024-01-15

## Databases Searched

### Semantic Scholar
- Query: "deep learning" AND "bearing fault diagnosis"
- Date searched: 2024-01-15
- Filters: peer-reviewed, 2015–present
- Results returned: 1,247
- Relevant in first 20: 16/20 (80%)

### IEEE Xplore
- Query: ("Deep Learning" OR CNN) AND ("Bearing Fault" OR "Fault Diagnosis")
- Date searched: 2024-01-15
- Filters: journals + conferences, 2015–present
- Results returned: 234
- Relevant in first 20: 18/20 (90%)

### arXiv
- Query: deep learning bearing fault diagnosis
- Date searched: 2024-01-15
- Results returned: 156
- Relevant in first 20: 8/20 (40%)

### TR Dizin
- Query: site:trdizin.gov.tr "derin öğrenme" "rulman arızası"
- Date searched: 2024-01-15
- Results returned: 23
- Relevant in first 23: 18/23 (78%)

## De-duplication Summary
- Total raw results: 1,660
- Deduplicated (DOI-based + title-normalized): 1,380
- Unique records for screening: 1,380

## Additional Sources
- Citation tracking (backward snowballing): added 12 records from references
- Forward snowballing (Google Scholar): added 8 records citing key papers
- **Final screening pool: 1,400 records**

## Search Strategy Rationale
- Year range (2015–present) chosen to capture recent deep learning surge
- Databases selected cover engineering + CS + multidisciplinary venues
- Terms ("bearing fault", "fault diagnosis", "anomaly detection") are synonymous;
  all three used to maximize sensitivity
- Turkish sources included (mandatory for TR-local phenomena check)

## Study Selection Process
- Stage 1 (title/abstract): 2 independent screeners, inter-rater agreement kappa = 0.84
- Disagreements (n = 89): resolved via consensus discussion; 3 cases escalated to 3rd reviewer
- Stage 2 (full-text): 2 screeners assess against inclusion criteria

## Inclusion/Exclusion Criteria
### Inclusion
- Empirical study (not review or commentary)
- Addresses fault detection / diagnosis / anomaly detection
- Bearings or bearing-like mechanical systems
- Published peer-reviewed journal or major conference
- Any language (EN or TR) if DOI / permanent URL exists
- 2015 or later

### Exclusion
- Geological / seismic bearing (false positive from search)
- No quantitative results (only theory)
- Conference abstract only (full paper unavailable)
- Non-English, non-Turkish language
- Predatory publisher / journal (checked via venue_check.py)
```

---

## PRISMA Flow Diagram Generation

Execute (don't read). Either derive counters straight from the registry:
```bash
python scripts/prisma_flow.py --registry sources/registry.jsonl --out-dir outline
```
or pass explicit counters as a JSON object (real keys — not `--identified`/
`--deduplicated`/etc. as separate flags, those don't exist):
```bash
python scripts/prisma_flow.py --counts '{"identified":1660,"duplicates":280,
  "screened":1380,"excluded_screening":1157,"fulltext":223,
  "excluded_fulltext":195,"excluded_reasons":{"no metrics":80,"wrong population":115},
  "included":28}' --out-dir outline
```

### Reports you sought but never obtained

PRISMA 2020 puts *"Reports not retrieved"* in its own box, between **sought for
retrieval** and **assessed for eligibility**. Use it — a paywalled article or an
access-restricted thesis belongs there, and nowhere else:

- Marking it `excluded` asserts an eligibility judgement nobody made. You did not
  decide the study was ineligible; you never opened it.
- Leaving it `candidate` makes `prisma_flow.py` count it as assessed at full text,
  so the flow claims a bigger eligibility assessment than actually happened.

```bash
python scripts/registry_db.py set-status SRC-0031 unretrieved \
  --stage fulltext --reason "access-restricted thesis — record page only, no full text"
```

`derive_counts` then reports `sought`, `not_retrieved` and `fulltext` separately, and
`check()` enforces `sought - not_retrieved == fulltext`. Both keys are optional in a
hand-written `--counts` object: omit them and `not_retrieved` is 0, which is the
correct flow for a review that obtained everything it sought.

Report the number in Methods, and say what it does to the finding. A retrieval gap is
not random — the reports you cannot reach differ systematically from the ones you can
(paywalled journals carry better-funded work; non-indexed repositories carry local
work), so it belongs in the limitations as an **access bias**, distinct from
publication bias.

This generates both:
- Mermaid diagram (text, Markdown-embeddable)
- TikZ diagram (LaTeX-embeddable)

Include in the Methods or Results section with caption:
```
**Figure 1.** PRISMA 2020 flow diagram showing study selection process. 
A total of 1,660 records were identified across five databases (Semantic Scholar, 
IEEE Xplore, arXiv, TR Dizin, DergiPark). After deduplication (n = 1,380), 
title/abstract screening excluded 1,157 records. Full-text assessment of 223 
candidate articles led to 195 exclusions (reasons documented in appendix), 
yielding 28 studies for synthesis.
```

---

## Data Extraction Table

Create a spreadsheet (example structure) or CSV:

| Study ID | Author, Year | Venue | Design | N | Method | Metric | Result | QoE |
|----------|---|---|---|---|---|---|---|---|
| S-001 | Kaya et al., 2023 | MSSP | Empirical | 2,000 signals | CNN | Accuracy | 96.4% | Q1 |
| S-002 | Özdemir et al., 2021 | arXiv | Empirical | 1,200 signals | LSTM | F1 | 0.94 | Low |

- **Study ID:** auto-generated (S-001, S-002, …) for cross-referencing
- **QoE:** Quality of Evidence (from GRADE: High / Moderate / Low / Very Low)

Export this table to Excel via `/export-excel --sheet extraction`.

---

## Certainty of Evidence (GRADE)

For each finding, assess certainty using GRADE:

| Certainty | Definition | Implication |
|-----------|-----------|-------------|
| **High** | Further research unlikely to change the finding | Recommend for practice |
| **Moderate** | Further research may change the finding | Conditional recommendation |
| **Low** | Further research likely to change the finding | Weak or no recommendation |
| **Very Low** | Finding highly uncertain | No recommendation (consider further study) |

Factors *reducing* certainty:
- Risk of bias (study design flaws)
- Inconsistency (findings conflict across studies)
- Indirectness (evidence is indirect to the question)
- Imprecision (small sample size, wide confidence intervals)
- Publication bias (positive results more likely published)

---

## Example PRISMA Methods Section (Brief)

```markdown
## Methods

### Study Design & Protocol
This systematic review followed PRISMA 2020 guidelines. 
Protocol registered with PROSPERO on [date] (ID: CRDXXXXXXXXXX).

### Eligibility Criteria
**PICO framework:**
- **Population:** Mechanical systems with rolling-element bearings
- **Intervention:** Deep learning / machine learning-based fault detection
- **Comparison:** Traditional signal processing or classical ML baselines
- **Outcome:** Fault detection accuracy, precision, recall, F1 score

**Inclusion:** Peer-reviewed empirical studies, 2015–present, EN or TR
**Exclusion:** Opinion pieces, conference abstracts, non-peer-reviewed, 
geological applications, datasets unavailable

### Information Sources
Five databases searched on [date]: Semantic Scholar, IEEE Xplore, arXiv, 
TR Dizin, DergiPark. Additional sources via backward/forward snowballing. 
Search strategy and full queries in Supplementary Material.

### Study Selection
Two reviewers independently assessed titles/abstracts (kappa = 0.84) 
and full texts. Disagreements resolved via consensus; 3 cases by 3rd reviewer.

### Data Extraction
Extracted: author, year, venue, method, dataset, metrics, results. 
Extraction form in Supplementary Material.

### Quality Assessment
Risk of bias assessed using [tool, e.g., ROBINS-I for observational]. 
Quality of evidence rated using GRADE.

### Synthesis
Findings organized thematically (CNN architectures, transfer learning, 
transfer domains) and reported narratively with summary tables.

## Results

### Study Selection
[Include PRISMA flow diagram here]

1,660 records identified → 1,380 deduplicated → 223 full-text 
assessed → 28 studies included in synthesis (Figure 1).

### Study Characteristics
[Include characteristics table]

Included studies: 18 journal articles, 10 conference papers. 
Publication years: 2015–2024. Methods: CNNs (14 studies), 
LSTMs (7), transfer learning (9), ensemble (8).

### Synthesis
[Narrative synthesis organized by theme]
```

---

## Common Mistakes (Avoid These)

| Mistake | Fix |
|---------|-----|
| No search-log.md (irreproducible) | Create and commit search-log.md; include every query, database, date, hit count |
| PRISMA flow diagram counts don't match text | Keep diagram and text in sync; regenerate diagram if numbers change |
| Quality assessment missing | Always assess risk of bias; include in table; note in synthesis |
| "n = 28 studies" without clear path | Show: 1,660 → 1,380 → 223 → 28; readers need to understand attrition |
| No GRADE certainty rating | Rate each finding (High / Moderate / Low / Very Low); impacts recommendations |
| Conflicting results not discussed | When studies disagree, explore why (population, method, dataset differences) |
| Inclusion/exclusion criteria not explicit | Be precise: "Conference abstracts only" (exclude) vs "Conference abstracts with full paper" (include) |

---

## See Also

- **PRISMA 2020 Checklist:** https://www.prisma-statement.org/
- **GRADE Approach:** https://www.gradeworkinggroup.org/
- **Cochrane Risk of Bias Tool:** https://www.cochrane.org/
- **prisma_flow.py** — execute to generate flow diagrams
