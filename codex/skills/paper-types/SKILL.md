---
name: paper-types
description: Use when selecting or learning about paper types. Given research questions or a study design, identifies the matching paper type (11 types: IMRaD empirical, systematic/meta-analysis, narrative review, scoping review, qualitative, case report, RCT report, observational, theoretical, CS conference, short paper) and points to its reference guide and rubric.
---

# Paper Types — Selection & Guidance

> **Maintenance note:** `reporting-guidelines/SKILL.md`'s "Step 1: Identify
> Your Study Type" flowchart asks the same primary-data/design/scope
> questions as the tree below, for a different purpose (guideline/checklist
> selection vs. reference/rubric file selection). If you change the
> classification logic here (add/remove a type, change a routing question),
> update that flowchart too — they are two independent copies, not one
> shared source.

## Quick Decision Tree

1. **Did you collect primary data (your own)?**
   - Yes → Go to step 2
   - No, you reviewed literature → Go to step 5

2. **Is your study randomized with treatment assignment?**
   - Yes → **RCT Report** (Section 7)
   - No → Go to step 3

3. **What's your design?**
   - Cohort, case-control, or cross-sectional → **Observational Study** (Section 8)
   - Single case with detailed timeline → **Case Report** (Section 6)
   - Interviews/focus groups/ethnography → **Qualitative Study** (Section 5)
   - Experiment/lab study → **Empirical Research (IMRaD)** (Section 1)

4. **For empirical studies:** Does your research question test a hypothesis or explore mechanistically?
   - Tests hypothesis/comparison → **Empirical Research (IMRaD)**
   - Describes/explores without pre-registered hypothesis → **Qualitative Study** or **Case Report**

5. **You reviewed literature. What scope?**
   - Systematic search of all databases, explicit criteria, ≥2 screeners, flow diagram → **Systematic Review / Meta-analysis** (Section 2)
   - Mapping the field (breadth over depth) → **Scoping Review** (Section 4)
   - Narrative synthesis of known themes, selective scope → **Narrative Review** (Section 3)

6. **Publishing venue?**
   - Academic journal, any discipline → empirical/review/qualitative/case/observational per above
   - CS/engineering conference (IEEE/ACM/ICML/NeurIPS) → **Conference Paper** (Section 9)
   - Conference with strict page limit (2–4 pages) → **Short Paper / Letter** (Section 10)
   - Theory, no empirical data, building argument architecture → **Theoretical/Conceptual Paper** (Section 11)

---

## Type Summaries (click reference links for full guidance)

### 1. Empirical Research Article (IMRaD)
**When:** Testing a hypothesis or comparing conditions with experimental/quasi-experimental design. Primary data collection (lab, field, quasi-experiment). Typical venue: peer-reviewed journal in natural/social sciences, engineering.  
**Structure:** Introduction (RQ/hypothesis) → Methods (design, participants, procedures, measures) → Results (statistical/descriptive findings) → Discussion (interpretation, limitations, implications) → Conclusion.  
**Word budget:** ~6000–8000 words; typical proportions I:15% M:25% R:25% D:30% C:5%.  
**Key discipline:** Hypothesis ↔ findings tracing; statistical reporting standards (STROBE for observational, CONSORT for RCT).  
**Reference:** [imrad.md](reference/imrad.md)  
**Rubric:** [rubrics/imrad.md](rubrics/imrad.md)

### 2. Systematic Review / Meta-analysis
**When:** Answering a question by synthesizing ALL evidence from a systematic search; optionally pooling results quantitatively (meta-analysis). Rigorous protocol (ideally pre-registered). Typical venue: health sciences, social sciences, systematic review journals.  
**Structure:** Introduction (RQ, rationale) → Methods (PRISMA protocol, search strategy, inclusion/exclusion, screening process, data extraction) → Results (flow diagram, characteristics table, synthesis/meta-analysis results) → Discussion (certainty of evidence, implications) → Conclusion.  
**Special requirements:** PRISMA 2020 27-item checklist; flow diagram (identified → deduplicated → screened → excluded+reason → included); search-strategy reproducibility (databases, dates, keywords, hit counts per database).  
**Word budget:** ~8000–12000 words; detailed Methods & Results.  
**Key discipline:** Search reproducibility (every query logged), inclusion/exclusion criteria applied consistently by ≥2 reviewers.  
**Reference:** [reference/systematic-review.md](reference/systematic-review.md)  
**Rubric:** [rubrics/systematic-review.md](rubrics/systematic-review.md)

