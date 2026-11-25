# CS/Engineering Conference Papers

## Major Venues & Their Conventions

| Conference | Page limit | Style | Review focus | Typical acceptance rate |
|---|---|---|---|---|
| **ICML** | 8 + refs | NeurIPS style | Method novelty, experimental rigor, theoretical insight | ~25% |
| **NeurIPS** | 8 + refs | NeurIPS style | ML methods, learning theory, applications | ~25% |
| **ICCV** | 8 + refs + suppl | IEEE | Computer vision, novel architectures/datasets | ~25% |
| **ACL** | 8 + refs + suppl | ACL (2-col) | NLP, language understanding, benchmarks | ~25% |
| **IEEE** (various) | 6–8 | IEEE | Systems, applications, practical contributions | ~30–50% |
| **AAAI** | 6 | AAAI | AI broadly; strong acceptance variety | ~25% |

**Note:** Page limits are STRICT; exceeding them is grounds for desk rejection at many venues.

---

## Structure (Standard CS Conference Format)

### 1. Title & Abstract
- **Title:** Specific, conveys contribution (not: "A Neural Network Approach to X").
- **Abstract:** 150–250 words. Sections: Problem → Proposed approach → Key results → Significance.
- Example abstract:
  > "Image classification on edge devices requires models that are both accurate and computationally efficient. Existing approaches face a trade-off: lightweight models sacrifice accuracy, while high-accuracy models are too slow. We propose EdgeNet, a novel architecture combining depthwise convolution with adaptive batch normalization, achieving 92.4% accuracy on ImageNet while reducing inference latency by 40% on mobile devices. Extensive experiments on 5 datasets and 3 hardware platforms demonstrate consistent improvements over state-of-the-art efficient models. Code is available at [URL]."

### 2. Introduction
- **Problem statement:** (2–3 paragraphs) What's unsolved? Why does it matter?
- **Prior work summary:** (1–2 paragraphs) Existing approaches and their limitations.
- **Contribution statement:** "Our contributions are: (1) [specific technical novelty], (2) [empirical result], (3) [analysis/insight]."
- **Paper roadmap:** "Section 2 reviews related work; Section 3 presents our method; Section 4 reports experiments."
- **Word budget:** ~800 words.
- **Tense:** Present (general statements); past (prior work).

### 3. Related Work
- **Scope:** Don't repeat the entire field; focus on most relevant 10–20 papers.
- **Organization:** Group by approach (e.g., "Convolutional architectures," "Pruning methods," "Knowledge distillation").
- **Positioning:** For each group, explicitly state: "Smith et al. (2020) proposed X, which [limitation]. Our approach differs by [your innovation]."
- **Avoid:** Generic lists ("A proposes B, C proposes D…"). Make it conversational; show why prior work falls short.
- **Word budget:** ~1000–1200 words.

### 4. Method / Approach
- **Overview:** High-level idea (1 paragraph, maybe a diagram).
- **Detailed technical description:** 
  - Architecture (if novel): diagrams, pseudocode, equations.
  - Training procedure: loss functions, optimization, hyperparameters, training tricks.
  - Specific innovations: Which components are new?
- **Justify design choices:** "We use depthwise convolution because [reason: computational efficiency, prior success, etc.]."
- **Word budget:** ~1200–1500 words.

### 5. Experiments
- **Datasets:** Name, size, splits (train/val/test), why relevant.
- **Baselines:** List all comparison methods (cite them). CRITICAL: Are baselines fair?
  - Same training procedure? Same hyperparameter tuning? Same hardware?
  - If you use different training data, acknowledge it.
- **Metrics:** Define exactly (e.g., "Top-1 accuracy on ImageNet validation set").
- **Main results:** Table or figure showing your method vs. baselines.
  - **Format:** Method name × metrics columns. Bold best results. Include ± std if reporting multiple seeds.
  - Example:
    ```
    | Method           | Accuracy (%) | Latency (ms) | Params (M) |
    |------------------|--------------|--------------|-----------|
    | MobileNetV2      | 72.0 ± 0.3   | 45.2         | 3.5       |
    | EfficientNetB0   | 77.1 ± 0.2   | 38.1         | 5.3       |
    | **EdgeNet** (ours) | **79.4 ± 0.2** | **32.5**    | **4.1**   |
    ```
- **Ablation studies:** Remove each component; show its contribution.
  - Table: Method × variant (full model, -component A, -component B, etc.) × metric.
- **Sensitivity analyses:** Hyperparameter sensitivity, training data size, etc. (figures or brief tables).
- **Statistical significance:** Report over multiple seeds (n=5 minimum); use confidence intervals or error bars. If comparing two methods, consider significance testing (t-test, sign test) and report it.
- **Word budget:** ~1200–1500 words (bulk of the paper).

