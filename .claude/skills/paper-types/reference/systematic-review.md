# Systematic Review & Meta-Analysis

## PRISMA 2020: 27-Item Checklist

This checklist maps to manuscript sections. Every item must be addressed (can be marked "not applicable" if justified).

| # | Item | Typical Location | What to Include |
|----|------|------------------|-----------------|
| 1 | Title identifies as SR/MA | Title | "Systematic Review and Meta-analysis of…" or "Scoping Review of…" |
| 2 | Structured abstract with PICO | Abstract | Background, objectives, databases, study selection, data synthesis method, main findings, conclusions |
| 3 | Registration (pre-registration) | Methods or note | Protocol ID (PROSPERO, OSF, etc.) and date |
| 4a | Rationale & objectives clearly stated | Introduction | What question does this review answer? Why is it important? |
| 4b | Explicit PICO or PEO framing | Introduction or Methods | Population, Intervention, Comparison, Outcome (or Population, Exposure, Outcome for observational) |
| 5a | Information sources (databases, date range) | Methods: Search strategy | Which databases? (PubMed, Embase, Scopus, etc.) Dates of search. Who did it? |
| 5b | Search strategy | Methods or Appendix | Full search query per database (MeSH terms, keywords, Boolean operators) and number of hits per database |
| 6a | Study selection process | Methods: Selection | Who screened titles/abstracts? Who screened full texts? How was disagreement resolved? (2 independent reviewers standard) |
| 6b | Data extraction process | Methods: Extraction | What data were extracted? Who did it? How was disagreement resolved? Form/template used? |
| 6c | Data items extracted | Methods: Extraction or Table | List the variables: author, year, design, population, intervention, outcomes, results, funding, conflicts |
| 6d | Study risk-of-bias assessment | Methods: Risk of Bias | Which tool? (Cochrane ROB 2, ROBINS-I, etc.) Who assessed? Independent? |
| 7 | Effect measure for meta-analysis | Methods: Data Synthesis | If MA: was outcome continuous or categorical? (Standardized MD, MD, SMD, RR, OR, etc.) |
| 8a | Study selection flow diagram | Results (Figure 1) | PRISMA Flow Diagram: identified (N) → deduplicated (N) → screened titles/abstracts (N) → excluded with reasons (N) → full texts reviewed (N) → excluded with reasons (N) → included in synthesis (N) → included in MA (N) |
| 8b | Characteristics of included studies | Results (Table 1) | Author, year, country, design, population (N, demographics), intervention, comparison, outcomes, follow-up, funding, conflicts |
| 8c | Risk-of-bias summary | Results (Table or Figure) | Risk of bias per study and overall, by outcome |
| 9 | Effect estimates per outcome | Results (Table or Figure) | Point estimate (MD, SMD, RR, OR) with 95% CI, separate by subgroup if applicable, separate by MA-eligible vs descriptive studies |
| 10a | Certainty of evidence assessment | Results or Discussion | GRADE or similar (high, moderate, low, very low) per outcome |
| 10b | Heterogeneity description | Results | I² statistic, Q-test, range of effects; reasons for heterogeneity explored (population, intervention, measurement) |
| 11 | Meta-analysis synthesis method | Results | Random-effects vs fixed-effects model; method for pooling (Mantel-Haenszel, DL, etc.); handling of missing data |
| 12 | Reporting bias assessment | Results | Funnel plot inspection; Egger's test if ≥10 studies; publication bias discussion |
| 13 | Certainty limitations | Discussion | What limits certainty? (Risk of bias, imprecision, inconsistency, indirectness, publication bias) |
| 14 | Interpretation in context of other evidence | Discussion | How does this fit with existing knowledge? Aligned or conflicting findings? |
| 15 | Discussion of implications for practice/policy | Discussion | What should clinicians/policymakers do based on this? |
| 16 | Discussion of implications for future research | Discussion | What questions remain? What do we need to know next? |
| 17 | Limitations of the review | Discussion | Scope limitations, search limitations, heterogeneity, missing data, publication bias considerations |
| 18 | Registration details & amendments | Methods | PROSPERO ID; any deviations from protocol |
| 19 | Funding sources of included studies | Results or appendix | Conflicts of interest of included studies (a marker of bias) |
| 20 | Funding of the review | Title page or end | Who funded this SR/MA? |
| 21 | Data availability & accessibility | Methods or online appendix | Data extraction sheet available? Code available? |
| 22 | Non-English studies | Methods: Search strategy | Were non-English databases searched? Non-English studies included? How? |
| 23 | Quality assessment tools used | Methods | Cite the ROB tool(s) used and provide the reference |
| 24 | Effect size calculation details | Methods or Appendix | If standardizing across studies, show the formula |
| 25 | Subgroup and sensitivity analyses | Results | Planned analyses: population subgroups, dose-response, study design, publication type. Were findings robust? |
| 26 | Conflict of interest statement | End | Authors' conflicts; funding of the review; any vested interests |
| 27 | Ethical approval & consent | Methods | IRB approval if qualitative component; data sharing agreements if applicable |