### 3. Narrative Review
**When:** Synthesizing known themes in a topic; NOT exhaustive search, but expert-curated synthesis. Conceptual framework builds the narrative. Typical venue: review journals, book chapters, journals seeking "state of the art" pieces.  
**Structure:** Introduction (topic scope, why now) → thematic sections (each theme addressed via 2+ sources in conversation, not list) → Synthesis & gaps (conceptual framework, what's missing, future directions) → Conclusion.  
**Word budget:** ~6000–10000 words; varies by venue.  
**Key discipline:** Synthesis ≠ annotated bibliography; each paragraph weaves ≥2 sources together to build a point.  
**Reference:** [reference/systematic-review.md](reference/systematic-review.md) (search strategy basics apply; narrative reviews use selective scope, documented openly)  
**Rubric:** [rubrics/systematic-review.md](rubrics/systematic-review.md) (adapt "systematic" requirements: scope is selective, not exhaustive; document it clearly)

### 4. Scoping Review
**When:** Mapping the field to identify scope, gaps, and research types (not deep synthesis). Useful before launching a full systematic review. Follows PRISMA-ScR. Typical venue: specialized journals, health/social sciences.  
**Structure:** Introduction (topic, PEO/PIO framing) → Methods (PRISMA-ScR protocol, search strategy, inclusion criteria, screening, extraction) → Results (flow diagram, characteristics table, mapping table showing themes/gaps) → Discussion (implications, limitations) → Conclusion.  
**Special requirements:** PRISMA-ScR 22-item checklist; mapping table (papers × dimensions like methodology, population, outcome).  
**Word budget:** ~7000–10000 words.  
**Key discipline:** Breadth over depth; documenting what types of research exist in the field.  
**Reference:** [reference/systematic-review.md](reference/systematic-review.md) (PRISMA-ScR variant)  
**Rubric:** [rubrics/systematic-review.md](rubrics/systematic-review.md)

### 5. Qualitative Study
**When:** Exploring lived experience, perceptions, meanings, processes (interviews, focus groups, ethnography, document analysis). Rigor via member checking, reflexivity, saturation. Typical venue: social sciences, nursing, education, psychology journals.  
**Structure:** Introduction (research question, context, rationale) → Methods (design, participants, data collection procedures, analysis procedure, reflexivity/researcher positionality) → Findings (themes with supporting quotes, page numbers) → Discussion (interpretation, theoretical implications, limitations) → Conclusion.  
**Special requirements:** COREQ or SRQR 32–32-item checklist; theme–quote–source chain (every quote includes source ID and page; no orphan themes); saturation criterion documented.  
**Word budget:** ~6000–8000 words.  
**Key discipline:** Quote fidelity (verbatim, page numbers, context) and theme rigor (saturated, not forced).  
**Reference:** [reference/qualitative.md](reference/qualitative.md)  
**Rubric:** [rubrics/qualitative.md](rubrics/qualitative.md)

### 6. Case Report
**When:** Describing a rare, unusual, or instructive single case (medical, clinical, organizational). CARE checklist required. Typical venue: medical journals, case-report journals, clinical practice.  
**Structure:** Introduction (case significance, rationale) → Case presentation (patient/case demographics, history, timeline of events, intervention, outcome) → Discussion (what this case teaches, positioning vs literature, limitations) → Conclusion.  
**Special requirements:** CARE 13-item checklist; detailed timeline (dates and sequence matter); explicit consent statement.  
**Word budget:** ~2000–3000 words.  
**Key discipline:** Timeline precision; medical/legal transparency (consent, privacy).  
**Reference:** [reference/case-report.md](reference/case-report.md)  
**Rubric:** [rubrics/imrad.md](rubrics/imrad.md) (adapt: single case = different Results structure)

### 7. RCT Report
**When:** Testing a randomized treatment assignment in a controlled trial (typically health, education, behavior). Highest evidence level for causal claims. Typical venue: medical/health/education journals.  
**Structure:** Introduction → Methods (design, randomization procedure, blinding, participants, intervention, outcome measures, statistical analysis plan) → Results (flow diagram with participant attrition, baseline characteristics table, outcome results by group, statistical tests, adverse events) → Discussion → Conclusion.  
**Special requirements:** CONSORT 25-item checklist; flow diagram (enrolled → randomized → allocated → followed-up → analyzed, with exclusion counts at each stage); pre-registration (trial ID, date); analysis plan stated before results.  
**Word budget:** ~6000–8000 words.  
**Key discipline:** Blinding specification, statistical precision (means ± SE, p-values, CIs), participant flow transparency.  
**Reference:** [reference/imrad.md](reference/imrad.md) (structure); CONSORT checklist lives in the reporting-guidelines skill  
**Rubric:** [rubrics/imrad.md](rubrics/imrad.md)

### 8. Observational Study
**When:** Cohort, case-control, or cross-sectional design; no randomization. Describing patterns, associations, prevalence. Typical venue: epidemiology, social sciences, psychology journals.  
**Structure:** Introduction (research question, context) → Methods (study design specification, participants/cases, exposure/outcome measurement, data collection, confounders, statistical analysis plan) → Results (participant flow, characteristics tables, main and sensitivity/subgroup analyses) → Discussion → Conclusion.  
**Special requirements:** STROBE 22-item checklist (variant by design type: cohort/case-control/cross-sectional); confounder specification; flow diagram.  
**Word budget:** ~6000–8000 words.  
**Key discipline:** Design-specific reporting (cohort: follow-up; case-control: matching; cross-sectional: point estimate + CI).  
**Reference:** [reference/imrad.md](reference/imrad.md) (structure); STROBE checklist lives in the reporting-guidelines skill  
**Rubric:** [rubrics/imrad.md](rubrics/imrad.md)

### 9. Theoretical / Conceptual Paper
**When:** Building argument, no empirical data. Proposing theory, framework, model, or analyzing concepts. Typical venue: theory journals, philosophy, conceptual papers in specialized journals.  
**Structure:** Introduction (problem being addressed, thesis statement) → argument architecture (proposition → evidence/warrant → implication, repeated across sections) → Implications & future directions → Conclusion.  
**Word budget:** ~5000–7000 words.  
**Key discipline:** Claim–evidence–warrant chain (Toulmin model); explicit proposition–evidence mapping (avoid unsupported claims).  
**Reference:** [reference/theoretical.md](reference/theoretical.md)  
**Rubric:** [rubrics/theoretical.md](rubrics/theoretical.md)

### 10. CS / Engineering Conference Paper
**When:** Publishing at IEEE/ACM/ICML/NeurIPS/AAAI/etc. Possibly with strict page limits and camera-ready rules. Emphasis on novelty, reproducibility, comparison rigor.  
**Structure:** Intro (problem, contribution) → Related work (explicit positioning vs prior art) → Method/Approach → Experiments (baselines, datasets, metrics, ablations, results tables/figures) → Discussion/Conclusion.  
**Special requirements:** Page limit (usually 6–8 pages + references); camera-ready formatting (IEEE/ACM style); code/data availability statement (NeurIPS reproducibility checklist); comparison fairness (equal experimental conditions, multiple seeds, statistical significance).  
**Word budget:** ~5000–6000 words (strict).  
**Key discipline:** Baseline selection (fair, well-known, recent); ablation design; seed protocol & significance testing; positioning vs related work (not just citations, but explicit comparison).  
**Reference:** [reference/conference-cs.md](reference/conference-cs.md)  
**Rubric:** [rubrics/conference-cs.md](rubrics/conference-cs.md)

### 11. Short Paper / Letter
**When:** Preliminary findings, negative results, rapid communication, letters to the editor, conference short papers. Venue-specific format. Typical venue: any journal's "Short Communication" or "Letter" section; some conferences.  
**Structure:** Varies by venue; typically Introduction + Methods + Results + Discussion compressed into 2–4 pages; or Introduction + key point + conclusion.  
**Word budget:** 1500–2500 words max (strict).  
**Key discipline:** Every word counts; prioritize the novel/surprising finding; constraints are part of the art.  
**Reference:** [reference/conference-cs.md](reference/conference-cs.md) (page-limit discipline applies; adapt proportions)  
**Rubric:** [rubrics/conference-cs.md](rubrics/conference-cs.md) (adapt for brevity)

---

## Canonical Type → File Resolution

PROJECT.md's `- **Type:**` bullet holds one of 15 enum keys (see the template's
own comment). **Consumers (submit-check, reviewer-critic, critique) MUST look
up both the reference file and the rubric file in this table — never
substitute `reference/<type>.md` or `rubrics/<type>.md` naively.** Several
type keys deliberately share a file (e.g. narrative/scoping review reuse the
systematic-review reference; case-report/RCT/observational share the IMRaD
rubric), and the two columns are NOT the same mapping — reference and rubric
diverge for several types.