### 6. Results & Discussion
- **Interpretation:** What do results show? Do they support the claims?
- **Ablation interpretation:** Which components matter most?
- **Failure cases:** When does your method not work? Why?
- **Comparison to baselines:** Not just numbers; explain why your approach is better (is it more general, more efficient, more robust?).
- **Limitations:** Honest assessment (e.g., "Our method assumes [X]; on datasets without [X], performance drops").
- **Word budget:** ~800–1000 words (can be combined with Results).

### 7. Conclusion
- **Summary:** Restate contribution and main results.
- **Implications:** Why does this matter? What does it enable?
- **Future work:** Open questions, limitations to address.
- **Word budget:** ~300–400 words.

### 8. Reproducibility Statement (NeurIPS/ICML requirement)
- **Dataset availability:** "ImageNet used in experiments is publicly available at [link]. Our custom dataset is available at [link]."
- **Code:** "Code is available at https://github.com/[repo]. Supplementary materials include [what]."
- **Training details:** "All experiments were run on NVIDIA V100 GPUs. Training time: ~12 hours. Learning rate decay, batch size, optimizer: [specify]. Trained with PyTorch 1.10.2."
- **Random seeds:** "All results are averaged over 5 runs with different random seeds: [list seeds]."
- **Hardware/software versions:** "Results may vary slightly with different PyTorch versions; we tested with 1.10.2 and 1.11.0."

---

## Baseline Fairness (CRITICAL for reviewing & publishing)

The #1 criticism of ML papers: baselines aren't comparable.

### Fairness checklist

- [ ] **Same hyperparameter tuning budget:** If you spent 2 weeks tuning your method, spend 2 weeks on baselines too (or be explicit about it).
- [ ] **Same training data:** Did you use data augmentation your baselines didn't? Same preprocessing?
- [ ] **Same compute budget:** If comparing to a smaller baseline, acknowledge it; compare like-for-like (e.g., same model size, same latency budget).
- [ ] **Recent baselines:** Don't compare to 10-year-old methods; include recent SOTA.
- [ ] **Multiple runs:** Report std dev or CIs for all methods (not just yours). If your method has ±0.5%, show baselines' ±s too.
- [ ] **Re-implementation check:** Did you re-implement baselines or use published numbers? Re-implementations often perform better (different library, optimizations). Be explicit.

### Fair baseline statement

> "We compared our method against [baseline names]. For fair comparison, we: (1) used the same data augmentation for all methods, (2) tuned hyperparameters equally for our method and baselines using the validation set, (3) reported results over 5 runs with different seeds, and (4) used the same hardware (V100 GPU) for all experiments. Results are [table]."

---

## Ablation Study Design

An ablation shows which components of your method contribute to performance.

### Good ablation

| Variant | Accuracy | Latency |
|---------|----------|---------|
| Baseline (standard CNN) | 72.0% | 45ms |
| + Depthwise conv (ours) | 75.2% | 38ms |
| + Adaptive BN (ours) | 77.1% | 36ms |
| + Skip connections (ours) | 79.4% | 32ms |
| **Full method** | **79.4%** | **32ms** |

**Caption:** "Ablation study on ImageNet validation set. Each row shows the contribution of one component. Depthwise convolution provides the largest improvement (3.2%), followed by adaptive batch normalization (1.9%)."

### Poor ablation (AVOID)

