---
name: literature-review
description: "Literature-review METHODOLOGY knowledge: how to design search strategies, frame RQs (PICO/PEO/SPIDER), choose databases, set inclusion criteria, screen in two stages, snowball, and synthesize. Use for HOW-TO/conceptual questions about reviewing. To actually RUN a review use the /lit-review or /slr commands. Triggers on: 'literature review', 'systematic review', 'research question', 'PICO', 'inclusion criteria', 'screening protocol', 'literature search', 'search strategy', 'bibliographic database', 'synthesis', 'what is SCIE/ESCI/Scopus', 'quartile meaning', 'predatory journal signs'."
---

# Literature Review — Full-Cycle Workflow

This skill guides you through the literature review pipeline: from research question to final synthesis. The approach is systematic by default but scales to rapid scoping reviews. Bilingual (EN/TR) search is built in; duplicate detection handles multilingual result sets.

## The Workflow (9 Steps)

### 1. Define Research Questions (RQs)

Start with 1–4 clear, specific research questions. Each should be:
- **Answerable:** your literature search can address it.
- **Specific enough:** not "What is machine learning?" but "What ML architectures are most effective for time-series anomaly detection in IoT systems?"
- **Framed for downstream use:** each RQ will tag a subset of evidence cards; drafts will retrieve cards by RQ tag.

Example RQs:
- RQ1: What deep learning architectures have been applied to bearing fault diagnosis?
- RQ2: What datasets exist for bearing fault diagnosis benchmarking?
- RQ3: How does CNN performance compare to traditional signal-processing baselines?

### 2. Select Framing Methodology

Choose one, based on your question type and paper type:

| Framing | Best for | Output |
|---------|----------|--------|
| **PICO** (Population, Intervention, Comparison, Outcome) | Clinical/health studies, RCTs, observational studies | Inclusion/exclusion criteria for patient populations, interventions, and measured outcomes |
| **PEO** (Population, Exposure, Outcome) | Observational studies, epidemiology, social sciences | Criteria for who is studied, what exposure/exposure variation, what outcomes |
| **SPIDER** (Sample, Phenomenon, Design, Evaluation, Research type) | Qualitative studies, exploratory research, theory development | More flexible framing for diverse methodologies |
| **Concept-based** (concept 1 × concept 2 × context) | Systematic reviews of theoretical concepts, scoping reviews | 3-dimensional keyword matrix: concept A (terms), concept B (terms), context/population (terms) |

For the bearing fault example (mixed methods): **Concept-based** with three dimensions:
- Concept 1: fault detection methods (CNN, autoencoders, signal processing, …)
- Concept 2: bearing types / fault types (rolling-element, journal, …)
- Context: industrial IoT, condition monitoring, vibration analysis

### 3. Build a Dual-Language Keyword Matrix

See [bilingual-search.md](reference/bilingual-search.md) for the full protocol. In brief:

```
Concept 1 (Methods):
  EN: CNN, deep learning, neural network, autoencoder, signal processing, …
  TR: derin öğrenme, yapay sinir ağı, sinyal işleme, …

Concept 2 (Fault types):
  EN: bearing fault, anomaly detection, failure mode, …
  TR: rulman arızası, anormallik tespiti, arıza modu, …

Context:
  EN: condition monitoring, IoT, predictive maintenance, …
  TR: durumsal izleme, IoT, öngörülü bakım, …
```

Decision on search languages: always produce EN+TR matrices. The bilingual-search skill rule: if a topic is Turkey-local (Turkish education policy, Turkish health legislation, Turkish dialect research), search TR sources mandatory. If topic is international (deep learning, COVID-19 vaccines), still search TR for completeness but expect EN to dominate.

### 4. Select Databases & Apply Search Strategy

Standard academic databases:
- **Multidisciplinary:** Google Scholar, Semantic Scholar, Crossref, OpenAlex
- **Computer science/engineering:** arXiv, DBLP, IEEE Xplore, ACM Digital Library
- **Life sciences:** PubMed, PubMed Central, EMBASE
- **General:** JSTOR, ProQuest, EBSCO

Turkish-specific sources (see [turkish-databases.md](reference/turkish-databases.md)):
- **TR Dizin** (trdizin.gov.tr) — indexes Turkish academic journals
- **DergiPark** (dergipark.org.tr) — open-access Turkish journals
- **YÖK Thesis Center** (tez.yok.gov.tr) — all Turkish theses (BSc, MSc, PhD)

