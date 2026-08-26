---
name: academic-writing
description: Use when drafting sections or editing for clarity. Provides paragraph architecture (topic→evidence→interpretation→bridge), per-section tense discipline, hedging ladders, banned patterns, signal-word banks, and language-specific conventions (Turkish register, English articles). Covers paraphrase discipline with source fidelity.
---

# Academic Writing: Core Conventions

## Paragraph Architecture (Universal Model)

Every paragraph should follow: **Claim → Evidence → Interpretation → Bridge**.

### 1. Claim (Topic Sentence)
- **Function:** States the main idea or assertion of the paragraph.
- **Form:** Usually the first sentence; sometimes the second (after a transition).
- **Examples:**
  - "Deep learning has revolutionized image classification tasks."
  - "Prior studies disagree on the effect of X."
  - "Method A has three major limitations."

### 2. Evidence (Supporting Material)
- **Function:** Grounds the claim with data, citations, or examples.
- **Forms:**
  - **Citation:** "Research shows that [@author2024key]."
  - **Data:** "Our experiments yielded a 92% accuracy rate."
  - **Example:** "For instance, in the MNIST dataset, convolutional networks outperformed…"
  - **Logic:** "If we accept that X leads to Y, and we observe X, then…"

### 3. Interpretation (Explanation)
- **Function:** Explains *why* the evidence matters; connects it to the claim.
- **Form:** "This indicates that…" or "What this suggests is…" or "In other words…"
- **Example:** "This 5% improvement is significant because it suggests that the proposed loss function better captures…"

### 4. Bridge (Transition)
- **Function:** Connects this paragraph to the next; shows flow of thought.
- **Forms:**
  - **Forward-looking:** "Having established X, we now turn to Y."
  - **Comparative:** "Similarly, prior research on Y…"
  - **Causal:** "Because X holds true, the implications for Y are…"

### Full Example

> **Claim:** "Deep learning models trained on insufficient data often overfit, reducing generalization to unseen examples." **Evidence:** "Chen et al. (2023) found that a CNN trained on only 500 images achieved 87% accuracy on training data but 61% on held-out test data ([@chen2023name])." **Interpretation:** "This 26-point gap indicates that the model learned noise or dataset-specific patterns rather than generalizable features." **Bridge:** "To address this, regularization techniques like dropout and data augmentation have become standard practice in the field."

---

## Per-Section Tense Discipline

### Introduction (Present Tense)
- Describe the field, state general knowledge, pose questions.
- **Example:** "Neural networks have been the dominant approach for image classification." (present perfect = established fact)
- **Guideline:** Use present tense to speak about the state of the field. Use past tense only for specific prior findings: "Smith et al. (2020) found that…"

### Methods (Past Tense)
- Describe what you did (specific to your work).
- **Example:** "We recruited 50 participants and conducted semi-structured interviews lasting 60 minutes."
- **Guideline:** Everything you did is in the past (even if writing in present session). The procedure is complete before writing.

### Results (Past Tense)
- Report what you found.
- **Example:** "Results showed that the proposed method achieved 94.2% accuracy, compared to 87% for the baseline."
- **Exception:** If presenting data in a table, the table itself is timeless (present tense OK for table headers: "Accuracy (%)").