- Removing multiple components at once (can't tell which helps).
- Ablating without reporting key metrics (e.g., showing accuracy but not latency when latency is a claimed benefit).
- Ablations on a toy dataset not representative of real performance.

---

## Page & Figure Conventions

### Fitting into page limits

- **Font size:** 10pt minimum (reviewers need to read it).
- **Figures & tables:** Aim for ~1 per 500 words. Use 2-column layout efficiently.
- **Text placement:** Keep text next to related figures (avoid "see Figure 3 on page 8" when Figure 3 is on page 2).
- **Captions:** Self-contained; reader shouldn't need to read text to understand the figure.

### Figures (best practices)

- **Comparison plots:** Line plots (method × hyperparameter/dataset), bar charts (method × metric), confusion matrices, learning curves.
- **Architecture diagrams:** Block diagrams (clear flow); annotate dimensions (e.g., "32×32×64" for layer output).
- **Qualitative results:** Show success and failure cases side-by-side.
- **Heatmaps:** Use colorblind-friendly palettes (viridis, not jet).
- **Resolution:** 300 DPI if images; vector graphics (PDF, SVG) for plots (resizable).

### Tables

- **Compact:** Fit on one column if possible; if spanning both columns, align it at the top of a page.
- **Emphasis:** Bold best results (per column). Underline second-best if appropriate.
- **Clarity:** Column headers = metric names + unit (e.g., "Accuracy (%)", "Latency (ms)").
- **Caption:** "Table 1. Main results on ImageNet. Our method (EdgeNet) achieves [X]% accuracy while [Y]ms latency. Comparisons: [A] [advantage], [B] [disadvantage]."

---

## Checklist Before Submission

| Item | Status |
|------|--------|
| Title is specific & clear | ☐ |
| Abstract is 150–250 words, has problem/method/results/significance | ☐ |
| Related work clearly positions our contributions vs. prior work | ☐ |
| Method section is detailed enough to re-implement | ☐ |
| Experiments section specifies: datasets, baselines, metrics, splits | ☐ |
| Baselines are fair (same tuning, same data, recent SOTA) | ☐ |
| Ablations show contribution of each component | ☐ |
| Results tables/figures: all methods have std dev or error bars | ☐ |
| Results are clearly labeled (bolded best, legends clear) | ☐ |
| Limitations and failure cases discussed | ☐ |
| Reproducibility statement: code, data, hyperparameters, hardware | ☐ |
| Page count ≤ page limit (main paper + references only) | ☐ |
| Figures readable at full-page size; captions self-contained | ☐ |
| Writing is clear; no grammatical errors | ☐ |
| All citations have author names, years, venues (not just "et al.") | ☐ |
| No author identifying information in main paper (anonymized for review) | ☐ |
| Appendix/supplementary material has additional ablations, qualitative results | ☐ |

---

## Camera-Ready (Post-Acceptance)

After acceptance, most conferences require a **camera-ready** version with revisions.

### Common camera-ready tasks

- **Address reviewer feedback:** Revise text, update experiments, add missing baselines.
- **Update references:** Add citations to papers that came out during review (note: some venues freeze references at camera-ready deadline).
- **Final proofs:** Typeset correctly; images at correct resolution.
- **Acknowledgments:** Add (was omitted during review to preserve anonymity); acknowledge funding.
- **Supplementary materials:** Submit extended ablations, proofs, qualitative results not in main paper.

### Supplementary materials (best practices)

- Extended ablations or sensitivity analyses.
- Proofs of theorems (if theoretical contribution).
- Additional qualitative examples (failures, edge cases).
- Code/model release details (if applicable).
- Ethical considerations (if applicable; increasingly expected).
- **Keep supplementary materials BRIEF** (reviewers read them selectively).

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Baselines are weak or outdated | Use recent SOTA; ensure fair comparison (same tuning, data) |
| Ablation doesn't isolate components (removes multiple at once) | Remove one component per row; keep everything else the same |
| Results lack error bars or std dev | Report over ≥3 seeds; show ±std in tables or error bars in figures |
| Method description too vague to re-implement | Include pseudocode, hyperparameters, training details, software versions |
| Related work lists papers without saying how they differ from ours | For each prior work, state: "Smith et al. proposed [X], which [limitation]. Our approach [innovation]." |
| Overstated claims ("state-of-the-art" when baselines are weak) | Be precise: "Outperforms [specific baselines] on [dataset]; slightly below [harder baseline]" |
| Figures unreadable at actual page size (too small font, lines too thin) | Print draft at actual size; text must be 10pt minimum; lines visible |
| Page limit exceeded (appendix counts for some venues) | Ruthlessly cut; move details to supplementary materials if allowed |
| Code not released despite reproducibility claim | Release early (anonymized repo); commit to release timeline in appendix |

---

## Rebuttal (Post-Review, if Accepted & Revised)

If your paper receives feedback requiring a rebuttal or revision:

### Rebuttal format (if required)

1. **Summarize each review:** "Reviewer 1 raised three concerns: (1) [X], (2) [Y], (3) [Z]."
2. **Address each point:** 
   - If you agree, explain how you revised: "We now [action]; see revised Section [X]."
   - If you disagree, explain why politely: "We respectfully disagree because [reasoning]. However, we added [clarification] to address the concern."
3. **Highlight changes:** "Main changes: (1) Added comparison to [baseline] (Table 3). (2) Expanded ablation in Section 4.2. (3) Clarified method in pseudocode."

### Tone

- Respectful (reviewers are volunteers).
- Specific (reference section numbers, table numbers).
- Honest (if you can't implement a suggestion, explain why; offer alternative).

---

## References

- **Conventions:** IEEE, ACM, NeurIPS author guides (check conference website).
- **Machine Learning for Systems papers:** Frequently published in NeurIPS, ICML, OSDI, SOSP (good models to emulate).
- **Benchmark datasets:** Discuss in Methods; cite original paper.
