---
name: comparative-analysis
description: Use when designing comparisons, analyzing findings against literature, building argument structures, or evaluating methods — when questions arise about criteria selection (what should I compare on?), trade-off framing, fair baselines, synthesis of conflicting evidence, gap reasoning (what prior work is missing?), causal vs correlational claims, or when a Discussion draft needs rigorous comparison logic. Consumed by synthesis step, Discussion drafting, and reviewer-critic's comparison rubric.
---

# Comparative Analysis: Expert-Grade Reasoning

Master patterns for building sound comparisons, analyzing trade-offs, and argumentation in academic writing.

## Pre-comparison discipline

### Explicit criteria before comparison

**Rule:** Define your comparison criteria BEFORE building the table.

**Wrong workflow:**
1. Gather methods A, B, C from literature
2. Build table with whatever metrics are available
3. Claim "our method is better because it has highest accuracy"

**Right workflow:**
1. State the research question: "How does our segmentation method compare to state-of-the-art under resource constraints?"
2. Define criteria that matter for THIS question:
   - Accuracy (Dice coefficient)
   - Speed (inference time per image)
   - Model size (parameters)
   - Memory requirement (peak RAM during inference)
3. Only then: gather methods that can be fairly compared on these criteria
4. Build table with explicit criteria order

### Criteria-weighting justification

When you prioritize some criteria over others, state why explicitly.

```
Justification for comparison criteria (medical imaging context):
- Primary: Dice coefficient (clinical accuracy — non-negotiable)
- Secondary: False positive rate (safety: wrong detections can lead to unnecessary surgery)
- Tertiary: Inference time (practical: must be <5 seconds per CT scan)
- Not evaluated: Model size (GPUs are available; computation not a bottleneck in hospital setting)
```

**In Discussion:**
"We prioritize Dice over model size because clinical accuracy is non-negotiable, whereas model compression can be addressed in a future deployment phase."

## Trade-off framing (no free lunches)

### Canonical trade-offs in ML

1. **Accuracy vs interpretability**
   - Deep neural networks: high accuracy, low interpretability
   - Decision trees: lower accuracy, high interpretability
   - Neither dominates; choice depends on use case

2. **Accuracy vs fairness**
   - Maximizing overall accuracy may worsen performance on underrepresented groups
   - Trade-off: lower global accuracy for more equitable per-group performance

3. **Accuracy vs speed**
   - Larger models (ResNet-101) often more accurate than smaller models (ResNet-18), but slower
   - Accuracy-speed Pareto frontier: no method better on both

4. **Generalization vs specialization**
   - A method tuned to Dataset A may fail on Dataset B
   - A method that works on all datasets often has lower peak accuracy on any single dataset

### Honest trade-off language

**Avoid:** "Our method is better" (binary claim, implies dominance on all criteria)

**Prefer:** 
- "Our method achieves higher accuracy (+2.3%) at the cost of 3× inference time"
- "Trade-off: +1.5% accuracy for −40% model size"
- "Pareto frontier analysis shows method X dominates method Y on speed; method Y dominates on accuracy"

### Pareto frontier (when trade-offs exist)

```python
import matplotlib.pyplot as plt

# Methods with accuracy-speed trade-off
methods = {
    'ResNet-50': (0.762, 50),      # (accuracy, ms per image)
    'EfficientNet': (0.788, 30),
    'MobileNet': (0.710, 10),
    'Ours': (0.821, 35)
}

fig, ax = plt.subplots(figsize=(8, 6))
for name, (acc, time) in methods.items():
    marker = '*' if name == 'Ours' else 'o'
    ax.scatter(time, acc, s=200, marker=marker, label=name)

ax.set_xlabel('Inference Time (ms)', fontsize=12)
ax.set_ylabel('Accuracy', fontsize=12)
ax.set_title('Accuracy-Speed Trade-off', fontsize=13, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)
plt.savefig('pareto_frontier.pdf', dpi=300, bbox_inches='tight')
plt.close()
```

**Caption:** "Accuracy-speed trade-off. Our method (star) lies on the Pareto frontier, offering the best accuracy-speed combination. ResNet-50 and MobileNet are dominated by EfficientNet (better on both metrics)."

## Fair-baseline principle

### What makes a baseline unfair?

1. **Undertuned baseline:** Baseline given 10 hyperparameter trials; your method gets 100.
   → Baseline appears worse than it is.

2. **Reimplemented baseline:** Official code uses batch norm v2; reimplementation uses v1.
   → Different behavior; unfair comparison.

