# Results Presentation for ML Papers

Comparison-table design, learning curves, confusion matrices, qualitative examples, and matplotlib conventions.

## Comparison-table design

### Canonical structure (method × metric)

```
| Method | Accuracy | F1 (macro) | AUROC | Comp. time | Params |
|--------|----------|-----------|-------|-----------|--------|
| Baseline A | 0.876 ± 0.008 | 0.743 ± 0.012 | 0.921 ± 0.009 | 12h | 50M |
| Baseline B | 0.891 ± 0.006 | 0.768 ± 0.010 | 0.936 ± 0.008 | 16h | 120M |
| **Ours** | **0.912 ± 0.007** | **0.801 ± 0.009** | **0.951 ± 0.006** | **14h** | **85M** |
```

**Conventions:**
- Bold the best value in each column
- Always show ± std over multiple runs (not min/max)
- Right-align numbers for visual comparison
- Include at least 2 metrics (never a single metric)
- Report practical considerations (compute time, model size)

### Per-dataset breakdown (important for generalization claims)

```
| Method | ImageNet | CIFAR-10 | Avg |
|--------|----------|----------|-----|
| ResNet-50 | 0.762 ± 0.005 | 0.968 ± 0.003 | 0.865 |
| EfficientNet-B0 | 0.788 ± 0.004 | 0.971 ± 0.002 | 0.880 |
| **Ours** | **0.821 ± 0.006** | **0.974 ± 0.003** | **0.898** |
```

**Why:** Shows if your method is broadly better or only good on specific datasets.

### Per-class breakdown (for imbalanced data)

```
| Class | Precision | Recall | F1 |
|-------|-----------|--------|-----|
| Dog | 0.89 ± 0.05 | 0.85 ± 0.06 | 0.87 ± 0.04 |
| Cat | 0.92 ± 0.03 | 0.88 ± 0.04 | 0.90 ± 0.03 |
| Bird | 0.76 ± 0.08 | 0.72 ± 0.10 | 0.74 ± 0.07 |
| **Macro avg** | **0.86** | **0.82** | **0.84** |
```

**Why:** Identifies classes where the model struggles (actionable insights for improvement).

### Ablation table (shows contribution of each component)

```
| Ablation | Accuracy | Δ | Significant |
|----------|----------|-----|-------------|
| Baseline (all components) | 0.912 ± 0.007 | — | — |
| − Attention module | 0.901 ± 0.008 | −1.1% | ✓ (p<0.01) |
| − Focal loss | 0.905 ± 0.009 | −0.7% | ✓ (p<0.05) |
| − Augmentation | 0.897 ± 0.010 | −1.5% | ✓ (p<0.001) |
```

**Conventions:**
- Δ shows absolute change from baseline
- Include p-values or ✓/✗ significance marker
- Remove one component at a time

### Comparison on benchmark (e.g., COCO detection)

```
| Method | mAP@0.5 | mAP@0.75 | mAP@[0.5:0.95] | AP_S | AP_M | AP_L |
|--------|---------|----------|----------------|------|------|------|
| Faster R-CNN | 0.410 | 0.212 | 0.312 | 0.195 | 0.338 | 0.438 |
| RetinaNet | 0.429 | 0.231 | 0.338 | 0.234 | 0.365 | 0.430 |
| **YOLO v8** | **0.480** | **0.268** | **0.378** | **0.268** | **0.412** | **0.491** |
```

**Why:** mAP@[0.5:0.95] is COCO standard (strictest); include AP_S/M/L to show if one size class is problematic.

## Learning curves

### Plot: training vs validation loss over epochs

```python
import matplotlib.pyplot as plt
import numpy as np

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

# Left: Loss curve
epochs = np.arange(1, 101)
train_loss = 2.3 * np.exp(-epochs / 30) + 0.1 * np.random.randn(100)
val_loss = train_loss + 0.02 * epochs / 100

ax1.plot(epochs, train_loss, label='Training', linewidth=2, color='#1f77b4')
ax1.plot(epochs, val_loss, label='Validation', linewidth=2, color='#ff7f0e')
ax1.fill_between(epochs, train_loss - 0.05, train_loss + 0.05, alpha=0.2, color='#1f77b4')
ax1.fill_between(epochs, val_loss - 0.05, val_loss + 0.05, alpha=0.2, color='#ff7f0e')
ax1.set_xlabel('Epoch', fontsize=11)
ax1.set_ylabel('Loss', fontsize=11)
ax1.set_title('Training Dynamics', fontsize=12, fontweight='bold')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Right: Accuracy curve with error bands
train_acc = 0.6 + 0.3 * (1 - np.exp(-epochs / 20))
val_acc = train_acc - 0.02
train_std = 0.01 * np.ones_like(epochs)
val_std = 0.015 * np.ones_like(epochs)

ax2.plot(epochs, train_acc, label='Training', linewidth=2, color='#1f77b4')
ax2.plot(epochs, val_acc, label='Validation', linewidth=2, color='#ff7f0e')
ax2.fill_between(epochs, train_acc - train_std, train_acc + train_std, alpha=0.2, color='#1f77b4')
ax2.fill_between(epochs, val_acc - val_std, val_acc + val_std, alpha=0.2, color='#ff7f0e')
ax2.set_xlabel('Epoch', fontsize=11)
ax2.set_ylabel('Accuracy', fontsize=11)
ax2.set_title('Validation Accuracy', fontsize=12, fontweight='bold')
ax2.legend()
ax2.grid(True, alpha=0.3)
ax2.set_ylim([0.5, 1.0])

plt.tight_layout()
plt.savefig('learning_curves.pdf', dpi=300, bbox_inches='tight')
plt.savefig('learning_curves.png', dpi=300, bbox_inches='tight')
plt.close()
```

