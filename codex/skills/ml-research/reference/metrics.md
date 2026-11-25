# ML Metrics Catalog

Task-appropriate metric selection, definitions, and reporting conventions.

## Classification

### Accuracy
- **Definition:** (TP + TN) / (TP + TN + FP + FN). Percentage correct.
- **When to use:** Balanced datasets only. Never alone on imbalanced data.
- **Pitfalls:** On imbalanced data (99% negative class), accuracy of 99% is useless. Always report per-class metrics too.
- **Reporting:** Accuracy = 0.856 ± 0.012 (5 seeds). If imbalanced, add per-class F1 or precision/recall per class.

### Precision & Recall
- **Precision:** TP / (TP + FP). Of predicted positive, how many were correct?
- **Recall (sensitivity):** TP / (TP + FN). Of actual positive, how many were found?
- **When to use:** Always report both for imbalanced classification. Different business metrics call for different trade-offs (medical screening: recall; spam detection: precision).
- **Pitfalls:** High precision, low recall = few predictions. High recall, low precision = many false alarms.
- **Reporting:** Per-class precision and recall; if binary, report for positive class only or both.

### F1-Score
- **Definition:** 2 × (precision × recall) / (precision + recall). Harmonic mean.
- **Macro F1:** Average F1 per class (unweighted).
- **Micro F1:** F1 computed globally (same as accuracy for multiclass).
- **Weighted F1:** F1 per class, averaged by class frequency.
- **When to use:** Imbalanced multiclass; penalizes both false positives and false negatives equally.
- **Reporting:** Report macro F1 for imbalanced data; micro F1 if classes are balanced. Example: "Macro F1 = 0.742 ± 0.018 (5 seeds)."

### AUROC (Area Under Receiver Operating Characteristic Curve)
- **Definition:** Integral of TPR vs FPR curve as threshold varies.
- **Range:** 0 to 1 (1 = perfect, 0.5 = random).
- **When to use:** Ranking problems; when you want threshold-independent metric; probability outputs.
- **Pitfalls:** AUROC is insensitive to class imbalance (both classes contribute equally). Does not tell you the best operating point.
- **Reporting:** AUROC = 0.891 ± 0.015 (5 seeds). Include ROC curve in paper.

### AUPRC (Area Under Precision-Recall Curve)
- **Definition:** Integral of precision vs recall curve.
- **Range:** 0 to 1 (class frequency baseline = % positive).
- **When to use:** Imbalanced data; when you care more about the positive class.
- **Pitfalls:** More sensitive to class imbalance than AUROC. Do not confuse with AUROC.
- **Reporting:** AUPRC = 0.743 ± 0.022 (5 seeds). Include PR curve.

### Matthews Correlation Coefficient (MCC)
- **Definition:** (TP×TN - FP×FN) / √[(TP+FP)(TP+FN)(TN+FP)(TN+FN)]
- **Range:** -1 to +1 (0 = random, 1 = perfect).
- **When to use:** Imbalanced binary classification. Better than accuracy for imbalanced data.
- **Pitfalls:** Symmetric (treats FP and FN equally); not suitable if cost asymmetry exists.
- **Reporting:** MCC = 0.624 ± 0.031 (5 seeds).

## Object Detection

### mAP (mean Average Precision) @ IoU threshold
- **Definition:** Average precision (area under precision-recall curve) averaged over IoU thresholds or classes.
- **Variants:**
  - mAP@0.5: IoU ≥ 0.5 (COCO common threshold)
  - mAP@0.75: IoU ≥ 0.75 (stricter)
  - mAP@[0.5:0.95:0.05]: average over IoU in 0.5 to 0.95 (COCO standard)
- **When to use:** Object detection benchmarks (COCO, Pascal VOC, etc.). Standard for the field.
- **Pitfalls:** mAP@0.5 is lenient; mAP@0.5:0.95 is stricter. Papers must specify which. Different datasets use different standards.
- **Reporting:** "mAP@0.5:0.95 = 0.312 ± 0.008 (3 seeds)" or "mAP@0.5 = 0.512 (single run, COCO validation set)."

### IoU per class
- **Definition:** Intersection over union per object class.
- **When to use:** Fine-grained analysis; know which classes are hard.
- **Reporting:** Table with class names and per-class IoU; highlight worst-performing class.

## Semantic Segmentation

### Dice Coefficient
- **Definition:** 2 × |X ∩ Y| / (|X| + |Y|). Overlap between prediction and ground truth.
- **Range:** 0 to 1 (1 = perfect overlap).
- **When to use:** Segmentation with class imbalance (medical imaging). Threshold-independent.
- **Pitfalls:** Treats all voxels equally; does not penalize boundary errors more than interior errors.
- **Reporting:** Dice = 0.876 ± 0.023 (5 seeds). Report per-class Dice for multiclass.

