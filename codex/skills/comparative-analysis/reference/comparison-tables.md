# Comparison Tables: Canonical Shapes and When to Use Each

## Type 1: Method × Criteria (most common)

### Shape

| Method | Metric 1 | Metric 2 | Metric 3 | Trade-off metric |
|--------|----------|----------|----------|------------------|
| Baseline A | value | value | value | value |
| Baseline B | value | value | value | value |
| **Ours** | **value** | **value** | **value** | **value** |

### When to use

- Comparing multiple methods on a fixed set of criteria (most papers)
- Benchmarking your method against baselines
- Showcasing multiple facets of the method (accuracy, speed, size, fairness)

### Example: Image classification

```
| Method | Accuracy | F1 (macro) | Inference (ms) | Model size (MB) |
|--------|----------|-----------|----------------|-----------------|
| ResNet-50 | 0.762 ± 0.005 | 0.743 ± 0.008 | 45 | 98 |
| EfficientNet-B0 | 0.788 ± 0.004 | 0.768 ± 0.006 | 28 | 41 |
| **Ours** | **0.821 ± 0.006** | **0.801 ± 0.007** | **35** | **62** |
```

**Rationale:** Accuracy is primary criterion; F1 validates on imbalanced data; speed and size show practical trade-offs.

### Example: NLP (machine translation)

```
| Model | BLEU | ROUGE-L | Training time | Data req. |
|-------|------|---------|---------------|-----------|
| Baseline (RNN) | 24.3 | 0.421 | 48h | 2M pairs |
| Transformer | 28.9 | 0.473 | 72h | 2M pairs |
| **Ours** | **30.2** | **0.489** | **60h** | **1.5M pairs** |
```

**Rationale:** BLEU is standard for MT; ROUGE-L (longest common subseq) captures reordering; data efficiency shows practical advantage.

## Type 2: Per-dataset breakdown

### Shape

| Method | Dataset A | Dataset B | Dataset C | Avg |
|--------|-----------|-----------|-----------|-----|
| Baseline A | value | value | value | value |
| Baseline B | value | value | value | value |
| **Ours** | **value** | **value** | **value** | **value** |

### When to use

- Testing generalization across datasets
- Showing if your method is broadly better or only good on specific datasets
- Comparing on multiple benchmarks (standard in top-tier venues)

### Example: Multi-dataset evaluation (object detection)

```
| Method | COCO | Pascal VOC | Cityscapes | Average mAP |
|--------|------|-----------|-----------|-------------|
| Faster R-CNN | 0.378 | 0.802 | 0.542 | 0.574 |
| YOLO v8 | 0.408 | 0.834 | 0.618 | 0.620 |
| **Ours** | **0.425** | **0.851** | **0.651** | **0.642** |
```

**Key insight:** If average mAP is high but one dataset is low, that's a generalization weakness worth investigating.

### Example: How to interpret per-dataset results

- **Consistent across datasets (like above):** Strong generalization claim licensed
- **Inconsistent (e.g., Ours: 0.92 on A, 0.68 on B):** Your method has a weakness on Dataset B type. Investigate why.
  - "High performance on CIFAR-10 (32×32 images) but weak on ImageNet (224×224) suggests our method struggles with large images."

## Type 3: Per-class breakdown (imbalanced classification)

### Shape

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|----------|
| Class 1 | value | value | value | N samples |
| Class 2 | value | value | value | N samples |
| Class 3 | value | value | value | N samples |
| **Macro avg** | **value** | **value** | **value** | — |

### When to use

- Imbalanced classification (classes have different frequencies)
- Identifying which classes are hard for the model
- Actionable feedback (if Class X is always misclassified, investigate)

### Example: Medical diagnosis (imbalanced)

```
| Disease | Precision | Recall | F1 | Support |
|---------|-----------|--------|-----|---------|
| Healthy | 0.94 | 0.89 | 0.92 | 8000 |
| Mild | 0.76 | 0.68 | 0.72 | 1200 |
| Severe | 0.68 | 0.82 | 0.74 | 300 |
| **Weighted avg** | **0.91** | **0.87** | **0.89** | 9500 |
```

**Interpretation:**
- Healthy is easy (high precision/recall).
- Mild is harder (low precision and recall).
- Severe has high recall (catches most cases, good for safety) but lower precision (false alarms).

**Discussion:** "The model is conservative on Severe cases (high recall=0.82), correctly identifying 82% of true severe cases. However, it has false positives (precision=0.68), flagging 32% of positive predictions as false alarms. This trade-off is clinically desirable: missing severe cases is worse than extra testing."

## Type 4: Ablation study

### Shape

| Component | Accuracy | Δ | Significant | Std. error |
|-----------|----------|--------|-----------|-----------|
| Full (all) | 0.912 | — | — | 0.007 |
| − Component A | 0.901 | −1.1% | ✓ | 0.008 |
| − Component B | 0.905 | −0.7% | ✓ | 0.009 |
| − Component C | 0.897 | −1.5% | ✓ | 0.010 |

### When to use

- Justifying design choices (why did you include Component X?)
- Showing contribution of each part
- Answering "what if we simplified?"

### Key rules