3. **Different preprocessing:** Baseline code assumes 256×256 input; you use 224×224.
   → Changes effective regularization; unfair.

4. **Cherry-picked baseline:** You compare to an old method (2010) rather than the current state-of-the-art (2024).
   → Looks good but not meaningful.

5. **Single run vs multiple seeds:** You report 5-seed results for your method; baseline is 1 run.
   → Unfair variance estimate.

### Fairness checklist

Before claiming superiority:
- [ ] Baselines from official code or well-cited reimplementations
- [ ] Same hyperparameter tuning budget (# trials, search space)
- [ ] Same preprocessing (normalization, augmentation, splits)
- [ ] Same random seed protocol (same # seeds)
- [ ] Baselines are state-of-the-art (not outdated methods)
- [ ] Baseline paper results cited (sanity check: does our reimplementation match published results?)

**In Methods:**
"All methods used the same preprocessing (ImageNet normalization) and augmentation strategy. Hyperparameter tuning was performed on the validation set using 50 random trials for each method. Baselines traced to official implementations (with commit SHAs documented). All experiments ran with 5 random seeds using the same seed values."

## Steel-manning opposing findings

### Identify opposing claims

When literature shows conflicting results (Method X works for Dataset A but fails on Dataset B), don't ignore it.

**Wrong:** "Study Z found opposite results, but they used outdated techniques."
**Consequence:** Strawman argument; appears dismissive.

**Right:** "Study Z found opposite results on Dataset B. We hypothesize the difference arises because Dataset B has [specific characteristic] that Dataset A lacks. Under [characteristic], Method X's [component] becomes less effective."
**Consequence:** Respectful, scientifically interesting.

### How to incorporate contradictory findings

```
Discussion section on contradictory evidence:

"While Zhang et al. (2022) reported that attention mechanisms hurt performance on small images,
our ImageNet results show +2.3% improvement. We attribute this difference to:
1. Dataset size: Zhang's dataset (CIFAR-10, 32×32) is much smaller than ImageNet (224×224).
   Attention mechanisms may overfit on small images due to limited pixel context.
2. Augmentation: Our training uses stronger augmentation (RandAugment + Cutmix),
   which may provide additional regularization that makes attention mechanisms beneficial.

To test this hypothesis, we evaluated our method on CIFAR-10 (Table 4) and found
a smaller attention gain (+0.8%, not significant), supporting the dataset-size theory."
```

**Pattern:** Respect the opposing finding, propose a mechanism for the difference, test it.

## From comparison to claim: what claims are licensed?

### Comparison table → what you CAN claim

```
| Method | Accuracy | F1 | Speed |
|--------|----------|-----|-------|
| Baseline A | 0.876 | 0.743 | 50ms |
| Baseline B | 0.891 | 0.768 | 100ms |
| Ours | 0.912 | 0.801 | 75ms |
```

**Licensed claims:**
- ✓ "Our method achieves 91.2% accuracy, outperforming baselines by 2.1%."
- ✓ "On this benchmark, our method is 33% faster than Baseline B."
- ✓ "Trade-off: we gain +2.1% accuracy at cost of +25% inference time vs Baseline A."
- ✓ "Our method achieves the best F1 score (0.801) on this dataset."

**UNLICENSED claims (too strong):**
- ✗ "Our method is objectively better than prior work."
  (Why: "better" is undefined without criteria; only better on this benchmark.)
- ✗ "Our method is the state-of-the-art."
  (Why: only on this specific dataset and metric; other benchmarks unknown.)
- ✗ "Our method solves the problem of X."
  (Why: comparison shows improvement; problem not "solved" until no further gains possible.)
- ✗ "Baselines are fundamentally flawed."
  (Why: comparison shows they underperform; not why — don't speculate on mechanisms.)

### Comparison across multiple datasets → generalization claims

```
| Method | ImageNet | CIFAR-10 | Places365 | Avg rank |
|--------|----------|----------|-----------|----------|
| ResNet-50 | 0.762 | 0.968 | 0.735 | 3 |
| EfficientNet | 0.788 | 0.971 | 0.751 | 2 |
| **Ours** | **0.821** | **0.976** | **0.768** | **1** |
```

**Licensed claims:**
- ✓ "Our method ranks first on all three benchmarks, suggesting consistent generalization."
- ✓ "Across diverse datasets (natural images, small images, scene recognition), our method maintains +2–3% advantage."

**UNLICENSED claims:**
- ✗ "Our method generalizes to any image classification task."
  (Why: only tested on 3 benchmarks; medical/satellite images unknown.)
- ✗ "Our method solves the generalization problem."
  (Why: outperforms baselines on 3 datasets, not 100% success rate.)

## Gap reasoning: "no prior work combines X+Y"

### How to verify a gap claim safely

**Dangerous shortcut:** "No one has combined attention + convolution before because I didn't see it in the papers I read."

**Correct approach:**

1. **Systematic search:** Search with terms like "attention convolution", "transformer CNN", "hybrid architecture".
   - Use multiple databases (Google Scholar, Semantic Scholar, arXiv)
   - Search in different languages if applicable

2. **Document non-findings:** Keep a list of "negative results" (papers you checked but that don't combine X+Y).
   - Otherwise you're just reporting absence of evidence (not evidence of absence)

3. **Nuance the claim:**
   ```
   Weak claim: "No prior work combines attention and convolution."
   
   Stronger claim: "While prior work has explored attention (Smith 2021) and convolution
   (Jones 2020) separately, and hybrid architectures exist (Brown 2023), the specific
   combination of [our novelty] with [our design choice] under [our constraint] has not
   been explored. Our search covered [X databases] with terms [Y, Z]."
   ```

4. **Acknowledge related work:** Show that you're building on prior work, not claiming ex nihilo.
   ```
   "Building on Vision Transformers (Dosovitskiy et al. 2021) and efficient CNNs (Tan & Le 2019),
   we propose to combine their strengths via [mechanism]. Prior work has not explored this specific
   combination because [reason: different constraints, different problem setup, different era]."
   ```

### Example: gap claim done right

"Prior work on few-shot learning (Prototypical Networks, Matching Networks) focuses on classification tasks. Prior work on meta-learning for regression (MAML) assumes continuous outputs. The combination—few-shot regression in tabular data with categorical features—has not been addressed. Our search of Google Scholar + Semantic Scholar (search terms: 'few-shot regression', 'meta-learning tabular', 'few-shot structured data') found no papers combining these constraints."

## Causal-language discipline

### Correlation ≠ Causation: phrasing bank

**Observational study (no randomization):**
- ✓ "X is associated with Y"
- ✓ "X co-occurs with Y"
- ✓ "X predicts Y in this dataset"
- ✓ "Higher X correlates with higher Y"
- ✗ "X causes Y" (unsupported)
- ✗ "X leads to Y" (implies causation)

**RCT (randomized controlled trial):**
- ✓ "X causes Y"
- ✓ "X significantly improves Y"
- ✓ "X leads to higher Y"
- ✓ "Intervention X results in Y"

**Observational study WITH confounding control (matching, regression):**
- ✓ "After controlling for confounders, X is associated with Y"
- ✓ "X predicts Y independent of Z" (Z is confounder)
- ? "X may influence Y" (cautious)
- ✗ "X causes Y" (still just observational)

**ML/experimental setting (ablation study):**
- ✓ "Removing component X decreases accuracy by 2.1%"
- ✓ "Component X contributes +2.1% to accuracy"
- ✓ "Adding attention improves F1 by 0.8% (p<0.05)"
- ? "Attention enables better feature extraction" (speculating on mechanism)
- ✗ "Attention is necessary for good performance" (only true for this dataset/task)

### Table: study design → licensed verbs

| Study design | Licensed verbs | Example sentence |
|---|---|---|
| Observational | is associated with, correlates with, predicts | "Sleep duration is associated with test performance in this cohort." |
| RCT | causes, leads to, improves | "Cognitive behavioral therapy causes reduction in anxiety (p<0.001)." |
| Ablation (ML) | contributes, enables, removes | "Attention contributes +2.1% accuracy; removing it decreases performance." |
| Regression (controlled) | predicts (after controlling for X) | "Age predicts mortality independent of BMI." |
| Case report | describes, demonstrates | "This case demonstrates an unusual presentation of X." |
| Mechanistic model | enables, allows, facilitates | "This architecture enables efficient processing of long sequences." |

### Example: correct causal language in Discussion

"Our ablation study (Table 3) shows that removing the attention module decreases accuracy by 2.1% (p<0.01). This result suggests attention contributes meaningfully to our model's performance. However, this does not establish that attention is necessary for high performance; future work should test our method on datasets where attention may hurt (e.g., CIFAR-10, as noted in prior work)."

## Reference files

- **comparison-tables.md** — canonical table shapes (method × criteria, chronological capability matrix, taxonomy trees), when each fits, worked examples
- **argumentation.md** — Toulmin claim–ground–warrant mapping for academic prose, gap-reasoning patterns with checklists, causal-language discipline with phrasing bank

