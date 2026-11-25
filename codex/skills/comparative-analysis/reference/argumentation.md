# Argumentation: Toulmin Logic and Causal Discipline

Mapping claims to evidence, gap reasoning with verification checklists, and correlation-vs-causation phrasing.

## Toulmin model: Claim → Ground → Warrant

Every empirical argument has three parts:

1. **Claim** (conclusion): "Our method is more accurate than baselines."
2. **Ground** (data): Table 1 shows accuracy of 0.912 vs 0.876–0.891.
3. **Warrant** (rule connecting ground to claim): "Higher accuracy on a standard benchmark indicates superior method performance."

### Structure template

```
CLAIM: [Your proposition]
├─ GROUND: [Evidence from data, experiments, or literature]
│  └─ Source: [Table X, Figure Y, citation]
├─ WARRANT: [Rule or principle that licenses the inference]
│  └─ Justification: [Why this rule applies here]
└─ QUALIFIER: [Scope limitation: "in this context", "for this dataset", etc.]
```

### Worked example 1: Method comparison

**Claim:** "Our CNN architecture is more robust than ResNet-50 to adversarial perturbations."

**Ground:**
- ResNet-50 fooling rate on FGSM attack (ε=0.3): 73% (1000 random images)
- Our method fooling rate: 28%
- Difference: 45 percentage points

**Warrant:** "Lower fooling rate indicates higher adversarial robustness. Measuring on the same attack (FGSM) and same image set ensures fair comparison."

**Qualifier:** "on FGSM attacks at ε=0.3. Robustness to PGD attacks is not evaluated."

**Full paragraph:**
"Our method shows significantly higher adversarial robustness than ResNet-50 (Table 4). On FGSM attacks (ε=0.3), ResNet-50 is fooled 73% of the time, whereas our method is fooled only 28%, a 45-point improvement. This suggests our method's attention mechanism provides an implicit defense mechanism. However, this evaluation is limited to FGSM; robustness to stronger attacks (PGD, AutoAttack) remains unknown."

### Worked example 2: Generalization claim

**Claim:** "Our method generalizes across diverse image domains."

**Ground:**
- ImageNet-1K: 92.1% accuracy (standard natural images)
- Medical imaging (ChexPert): 89.3% accuracy
- Satellite imagery (RESISC45): 87.6% accuracy
- Average: 89.7% vs baseline average 87.1% (+2.6% points)

**Warrant:** "Performance consistency across diverse datasets indicates domain generalization. We tested on three orthogonal domains (natural, medical, satellite) with different visual characteristics."

**Qualifier:** "Among three image classification domains. Generalization to video, audio, or text is not tested."

**Full paragraph:**
"Our method demonstrates strong generalization across diverse image domains (Table 5). On ImageNet-1K (natural images), we achieve 92.1%; on ChexPert medical imagery, 89.3%; on RESISC45 satellite imagery, 87.6%. This consistency (89.7% average ± 2.0%) outperforms baselines (87.1% ± 2.8%), suggesting our method's robustness to domain shift. The improvement is largest on out-of-distribution data (satellite imagery: +2.3% vs baseline), indicating robustness benefits beyond natural images. Limitations: generalization to video or audio domains is untested."

## Gap reasoning: "No prior work combines X+Y"

### Three types of gaps

1. **Empirical gap:** Method exists, but not tested on this dataset/condition
   - "No prior work has evaluated attention mechanisms on 32×32 images (CIFAR-10)."
   - Verification: Search for [method] + [dataset] in Google Scholar

2. **Methodological gap:** Two techniques exist separately, but not combined
   - "Vision Transformers (2021) enable global attention; efficient CNNs (EfficientNet) prioritize speed. Their combination under low-resource constraints is unexplored."
   - Verification: Search for "efficient transformer" + "CNN hybrid" + relevant terms

3. **Theoretical gap:** A principle or mechanism is known, but not formally analyzed
   - "While attention mechanisms have been used in vision, the theoretical justification for [specific property] is missing."
   - Verification: Citation search for formal analysis + mechanism

### Verification checklist for gap claims

Before claiming "no prior work exists":

**Broad search:**
- [ ] Google Scholar search: [X] + [Y] (direct combination search)
- [ ] Semantic Scholar: same search
- [ ] arXiv (last 3 years): catch recent preprints
- [ ] Related work section of 3–5 recent papers in the area
- [ ] Check citations in recent survey papers

**Specific databases:**
- [ ] Conference proceedings (NeurIPS, ICML, CVPR, ACL, etc.)
- [ ] Specialized venues (domain-specific journals)
- [ ] Preprint servers (arXiv, bioRxiv, medRxiv)
- [ ] Technical reports from companies (Google, Meta, OpenAI, etc.)

**Negative results:**
- [ ] List papers you checked but that DON'T combine X+Y (show work)
- [ ] Note why each related paper doesn't fill the gap

