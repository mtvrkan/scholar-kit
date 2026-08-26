# Synthesis — Integrating Evidence Across Sources

**Synthesis ≠ annotated bibliography.** An annotated bibliography summarizes each paper individually. Synthesis *integrates* findings across papers to answer your research questions, identify patterns, note gaps, and reveal conflicts.

This file teaches synthesis patterns and the discipline that separates reviewer-level work from AI-generated checklists.

---

## The Core Rule: ≥2 Sources Per Paragraph

**If a paragraph cites only one source, it is a summary, not a synthesis.** The moment you cite a second source, you have created a relationship:

- **Confirmation:** "Both Smith (2023) and Jones (2022) find that CNN outperforms RNN on time-series data."
- **Conflict:** "Smith reports 94% accuracy, while Jones reports 87%; the difference may reflect dataset size (2M vs 50k samples)."
- **Chronological evolution:** "Early work (2015–2018) focused on raw signal input; recent papers (2019–2024) extract features first."
- **Methodological contrast:** "Signal-processing baselines achieve 78% accuracy (Davis et al.), whereas deep learning averages 92% (10-paper analysis)."

This rule prevents the "list of papers" disease.

---

## Five Synthesis Patterns

### 1. Thematic Synthesis (Most Common)

Group papers by concept or result type. Organize your synthesis section around themes.

**Structure:**
```
## Synthesis: Fault Detection Methods

### Deep Learning Architectures
Five papers applied CNNs to bearing fault detection. Smith et al. (2023) 
and Kaya et al. (2023) both report >95% accuracy using 1D convolutions on 
raw vibration time-series [Strength 5, SCI-E Q1]. In contrast, Jones (2022) 
achieved 89% with a manually-engineered feature extractor [Strength 3, arXiv]. 
The 6% gap likely reflects: (a) dataset size (Jones used <50k samples; Smith 
used 2M), (b) validation protocol (Jones used simple train/test split; Smith 
used nested cross-validation). Evidence converges on: CNN + large dataset + 
rigorous validation = state-of-the-art.

### Transfer Learning Approaches
Three papers explored transfer learning for bearing diagnostics. Brown et al. 
(2023) fine-tuned a pre-trained ResNet50 on bearing data, achieving rapid 
convergence [Strength 4, Q1]. Wilson (2022) used a domain-adaptation approach, 
addressing distribution shift between lab-collected and industrial bearings 
[Strength 3, Q2]. Neither paper directly compared transfer vs. training-from-scratch; 
a gap in the literature.

### Open Questions
- Optimal transfer-learning source (ImageNet vs. bearing-specific pretraining?)
- Performance on degraded-bearing data vs. early-failure scenarios
```

**Advantage:** Readers see *landscape* of methods and understand gaps.

---

### 2. Chronological Synthesis

Trace the evolution of the field. How has thinking/methods changed?

**Structure:**
```
## Evolution of Bearing Fault Diagnosis

**Precomputation Era (1995–2010):** Classical signal processing dominated. 
Davis et al. (1998) and Smith (2005) reported wavelet and Fourier-based 
feature extraction, with SVM classifiers achieving 85–90% accuracy 
[Strength 5, seminal work; Strength 4, follow-up].

**Machine Learning Era (2010–2018):** Researchers applied random forests 
and gradient boosting. Brown et al. (2012) reported 92% accuracy on a 
public bearing dataset, a notable improvement over wavelets 
[Strength 4, influential]. The field converged on: automated feature 
selection > handcrafted features.

**Deep Learning Breakthrough (2015–present):** CNN adoption exploded. 
Kaya et al. (2020) and Wilson et al. (2021) independently discovered that 
1D convolutions on raw signals outperformed all prior approaches, achieving 
96%+ accuracy [Strength 5, multiple confirmations, Q1 venues]. Ablation 
studies revealed: depth matters (≥4 layers), but extreme depth (>20 layers) 
adds minimal gain.

**Current Frontier (2023–2024):** Attention mechanisms and domain adaptation. 
Taylor et al. (2024) apply vision transformers to bearing diagnostics 
[Strength 3, arXiv, preliminary]; early results (94%) are competitive with CNNs 
but no clear advantage yet.
```

**Advantage:** Readers see *trajectory* of the field and where it's heading.

---

### 3. Methodological Synthesis

Compare *how* studies answer the same question. Differences in method explain differences in findings.