| Type key (PROJECT.md) | Reference file | Rubric file |
|---|---|---|
| `empirical-imrad` | `reference/imrad.md` | `rubrics/imrad.md` |
| `systematic-review` | `reference/systematic-review.md` | `rubrics/systematic-review.md` |
| `narrative-review` | `reference/systematic-review.md` | `rubrics/systematic-review.md` |
| `scoping-review` | `reference/systematic-review.md` | `rubrics/systematic-review.md` |
| `qualitative` | `reference/qualitative.md` | `rubrics/qualitative.md` |
| `case-report` | `reference/case-report.md` | `rubrics/imrad.md` |
| `rct` | `reference/imrad.md` | `rubrics/imrad.md` |
| `observational` | `reference/imrad.md` | `rubrics/imrad.md` |
| `theoretical` | `reference/theoretical.md` | `rubrics/theoretical.md` |
| `conference-cs` | `reference/conference-cs.md` | `rubrics/conference-cs.md` |
| `short-paper` | `reference/conference-cs.md` | `rubrics/conference-cs.md` |
| `thesis-bsc` | *(see thesis-structure skill, not a reference/ file)* | `rubrics/thesis.md` |
| `thesis-msc` | *(see thesis-structure skill, not a reference/ file)* | `rubrics/thesis.md` |
| `thesis-phd` | *(see thesis-structure skill, not a reference/ file)* | `rubrics/thesis.md` |
| `thesis-cumulative` | *(see thesis-structure skill, not a reference/ file)* | `rubrics/thesis.md` |

