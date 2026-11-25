# IMRaD: Empirical Research Article

## Structure & Typical Word Proportions

| Section | % | Word Budget (6000-word target) | Content |
|---------|---|------|---------|
| Introduction | 15% | 900 | Context, gap, RQ/hypothesis |
| Methods | 25% | 1500 | Design, participants, procedures, measures, analysis plan |
| Results | 25% | 1500 | Findings presented (tables, figures, statistical summaries) |
| Discussion | 30% | 1800 | Interpretation, implications, limitations, positioning |
| Conclusion | 5% | 300 | Key takeaway, future work |

*Adjust proportions if your paper is shorter or longer; maintain the rough shape.*

---

## Section-by-Section Guidance

### Introduction (~900 words)

**Content sequence:**
1. **Context & significance** (2–3 sentences): Why does this problem matter? What field/audience cares?
2. **Literature landscape** (3–5 paragraphs): What is known? Cite 4–8 key papers. Identify the trend (e.g., "Most prior work focuses on X, but Y is understudied").
3. **The gap** (1 paragraph): What's NOT known? What's the unresolved question or contradiction?
4. **Research question / hypothesis** (1 paragraph, 2–3 sentences): State it clearly. If testing a hypothesis, express as a declarative prediction ("We hypothesize that X increases Y under condition Z").
5. **Significance & implications preview** (1 paragraph): What will this answer change?

**Tense discipline:** Present tense (e.g., "Research shows that…"; "The literature indicates…"). 

**Hedging:** Use "suggest," "indicate," "emerging evidence" (not overconfident; not anemic). Avoid "may" and "might" in Intro — be more direct.

**Citation format:** Pandoc style: `[@surname2024keyword]`.

### Methods (~1500 words)

**Content sequence (adjust per design):**
1. **Study design** (2–4 sentences): Type (e.g., randomized controlled trial, quasi-experimental, cohort), setting, timeframe. If quasi-experimental, explain why randomization wasn't possible.
2. **Participants/sample** (2–3 paragraphs):
   - Inclusion/exclusion criteria (explicit).
   - Recruitment procedure (how did they enter the study?).
   - Sample size & power (if applicable: pre-registered power analysis, effect size, α, power).
   - Demographics (table or 2–3 sentences).
3. **Intervention / independent variable** (if applicable; 2–3 paragraphs):
   - What was manipulated or compared?
   - Dosage, duration, fidelity checks.
   - Control condition (what did controls receive?).
4. **Measures / instruments** (2–3 paragraphs):
   - For each outcome: instrument name, what it measures, range/scoring, reliability (α or ICC), validity evidence if known.
   - Primary vs secondary outcomes (if specified pre-hoc).
5. **Procedure / data collection** (1–2 paragraphs):
   - Timeline (when did measurement occur?).
   - Blinding (who was blinded to condition?).
   - Data collection method (survey, interview, device, observation).
6. **Data analysis** (1–2 paragraphs):
   - Statistical tests planned (regression, t-test, ANOVA, etc.); state before results section.
   - Handling of missing data (listwise deletion, multiple imputation).
   - Significance level (α = 0.05 default, unless pre-registered otherwise).
   - Sensitivity analyses or subgroup analyses planned.
7. **Ethics** (1 paragraph): IRB approval number; informed consent procedure; any special protections.

**Tense discipline:** Past tense ("We recruited…"; "Participants completed…"; "Data were analyzed…").

**Detail level:** Enough that another researcher could replicate it.

**Red flags:**
- Vague methods ("participants filled out a survey"—which survey? how scored?).
- Unspecified analysis plan (appears to have been decided after seeing data).
- No mention of confounders or threats to validity.

### Results (~1500 words)

**Content sequence:**
1. **Participant flow** (1 paragraph or flow diagram):
   - N recruited, N enrolled, N completed, N analyzed (include dropouts + reasons if notable).
   - Any missing data rates.
2. **Descriptive statistics** (table or 1 paragraph):
   - Baseline characteristics (means ± SD or count/%).
   - If groups: demonstrate baseline comparability (or report any imbalances).