**Structure:**
```
## Methodological Comparison: Training Data Volume

The literature shows high variance in dataset size, explaining result disparities.

Smith et al. (2023) use a proprietary industrial database (2M bearing 
operating hours) and report 96% test accuracy [Strength 5; access: restricted]. 
Jones et al. (2022) use the open CWRU Bearing Dataset (1,000 samples) and 
report 92% accuracy with the same CNN architecture [Strength 4; access: public]. 
The 4% gap correlates with a 2,000× difference in training data.

Brown (2021) directly studies this scaling relationship on the same architecture: 
100 samples → 78% acc; 1,000 samples → 88% acc; 100,000 samples → 95% acc 
[Strength 4; excellent controls]. This suggests: deep learning gains saturate 
above 50k–100k samples for bearing diagnosis.

**Implication:** Comparisons of "CNN vs. RNN" in the literature conflate two 
variables: architecture *and* dataset size. Controlled comparisons are rare.
```

**Advantage:** Readers understand *which differences matter* and when to trust comparisons.

---

### 4. Conflict Mapping Synthesis

When studies contradict, *explain why*.

**Structure:**
```
## Conflicting Evidence: Transfer Learning Effectiveness

Two camps have emerged with divergent findings.

**Optimistic camp:** Smith et al. (2023) and Davis (2022) report that 
fine-tuning ImageNet pre-trained ResNet50 reduces training time by 10× and 
improves accuracy by 3–5% vs. training from scratch [Strength 4; Q1 venues; 
datasets: CWRU + proprietary]. Both use industrial-setting validation.

**Skeptical camp:** Jones (2021) and Wilson (2020) find that transfer learning 
provides no significant benefit (≤1% accuracy gain; within noise bounds) and 
adds implementation complexity [Strength 4; Q2 venues; datasets: lab-collected, 
imbalanced]. Both use conservative statistical testing (significance: p<0.05).

**Reconciliation:** The optimistic camp's datasets are larger (>50k samples) 
and represent true domain shift (ImageNet → bearings). The skeptical camp uses 
smaller datasets (<10k samples) where transfer learning overfits. Our own 
evidence card analysis reveals: transfer learning helps when (a) target dataset 
<5k samples AND (b) source domain is distant from target. Below this threshold, 
training from scratch converges equally fast.

**Recommendation:** Cite both findings; in your Methods, specify your data 
regime and justify your transfer-learning choice.
```

**Advantage:** Readers see that "conflicting literature" is often reconcilable via careful reading.

---

### 5. Meta-Synthesis (Quantitative Across Many Papers)

When you have 20+ papers with similar metrics, summarize the distribution.

**Structure:**
```
## Performance Landscape: CNN-Based Bearing Diagnosis Across 18 Studies

We extracted accuracy/F1 scores from 18 empirical papers using CNN-based 
diagnosis on bearing datasets (2015–2024). Here's the landscape:

**Accuracy distribution (n=18):**
- Median: 94.2%
- Range: 78% (Jones, small dataset) to 98.1% (Smith, large proprietary dataset)
- IQR: 91–96%

**Factors explaining variance (via card metadata analysis):**

*Training set size (r = 0.67, strong):*
- <10k samples: median 87% acc (n=4)
- 10k–100k: median 92% acc (n=7)
- >100k: median 96% acc (n=7)

*Validation protocol (rigorous vs. simple):*
- Nested cross-validation (Strength 5): median 93% acc (n=8)
- Simple train/test split (Strength 3): median 91% acc (n=6)
- ~2% difference attributable to overfitting in looser protocols

*Architecture depth:*
- 2–4 layers: median 91% acc (n=5)
- 5–8 layers: median 94% acc (n=9)
- >8 layers: median 94.3% acc (n=4)
- Depth matters up to ~6 layers; beyond that, diminishing returns.

**Conclusion:** 94% accuracy is the "typical" CNN result on public bearing datasets 
with standard validation. Achieving 96%+ requires large proprietary data or 
specialized preprocessing. Interestingly, no recent paper (2023–2024) exceeds 
Smith et al. (2020)'s 98.1% record, suggesting a ceiling has been reached.
```

**Advantage:** Quantitative summary reveals true state of the art without cherry-picking.

---

## Synthesis Workflow

### Step 1: Organize Evidence Cards by RQ & Theme