### Discussion (Present Tense + Hedging)
- Interpret findings, compare to literature, theorize.
- **Example:** "These findings suggest that the loss function improves generalization (present), as evidenced by our results (past). Prior work indicates similar patterns [@citation2024]."
- **Guideline:** Hedging is appropriate here (you're interpreting, not stating absolute truth).

### Conclusion (Present Tense)
- Summarize and look forward.
- **Example:** "This work demonstrates that X is possible. Future research should investigate whether Y applies to…"

---

## Hedging Ladder (Claim Strength vs. Evidence Strength)

Match hedging language to your evidence strength:

| Strength | Verb/Phrase | Example |
|----------|-------------|---------|
| **5 (Certain)** | demonstrate, show, prove, establish | "Results demonstrate that X causes Y." (use only with strong evidence: RCT, multiple studies) |
| **4 (Strong)** | indicate, suggest, provide evidence that | "Findings indicate that X likely causes Y." (good evidence: consistent pattern, multiple datasets) |
| **3 (Moderate)** | suggest, imply, hint at, appear to | "Results suggest that X may influence Y." (decent evidence: one solid study, needs replication) |
| **2 (Weak)** | may suggest, might, could | "These findings may suggest that X could influence Y." (limited evidence: single study, small N) |
| **1 (Uncertain)** | may possibly, might tend to | "One might speculate that X possibly influences Y." (very limited, avoid in academic writing) |

### Examples

| Claim | Strength | Hedged Phrasing |
|-------|----------|-----------------|
| Your hypothesis is supported | 4–5 | "Results **demonstrate** the hypothesis" (RCT, large sample, clear effect) |
| You found a pattern but it's not universal | 3–4 | "This **suggests** a pattern; further work is needed to confirm" |
| One prior study found something | 2–3 | "One study **indicates** that X; however, replication is needed" |
| You're speculating | 1–2 | Avoid or use: "Future work could explore whether…" |

---

## Banned Patterns (Eliminate These)

### 1. Vague "This" (without noun anchor)
| Bad | Good |
|-----|------|
| "The model was trained for 100 epochs. This improved accuracy." | "The model was trained for 100 epochs. **This training regime** improved accuracy." Or: "As a result, accuracy improved." |
| "We used data augmentation. This is important." | "We used data augmentation. **This technique** is important because…" |

**Fix:** Replace "This" with "This [noun]" or rewrite to avoid ambiguity.

### 2. Chained Nominalizations (noun → noun → noun pileup)
| Bad (Hard to parse) | Good (Clear structure) |
|-----|------|
| "The implementation of the adoption of the framework requires understanding of the theory underlying…" | "To implement the framework, researchers must understand the underlying theory…" |
| "Improvement in model accuracy through regularization application shows regularization method effectiveness." | "Regularization improves model accuracy, demonstrating regularization's effectiveness." |

**Fix:** Use verbs instead of nouns where possible. "Implementation requires" not "Implementation of X requires."

### 3. Empty Intensifiers (add no meaning)
| Bad | Good |
|-----|------|
| "This is a **very important** finding." | "This finding is significant because [explain why]." |
| "The results are **quite remarkable**." | "The results show [specific outcome that is remarkable]." |
| "The method is **extremely novel**." | "The method differs from prior work by [specific difference]." |

**Fix:** Show the importance via specificity, not adjectives. Let data/analysis speak.

### 4. Weak Passivity (hiding the agent)
| Bad | Good |
|-----|------|
| "It was found that X improves Y." | "Our experiments show that X improves Y." |
| "It is believed that…" | "Researchers believe that…" or "Current theory suggests that…" |
| "The model was trained." (by whom? when?) | "We trained the model for 100 epochs using SGD with learning rate 0.001." |

**Fix:** Use active voice when possible. Passive is OK for methods if agent is clear from context.

### 5. Hedging Gone Wrong (too much or too little)
| Bad (Over-hedged) | Bad (Overconfident) | Good |
|---|---|---|
| "It might possibly be suggested that perhaps X could conceivably influence Y." | "X definitely causes Y." (without evidence) | "Evidence suggests that X influences Y." |
| "One could speculate that…" (avoid) | "Our single experiment proves X." | "Our results indicate X; further validation is needed." |

**Fix:** Match hedging to evidence. Use the ladder above.

---

## Signal-Word Bank (Transitions & Connectivity)

### Contrast / Opposition
- "However," "In contrast," "Conversely," "Yet," "Although," "Despite this," "On the other hand."
- Example: "Traditional methods are faster; **however**, they sacrifice accuracy."

### Concession (accepting a point before arguing yours)
- "Granted," "Admittedly," "One could argue that," "To be fair," "It is true that…"
- Example: "**Granted**, prior work has shown X; our results suggest Y is also important."

### Causality / Reason
- "Because," "Since," "As a result," "Therefore," "Consequently," "Thus," "This explains why."
- Example: "**Because** the dataset was imbalanced, we used stratified sampling."

### Addition / Reinforcement
- "Furthermore," "Moreover," "In addition," "Also," "Similarly," "Likewise."
- Example: "The method is accurate. **Moreover**, it is computationally efficient."

### Emphasis / Importance
- "Notably," "Significantly," "Importantly," "It is worth noting that," "Crucially."
- Example: "**Notably**, this is the first study to combine X and Y."

### Temporal / Sequential
- "First," "Subsequently," "Meanwhile," "Finally," "Earlier," "Following this."
- Example: "**First**, we collected data. **Subsequently**, we analyzed it."

### Summary / Conclusion
- "In summary," "In conclusion," "To summarize," "Overall," "In short," "To recap."
- Example: "**In summary**, our findings suggest three key implications."

### Example / Illustration
- "For instance," "For example," "Specifically," "To illustrate," "Consider…"
- Example: "Our method applies to various domains. **For instance**, in medical imaging, it achieved 98% accuracy."

---

## Paragraph Cohesion Checklist

Before submitting a draft:
- [ ] Does every paragraph have a clear topic sentence (claim)?
- [ ] Is there evidence (citation or data) supporting the claim?
- [ ] Is there interpretation (why does this matter)?
- [ ] Does the paragraph end with a bridge to the next paragraph (or final sentence connects to next idea)?
- [ ] Do sentences within the paragraph use signal words (however, moreover, for instance) to show relationships?
- [ ] Is tense consistent and appropriate for the section?
- [ ] Are hedges matched to evidence (strong claim = strong evidence)?

---

## Language-Specific Guidance

### Turkish Academic Writing
See **[turkish-academic.md](reference/turkish-academic.md)** for:
- Passive voice norm (yapılmıştır, bulunmuştur)
- Term unity (one concept = one Turkish term throughout)
- TDK number/unit conventions
- Common expression errors

### English Academic Writing
See **[english-academic.md](reference/english-academic.md)** for:
- Article usage (the #1 error of Turkish authors)
- Collocation bank for academic verbs
- Nominalization-overload repair patterns

### Paraphrase Discipline
See **[paraphrase.md](reference/paraphrase.md)** for:
- Source-faithful paraphrase technique
- "Change the structure too" rule
- Self-check questions
- When to quote verbatim (with page-number discipline)

---

## Claim Strength: Never Say More Than Your Source

A citation can be real, resolvable and correctly formatted while the sentence
built on it still misrepresents the cited work. `/verify-citations` answers
"does this reference exist?"; it cannot answer "does it say that?".

The ordered scale (rungs 0–5, TR + EN), the one-directional rule (writing
*weaker* than your source is always safe; writing *stronger* is the defect), the
attributive-participle trap ("reduced capacity" is an outcome, not a claim), and
the evidence→rung table live in **[claim-strength.md](reference/claim-strength.md)**.

Deterministic half: `python scripts/claim_check.py` compares each cited
sentence's rung against the evidence cards for the sources it cites, and flags
empirical assertions carrying neither a citation nor an own-work marker.
WARN-only — a rung difference is often legitimate; the check exists so you make
that call deliberately.

---

## Quick Reference: Tense Table

| Section | Tense | Example |
|---------|-------|---------|
| **Introduction** | Present (general knowledge); past (prior studies) | "Research **shows** that X is important. Smith et al. **found** that…" |
| **Methods** | Past (what we did) | "We **recruited** 50 participants. Data **were analyzed** using…" |
| **Results** | Past (what we found) | "Results **showed** a 5% improvement. The method **achieved** 92% accuracy." |
| **Discussion** | Present (interpretation, theory); past (our results) | "Our findings **suggest** that…. **We found** that…" |
| **Conclusion** | Present (broader implications, general statements) | "This work **demonstrates** that X **is** possible. Future work should **investigate** Y." |

---

## One-Sentence Summaries Per Reference File

- **turkish-academic.md:** Use passive voice as the norm, maintain term unity (EN term in parentheses on first mention), apply TDK conventions for numbers/units.
- **english-academic.md:** Master article usage (a/an vs. the), use strong academic collocations (not "have an issue" but "face a challenge"), avoid nominalization overload.
- **paraphrase.md:** Paraphrase with structure change, cite the source, check that meaning is preserved without copying phrasing, quote verbatim only for key passages (with page numbers).
- **claim-strength.md:** Keep every claim on the rung its source actually supports; weakening is safe, strengthening is the defect; watch for adjectives silently promoted into verbs.

---

## Practice Exercises

### Exercise 1: Fix the vague "this"
> "The model achieved 95% accuracy. This was a major breakthrough."

**Answer:** "The model achieved 95% accuracy. **This performance** was a major breakthrough (an 8-point improvement over prior work)."

### Exercise 2: Fix the nominalizations
> "The implementation of the algorithm through the use of data augmentation resulted in accuracy improvement."

**Answer:** "Implementing the algorithm with data augmentation improved accuracy."

### Exercise 3: Match hedging to evidence
> Evidence: One study with n=20 found X. Your phrasing: "X is proven."

**Answer:** "Preliminary evidence suggests that X may occur; larger studies are needed to confirm."

### Exercise 4: Add signal words
> "The method is fast. It is accurate. It is cheap. These are advantages."

**Answer:** "The method is fast. **Moreover**, it is accurate. **Furthermore**, it is cheap. **Together, these characteristics** make it attractive for deployment."

---

## References & Resources

- See reference files for language-specific guidance:
  - [reference/turkish-academic.md](reference/turkish-academic.md)
  - [reference/english-academic.md](reference/english-academic.md)
  - [reference/paraphrase.md](reference/paraphrase.md)
  - [reference/claim-strength.md](reference/claim-strength.md)
- APA 7 Style Guide: aspastyle.apa.org
- Merriam-Webster for academic collocations and usage.