### mIoU (mean Intersection over Union)
- **Definition:** IoU per class, then averaged.
- **When to use:** Standard for semantic segmentation (Cityscapes, ADE20K).
- **Pitfalls:** Treats rare and common classes equally; if 1% of image is rare class, 50% IoU on rare class = 0.5% of overall mIoU.
- **Reporting:** mIoU = 0.652 ± 0.019 (5 seeds). Include per-class IoU table.

### Boundary F1
- **Definition:** F1 score at object boundaries (thin contour matching).
- **When to use:** Evaluate boundary quality separately from interior; often more informative than Dice for medical imaging.
- **Reporting:** Include boundary F1 alongside Dice; show where models fail (boundary-heavy vs background-heavy errors).

## NLP Tasks

### BLEU (Bilingual Evaluation Understudy)
- **Definition:** N-gram overlap (1 to 4-gram default) between prediction and reference, brevity penalty for short outputs.
- **Range:** 0 to 100 (100 = exact match all n-grams).
- **When to use:** Machine translation, sequence-to-sequence tasks.
- **Pitfalls:** Does not capture synonyms or paraphrase. BLEU ≤ 40 is common even for human-quality outputs. Do not rely on BLEU alone.
- **Reporting:** BLEU@4 = 28.5 (sacreBLEU corpus); always specify corpus and tokenization. Report alongside ROUGE and BERTScore.

### ROUGE (Recall-Oriented Understudy for Gisting Evaluation)
- **Definition:** N-gram recall vs reference (ROUGE-1/2/L for unigram/bigram/longest-common-subsequence).
- **Range:** 0 to 1.
- **When to use:** Summarization, abstractive tasks.
- **Pitfalls:** F-score of ROUGE can differ from recall; specify F, P, R. ROUGE-1 = unigram recall; highly correlated with length.
- **Reporting:** ROUGE-1 F = 0.412 ± 0.008, ROUGE-2 F = 0.187 ± 0.006, ROUGE-L F = 0.388 ± 0.009 (5 seeds).

### BERTScore
- **Definition:** Contextual embedding similarity (cosine between BERT token embeddings of prediction and reference).
- **Range:** 0 to 1.
- **When to use:** Semantic quality beyond surface n-grams; better correlation with human judgment than BLEU/ROUGE.
- **Pitfalls:** Requires pretrained model (default base-uncased); model choice affects scores. Do not compare BERTScore across different base models.
- **Reporting:** BERTScore (base-uncased) F = 0.921 ± 0.006 (5 seeds); always specify model and language.

### METEOR (Metric for Evaluation of Translation with Explicit Ordering)
- **Definition:** Unigram precision + recall with synonymy/paraphrase matching + word order penalties.
- **When to use:** Machine translation; combines surface and semantic matching.
- **Reporting:** METEOR = 0.384 ± 0.012 (5 seeds, test set).

### Perplexity
- **Definition:** 2^(cross-entropy loss). Geometric mean probability per token.
- **When to use:** Language model evaluation; lower is better.
- **Pitfalls:** Not comparable across different vocabularies. Must report on same test set.
- **Reporting:** Perplexity = 24.3 ± 1.8 (5 seeds, on standard test set e.g., WikiText-103).

### Exact Match (EM)
- **Definition:** Percentage of predictions exactly matching reference (binary: 0 or 1 per sample).
- **When to use:** QA, slot-filling, structured prediction.
- **Pitfalls:** Too strict for open-ended tasks. Use with F1 on tokens/entities.
- **Reporting:** EM = 0.684 ± 0.018 (5 seeds).

## Regression

### RMSE (Root Mean Squared Error)
- **Definition:** √(mean of (y_true - y_pred)²).
- **When to use:** Standard for regression; penalizes large errors more.
- **Pitfalls:** Sensitive to outliers. Report with MAE for robustness picture.
- **Reporting:** RMSE = 3.24 ± 0.18 (5 seeds). Include units (e.g., "3.24 meters").

### MAE (Mean Absolute Error)
- **Definition:** mean of |y_true - y_pred|.
- **When to use:** Regression; robust to outliers.
- **Pitfalls:** Does not heavily penalize large errors (RMSE is better for outlier-sensitive applications).
- **Reporting:** MAE = 2.15 ± 0.11 (5 seeds).

### R² (Coefficient of Determination)
- **Definition:** 1 - (SS_res / SS_tot); fraction of variance explained.
- **Range:** -∞ to 1 (1 = perfect, 0 = mean predictor, <0 = worse than mean).
- **When to use:** When you want a scale-independent goodness-of-fit.
- **Pitfalls:** R² alone does not mean good predictions (high R² on tiny range). Always show scatter plot + error distribution.
- **Reporting:** R² = 0.923 ± 0.008 (5 seeds), RMSE = 3.24 ± 0.18. Never R² alone.

### MAPE (Mean Absolute Percentage Error)
- **Definition:** mean of (|y_true - y_pred| / |y_true|) × 100%.
- **When to use:** When errors should be relative to target magnitude (e.g., forecasting).
- **Pitfalls:** Undefined if y_true = 0. Asymmetric (underpredictions and overpredictions penalized differently).
- **Reporting:** MAPE = 12.4% ± 2.1% (5 seeds).