**Conventions:**
- Use ±1σ bands (lighter shade) around the mean curve
- Always save as both PDF (print quality) and PNG (web)
- Dpi=300 minimum
- Include grid for readability

### Caption for learning curves

"**Figure 3:** Training dynamics over 100 epochs. (Left) Training and validation loss, showing convergence by epoch 50. (Right) Validation accuracy with ±1σ bands over 5 random seeds. The model reaches 92.1% accuracy by epoch 80 with minimal overfitting (gap between train and val <2%)."

## Confusion matrices

### Plot: multi-class confusion matrix

```python
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# Example: 5-class classification
y_true = np.array([0, 1, 2, 1, 3, 4, 2, 0, 1, 3])
y_pred = np.array([0, 1, 1, 1, 3, 4, 2, 0, 2, 3])
classes = ['Dog', 'Cat', 'Bird', 'Fish', 'Horse']

cm = confusion_matrix(y_true, y_pred)

fig, ax = plt.subplots(figsize=(8, 7))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
            xticklabels=classes, yticklabels=classes, 
            ax=ax, cbar_kws={'label': 'Count'})
ax.set_xlabel('Predicted Label', fontsize=12)
ax.set_ylabel('True Label', fontsize=12)
ax.set_title('Confusion Matrix (5-class)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('confusion_matrix.pdf', dpi=300, bbox_inches='tight')
plt.savefig('confusion_matrix.png', dpi=300, bbox_inches='tight')
plt.close()
```

**Conventions:**
- Use sequential colormap (Blues, Greys, Viridis) for clarity
- Annotate each cell with the count (integer, not percentage)
- Diagonal should be darkest (correct predictions)
- Off-diagonal confusion patterns show where the model fails

### Normalized confusion matrix (if categories have different frequencies)

```python
cm_normalized = cm.astype('float') / cm.sum(axis=1, keepdims=True)

fig, ax = plt.subplots(figsize=(8, 7))
sns.heatmap(cm_normalized, annot=True, fmt='.2f', cmap='Blues',
            xticklabels=classes, yticklabels=classes, ax=ax, 
            vmin=0, vmax=1, cbar_kws={'label': 'Recall'})
ax.set_xlabel('Predicted Label', fontsize=12)
ax.set_ylabel('True Label', fontsize=12)
ax.set_title('Normalized Confusion Matrix (Recall per class)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('confusion_matrix_normalized.pdf', dpi=300, bbox_inches='tight')
plt.close()
```

**Why normalized?** Shows recall (true positive rate) per class, useful for imbalanced datasets.

### Caption for confusion matrices

"**Figure 5:** Confusion matrices on test set (5 seeds averaged). (Top) Absolute counts; diagonal represents correct predictions. (Bottom) Normalized by true class (row-wise), showing per-class recall. The model confuses 'Cat' and 'Bird' most frequently (15% of Cat images misclassified as Bird)."

## Qualitative examples

### Layout: success and failure cases

```python
import matplotlib.pyplot as plt

# Load images
img_success = [img1, img2, img3]  # 3 correct predictions
img_failure = [img4, img5, img6]  # 3 wrong predictions

fig, axes = plt.subplots(2, 3, figsize=(12, 8))
titles_success = [
    'True: Dog, Pred: Dog (conf=0.98)',
    'True: Cat, Pred: Cat (conf=0.95)',
    'True: Bird, Pred: Bird (conf=0.92)'
]
titles_failure = [
    'True: Dog, Pred: Cat (conf=0.62)',
    'True: Bird, Pred: Cat (conf=0.58)',
    'True: Fish, Pred: Dog (conf=0.71)'
]

# Plot successes (top row)
for i, ax in enumerate(axes[0]):
    ax.imshow(img_success[i])
    ax.set_title(titles_success[i], fontsize=10, fontweight='bold')
    ax.axis('off')

# Plot failures (bottom row)
for i, ax in enumerate(axes[1]):
    ax.imshow(img_failure[i])
    ax.set_title(titles_failure[i], fontsize=10, fontweight='bold', color='red')
    ax.axis('off')

fig.suptitle('Qualitative Examples: Correct vs Incorrect Predictions', 
             fontsize=13, fontweight='bold', y=0.98)
plt.tight_layout()
plt.savefig('qualitative_examples.pdf', dpi=300, bbox_inches='tight')
plt.savefig('qualitative_examples.png', dpi=300, bbox_inches='tight')
plt.close()
```