Use the scout agent (`literature-scout`) to run multi-database searches in parallel. The scout will:
- Log every search query, database, date, and hit count
- De-duplicate across sources (DOI-first, then title-normalized matching)
- Enrich results with venue index status (SCI-E, Scopus, TR Dizin, etc.)
- Return a ranked candidate list (by relevance + venue quality)

### 5. Two-Stage Screening

**Stage 1 (Title/Abstract):** You review candidate list (typically 50–300 hits) and mark:
- ✓ **Include:** title/abstract clearly relevant; advance to full text.
- ✗ **Exclude:** clearly out of scope; record reason (e.g., "Not peer-reviewed", "Different population", "Predatory journal flagged").
- ? **Unclear:** advance to full-text review for decision.

**Stage 2 (Full-Text):** For each included paper, the `source-analyst` agent reads the PDF and:
- Confirms relevance against inclusion/exclusion criteria
- Extracts structured evidence cards (findings, methods, datasets, metrics, limitations)
- Scores methodological rigor (1–5 strength rating)
- Flags conflicting findings

### 6. Forward & Backward Snowballing (Optional)

**Backward snowballing:** Look at references in your included papers. Are there seminal papers or highly-cited sources you missed?

**Forward snowballing:** Use Google Scholar or Semantic Scholar to find papers citing your key included papers. Are recent papers building on them?

Snowballing is most valuable in rapidly-evolving fields (ML, COVID-19 literature) or when your database searches yield surprisingly few hits.

### 7. Saturation & Stopping Criterion

Continue searching and screening until:
- **Knowledge saturation:** new papers contribute no new concepts, methods, or findings; you're seeing the same themes repeated.
- **Study saturation:** the evidence cards show consistent findings; conflicting findings have been identified and characterized.
- **Practical limit:** you've reviewed 50–200 papers (typical for narrative reviews) or 100+ papers (systematic reviews). For large datasets (500+ papers), use staged analysis: screen a batch, synthesize, decide if more searching is needed.

For systematic reviews, use the PRISMA flow diagram (see [prisma.md](reference/prisma.md)): track identified / de-duplicated / screened / excluded (with reason) / included. The diagram communicates transparency.

### 8. Synthesis (The Hard Part)

See [synthesis.md](reference/synthesis.md) for deep guidance. In brief:

**Synthesis ≠ annotated bibliography.** An annotated bibliography lists papers and summarizes each. Synthesis *integrates* findings across papers: it identifies patterns, themes, contradictions, and gaps.

Patterns to look for:
- **Thematic:** group papers by concept (e.g., "CNN architectures", "transfer learning strategies", "explainability methods").
- **Chronological:** evolution of the field (early classical methods → neural networks → recent transformer-based approaches).
- **Methodological:** what methods dominate? What methodological gaps exist?
- **Empirical:** do all studies agree on dataset difficulty? Metric hierarchy? Baseline performance?
- **Conflict:** what findings contradict? Why? (different populations, datasets, evaluation protocols, publication bias?)

**Rule: ≥2 sources per paragraph.** If you cite only one source in a paragraph, you're summarizing, not synthesizing. The minute you cite a second source, you create a synthesis: comparison, confirmation, or conflict.

### 9. Write Up & Document

**Outcomes:**
- `sources/registry.jsonl` — all screened sources, with status (included/excluded/duplicate) and DOI/venue metadata.
- `evidence/cards.jsonl` — structured findings, methods, datasets from included papers, tagged by RQ.
- `search-log.md` — (if systematic) every query run, by database, hit count, date.
- `PRISMA flow diagram` — (if systematic) counts at each stage.
- `literature-synthesis.md` — thematic / chronological / methodological narrative tying papers together.

---

## PICO/PEO/SPIDER Templates (Quick Reference)

