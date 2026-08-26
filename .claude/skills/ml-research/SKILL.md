---
name: ml-research
description: Use when reading ML/DL/NLP/CV/signal-processing papers or designing experiments — when questions arise about architecture extraction, dataset splits, baselines, metric selection (which metric for my task?), multi-seed results reporting, ablation-study design, reproducibility/environment capture, hyperparameter tables, leakage detection, significance testing, preprocessing chains, or code/data availability statements. Source-analyst uses this skill's extraction schema to standardize ML paper reading.
---

# ML Research Expertise Pack

Expert-grade reading, extraction, and design guidance for machine learning, deep learning, NLP, computer vision, signal processing, and data science papers.

## Core competencies

1. **Paper extraction schema** (JSON-ish structure source-analyst follows):
```
{
  "task": "image classification on ImageNet",
  "task_type": "classification|detection|segmentation|regression|nlp|signal|retrieval",
  "architecture": {
    "name": "ResNet-50",
    "family": "CNN",
    "key_details": "residual blocks, skip connections",
    "novel_components": ["spatial attention", "progressive resizing"]
  },
  "dataset": {
    "name": "ImageNet-1K",
    "splits": {"train": 1281167, "val": 50000, "test": 100000},
    "preprocessing": "resized to 224×224, normalized per ImageNet",
    "augmentation": "RandAugment on train set"
  },
  "baselines": [
    {"model": "VGG-16", "accuracy": 0.710},
    {"model": "Inception-v3", "accuracy": 0.788}
  ],
  "main_results": [
    {"metric": "accuracy", "value": 0.762, "std": 0.003, "seeds": 5}
  ],
  "ablations": [
    {"removed": "skip_connections", "accuracy_drop": 0.045},
    {"added": "layer_norm", "improvement": 0.008}
  ],
  "compute": {"gpu": "8× V100", "training_hours": 24, "code_available": true},
  "reproducibility_score": 4,
  "page_limit": 8,
  "language": "en"
}
```

2. **Task-to-metric mapping** → see `reference/metrics.md` for:
   - Classification: accuracy, precision, recall, F1 (macro/micro), AUROC, AUPRC, MCC
   - Detection: mAP@IoU, IoU per class
   - Segmentation: Dice, mIoU, boundary F1
   - NLP: BLEU, ROUGE, METEOR, BERTScore, perplexity, exact match
   - Regression: RMSE, MAE, R², MAPE
   - Signal/image: SNR, PSNR, SSIM, spectral distortion
   - Retrieval/ranking: MRR, nDCG, recall@k
   - Clustering: ARI, NMI, silhouette
   Each metric includes: definition, when-to-use, pitfalls, reporting conventions

3. **Experiment design discipline** → see `reference/experiment-design.md` for:
   - Baseline fairness (same tuning budget for all baselines)
   - Ablation design (one variable at a time, effect size >0.5% to report)
   - Data leakage checklist (temporal, duplicate, preprocessing-before-split, target leakage)
   - Train/val/test protocol (random split vs stratified vs time-based)
   - Seed protocol & statistical significance (paired t-tests, multiple-comparison correction)
   - Hyperparameter reporting tables (all HP values for reproducibility)

4. **Reproducibility discipline** → see `reference/reproducibility.md` for:
   - NeurIPS-style reproducibility checklist (environment, hyperparameters, code/data availability)
   - Environment capture (requirements.txt / poetry.lock / environment.yml + hardware + runtime versions)
   - Model cards & data cards (use templates)
   - Code availability statements (from GitHub links to "code available upon request")

5. **Signal & image processing** → see `reference/signal-image.md` for:
   - Preprocessing chains (filtering, normalization, augmentation)
   - Feature extraction (FFT, STFT, wavelet, MFCC, handcrafted features)
   - Augmentation policies (how augmentation can leak between sets)
   - How to report preprocessing in Methods

6. **Results presentation** → see `reference/results-presentation.md` for:
   - Comparison-table design (bold best, ± std, per-dataset columns, statistical markers)
   - Learning curves (with ±1σ bands)
   - Confusion matrices (per-class F1)
   - Qualitative-example grids
   - Matplotlib conventions data-scientist follows (300 dpi, PDF+PNG, colorblind palettes)

## Reading ML papers: extraction checklist

When source-analyst reads an ML paper, it extracts:

