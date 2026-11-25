# CONSORT 2010: Randomized Controlled Trials

## Checklist (25 Items)

| # | Item | Where in Manuscript |
|----|------|---|
| **1a** | Title identifies trial as randomized | Title page |
| **1b** | Subtitle mentions design (parallel, crossover, etc.) | Title / abstract |
| **2a** | Structured abstract: background, objectives, methods, results, conclusions | Abstract (150–250 words) |
| **2b** | Trial registration number and registry name | Abstract or Methods |
| **3a** | Scientific background and explanation of rationale | Introduction |
| **3b** | Specific objectives or hypotheses | Introduction (end) |
| **4a** | Trial design (parallel, factorial, etc.) and allocation ratio | Methods: Trial Design |
| **4b** | Important changes to methods after trial commencement | Methods or Appendix |
| **5** | Type of randomization; details of any restrictions (blocking, stratification) | Methods: Randomization |
| **6a** | Method used to generate random allocation sequence | Methods: Randomization |
| **6b** | Type of randomization scheme (random number generator, sealed envelopes, etc.) | Methods: Randomization |
| **7a** | Who generated allocation sequence | Methods: Randomization |
| **7b** | Who enrolled participants and assigned interventions | Methods: Randomization |
| **8a** | Blinding: was participant blinded? | Methods: Blinding |
| **8b** | Was care provider (clinician) blinded? | Methods: Blinding |
| **8c** | Was outcome assessor blinded? | Methods: Blinding |
| **8d** | If blinding was not possible, state that and why | Methods: Blinding |
| **9** | How sample size was determined (power analysis: N, effect size, α, power) | Methods: Sample Size |
| **10** | How sample size accounts for anticipated attrition | Methods: Sample Size |
| **11a** | When interim analyses were planned (if any) | Methods: Statistical Analysis |
| **11b** | Stopping rules for interim analyses | Methods: Statistical Analysis |
| **12a** | Statistical tests used for primary and secondary outcomes | Methods: Statistical Analysis |
| **12b** | Adjustment for multiple comparisons (if applicable) | Methods: Statistical Analysis |
| **12c** | Methods for additional analyses (subgroups, sensitivity) | Methods: Statistical Analysis |
| **12d** | Any methods to promote transparency (e.g., pre-registration details) | Methods or Appendix |
| **13a** | For each group: N randomized, N who received intended intervention, N analyzed | Results: Participant Flow (Figure 1: Flow Diagram) |
| **13b** | For each group: number and reasons for exclusions and losses to follow-up | Results: Flow Diagram |
| **14a** | Dates defining the periods of recruitment and follow-up | Methods or Results |
| **14b** | Why trial ended or stopped | Results (if applicable) |
| **15a** | Baseline demographic and clinical characteristics, by group | Results: Table 1 (Baseline Characteristics) |
| **15b** | For continuous variables: means (SD); for categorical: counts (%) | Results: Table 1 |
| **15c** | Baseline comparison: were groups comparable? (p-values or equivalence testing) | Results: Table 1 or Discussion |
| **16** | For each primary and secondary outcome: summary data for each group + estimated effect size with CI | Results (Tables or Figures) |
| **17a** | Total amount of missing data per group | Results or Appendix |
| **17b** | Reason for missing data per group | Results or Appendix |
| **17c** | Methods for addressing missing data (intention-to-treat analysis, multiple imputation, etc.) | Methods: Statistical Analysis & Results |
| **18** | Number of participants (denominator) included in each analysis; if denominators changed, explain why | Results (Table footnotes) |
| **19** | All important harms or unintended effects, by group, with denominators | Results: Adverse Events |
| **20** | Summary of results for each primary and secondary outcome | Discussion (opening) |
| **21** | Results in context of other evidence; any pre-specified subgroup or sensitivity analyses | Discussion |
| **22** | Interpretation consistent with trial objectives and results; appropriate caution about inferences | Discussion |
| **23** | Trial design, setting, participants: how do they limit generalizability? | Discussion: Limitations |
| **24** | Costs or resources required by intervention (if applicable) | Discussion or Methods |
| **25** | Registration number and name of trial register; date of registration | Methods or Appendix |

