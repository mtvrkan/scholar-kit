# STROBE: Observational Studies (Cohort, Case-Control, Cross-Sectional)

## Checklist (22 Items + Design-Specific Variants)

| # | Item | Location |
|----|------|----------|
| **1a** | Title + abstract indicates study design | Title / Abstract |
| **1b** | Key elements: study design, setting, participants, exposures, outcomes | Abstract |
| **2** | Study design clearly stated (prospective cohort, case-control, cross-sectional) | Methods: Study Design |
| **3** | Background and rationale | Introduction |
| **4** | Research objectives and hypotheses | Introduction (end) |
| **5a** | Eligible criteria: inclusion and exclusion | Methods: Participants |
| **5b** | Sources and methods of selection of participants | Methods: Participants |
| **6** | For matched studies: matching criteria and number of exposed/unexposed per matched group | Methods: Design Specifics |
| **7a** | Exposure definition: how measured, categories, timing | Methods: Exposure |
| **7b** | Exposure assessed as continuous or categorical; cutoffs specified | Methods: Exposure |
| **8** | For matched studies: describe matching process | Methods: Design Specifics |
| **9** | Outcome definition: how measured, validation, timing of measurement | Methods: Outcomes |
| **10** | Follow-up period for cohort studies (start date, end date) | Methods: Follow-up |
| **11a** | Potential confounders: definition, measurement, categories | Methods: Covariates |
| **11b** | Rationale for selection of confounders | Methods: Covariates (or Discussion) |
| **12a** | Sample size: how was it calculated? (power, effect size, precision) | Methods: Sample Size |
| **12b** | Explanation of any interim analyses or stopping rules | Methods: Sample Size (if applicable) |
| **13** | Quantitative variables: mean and SD (or median and IQR); categorical: count and % | Results: Descriptive Stats |
| **14a** | Number of participants with missing data per variable | Results or Appendix |
| **14b** | Reasons for missingness and handling methods | Results or Appendix |
| **15** | Cohort: number of participants with each outcome; case-control: number with exposure | Results: Outcome Counts |
| **16** | Unadjusted associations (crude analysis); then adjusted associations (accounting for confounders) | Results: Main Analysis |
| **17** | Other analyses: subgroup, interaction, sensitivity | Results: Additional Analyses |
| **18** | Study design limitations and potential biases | Discussion: Limitations |
| **19** | Interpretation: results in context of other evidence and assumptions | Discussion |
| **20** | Generalizability: to whom do results apply? | Discussion: Limitations |
| **21** | Sources of funding and conflicts of interest | Funding statement |
| **22** | Availability of data | Data Availability |

---

## Design-Specific Guidance

### Cohort Studies

**Critical items:**
- **Exposure assessment (Item 7):** How was exposure measured at baseline? Is it objective (medical record, lab) or self-reported (questionnaire)?
- **Follow-up (Item 10):** When did follow-up start? How long was follow-up? How often were outcomes assessed?
- **Loss to follow-up (Item 14):** Report N lost per group, reasons, and % loss. Compare characteristics of those lost vs. retained.
- **Outcome assessment (Item 9):** Was outcome assessor blinded to exposure? How validated was the outcome measure?

**Flow diagram:**
```
[Cohort defined at baseline, exposure-free]
        ↓
  [Exposed: N=XXX]     [Unexposed: N=XXX]
     ↓ (follow-up)          ↓
  [With outcome: N]     [With outcome: N]
  [Without outcome: N]  [Without outcome: N]
  [Lost to FU: N]       [Lost to FU: N]
```

### Case-Control Studies

**Critical items:**
- **Case/control definition (Items 5, 9):** How are cases (people with outcome) and controls (people without outcome) defined? Are controls from the same source population?
- **Matching (Item 8):** If matched, on what variables? Report matching ratio (e.g., 1:1, 1:2).
- **Exposure assessment (Item 7):** Exposure in case-control is measured retrospectively. Was assessor blinded to case/control status?
- **Temporal relationship (Item 10):** Outcome occurred before exposure was measured. This is inherent to design; clearly state it.

**Flow diagram:**
```
[Population at risk for outcome]
        ↓
  [Cases (with outcome): N=XXX] | [Controls (without outcome): N=XXX]
     ↓ (look back)                   ↓
  [Exposed in past: N]           [Exposed in past: N]
  [Unexposed in past: N]         [Unexposed in past: N]
```

### Cross-Sectional Studies

**Critical items:**
- **Sampling (Item 5):** How were participants selected? Is it representative of the target population?
- **Exposure & outcome measured simultaneously (Item 10):** Cross-sectional cannot establish causality; state this explicitly.
- **Temporal clarity (Item 10):** Even though measured simultaneously, exposure should logically precede outcome conceptually.

---

## Confounder Specification (Item 11 — Critical)

**Confounders are variables that:**
1. Are associated with both exposure and outcome.
2. Are not on the causal pathway (not a mediator).

**Example:** Studying the effect of exercise on heart disease, age is a confounder (age affects both exercise habits and heart disease risk). Gender might be, depending on the analysis.

**What to report:**
- List all potential confounders measured.
- For each, state: definition, measurement method, categories (if categorical).
- Rationale: why was this confounder selected?

**In Results:**
- Report both crude (unadjusted) and adjusted analyses.
- Show what confounders were adjusted for (e.g., "adjusted for age and sex").

---

## Bias Checklist (Item 18)

| Type of Bias | Mitigation Strategy | Where to Report |
|---|---|---|
| **Selection bias** | Clearly define population, inclusion/exclusion; report participation rate | Methods + Results |
| **Information bias** | Validate outcome/exposure measurement; if self-reported, assess accuracy | Methods |
| **Confounding** | Measure and adjust for known confounders | Methods + Results |
| **Loss to follow-up** (cohort) | Report %, reasons, compare characteristics of lost vs. retained | Results + Discussion |
| **Recall bias** (case-control) | Minimize time between outcome and exposure measurement; use medical records if possible | Methods |
| **Detection bias** | Blind outcome assessor to exposure/case-control status (if possible) | Methods |

---

## Common Omissions

| Item | Missing? | Fix |
|---|---|---|
| Study design clearly stated | "We conducted a study..." (unclear if prospective cohort, case-control, etc.) | State: "This is a prospective cohort study" or "case-control study" |
| Confounders specified | No mention of how confounding was addressed | List potential confounders; explain why measured; state adjustment method in analysis |
| Follow-up duration & attrition | "Patients were followed" (for how long? who dropped out?) | Report: start date, end date, N lost, reasons for loss, % loss per group |
| Outcomes described | "Heart disease was the outcome" (how measured?) | Validate: "Heart disease was defined as hospitalization for MI or death from cardiac cause, confirmed by medical record review" |
| Exposure assessment | "Participants reported exercise" (how validated?) | Detail: "Habitual physical activity was measured using the International Physical Activity Questionnaire (IPAQ), which has been validated in [population]" |
| Crude vs. adjusted | Only adjusted results shown | Report both crude and adjusted; show what confounders were adjusted for |

---

## References

- **STROBE Statement:** strobe-statement.org
- **STROBE Explanation & Elaboration:** von Elm et al. (2007). The Lancet.
- **Design-specific extensions:** STROBE has variants for specific study types (DNA, cohort, etc.)