**Regional/language gaps:**
- [ ] If topic is geographically localized, search regional databases
- [ ] If relevant work in Turkish/Chinese/etc., search those sources

### Example: proper gap claim

**Weak:** "No one has used attention in computer vision."
**Problem:** Patently false; Citation-based reasoning obvious.

**Strong (with verification):**
"While attention mechanisms have been extensively studied in vision (Dosovitsky et al. 2021, Vaswani et al. 2017), their application to few-shot learning with external memory has been limited. Prototypical Networks (Snell et al. 2017) use attention for classification but not for memory management. MAML (Finn et al. 2017) meta-learns but without attention. A hybrid approach—combining attention-based memory with meta-learning for few-shot learning—has not been explored in prior work. Our search of NeurIPS/ICML/CVPR (2018–2024) and arXiv (keywords: 'few-shot learning', 'attention', 'meta-learning') found no such combination."

### Checklist for gap reasoning in Discussion

When writing a gap claim:

- [ ] Describe the gap specifically (not vague "unexplored")
- [ ] Cite related work that comes close but doesn't fill the gap
- [ ] Explain why the gap exists (different constraints, different era, different problem setup)
- [ ] Document your search strategy (show that absence is not from lack of trying)
- [ ] Acknowledge partial overlaps (if prior work covers 80% of your novelty, say so)

## Causal language and study design

### Rule: Study design → licensed verbs

Different experimental designs license different causal language. Use this table when writing Results/Discussion.

| Study design | Licensed verbs | Example | Licensed verbs | Unlicensed |
|---|---|---|---|---|
| Observational (cohort, case-control, survey) | is associated with, correlates with, predicts | "Age is associated with income in this cohort." | "may contribute to" | "causes", "leads to" |
| Randomized Controlled Trial (RCT) | causes, improves, increases, decreases | "Cognitive behavioral therapy causes reduction in anxiety (p<0.001)." | — | "may be associated with" |
| Ablation study (ML) | contributes, enables, removes, affects | "Attention contributes +2.1% accuracy; removing it decreases F1 by 1.8%." | "appears to be important for" | "is necessary for", "ensures" |
| Mechanistic model or theory | enables, allows, facilitates, governs | "This architecture enables efficient long-range dependencies." | — | "guarantees", "proves" |
| Case report | describes, demonstrates, illustrates | "This case demonstrates an atypical presentation of X." | — | "proves", "shows that X causes" |
| Qualitative interview | reports, suggests, indicates | "Participants reported difficulty with feature X." | "may indicate that" | "shows" |
| Time-series analysis (temporal associations) | precedes, predicts, is correlated with over time | "Increases in policy X precede increases in outcome Y by 6 months." | "may contribute" | "causes" |

### Phrasing bank: Correlation ≠ Causation

**Correct observational phrasing (no randomization):**

```
✓ "Sleep deprivation is associated with lower test performance."
✓ "Countries with higher education spending have higher test scores (r=0.68)."
✓ "In this population, coffee consumption predicts alertness levels."
✓ "There is a positive correlation between exercise frequency and mood."
✓ "After controlling for socioeconomic status, race is still associated with health outcomes."

✗ "Sleep deprivation causes lower test performance."
  (confounders: illness, stress, caffeine use)
✗ "Increasing education spending causes higher test scores."
  (confounders: wealth, prior achievement levels)
```

**Correct RCT phrasing (randomization):**

```
✓ "The intervention caused a 12-point increase in test scores (95% CI: 8–16)."
✓ "Cognitive behavioral therapy significantly improves anxiety symptoms (p<0.001, Cohen's d=1.2)."
✓ "Participants receiving the treatment showed 40% higher recovery rates (RR=1.40, 95% CI: 1.15–1.71)."
✓ "Randomization to the intervention group led to weight loss of 5 kg on average."

✗ "Cognitive behavioral therapy may improve anxiety." (you have evidence; be direct)
✗ "The intervention appears to increase test scores." (RCT provides causal evidence; state it clearly)
```

**Correct ML ablation phrasing:**

```
✓ "Removing attention decreases accuracy by 2.1% (p<0.01)."
✓ "The attention mechanism contributes approximately 2.1% to the model's accuracy."
✓ "Focal loss is important for handling class imbalance; ablating it reduces F1 by 1.8%."
✓ "Adding this component enables the model to process longer sequences."

✗ "Attention is necessary for high performance." (only true on this dataset/task)
✗ "Focal loss solves the class imbalance problem." (it helps; problem not "solved")
✗ "This attention mechanism causes better generalization." (you showed accuracy gains; causal mechanism unclear)
```

**Hedging for mechanistic claims (when mechanism is speculated):**

```
✓ "We hypothesize that the attention mechanism improves accuracy by emphasizing key spatial regions."
✓ "These results suggest that our method's gains may stem from better feature alignment."
✓ "One explanation for the improvement could be that positional encoding helps the model..."
✓ "The mechanism underlying this improvement remains unclear; future work should investigate whether..."

✗ "Attention works by focusing on salient regions." (true in general; you haven't proven YOUR specific mechanism)
```