## Signal Processing & Image Quality

### SNR (Signal-to-Noise Ratio)
- **Definition:** 10 log₁₀(P_signal / P_noise).
- **Unit:** dB.
- **When to use:** Audio, ECG, seismic, radar signal enhancement.
- **Pitfalls:** Definition of "noise" is task-dependent. Must clarify what is signal vs noise.
- **Reporting:** SNR = 18.5 ± 1.2 dB (5 seeds, averaged over test set).

### PSNR (Peak Signal-to-Noise Ratio)
- **Definition:** 10 log₁₀(MAX² / MSE), where MAX is max pixel value (e.g., 255 for 8-bit images).
- **Unit:** dB. Higher is better.
- **When to use:** Image compression, image restoration (denoising, super-resolution).
- **Pitfalls:** PSNR does not correlate well with human perception. Use with SSIM.
- **Reporting:** PSNR = 32.4 ± 0.6 dB (5 seeds, on test set). Include SSIM.

### SSIM (Structural Similarity Index)
- **Definition:** Correlation of luminance, contrast, and structure between images (range 0 to 1).
- **When to use:** Image quality assessment; correlates better with human judgment than PSNR.
- **Pitfalls:** Kernel window size affects results. Use same window size across papers.
- **Reporting:** SSIM = 0.891 ± 0.018 (5 seeds). Include PSNR too.

### Spectral Distortion
- **Definition:** Euclidean distance between predicted and ground-truth spectrogram (if applicable).
- **When to use:** Speech processing, audio restoration.
- **Pitfalls:** Normalize spectrograms before computing distance.
- **Reporting:** Spectral distortion = 1.23 ± 0.15 (log magnitude, 5 seeds).

## Retrieval & Ranking

### MRR (Mean Reciprocal Rank)
- **Definition:** mean of (1 / rank of first relevant item).
- **Range:** 0 to 1.
- **When to use:** Search, information retrieval (you want the first result to be correct).
- **Pitfalls:** Only cares about first relevant result; ignores ranking of the rest.
- **Reporting:** MRR = 0.743 ± 0.031 (5 seeds, on test set of 1000 queries).

### nDCG (Normalized Discounted Cumulative Gain)
- **Definition:** DCG / IDCG, where DCG = Σ (2^relevance_i - 1) / log₂(i+1) (discounts relevance by position), IDCG = perfect ranking.
- **Variants:** nDCG@k (truncate at rank k).
- **When to use:** Ranking tasks where position and graded relevance matter (not binary).
- **Pitfalls:** Depends on k (nDCG@10 vs nDCG@100 very different). Must specify k.
- **Reporting:** nDCG@10 = 0.821 ± 0.012 (5 seeds). Include nDCG@100 if applicable.

### Recall@k
- **Definition:** Fraction of relevant items in top-k results.
- **When to use:** How many correct answers are in top-k? (e.g., recall@5, recall@10).
- **Pitfalls:** Different k values give different stories.
- **Reporting:** Recall@10 = 0.654 ± 0.019 (5 seeds). Report multiple k if space.

## Clustering

### ARI (Adjusted Rand Index)
- **Definition:** Similarity between two clusterings (ground truth vs predicted), adjusted for chance.
- **Range:** -1 to 1 (1 = perfect agreement, 0 = random, <0 = worse than random).
- **When to use:** Evaluate clustering when ground truth is available.
- **Reporting:** ARI = 0.712 ± 0.045 (5 seeds, over 10 random cluster initializations each).

### NMI (Normalized Mutual Information)
- **Definition:** Mutual information between two label sets, normalized.
- **Range:** 0 to 1 (1 = perfect agreement).
- **When to use:** Clustering quality when ground truth exists.
- **Reporting:** NMI = 0.834 ± 0.028 (5 seeds).

### Silhouette Score
- **Definition:** mean silhouette coefficient; measures how similar each point is to its own cluster vs other clusters.
- **Range:** -1 to 1 (1 = well-separated clusters, 0 = overlapping, <0 = wrong assignment).
- **When to use:** Unsupervised clustering quality when ground truth unknown.
- **Pitfalls:** Does not require ground truth but can favor certain cluster shapes (spherical).
- **Reporting:** Silhouette score = 0.524 ± 0.062 (5 runs, average over all samples).

## Multi-metric reporting best practice

1. Report **mean ± standard deviation** (not min/max) over ≥3 runs with different random seeds.
2. For imbalanced classification: never accuracy alone. Always include per-class F1 and/or macro F1.
3. For ranking/retrieval: report multiple k values (e.g., nDCG@1, nDCG@10, nDCG@100).
4. For regression: pair RMSE with MAE and/or R² for full picture.
5. For image quality: always PSNR + SSIM; add others if applicable (LPIPS, FID for generative).
6. For NLP: BLEU + ROUGE + BERTScore together; never BLEU alone.
7. Statistical significance: report p-value and effect size (Cohen's d) if claiming superiority.