---

## Key Sections (Expanded Guidance)

### Flow Diagram (Item 13a, 13b) — CRITICAL

**What it shows:**
```
                    Enrollment
                        ↓
              [Number screened: N=XXX]
                        ↓
        [Excluded N=XXX (reasons)]
                        ↓
              [Randomized: N=XXX]
              /                    \
    Allocated to           Allocated to
    Intervention           Control
    (N=XXX)                (N=XXX)
         ↓                      ↓
  [Received intervention]  [Received control]
  [N=XXX]                  [N=XXX]
     ↓                         ↓
  [Lost to FU: N=X]        [Lost to FU: N=X]
  [Reasons: ...]           [Reasons: ...]
     ↓                         ↓
  [Analyzed: N=XXX]        [Analyzed: N=XXX]
  [Excluded: N=X (why)]    [Excluded: N=X (why)]
```

**What it must show:**
- Enrolled (screened, eligible)
- Randomized (allocated)
- Intervention group: received intervention (N), lost to FU (N + reasons), analyzed (N)
- Control group: received control (N), lost to FU (N + reasons), analyzed (N)
- Numbers must add up logically

### Randomization (Items 5–7) — CRITICAL

**Must specify:**
1. **Method to generate allocation sequence:** (e.g., random.org, computer-generated, etc.)
2. **Restriction to randomization:** (e.g., stratified by age group, blocked in groups of 4, etc.)
3. **Allocation concealment:** (e.g., sealed envelopes, central randomization, etc.)
4. **Who did the randomization:** (e.g., "Trial statistician, independent of recruitment")

**Example:**
> "A statistician generated a random allocation sequence using random.org, stratified by site (3 strata) with random block sizes of 4 and 6. Allocation was concealed in sealed, opaque envelopes numbered sequentially. Research coordinators at each site enrolled participants and opened envelopes sequentially."

### Baseline Characteristics Table (Item 15) — CRITICAL

| Characteristic | Intervention (N=50) | Control (N=50) | p-value |
|---|---|---|---|
| Age (years), mean (SD) | 45.2 (10.3) | 46.1 (9.8) | 0.68 |
| Female, n (%) | 28 (56%) | 27 (54%) | 0.85 |
| BMI, mean (SD) | 26.4 (3.2) | 25.9 (3.1) | 0.41 |
| Prior diagnosis, n (%) | 12 (24%) | 11 (22%) | 0.82 |

**Interpretation:** p-values indicate baseline comparability. All p > 0.05 suggests good randomization (though p-values are not the only measure of balance).

### Harms / Adverse Events (Item 19)

**Must report:**
- Any serious adverse events (hospitalizations, deaths)
- Any adverse events related to intervention
- Dropout due to adverse events
- For each: numerator (N events) and denominator (N at risk)

**Example:**
> "Intervention group: 3 serious adverse events (1 myocardial infarction, 2 hospitalizations for worsening symptoms) out of 50 participants. Control group: 1 serious adverse event out of 50 participants. No deaths. 4 participants (2 intervention, 2 control) withdrew due to adverse events."

---

## Common Omissions

| Commonly Missing | Why It Matters | Fix |
|---|---|---|
| Flow diagram | Readers can't see attrition; suggests bias | Add: Enrolled → Randomized → Allocated → Followed → Analyzed |
| Randomization method | Can't assess allocation concealment; potential bias | Specify: sequence generation, concealment method, who did randomization |
| Baseline characteristics table | Can't verify randomization worked | Add Table 1 with demographics, baseline outcomes, p-values |
| Blinding description | Can't assess detection bias | State: who was blinded (participant, provider, outcome assessor) |
| Sample size justification | Can't assess if study is underpowered | Report: effect size assumption, α, power, resulting N |
| Missing data handling | Potential bias if not addressed | Report: % missing per group, reasons, method (ITT, LOCF, MI, etc.) |
| Adverse events | Can't assess safety | Report: any serious AEs, relation to intervention, withdrawals due to AE |

---

## References

- **Official CONSORT Statement:** consort-statement.org
- **CONSORT 2010 Explanation & Elaboration:** Schulz et al. (2010). Annals of Internal Medicine.
