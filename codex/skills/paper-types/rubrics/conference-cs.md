# Rubric: CS/Engineering Conference Papers

---

## Dimension 1: Technical Novelty & Contribution Clarity (1–5)

**Definition:** What is the novel contribution? Is it sufficiently clear and significant?

| Score | Anchor |
|-------|--------|
| **5** | Contribution is clearly stated (e.g., "We propose a new loss function that reduces overfitting by X%"). Novelty is evident (not a straightforward application of existing methods). Contribution is significant (advances state-of-the-art, enables new capability, simplifies existing approach, provides new insight). Position relative to prior art is explicit. |
| **4** | Contribution is clear. Novelty is present. Significance is justified. Positioning mostly clear. |
| **3** | Contribution stated but vague or incremental. Novelty is present but modest. Significance unclear. Positioning weak. |
| **2** | Contribution is unclear or appears to be straightforward application of existing methods. Significance not justified. **[MAJOR]** |
| **1** | Contribution is missing, trivial, or already exists in prior work. **[MAJOR]** |

**Reviewer checks:**
- What does this paper do that prior work does not?
- Is the contribution narrow (e.g., "apply method X to domain Y") or broad (e.g., "new method architecture")?
- Does the paper show *why* the contribution matters (does it improve accuracy, speed, interpretability, etc.)?

---

## Dimension 2: Baseline Fairness & Comparison Rigor (1–5)

**Definition:** Are baselines well-chosen, fairly treated, and recent? Are comparisons explicit about conditions?

| Score | Anchor |
|-------|--------|
| **5** | Baselines are state-of-the-art (within last 2 years). Comparison is fair: same data augmentation, hyperparameter tuning effort, hardware, training protocol for all methods. Hyperparameter tuning effort explicitly stated for author's method and baselines. Results table shows all methods with error bars/std (not just author's method). No cherry-picking. |
| **4** | Baselines are recent. Comparison mostly fair. Hyperparameter tuning mentioned. Error bars present for most methods. |
| **3** | Baselines present but may be outdated (3+ years). Fairness not fully discussed. Hyperparameter tuning effort unclear. Some methods lack error bars. |
| **2** | Baselines are old or weak. Fairness is questionable (e.g., author's method tuned more). Selective reporting (error bars only on author's results). **[MAJOR]** |
| **1** | No baselines or unfair comparison (e.g., different training data, different compute budget). **[MAJOR]** |

**Reviewer checks:**
- Are all baselines equally well-known and well-maintained (not comparing to deprecated code)?
- Did author spend same effort tuning baselines as their own method? (Or acknowledge imbalance?)
- Same training/validation/test split for all methods?
- Are confidence intervals or error bars shown for baseline methods, not just the proposed method?

---

## Dimension 3: Experimental Design & Ablation Study (1–5)

**Definition:** Are experiments well-designed? Do ablations isolate contribution?

| Score | Anchor |
|-------|--------|
| **5** | Ablation studies present: each main component of the method is removed or varied, showing its contribution. Ablations are isolated (one change at a time). Ablation table clearly shows contribution of each component. Sensitivity analysis: hyperparameter sensitivity, data size effects, or robustness to perturbations explored. Experiments on multiple datasets (≥3). |
| **4** | Ablation studies present and mostly well-designed. Experiments on 2–3 datasets. Sensitivity somewhat explored. |
| **3** | Ablation study present but may combine multiple changes. Experiments on limited datasets (1–2). Sensitivity not addressed. |
| **2** | Ablation study missing or poorly designed (removes multiple components at once, making contribution unclear). Single dataset only. **[MAJOR]** |
| **1** | No ablation study. Unclear which components contribute to performance. **[MAJOR]** |

**Reviewer checks:**
- Can you identify the contribution of each component from the ablation table?
- Is the full model consistently the best, or do some components sometimes hurt?
- Do results generalize (multiple datasets, or one dataset with train/val/test splits)?
- Are results sensitive to hyperparameters? (Report range or show robustness)

---

## Dimension 4: Statistical Rigor & Reporting (1–5)

**Definition:** Are results reported with sufficient statistics? Multiple seeds? Significance testing?

| Score | Anchor |
|-------|--------|
| **5** | Results averaged over multiple seeds (N≥5) with mean ± std or 95% CI reported. If comparing two methods, significance testing (t-test, sign test) or confidence intervals do not overlap. Exact N of seeds stated. Statistical methodology (e.g., "t-test, two-sided, α=0.05") specified. |
| **4** | Results over multiple seeds; std/CI mostly reported. Significance mostly discussed. N of seeds stated. |
| **3** | Results over some seeds; std/CI occasionally missing. Significance mentioned but not rigorously tested. Seed count vague. |
| **2** | Results from single run or seeds not mentioned. No error bars or CIs. Significance claimed without testing. **[MAJOR]** |
| **1** | No mention of multiple runs. Results presented without any measure of variability. **[MAJOR]** |