1. **One component per row** (never remove 2 things at once)
2. **Order by impact** (largest drop first)
3. **Include statistical significance** (p-value or ✓/✗ marker)
4. **Minimum effect >0.5%** (smaller effects are likely noise)
5. **Same seeds as main experiment** (don't use different seeds for ablations)

### Example: Ablation with significance

```
| Ablation | F1 | Δ | p-value | Interpretation |
|----------|-----|--------|---------|-----------------|
| Baseline | 0.801 | — | — | — |
| − Attention | 0.783 | −1.8% | <0.01 | Highly significant |
| − Focal loss | 0.791 | −1.0% | 0.042 | Significant (α=0.05) |
| − Aug (RandAugment) | 0.795 | −0.6% | 0.12 | Not significant (noise) |
```

**Interpretation:** "Only attention and focal loss are significant contributors. RandAugment's contribution (0.6%) is within noise margins (not significant)."

## Type 5: Chronological capability matrix (emerging capabilities over time)

### Shape

| Method | Year | Dataset A | Dataset B | Task X | Task Y | Interpretable | Code |
|--------|------|----------|----------|--------|--------|---------------|------|
| Method A | 2018 | ✗ | ✓ | ✓ | ✗ | ✓ | ✗ |
| Method B | 2020 | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ |
| Method C | 2022 | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ |
| **Ours** | **2024** | **✓** | **✓** | **✓** | **✓** | **✓** | **✓** |

### When to use

- Narrative/literature reviews where you're tracing the evolution of a field
- Showing that your work closes a gap (combines capabilities that prior work scattered)
- Distinguishing your contribution: what's new in 2024 vs 2022?

### Example: Evolution of self-supervised learning

```
| Method | Year | Unlabeled data | Video data | Language | Scaling | Requires labels? |
|--------|------|----------------|-----------|----------|---------|------------------|
| SimCLR | 2020 | ✓ | ✗ | ✗ | Limited | Yes (some) |
| MoCo | 2020 | ✓ | ✗ | ✗ | Good | Yes (some) |
| BYOL | 2020 | ✓ | ✗ | ✗ | Limited | Yes (some) |
| CLIP | 2021 | ✓ | ✗ | ✓ | Excellent | No |
| **Ours** | **2024** | **✓** | **✓** | **✓** | **Excellent** | **No** |

**Narrative:** Over 2020–2021, self-supervised learning emerged (SimCLR, MoCo, BYOL) but could not scale to language+vision or video. CLIP (2021) solved language+vision but ignored video. Our work closes this gap by enabling self-supervised learning on unlabeled video with language alignment, achieving [our result]."

## Type 6: Taxonomy/feature matrix (literature review)

### Shape

| Source | Type | Dataset | Metric A | Metric B | Limitations |
|--------|------|---------|----------|----------|------------|
| Paper A | Review | — | — | — | Narrative only |
| Paper B | Empirical | ImageNet | 0.82 | 95ms | Single seed |
| Paper C | Theory | — | — | — | No experiments |
| **Ours** | Empirical | Multi | **0.91** | **28ms** | 5 seeds, diverse data |

### When to use

- Systematic/scoping reviews: organizing literature by type, data, methods
- Positioning your work in the landscape
- Identifying gaps (which combinations of [approach] + [dataset] are missing?)

### Example: LLM fine-tuning approaches

```
| Method | Base model | Task | Dataset | Performance | Params | Compute |
|--------|-----------|------|---------|-------------|--------|----------|
| Prompt tuning | GPT-3 | Classification | 100 examples | 87% | 0 | None (API) |
| LoRA | LLaMA-7B | Classification | 100 examples | 91% | 16K | 1 GPU-day |
| Full fine-tune | LLaMA-7B | Classification | 100 examples | 94% | 7B | 10 GPU-days |
| **Ours** | LLaMA-7B | Classification+QA | 100 examples | **96%** | **2M** | **3 GPU-days** |
```

**Insight from table:** "Our method matches full fine-tuning accuracy (96%) with 3× fewer GPU-days and enables multi-task learning, which prior LoRA work does not."

## Design rules for all tables

### 1. Decimal precision

Use consistent decimal places (not "0.9" and "0.87" mixed).

```
WRONG:
| Method A | 0.9 |
| Method B | 0.87 |

RIGHT:
| Method A | 0.90 |
| Method B | 0.87 |
```

### 2. Bold the best

Always bold the best value in each column (including baselines if they win a metric).

```
| Method | Acc | Speed |
|--------|-----|-------|
| Baseline | 0.89 | **25ms** |  ← Best speed
| **Ours** | **0.92** | 50ms |   ← Best accuracy
```

### 3. Order rows by importance or performance

- **For method comparison:** Best to worst (your method at top or bottom, convention matters; check venue style guides)
- **For ablation:** Largest drop to smallest
- **For per-class:** Most common class to rarest (or weakest to strongest, be consistent)

### 4. Units and notation

Every column must have units (if applicable) or explicit meaning.

```
WRONG:
| Method | Time | Size |
| Ours | 35 | 62 |

RIGHT:
| Method | Inference time (ms) | Model size (MB) |
| Ours | 35 | 62 |
```

### 5. Error bars notation

```
Good: 0.912 ± 0.007       (mean ± std over N runs)
Good: 0.912 ± 0.007[5]    (mean ± std over 5 runs)
Also good: 0.912 (0.905–0.919)  (95% CI)

Avoid: 0.912 ± 0.007% (unclear what ± refers to)
Avoid: 0.912±0.007 (inconsistent spacing)
```

### 6. Footnotes for special cases

```
| Method | Accuracy | Notes |
|--------|----------|-------|
| Baseline (reimplemented) | 0.876 | ¹ |
| **Ours** | **0.912** | — |

¹ Official code unavailable; we reproduced from paper description.
  Our reimplementation achieves 0.876 vs reported 0.882 (small gap acceptable).
```

### 7. Caption for tables

Every table needs a caption that:
- States what the table shows (one sentence)
- Highlights key findings (one sentence)
- Notes any special conditions (error bars, seeds, datasets)

Example:
"**Table 3:** Comparison of classification methods on ImageNet. Our method achieves 92.1% accuracy, outperforming baselines by 2.1–3.0%. All results report mean ± std over 5 random seeds; baselines traced to official implementations (GitHub commit SHAs in Appendix)."