RCT and observational studies also carry their own reporting-guideline
checklist (CONSORT / STROBE) — that lookup is separate and already handled by
`submit-check`'s Step 2 (`type + subtype → guideline` table), not by this
table. All paths are relative to `.claude/skills/paper-types/`.

## Cross-Cutting Rules

**Hypothesis ↔ Findings Tracing (empirical only):**  
In Introduction, state the hypothesis/RQ clearly. In Results, use the same terminology. In Discussion, directly address what you found vs what you hypothesized. `word_budget.py --rq-trace` checks this automatically.

**Terminology Consistency:**  
Choose one term per concept (e.g., "CNN-based fault diagnosis" not also "deep learning anomaly detection" for the same thing). EN term + TR term on first mention (bilingual output).

**Limitations Honesty:**  
Every paper must include limitations (Methods or Discussion, depending on type). Mark assumptions; don't hide them.

**Figure / Table Sufficiency:**  
At least one table or figure per major result; captions are self-contained (reader shouldn't need to read text to understand the figure).

---

## Next Steps

1. **Choose your type** using the decision tree above.
2. **Read the reference file** linked in your type's summary.
3. **Check the rubric** (reviewer-critic will read it; you can too for self-review).
4. **Use /draft** to start writing; academic-writing skill covers register + tense + hedging.
5. **Use /verify-citations** before finalization (applies the reporting-guidelines checklist).
