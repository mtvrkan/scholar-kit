# Experiment Design for ML Papers

Baseline fairness, ablation studies, leakage prevention, statistical significance testing, and reproducibility.

## Baseline selection & fairness

### What makes a fair baseline?

1. **Same tuning budget:** All methods (yours + baselines) get equal compute for hyperparameter search.
   - Fair: 20 random HP trials for baseline A, 20 random HP trials for your method
   - Unfair: 100 trials for your method, 5 for baseline (baseline appears worse due to underfitting)

2. **Traced to published code:** Always start from the authors' official implementation or a well-cited reimplementation.
   - Good: "We used the official PyTorch implementation (github.com/author/method, commit abc123)"
   - Risky: "We reimplemented method X based on the paper" (reimplementations often differ subtly)

3. **Same random seed protocol:** If you report 5-seed results for your method, baselines get 5 seeds too.
   - Do NOT report: your method 5 seeds (mean ± std) vs baseline 1 run (single value)

4. **Same preprocessing:** Baselines and your method must use identical preprocessing.
   - Fair: All methods see ImageNet images resized to 224×224, normalized the same way
   - Unfair: Baseline gets 256×256 images (author's default), your method uses 224×224 (different effective regularization)

5. **State-of-the-art baseline:** Your baseline should be competitive with the state of the field when you started the work.
   - Good: YOLO v8 (current) compared to ResNet-50 for classification (solid reference)
   - Weak: Comparing to a 5-year-old method if newer exists

### Baseline table structure

```
| Method | Train Acc | Val Acc | Test Acc | Best HP | Compute |
|--------|----------|---------|----------|---------|----------|
| ResNet-50 | 0.923±0.005 | 0.891±0.008 | 0.887±0.009 | lr=0.01, BS=64 | 12h GPU |
| EfficientNet-B0 | 0.941±0.004 | 0.908±0.006 | 0.904±0.007 | lr=0.005, BS=128 | 8h GPU |
| **Ours** | **0.956±0.003** | **0.921±0.005** | **0.918±0.006** | lr=0.002, BS=64 | 14h GPU |
```

Key: bold the best, include ±std, report all hyperparameters, note compute (shows fairness).

## Ablation study design

### One variable at a time

**Rule:** Each ablation removes or adds exactly ONE design choice.

Good ablation:
- Remove residual connections from your architecture → see performance drop
- Add spatial attention to baseline → see performance gain
- Use different data augmentation strategy → see impact

Bad ablation:
- "Simplified architecture" (removed 3 things at once → can't identify which helped)
- "Full training pipeline" vs "minimal training" (many differences → confounded)

### Effect size threshold

Report ablations only if effect > 0.5% absolute.
- Example: Removing component X drops accuracy from 0.918 to 0.913 = 0.5% drop → reportable
- Example: Adding fancy loss drops accuracy from 0.918 to 0.919 = 0.1% gain → noise, omit

### Ablation table structure

```
| Ablation | Test Acc | Change | Significance |
|----------|----------|--------|--------------|
| Baseline (full) | 0.918±0.006 | — | — |
| - Residual connections | 0.873±0.008 | -4.5% | p < 0.001 |
| - Attention module | 0.901±0.007 | -1.7% | p < 0.01 |
| - Data augmentation | 0.905±0.009 | -1.3% | p < 0.05 |
```

Include p-values or significance marker; show that effect is not noise.

## Data leakage checklist

**Leakage = using information from outside the training set to build or tune the model.**

### Temporal leakage (time-series, forecasting)

❌ **Wrong:** Train set contains data from weeks 1–10, test set weeks 5–15 → test data overlaps training era.
✓ **Correct:** Train weeks 1–10, validation weeks 11–12, test weeks 13–15 (chronological split).

How to report: "We used temporal cross-validation to avoid look-ahead bias: training set (weeks 1–50), validation (weeks 51–60), test (weeks 61–70)."

### Duplicate leakage (same sample in train and test)

❌ **Wrong:** Download ImageNet → dedup globally? No. Same image ID appears in train and val sets? Possible.
✓ **Correct:** Verify no test sample ID appears in train set. "We verified no duplicates between train/val/test using MD5 hashing."

### Preprocessing leakage (fitting on all data before splitting)

❌ **Wrong:** Normalize all data (train + val + test) to mean=0, std=1, then split.
✓ **Correct:** Fit normalizer on train set only, apply to val and test.

How to report: "All preprocessing (normalization, PCA) was fitted on the training set; validation and test sets were transformed using training-set statistics."

### Target leakage (using target variable in features)

❌ **Wrong:** Feature engineering uses information about y (e.g., target class frequency per feature).
✓ **Correct:** Feature engineering uses only X; no information about y at all.

Example: "We did NOT use class distribution in feature selection; feature selection was unsupervised (variance-based)."

### Hyperparameter tuning on test set

❌ **Wrong:** Run baseline A with HP1, baseline B with HP2 on the test set, pick the best.
✓ **Correct:** Tune all methods on validation set, report test set results once (no retuning on test).

How to report: "Hyperparameter tuning was performed on the validation set; test results are final and were not used to reoptimize any component."

## Train/Validation/Test split protocol

### Random split (stateless data, e.g., image classification)
```python
# Correct protocol
train_indices, temp_indices = train_test_split(all_indices, test_size=0.3, random_state=42)
val_indices, test_indices = train_test_split(temp_indices, test_size=0.5, random_state=42)
# Result: 70% train, 15% val, 15% test
```

Report: "Random stratified split: 70% training, 15% validation, 15% test. Stratification by class ensured balanced class distribution in each set."

### Time-series split (temporal data, e.g., stock prices)
```python
# Correct protocol
n = len(data)
train_end = int(0.6 * n)
val_end = int(0.8 * n)
train = data[:train_end]
val = data[train_end:val_end]
test = data[val_end:]
```

Report: "Temporal split without overlap: training (first 60% by date), validation (middle 20%), test (final 20%)."

### Stratified split (classification with class imbalance)
```python
# Correct protocol
train_indices, test_indices = train_test_split(
    all_indices, test_size=0.2, stratify=labels, random_state=42
)
val_indices, test_indices = train_test_split(
    test_indices, test_size=0.5, stratify=labels[test_indices], random_state=42
)
```

Report: "Stratified random split ensured class distribution was preserved: training 80%, validation 10%, test 10%."

## Random seed protocol & statistical significance

### Seed choice & reporting

**Requirement:** Report results over ≥3 different random seeds.

```python
# Run with multiple seeds
for seed in [42, 123, 456, 789, 999]:
    set_seed(seed)
    model = train()
    results[seed] = evaluate(model)

# Aggregate results
mean_acc = np.mean([results[s]['accuracy'] for s in results])
std_acc = np.std([results[s]['accuracy'] for s in results])
print(f"Accuracy: {mean_acc:.3f} ± {std_acc:.3f}")
```

Report: "Accuracy = 0.918 ± 0.006 (5 seeds: {42, 123, 456, 789, 999})"

### Paired t-test for method comparison

**When to use:** Comparing two methods (baseline vs your method) with multiple seeds.

```python
baseline_results = [0.887, 0.891, 0.885, 0.889, 0.890]  # 5 seeds
your_results = [0.918, 0.920, 0.916, 0.922, 0.917]     # same 5 seeds

from scipy.stats import ttest_rel
t_stat, p_value = ttest_rel(your_results, baseline_results)
print(f"p-value: {p_value:.4f}")
# p < 0.05 → statistically significant
```

Report: "Paired t-test: p = 0.0031, indicating statistically significant improvement."

### Multiple comparison correction (Bonferroni)

**When to use:** If you have M comparisons (e.g., M ablations), adjust p-value threshold.

```python
from scipy.stats import ttest_rel
alpha = 0.05
M = 3  # 3 ablations
bonferroni_alpha = alpha / M  # 0.0167

for ablation in [ablation_1, ablation_2, ablation_3]:
    t_stat, p_value = ttest_rel(ablation, baseline)
    if p_value < bonferroni_alpha:
        print(f"{ablation}: SIGNIFICANT (p = {p_value:.4f})")
```

Report: "With Bonferroni correction for 3 ablations (α = 0.0167), ablations A and B were significant (p < 0.01), ablation C was not (p = 0.087)."

### Effect size (Cohen's d)

**Why:** "Statistically significant" ≠ "practically meaningful." Report effect size too.

```python
from scipy.stats import cohens_d
d = cohens_d(your_results, baseline_results)
print(f"Cohen's d: {d:.2f}")
# d < 0.2: negligible, 0.2–0.5: small, 0.5–0.8: medium, >0.8: large
```

Report: "Cohen's d = 1.42, indicating a large effect size (substantial improvement)."

## Hyperparameter reporting table

**Requirement:** Report all hyperparameter values used for training.

```
| Parameter | Baseline A | Baseline B | Ours |
|-----------|-----------|-----------|------|
| Learning rate | 0.001 | 0.005 | 0.002 |
| Batch size | 64 | 128 | 64 |
| Optimizer | Adam | SGD | AdamW |
| Weight decay | 1e-4 | 1e-5 | 1e-4 |
| Epochs | 100 | 200 | 150 |
| LR scheduler | cosine | step | cosine |
| Dropout | 0.1 | 0.0 | 0.2 |
| Data augmentation | RandAugment | Mixup | RandAugment + Cutmix |
| Compute | 12h V100 | 16h V100 | 14h V100 |
```

**Minimalist version (Methods section):**
"Training details: learning rate = 0.002, batch size = 64, optimizer = AdamW (β₁=0.9, β₂=0.999), weight decay = 1e-4, epochs = 150 with cosine annealing, dropout = 0.2. Data augmentation: RandAugment (N=2, M=9) + Cutmix (α=1.0). All experiments used 5 random seeds."

## Hyperparameter tuning discipline

### Grid search vs random search

- **Grid search:** Try all combinations of a discrete set (expensive but exhaustive)
  - Good for: ≤3 hyperparameters
  - Bad for: >5 hyperparameters (combinatorial explosion)
  
- **Random search:** Try N random combinations
  - Good for: >3 hyperparameters, cheaper than grid
  - Bad for: may miss optimal regions

- **Bayesian optimization:** Learn where good HPs are, sample intelligently
  - Good for: limited budget, high-dimensional space
  - Requires a tool (e.g., Optuna, Ray Tune)

**Report:** "Hyperparameter search: random search over 50 trials (learning rate ∈ [1e-4, 1e-2], batch size ∈ [32, 256], dropout ∈ [0, 0.5]) using the validation set."

### Overfitting to validation set

**Risk:** If you tune on validation set and report validation results, you're reporting on the tuning set (overfitting).

**Solution:** Always hold out a separate test set.

```
Train (60%) → tune HPs on Validation (20%) → report on Test (20%) ✓
                                        ↑
                                    Do NOT report Val results
```

Report: "Hyperparameter search was performed on the validation set; final results are reported on the held-out test set."