1. **Task clarity:** What is the paper trying to improve? Is the task well-motivated?
2. **Architecture novelty:** What is the main contribution? (architecture change, training strategy, dataset, metric redefinition, etc.)
3. **Dataset + splits:** All three required (train/val/test sizes; preprocessing; how splits were created)
4. **Baselines:** Are they state-of-the-art? Are they given equal tuning budget? 
5. **Metrics & values:** Task-appropriate metrics with mean ± std over N seeds (N should be ≥3)
6. **Ablations:** One-variable-at-a-time; effect size reported
7. **Statistical significance:** Paired t-test or equivalent; multiple-comparison correction if >1 ablation
8. **Compute:** GPU/CPU, hours/days, reproducibility impact
9. **Code & data:** Available? Under what license? 
10. **Reproducibility score:** 1 (minimal) to 5 (full environment + code + data)

## Designing ML experiments: checklist

**Dispatch methodology-advisor** to apply this checklist at expert level rather
than self-checking it: DESIGN mode (task type, datasets under consideration,
candidate baselines as input) before experiments start, or CRITIQUE mode (draft
path) to audit an existing Methods/Experiments section for leakage, missing
significance testing, or baseline unfairness. It returns a verdict, numbered
issues, and a validity-threat table — read-only, no edits (see
`.claude/agents/methodology-advisor.md`).

### Setup
- [ ] Research question clear in prose, not just empirical
- [ ] Hypothesis stated before experiments
- [ ] Target metric chosen before training (never metric-shopping)
- [ ] Train/val/test split strategy (random? stratified? time-based?) → document why
- [ ] ≥3 random seeds decided in advance

### Baselines
- [ ] Baselines are state-of-the-art for the task (check recent surveys)
- [ ] Baselines given same hyperparameter-tuning budget as proposed method
- [ ] Baseline code traced to published source (reproducible, not reimplementation)
- [ ] Same random seed protocol for all methods

### Ablations
- [ ] One design choice per ablation (never change 2 things at once)
- [ ] Effect size >0.5% to report (smaller may be noise)
- [ ] Ablation on test set only after val set confirmed it (no val-set cherry-picking)

### Leakage prevention
- [ ] Preprocessing (normalization, scaling) fitted on train only, applied to val/test
- [ ] Augmentation applied only to train set
- [ ] No label information in features (e.g., class balance not in feature engineering)
- [ ] No data from test set used in architecture/hyperparameter decisions
- [ ] Temporal data: no future information in features (check if applicable)

### Statistical significance
- [ ] Report mean ± std (standard deviation of N runs)
- [ ] Paired t-test for comparing two methods (not unpaired)
- [ ] Bonferroni correction if M ablations (p-value threshold = 0.05 / M)
- [ ] "Statistically significant" iff p < 0.05 AND effect size >1% (practical significance)

### Reproducibility
- [ ] Hyperparameters reported in table (learning rate, batch size, epochs, optimizer settings)
- [ ] Random seed values listed (or if "seed 0,1,2")
- [ ] Hardware specified (GPU model, CPU, RAM)
- [ ] Code available (GitHub or zenodo.org with DOI)
- [ ] Data available or download link + preprocessing code

## Common pitfalls

1. **Accuracy on imbalanced data:** Report per-class metrics (precision/recall/F1), not accuracy alone.
2. **BLEU score limits:** BLEU alone ≤ 40 valid; report BLEU+ROUGE+BERTScore for NLP.
3. **R² misuse:** R² ≠ accuracy for regression; report RMSE + MAE + R² together.
4. **Seed variation:** ±0.5% variation is noise; only effect >1% is reportable.
5. **Baseline re-implementation:** Always trace to published code; reimplementations often differ.
6. **Val set hyperparameter search:** Over-tuning on val set leaks val performance into hyperparameters.
7. **Test set reporting:** Never report test results during hyperparameter selection; test is final.

## Section references

- **metrics.md** — task → metric catalog, definitions, pitfalls, conventions
- **experiment-design.md** — baseline fairness, ablation, leakage, seed/significance protocol, HP tables
- **reproducibility.md** — NeurIPS checklist, environment capture, model/data cards, availability statements
- **signal-image.md** — preprocessing chains, filtering, feature extraction, augmentation, Methods reporting
- **results-presentation.md** — table design, learning curves, confusion matrices, qualitative grids, matplotlib rules