**Reviewer checks:**
- Are results reported as "mean ± std" for all methods? (Not just mean)
- Is N of seeds specified (e.g., "results averaged over 10 runs")?
- For claimed improvement, do 95% confidence intervals overlap or not?
- For neural networks: are different random seeds used? (Weight initialization, dropout sampling, data shuffling all matter)

---

## Dimension 5: Dataset Appropriateness & Transparency (1–5)

**Definition:** Are datasets appropriate for the research question? Are they well-documented?

| Score | Anchor |
|-------|--------|
| **5** | Datasets publicly available and cited (with year and repository). Train/val/test split clearly specified (e.g., "70/15/15"). Dataset size (N), class balance (if classification), and any preprocessing described. If using private data, author justifies and describes it. Dataset bias or limitations acknowledged. |
| **4** | Datasets public or justifiable. Splits mostly clear. Size/balance mentioned. Limitations discussed. |
| **3** | Dataset sources vague or unclear. Splits not always specified. Size/balance sometimes missing. |
| **2** | Dataset not fully described. Splits unclear. Private data used without justification. **[MAJOR]** |
| **1** | Datasets unknown or undisclosed. No information on sizes or splits. **[MAJOR]** |

**Reviewer checks:**
- Can readers reproduce this work using the same datasets?
- Is train/val/test split clearly documented (and not data-snooping, e.g., hyperparameter tuning on test set)?
- For imbalanced datasets, are metrics appropriate (accuracy on imbalanced data is misleading; F1, AUROC better)?
- If dataset is novel, is it published or will be published?

---

## Dimension 6: Metrics Appropriateness & Reporting (1–5)

**Definition:** Are metrics appropriate for the task? Are they reported completely?