3. **Primary outcome(s)** (2–4 paragraphs + 1–2 figures/tables):
   - State the result (e.g., "Mean X was significantly higher in Group A [M = 10.5, SD = 2.1] vs Group B [M = 8.3, SD = 2.4], t(98) = 3.2, p = 0.002, d = 0.64").
   - Include 95% CIs when possible.
   - Report effect sizes (Cohen's d, r, etc.), not just p-values.
   - If multiple comparisons, note any corrections (Bonferroni, etc.).
4. **Secondary outcome(s)** (1–2 paragraphs + tables):
   - Same format as primary; mark post-hoc tests clearly.
5. **Subgroup / sensitivity analyses** (1 paragraph or table):
   - If applicable: "In the subset of older participants (n=45), the effect remained significant…"
6. **Adverse events / unexpected findings** (1 paragraph if relevant):
   - Any harms, dropouts, or surprises.

**Tense discipline:** Past tense ("Results showed…"; "The effect was…").

**What NOT to do:**
- Interpret in Results (e.g., "This shows that X causes Y"—save that for Discussion).
- Repeat all numbers from tables in text (refer to the table; highlight the key pattern).
- Use p < 0.05 as the sole arbiter of importance (report the effect size and CI; a tiny p-value with a tiny effect is not impactful).

**Figures & tables:**
- Figures: for trends, distributions, complex patterns (e.g., interaction plots, learning curves, heatmaps).
- Tables: for descriptive data, statistical summaries, results by group.
- Captions must be self-contained and interpretable without reading the text.

### Discussion (~1800 words)

**Content sequence:**
1. **Key finding summary** (1 paragraph): Restate your primary result in plain language. Connect directly to your hypothesis ("We hypothesized that X would increase Y; results confirmed this hypothesis").
2. **Interpretation & mechanism** (2–3 paragraphs): 
   - Why did this happen? 
   - Cite similar findings in the literature (not just your work).
   - If results contradict prior work, explain why (sample difference, context, timing, measurement).
3. **Implications** (1–2 paragraphs):
   - Practical implications (e.g., for policy, treatment, practice).
   - Theoretical implications (what does this teach us about the mechanism?).
4. **Limitations** (1–2 paragraphs; MUST exist):
   - Sample size or characteristics (e.g., "Participants were predominantly white, limiting generalizability").
   - Measurement (e.g., "Self-report may have introduced social-desirability bias").
   - Design (e.g., "Lack of randomization prevents causal inference").
   - Be honest; don't hide them.
5. **Alternative explanations** (1 paragraph, if needed):
   - Could the result be due to confounding, selection bias, or measurement error? Address it.
6. **Future research** (1 paragraph):
   - What should next studies examine?
   - What questions remain open?
7. **Conclusion** (brief; roll into Discussion or separate).

**Tense discipline:** Present tense for general statements ("The literature suggests…"), past tense for your results ("We found…"). Hedging increases here: "likely," "suggest," "may indicate" (you're interpreting, not stating absolute truth).

**Debate convention:** 
- Avoid phrases like "This proves…" or "It is clear that…" (overclaimed).
- Use "This finding suggests…," "Our results indicate…," "One interpretation…"

**Anticipate the reviewer:**
- Rare or surprising result? Explain why your design supports it, not confounding.
- Negative result? Discuss statistical power and why non-significance is informative.
- Modest effect? Discuss practical significance, not just statistical.

### Conclusion (~300 words)

**Content:**
1. One-sentence summary of the key finding.
2. Why it matters (implications reiterated briefly).
3. Next steps (if not already in Discussion).
4. Final sentence: a strong close (e.g., "These results provide evidence that X is an effective approach and warrant further investigation").

**Tense:** Present tense (general claims about the field).

---

## Hypothesis ↔ Findings Tracing

**Golden rule:** Every hypothesis stated in Introduction must appear in Results and be addressed in Discussion.

**Example chain:**
- **Intro:** "We hypothesize that deep learning models with architectural feature X outperform baseline models on dataset Y."
- **Results:** "CNN with feature X (M acc = 94.2%) significantly outperformed the baseline (M acc = 87.3%), p < 0.001."
- **Discussion:** "The hypothesis was confirmed: feature X improved model accuracy, likely because [mechanism]. This aligns with prior findings by [citation]."

Use `python scripts/word_budget.py --rq-trace` to verify this chain in your draft.

---

## Word Budget Formulas

**For a 6000-word target:**
- Intro: 900 words → ~4–6 paragraphs, ~2 pages.
- Methods: 1500 words → ~6–8 paragraphs, ~2.5 pages.
- Results: 1500 words → 1 flow diagram + 2–3 tables/figures + 4–5 paragraphs, ~2.5 pages.
- Discussion: 1800 words → ~7–9 paragraphs, ~3 pages.
- Conclusion: 300 words → ~1 paragraph, 0.5 page.

**Scaling for longer papers (8000 words):**
- Multiply each by 1.33.
- Intro: 1200 words; Methods: 2000; Results: 2000; Discussion: 2400; Conclusion: 400.

**Scaling for shorter papers (4000 words, e.g., some conference formats):**
- Multiply each by 0.67.
- Intro: 600; Methods: 1000; Results: 1000; Discussion: 1200; Conclusion: 200.

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Methods so vague a replication is impossible | Include all details: instrument names, item counts, scoring procedures, statistical software versions, random seeds if applicable |
| Results list every statistical comparison (p-values dump) | Highlight the key pattern; use tables; report effect sizes alongside p-values |
| Discussion over-interprets a single result | Ground interpretation in the full literature; cite conflicting findings; address limitations openly |
| Hypothesis unstated or buried | State it clearly in Intro as a single sentence or short paragraph; repeat in Results |
| Intro literature review lacks synthesis (just a list) | Organize by theme, not chronology; each paragraph should argue a point, not list papers |
| No table of means/SD by group | Add it (essential for readers to understand the raw pattern before seeing p-values) |

---

## Reporting Standards

**Statistical reporting (APA 7):**
- Always report: M (mean), SD (standard deviation), N (sample size), test statistic (t, F, r), degrees of freedom, p-value, 95% CI when possible, effect size (d, r, η²).
- Example: "t(58) = 2.41, p = 0.019, d = 0.63, 95% CI [0.12, 1.13]"

**For ML / computer vision papers:**
- Report metrics over multiple seeds: "F1 = 0.87 ± 0.03 (n=5 seeds)".
- Name baselines explicitly (don't just say "baseline model").
- Report ablations in a table (method × ablation combination).
- Cite dataset sources; link to code if available.

---

## References & Links

- STROBE Statement (observational studies): https://www.strobe-statement.org/
- CONSORT Statement (RCTs): https://www.consort-statement.org/
- APA 7 Reporting Standards: https://apastyle.apa.org/