## Handling contradictory findings

### Pattern: Find, acknowledge, explain, test

When you encounter conflicting evidence in literature:

1. **Find it:** "Study X found opposite results."
2. **Acknowledge it:** Don't dismiss or minimize.
3. **Hypothesize why:** Propose a mechanism for the difference.
4. **Test it (if possible):** Gather data to adjudicate.

### Example: Handling contradiction

**Situation:** You claim attention helps; prior work says it hurts on small images.

**Weak response (strawman):**
"Zhang et al. (2022) found attention hurts performance, but their setup was non-standard."
→ Problem: Dismissive; appears to strawman the opposing finding.

**Strong response (steel-manning):**
"While Zhang et al. (2022) reported that attention mechanisms hurt performance on CIFAR-10 (32×32 images), our ImageNet results show +2.3% improvement. We hypothesize the difference arises because:
1. **Image size:** CIFAR-10 uses 32×32 images; ImageNet uses 224×224. With only 1024 pixels, attention mechanisms may overfit.
2. **Dataset size:** CIFAR-10 has 50K training images; ImageNet has 1.2M. Larger data provides more context for attention to learn.

To test this hypothesis, we evaluate our attention mechanism on CIFAR-10 (Table 4), restricting the method to match Zhang et al.'s setup exactly. We observe a smaller improvement (+0.8%, not statistically significant), consistent with their findings. This supports our hypothesis that attention gains are dataset/image-size dependent."

**Key elements:**
- ✓ Respect the prior finding (don't dismiss)
- ✓ Propose a testable mechanism (size, dataset, constraints)
- ✓ Test it if feasible (Table 4 replicates their setup)
- ✓ Synthesize findings (both findings are "true" under different constraints)

### Checklist for addressing contradictions

When literature contradicts your findings:

- [ ] Cite the contradictory work explicitly
- [ ] State their findings accurately (no strawman)
- [ ] Identify differences in setup (dataset, model, training)
- [ ] Propose a mechanism for the difference
- [ ] Design an experiment to test the hypothesis (if feasible)
- [ ] Update your claims to reflect the boundary conditions
  - Instead of: "Attention improves accuracy"
  - Say: "Attention improves accuracy on large images (224×224+); effects are neutral on small images (32×32)"

## Warrant types: Why does this evidence support that claim?

| Type | Warrant | Example |
|---|---|---|
| **Statistical** | "If p < 0.05, we reject the null hypothesis." | "The t-test yielded p=0.003, so the difference is statistically significant." |
| **Methodological** | "A randomized trial provides causal inference." | "Because we randomized, we can conclude X causes Y." |
| **Domain principle** | "In machine learning, lower loss = better model." | "Cross-entropy loss decreased from 0.45 to 0.38, indicating improved fit." |
| **Measurement validity** | "Confusion matrix on a held-out test set measures true accuracy." | "Test accuracy of 92% reflects real-world performance (unbiased estimate)." |
| **Comparative fairness** | "Equal tuning budget ensures fair baseline comparison." | "Baselines received the same 50 hyperparameter trials, so accuracy differences reflect method quality." |

### Weak warrants vs strong warrants

**Weak warrant (unstated):**
"Our method achieves 92% accuracy. Therefore, it's the state-of-the-art."
→ Missing warrant: Why does 92% accuracy imply SOTA? On what benchmark? Compared to what?

**Strong warrant (explicit):**
"Our method achieves 92% accuracy on ImageNet-1K, a standard benchmark. This outperforms published baselines (ResNet-50: 76.2%, EfficientNet-B0: 78.8%), all evaluated under identical preprocessing and augmentation (fair comparison). We therefore conclude our method advances the state-of-the-art on this benchmark."
→ Warrant: Standard benchmark + fair comparison + cited baselines = warrant is explicit

## Summary: Building a defensible claim

Every major claim in your paper should follow this structure:

```
CLAIM: [Your proposition — state it clearly]

GROUND: [Data or evidence]
  - Table/Figure: [citation to evidence]
  - Scale: [effect size, confidence intervals, number of replicates]

WARRANT: [Why does this evidence support the claim?]
  - [Principle or rule that connects ground to claim]
  - [Why it applies here]

QUALIFIER: [Scope limitation]
  - "on this benchmark"
  - "for this dataset"
  - "in this setup"

ACKNOWLEDGMENT OF LIMITS: [What remains unknown or untested?]
  - "Generalization to [other setup] is untested."
  - "Mechanism underlying this improvement remains unclear."
  - "Further work should investigate [open question]."
```

**Checklist before finalizing a major claim:**

- [ ] Claim is specific (not vague like "performs well")
- [ ] Ground is cited (table, figure, data)
- [ ] Warrant is explicit (rule that licenses the inference)
- [ ] Qualifier is stated (scope limitation)
- [ ] Acknowledges limits (what's not tested/known)