---

## Search Strategy Template

### Documentation (for reproducibility)

```
Database: PubMed
Date range: 2015 – 2024
Query executed: ("deep learning" OR CNN OR "neural network") AND (fault OR anomaly OR diagnosis) 
  AND (bearing OR vibration OR signal)
  NOT (review OR letter OR editorial)
Filters: English, human/animal studies if applicable
Date searched: [today's date]
Searcher: [name]
Hits: 247
```

**Repeat for each database** (Embase, Scopus, Web of Science, etc.).

### Search Strategy Construction

**Step 1: Identify concepts**
- Concept 1: Population/condition (e.g., "bearing fault," "machine learning diagnosis")
- Concept 2: Intervention/exposure (e.g., "deep learning," "CNN")
- Concept 3: Outcome (e.g., "diagnostic accuracy," "fault detection")

**Step 2: Gather synonyms & keywords per concept**
- Concept 1: bearing fault | bearing failure | bearing damage | bearing wear | rolling-element bearing fault
- Concept 2: CNN | convolutional neural network | deep learning | machine learning
- Concept 3: detection | diagnosis | classification | recognition

**Step 3: Build search string (use database-specific syntax)**
- PubMed (MeSH + text): (Diagnostic Accuracy[MeSH] OR "diagnostic accuracy"[tiab]) AND ("deep learning"[tiab] OR "neural network"[tiab] OR CNN[tiab])
- Scopus (field codes): TITLE-ABS-KEY(("bearing fault" OR "bearing failure") AND ("deep learning" OR CNN OR "neural network"))
- Web of Science: TS=(("bearing fault" OR "bearing failure") AND ("deep learning" OR CNN))

**Step 4: Test and document**
- Run the query; record number of results.
- Scan titles (first 20–30) for relevance.
- Adjust terms if too many irrelevant hits or too few relevant ones.

---

## Inclusion / Exclusion Criteria

### Template

**Inclusion Criteria:**
1. Study design: [RCT, cohort, case-control, cross-sectional, observational] (specify)
2. Population: [specific patient group, age, setting] (e.g., "adults aged 18–65 with Type 2 diabetes")
3. Intervention: [what was studied] (e.g., "any form of deep learning for fault diagnosis")
4. Comparison: [what it was compared to] (e.g., "baseline machine learning or conventional methods" or "none required")
5. Outcome: [what was measured] (e.g., "diagnostic accuracy, sensitivity, specificity")
6. Language: English, or English and [other language]
7. Publication: peer-reviewed journal, conference proceedings, or [other]
8. Year: [2015–2024] or [any]

**Exclusion Criteria:**
1. Study design: [editorials, letters, reviews] (exclude these)
2. Population: [if not matching inclusion; e.g., "pediatric patients only" if you need adults]
3. Outcome: [if not measured; e.g., "qualitative descriptions without quantified accuracy"]
4. Full text unavailable (unless abstract + supplementary data provide enough info)
5. Duplicates (by DOI first, then title-author-year if no DOI)
6. Retracted or withdrawn publications

**Justification note:** Why each criterion matters. Example: "Inclusion of both English and Turkish ensures coverage of international and local literature, addressing a known gap in some systematic reviews of [topic]."

---

## PRISMA-ScR (Scoping Reviews)

Scoping reviews differ from systematic reviews in scope (broader mapping vs. depth synthesis) and don't typically include risk-of-bias assessment. PRISMA-ScR has 22 items (subset of full PRISMA):