**Conventions:**
- Show 3–6 examples per category (success, failure)
- Include confidence scores and true labels
- Use red or different styling for failure cases
- Always save as PDF + PNG, 300 dpi

### Caption for qualitative examples

"**Figure 7:** Qualitative results. (Top) Correct predictions with high confidence (≥0.92). (Bottom) Failure cases, often ambiguous images or rare angles. Confidence scores range from 0.58–0.71 for failures, suggesting the model expresses appropriate uncertainty."

## Matplotlib conventions used by data-scientist

### Figure setup

```python
import matplotlib.pyplot as plt
import numpy as np

# Consistent style
plt.rcParams['font.size'] = 11
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 14

# Colorblind-safe palette (Okabe-Ito)
colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
plt.rcParams['axes.prop_cycle'].by_key()['color'] = colors
```

### Saving figures

```python
# Always save as BOTH PDF (print quality) and PNG (preview/web)
plt.savefig('figure_name.pdf', dpi=300, bbox_inches='tight')
plt.savefig('figure_name.png', dpi=300, bbox_inches='tight')
plt.close()  # Free memory

# Use pdf not eps (eps is old)
# Use png not jpg (png is lossless)
```

### Line styles for clarity

```python
# Different line styles for different lines (accessibility for b/w printing)
ax.plot(x, y1, label='Method A', linewidth=2, linestyle='-', color='#1f77b4')
ax.plot(x, y2, label='Method B', linewidth=2, linestyle='--', color='#ff7f0e')
ax.plot(x, y3, label='Method C', linewidth=2, linestyle=':', color='#2ca02c')
```

### Grid and spine styling

```python
# Minimal grid, no spines on top/right
ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
```

### Colorblind-safe palettes

**Okabe-Ito palette (8 colors, accessible to colorblind people):**
```
#1f77b4 (blue)
#ff7f0e (orange)
#2ca02c (green)
#d62728 (red)
#9467bd (purple)
#8c564b (brown)
#e377c2 (pink)
#7f7f7f (gray)
```

**Sequential (for heatmaps):**
- Use `viridis`, `cividis`, or `twilight` (all colorblind-safe)
- Avoid `jet`, `rainbow`, `hot` (problematic for colorblind readers)

### Caption template

"**Figure N:** [One-line title]. [2–3 sentences describing what the figure shows, what it demonstrates, and any key takeaways]. [If applicable: error bars show ±1σ over N seeds / ×N runs.]"

Example:
"**Figure 4:** Learning curves for the proposed method and three baselines. The proposed method reaches 92% validation accuracy by epoch 60, 5 epochs faster than the next-best baseline. Error bands (±1σ) over 5 seeds show that convergence is stable."

## Table template for paper submission

```markdown
| Model | ImageNet | CIFAR-10 | CIFAR-100 | Δ vs ResNet-50 | Compute |
|-------|----------|----------|-----------|----------------|----------|
| ResNet-50 | 0.762 ± 0.005 | 0.968 ± 0.003 | 0.823 ± 0.004 | — | 12h GPU |
| EfficientNet-B0 | 0.788 ± 0.004 | 0.971 ± 0.002 | 0.838 ± 0.003 | +2.6% | 8h GPU |
| Vision Transformer | 0.812 ± 0.006 | 0.974 ± 0.004 | 0.851 ± 0.005 | +5.0% | 24h GPU |
| **Ours (proposed)** | **0.821 ± 0.005** | **0.976 ± 0.003** | **0.862 ± 0.004** | **+5.9%** | **14h GPU** |

* Results averaged over 5 random seeds; ± denotes standard deviation.
* Δ vs ResNet-50 reported for ImageNet accuracy.
* All methods use identical preprocessing and augmentation.
```

## How to draft captions

When producing a figure with `data-scientist`, the agent returns:

1. File path to the saved figure (PDF + PNG, 300 dpi)
2. A caption draft
3. The exact Python script that generated it

**Caption checking list:**
- [ ] Describes what is shown (not just "Results")
- [ ] Explains what insight or claim the figure supports
- [ ] Notes if error bars/bands present (what do they represent?)
- [ ] Mentions all datasets/conditions (if multiple)
- [ ] Is 2–4 sentences (not 1, not 10)
- [ ] Can stand alone (reader understands without reading main text)