### PICO (for clinical/health studies)
```
Population:       Demographics, disease, health condition. E.g., "adults 18–65 with Type 2 diabetes"
Intervention:     The treatment/exposure being studied. E.g., "metformin therapy"
Comparison:       The alternative or control. E.g., "placebo" or "standard care"
Outcome:          Measured result. E.g., "HbA1c reduction", "quality of life"
Study design:     RCT, cohort, case-control. (Often implicit in RQ.)
Timeframe:        Duration of intervention and follow-up.

Inclusion criteria:
  - Population: age, comorbidities, disease stage
  - Intervention: drug, dosage, duration
  - Comparison: required or optional?
  - Outcomes: primary + secondary
  - Study design: RCT only, or observational too?
  - Language: EN only, or others?
  - Date range: e.g., 2015–present

Exclusion criteria:
  - Opinion pieces, editorials, non-peer-reviewed
  - Populations with confounding conditions
  - Outcomes not measuring clinical efficacy (e.g., only lab markers)
  - Conferences proceedings (depends on field; keep separate)
```

### PEO (for observational/exposure studies)
```
Population:       Who is being studied?
Exposure:         What is the risk factor / exposure of interest?
Outcome:          What is the measured result?

Typically used in epidemiology, environmental health, social sciences.
```

### SPIDER (for qualitative / exploratory)
```
Sample:           Who participated? How many? Sampling strategy?
Phenomenon:       What is being investigated? Central concept?
Design:           Study methodology (grounded theory, phenomenology, ethnography)?
Evaluation:       How was quality assessed? (rigor, credibility, transferability?)
Research type:    Qualitative, mixed-methods, theoretical?

More flexible than PICO; allows exploratory, iterative research.
```

---

## Handling Bilingual Results

See [bilingual-search.md](reference/bilingual-search.md) for full protocol. Key rules:

1. **Always build dual matrices:** even if you expect EN results to dominate, building a TR matrix is the search discipline. It surfaces Turkish-language gaps or hidden TR expertise.

2. **Deduplication (critical):** when you search both EN and TR, you'll find the same paper twice—once in English, once translated to Turkish. De-duplicate via:
   - DOI-first match (if both have DOI, same DOI = duplicate)
   - Title-normalized matching (normalize whitespace + diacritics + case, check ≥95% similarity)

3. **Track language in records:** every registry entry and card logs `lang: "en"` or `lang: "tr"`. In synthesis, note when findings come from EN-only vs TR-only sources (a finding known only in Turkish is noteworthy).

---

## Citations & Venue Quality

Before including a source:
- Run `/journal-check` to classify venue (SCI-E, Scopus, TR Dizin, predatory-flagged).
- Evidence from high-quality venues (SCI-E Q1, peer-reviewed) is weighted higher than pre-prints or low-quality outlets.
- See [venue-quality.md](reference/venue-quality.md) for index meanings and red flags.

---

## Common Mistakes (Avoid These)

| Mistake | Fix |
|---------|-----|
| Searching only one database | Use ≥3 (e.g., Semantic Scholar + Google Scholar + IEEE Xplore) for engineering topics |
| Using only English keywords | Build dual matrix; many non-English papers use EN abstracts + TR titles, easily missed |
| Including non-peer-reviewed or predatory sources | Check `/journal-check`; exclude predatory flags automatically |
| Stopping at Title/Abstract screening | Many false negatives; papers with vague abstracts need full-text review |
| Synthesis = list of papers | Every paragraph must synthesize ≥2 sources; if listing, it's annotation, not synthesis |
| Ignoring conflicting findings | Conflicts are the interesting part; acknowledge & explain in Discussion |
| No search log (for systematic reviews) | Search-log.md is mandatory for reproducibility; list queries, dates, hit counts |

---

## See Also

- [bilingual-search.md](reference/bilingual-search.md) — EN/TR decision matrix, transliteration, dedup rules
- [turkish-databases.md](reference/turkish-databases.md) — TR Dizin, DergiPark, YÖK Thesis Center: coverage, query patterns, metadata quirks
- [venue-quality.md](reference/venue-quality.md) — SCI-E/SSCI/AHCI/ESCI/Scopus/TR Dizin explained; quartiles; predatory red flags; `/journal-check` usage
- [prisma.md](reference/prisma.md) — PRISMA 2020 flow discipline; systematic review workflows
- [synthesis.md](reference/synthesis.md) — thematic / chronological / methodological synthesis patterns; "synthesis ≠ annotated bibliography" rule
- `literature-scout` agent — automates multi-database search + venue enrichment + dedup
- `evidence_db.py query --tags rq1` — retrieve cards for drafting, filtered by RQ