```bash
python scripts/evidence_db.py query --tags rq1 --type finding --min-strength 3
# Returns: all high-quality findings relevant to RQ1

python scripts/evidence_db.py conflicts
# Returns: cards that contradict each other → synthesis material
```

### Step 2: Lay Out Paragraphs by Theme

For each synthesis paragraph, identify:
1. **Primary sources** (2–5 papers): directly address the theme
2. **Methodology notes:** what differs between them?
3. **Synthesis claim:** what do they collectively show?

Write in this order:
1. State the theme/finding
2. Cite sources (e.g., "Smith and Jones both find X")
3. Compare/contrast (e.g., "but they diverge on Y because of Z")
4. Explain the variance
5. Close with a synthesis statement (e.g., "Evidence suggests X holds under conditions Y and Z")

### Step 3: Check for One-Source Paragraphs

Search your draft for paragraphs with only one citation. Rewrite:
- **Option A:** Add a second source (find a paper that confirms or contradicts)
- **Option B:** Reframe as a critical detail (move to Methods section)
- **Option C:** Delete (if it's just background trivia)

Example rewrite:
```
❌ (One source) "CNN has been applied to bearing fault diagnosis. 
   Smith et al. (2023) report 96% accuracy using a 1D CNN on vibration signals."

✅ (Two sources) "CNN-based bearing fault diagnosis has become dominant. 
   Smith et al. (2023) and Kaya et al. (2023) independently report >95% 
   accuracy, convergence on similar architectures (4–6 conv layers), and 
   the importance of data quantity (>50k samples). Davis (2020), using 
   <5k samples, achieved only 87% with the same architecture—a gap attributable 
   to insufficient training data."
```

---

## Red Flags (What *Not* to Do)

| Anti-Pattern | Why It Fails | Fix |
|---|---|---|
| **"Many studies show..."** without citing specifics | Vague; no evidence chain; hard to verify | Name specific studies: "Smith et al. (2023), Kaya et al. (2023), and Jones (2022) report..." |
| **Paragraph with 1 citation** | Summary, not synthesis | Add a second source and compare |
| **Listing papers without integration** | Annotated bibliography, not synthesis | Synthesize: find a relationship between papers (agreement, disagreement, evolution) |
| **Citing papers for methodology without results** | Misses the synthesis opportunity | Cite for both method and result; compare results across methods |
| **"According to X, this is important" without contrast** | No evidence of thought; just narration | Compare: "X emphasizes importance; Y disagrees; the field consensus is…" |
| **Ignoring conflicting evidence** | Intellectually dishonest; weak paper | Acknowledge and reconcile conflicts (explain divergence; decide which is stronger) |

---

## Template: Synthesis Paragraph

Use this template to start; then iterate:

```markdown
[Theme: ___________]

[Setting: X studies address this theme. Mention number/years range.]
Smith et al. (2023), Kaya et al. (2023), and Brown (2022) all apply [Method] 
to [Problem]. They report converging results: [Metric] ranges from [range] 
[Strength 5, 4, 3 notes].

[Variance: What differs between the papers? Why?]
However, [Source 1] uses [X] while [Source 2] uses [Y]. This difference 
explains the [result difference]: [Source 1] achieved [R1]; [Source 2] achieved [R2]. 
[Explain: Was it dataset size? Validation? Architecture choice?]

[Synthesis statement: What does this collectively mean?]
Evidence suggests that [Method] works reliably under [Conditions], achieving 
[typical Result]. The outliers (e.g., [Source 3]'s [unusual result]) are 
explainable by [reason], not a fundamental limitation.
```

---

## Practical Tips

1. **Start with thematic synthesis** — it's easiest to learn.
2. **Create a matrix:** rows = papers, columns = methods/results/dataset/venue quality. Patterns jump out.
3. **Use evidence cards with `conflicts_with` field:** the kit surfaces contradictions for you.
4. **Iteratively refine:** write a rough thematic synthesis first; then look for chronological or methodological angles to deepen it.
5. **Quantify when possible:** "10 of 18 papers report >94% accuracy" beats "most papers report high accuracy."

---

## See Also

- **evidence_db.py query** — retrieve cards by RQ/tag/strength; use to gather synthesis material
- **evidence-cards skill** — understand card schema, including `conflicts_with`
- **literature-review skill** — full review workflow; synthesis is Step 8
- PRISMA 2020 synthesis guidance: https://www.prisma-statement.org/