| Score | Anchor |
|-------|--------|
| **5** | Metrics are appropriate for the task (e.g., F1/AUROC for imbalanced classification, not accuracy; mAP for detection, not accuracy). All relevant metrics reported (not just the one that favors the author's method). Metric definitions provided if non-standard. Justification for metric choice included. |
| **4** | Metrics are appropriate. Most relevant metrics reported. Definitions clear. |
| **3** | Metrics appropriate but incomplete (e.g., accuracy only for imbalanced data). Definitions sometimes missing. |
| **2** | Metric choice questionable for the task (accuracy on imbalanced data). Only favorable metrics reported. Definitions vague. **[MAJOR]** |
| **1** | Metrics inappropriate or misleading. Single metric reported without context. **[MAJOR]** |

**Reviewer checks:**
- Is the task classification/detection/segmentation/regression/ranking? Are metrics aligned?
- For classification: imbalanced classes → F1/AUROC/precision-recall, not accuracy.
- For detection: mAP (mean average precision), IoU (intersection-over-union).
- For regression: RMSE/MAE/R² (are units clear?).
- For NLP: BLEU/ROUGE/BERTScore (and multiple references if paraphrase task).

---

## Dimension 7: Positioning vs. Related Work (1–5)

**Definition:** Is the paper clearly positioned relative to prior art? Differences explicit?

| Score | Anchor |
|-------|--------|
| **5** | Related Work section is organized thematically (not chronologically). For each major prior approach, the paper states: "X proposed method A (accomplishment Y). Our work differs by introducing Z (advantage: W)." Comparison is fair (acknowledges strengths of prior work, not strawman). Recent papers cited. |
| **4** | Related Work organized mostly thematically. Positioning mostly clear. Mostly recent citations. |
| **3** | Related Work present but may be chronological. Positioning somewhat vague. Some citations older. |
| **2** | Related Work is mostly a list ("Smith proposed X, Jones proposed Y…"). Positioning unclear or overstated ("first ever" when similar work exists). **[MAJOR]** |
| **1** | Minimal related work or positioning is absent. Overstatement of novelty. **[MAJOR]** |

**Reviewer checks:**
- Does each paragraph of Related Work argue a point (e.g., "Existing approaches focus on X; few address Y") rather than just listing papers?
- Does the paper explicitly state how it differs from each major prior approach?
- Are recent papers cited (from last 2 years in fast-moving fields like deep learning)?

---

## Dimension 8: Reproducibility & Code/Data Availability (1–5)

**Definition:** Can readers reproduce the work? Are code and data available?

| Score | Anchor |
|-------|--------|
| **5** | Code available (GitHub, GitHub.io, or supplementary materials) with license and README. Dataset available or accessible. Hyperparameters fully specified (learning rate, batch size, optimizer, warmup, etc.). Training time and hardware reported (GPU type, CUDA version, PyTorch version). Random seed(s) specified. Environment (Python version, major library versions) documented. |
| **4** | Code available (or will be released). Hyperparameters mostly specified. Hardware/software versions mentioned. Seeds specified. |
| **3** | Code availability mentioned but incomplete. Hyperparameters partially specified. Software version vague. |
| **2** | Code not available or only partial. Hyperparameters missing. Software/hardware not documented. **[MAJOR]** |
| **1** | No code/data availability statement. Critical hyperparameters missing. Unreproducible. **[MAJOR]** |

**Reviewer checks:**
- If authors claim to release code, is there a timeline (e.g., "upon publication")?
- Are all hyperparameters needed to train the model specified (or in appendix)?
- Are library versions that could affect results mentioned (e.g., PyTorch version changes behavior)?
- Is random seed(s) reported (especially for stochastic methods)?

---

## Dimension 9: Paper Presentation & Figure/Table Quality (1–5)

**Definition:** Is the paper clearly written? Are figures and tables informative?

| Score | Anchor |
|-------|--------|
| **5** | Writing is clear and concise. Figures and tables are self-contained (caption fully explains without reading text). Results table: all methods included, best results bolded, error bars shown. Architecture diagrams are clear (layer names, dimensions, operations labeled). |
| **4** | Writing is mostly clear. Figures/tables mostly self-contained. Presentation good. |
| **3** | Writing is adequate but could be clearer. Figures/tables require text to interpret. Presentation serviceable. |
| **2** | Writing is hard to follow. Figures are uninterpretable or missing key info. Results table lacks error bars or is disorganized. **[MAJOR]** |
| **1** | Writing is poor. Figures are illegible or misleading. Tables are confusing. **[MAJOR]** |

**Reviewer checks:**
- Can you understand the method from the abstract and figures alone?
- Are results figures/tables formatted clearly (legend, axis labels, units)?
- Do figures have captions that explain what is shown and why it matters?
- For architecture diagrams: are layer operations labeled (conv, pool, etc.)?

---

## Dimension 10: Limitations & Honest Discussion of Failure Cases (1–5)

**Definition:** Are limitations acknowledged? Are failure cases or negative results discussed?

| Score | Anchor |
|-------|--------|
| **5** | Limitations section explicitly lists: assumptions (e.g., "assumes labeled data available"), scope constraints (e.g., "evaluated on vision tasks; unknown if applicable to NLP"), and failure modes (e.g., "method struggles with X scenario"). Author discusses when/why method fails. Negative results (if any) are reported. Trade-offs are explicit (e.g., "gains accuracy but increases latency"). |
| **4** | Limitations discussed. Most failure modes acknowledged. Trade-offs mostly explicit. |
| **3** | Limitations mentioned but brief. Some failure modes discussed. Trade-offs implied but not explicit. |
| **2** | Limitations vague or minimized. Failure cases not discussed. Method presented as universally superior. **[MAJOR]** |
| **1** | No limitations section. Failures are hidden or denied. **[MAJOR]** |

**Reviewer checks:**
- Are assumptions about data, task, or deployment explicitly stated?
- If method fails on some datasets or conditions, are these acknowledged?
- Does paper claim "10% improvement" without mentioning that latency doubled (trade-off)?
- Does Discussion mention when/why method might not work?

---

## Scoring Summary

**Accept:** Most dimensions ≥3; no Major issues or only 1 minor Major (easily fixed).  
**Accept with Minor Revisions:** 1–2 Major issues; author fixes in 1 round (e.g., add missing ablation, specify hyperparameters).  
**Major Revisions:** 3+ Major issues or significant flaws (e.g., unfair baselines, no ablation, inadequate datasets).  
**Reject:** Multiple dimension scores of 1, or core flaws (baselines are weak/unfair, contribution is unclear or not novel, reproducibility severely compromised).

---

## Reviewer Guidance

- **Novelty bar:** Don't mistake "incremental improvement" for "not novel." Small improvements that advance the state-of-the-art are publishable if well-executed.
- **Fairness is critical:** Unfair baseline comparison is grounds for major revision or rejection.
- **Ablations matter:** They show *why* the method works, not just *that* it works.
- **Reproducibility:** Code/data availability + hyperparameters + seeds = community impact.