| Item | Applies | Key Difference |
|------|---------|-----------------|
| Title | Yes | Use "Scoping review" in title |
| Abstract | Yes | Include "scoping review" |
| Rationale | Yes | Rationale for SCOPE (map field, identify gaps, not synthesis of effectiveness) |
| Objectives | Yes | Explicit scope/boundaries |
| PICO/PEO | Yes | Population, Intervention (exposure), Context (what dimensions matter?) |
| Info sources | Yes | Databases, search dates |
| Search strategy | Yes | Documented queries per database |
| Study selection | Yes | 2 reviewers for screening; inclusion/exclusion applied |
| Data extraction | Yes | Data charting form; may include study design, population, methods, findings |
| Study characteristics | Yes | Table of included studies (author, year, country, design, population, key findings) |
| Findings synthesis | **No ROB** | Narrative synthesis or mapping table (studies × themes/dimensions, showing which topics are covered and gaps) |
| Certainty of evidence | **Not done** | Scoping reviews don't assess certainty; they map the landscape |
| Results flow diagram | Yes | PRISMA flow diagram still required |
| Limitations | Yes | State clearly |
| Conclusions | Yes | What did we learn about the field? What gaps exist? |

---

## Meta-Analysis Specific Notes

### When to do meta-analysis

- You have ≥5 studies (practical minimum; some say ≥3 if very similar).
- Outcomes are measured the same way (or can be standardized; e.g., all report accuracy, F1, AUROC).
- Studies are sufficiently similar (population, intervention, measurement) that pooling makes sense.
- Not too much heterogeneity (I² < 75% comfortable; >75% indicates high heterogeneity requiring subgroup exploration).

### Forest plot essentials

- Each row = one study; show point estimate + 95% CI.
- Diamond at bottom = pooled estimate.
- Vertical line at "no effect" (RR=1, MD=0, OR=1 depending on measure).
- Bold the pooled result.
- Caption: "Forest plot of [outcome] comparing [intervention] vs [comparison]."

### Heterogeneity exploration

If I² > 50%, explore:
1. **Population subgroups:** Separate analyses by age, baseline severity, setting.
2. **Intervention subgroups:** Dose, duration, delivery mode.
3. **Design:** Separate RCTs from observational studies.
4. **Measurement:** If different instruments, sensitivity analysis by instrument type.

### Publication bias assessment

- **Funnel plot:** Plot log(effect size) vs sample size (or SE). Asymmetry suggests bias.
- **Egger's test:** Statistical test for funnel asymmetry (p < 0.10 suggests bias).
- **Important:** Asymmetry ≠ publication bias; consider small-study effects from other sources (heterogeneity, methodological differences).

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Search strategy not fully reproducible (no database, no date, no exact query) | Document everything in Methods; include exact query syntax |
| Search limited to English only (without justifying) | State rationale for language limit; note if restricting limits scope |
| Single-reviewer screening (risk of bias creeping in) | Use 2 independent reviewers; report inter-rater agreement (κ or % agreement) |
| Studies of vastly different quality treated equally in MA | Conduct sensitivity analysis excluding high-ROB studies; use ROB as subgroup |
| No GRADE certainty assessment (readers don't know how confident to be) | Apply GRADE or similar; rate each outcome as high/moderate/low/very low certainty |
| Heterogeneity ignored (pooling effect sizes that differ wildly) | Investigate I²; subgroup analysis; consider narrative synthesis if too heterogeneous |
| No flow diagram or incomplete (reader can't track how you got to N included studies) | PRISMA Flow Diagram mandatory; fill all boxes: identified, deduplicated, screened, excluded+reasons, included |
| Conflicts of interest not disclosed | State conflicts and funding transparently |

---

## Tools & Resources

- **PROSPERO:** Register your protocol before searching (prosper.asu.edu.au or prospero.crd.york.ac.uk)
- **PRISMA 2020 Checklist:** prisma-statement.org
- **RevMan (Cochrane):** Free software for SR/MA data entry and forest plots (covidence.org for systematic data management)
- **GRADE:** gradeprojectonline.org (certainty assessment)
- **ROBINS-I tool:** Risk of Bias In Non-randomized Studies – Interventions (for observational studies)
- **Cochrane ROB 2:** Risk of Bias 2 tool (for RCTs)

---

## References

- Higgins JPT, Thomas J (eds). Cochrane Handbook for Systematic Reviews of Interventions (v6.4). Cochrane Collaboration, 2023.
- Moher D, et al. PRISMA 2020 explanation and elaboration. BMJ. 2021;372:n160.
- Tricco AC, et al. PRISMA extension for scoping reviews (PRISMA-ScR). Ann Intern Med. 2018;169(7):467–473.
