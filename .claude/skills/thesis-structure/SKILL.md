---
name: thesis-structure
description: "Thesis architecture & defense-prep KNOWLEDGE — BSc, MSc, PhD structure; classic 5-chapter + cumulative (article-based) variants; RQ↔chapter mapping with word_budget.py --rq-trace; Turkish thesis (YÖK) requirements (front-matter order, Özet↔Abstract equivalence, ethics declaration, acknowledgments, approval page); institute guideline ingestion; the concepts behind defense prep (viva questions, answer skeletons, presentation outline). Use when structuring or auditing a thesis, or preparing Özet/Abstract. To actually RUN guided defense preparation (jury question bank + presentation scaffold) use the /defense-prep command — this skill is its underlying knowledge, not the command."
---

## 1. Thesis Architecture Types

### 1.1 Classic 5-Chapter Structure

Standard for all thesis levels (BSc, MSc, PhD). Each chapter has a defined purpose and typical word proportion:

| Chapter | Purpose | Typical % | Content core |
|---------|---------|-----------|--------------|
| **1. Introduction** | Frame problem, state RQs, claim novelty | 15% | background, gap, research questions, thesis outline |
| **2. Literature Review** | Map prior work, position your contribution | 20% | thematic synthesis (not annotated bibliography), identifies gaps, hypotheses |
| **3. Methodology** | Describe design, methods, tools, data | 25% | study design, participants/data, procedures, analysis strategy, validity measures |
| **4. Results/Findings** | Present outcomes, data analysis results | 20% | organized per RQ (headings must mirror RQ statements), tables, figures, no interpretation |
| **5. Discussion & Conclusion** | Interpret, compare, claim contributions | 20% | answer each RQ, situate vs literature, limitations, future work, practical implications |

**RQ-Mapping Rule (enforced by `word_budget.py --rq-trace`):**  
Every RQ stated in Ch.1 must have a corresponding Results section heading in Ch.4 and a claim in Ch.5. Execute:
```bash
python scripts/word_budget.py --rq-trace
```
Returns mapping: RQ1 → Section 4.1.1 heading → Discussion answer, or FLAG if missing.

**Typical word counts (adjust per institution, field, degree):**
- BSc: 8,000–15,000 words
- MSc: 25,000–50,000 words
- PhD: 80,000–150,000 words

### 1.2 Cumulative (Article-Based) Thesis

Structure when your thesis comprises ≥2 peer-reviewed / submitted journal papers:

```
Ch.1: General Introduction (framing, overall RQ, synthesis of papers' motivation)
Ch.2: Literature Review (cross-cutting themes across the papers)
Paper 1 (standalone Methods + Results, verbatim or lightly adapted)
Paper 2 (standalone Methods + Results)
Ch.5: General Discussion (synthesize across papers, implications, limitations, future work)
```

**Front-matter (same as classic) + binding narrative** between papers. Each paper retains its own abstract; the dissertation gains an Özet + Abstract at the start. Common in STEM fields where students have multiple publications by completion.

---

## 2. Cross-Chapter Logic Chain

### Integrity checks (audit before finalization)

1. **Novelty cascade:**
   - Ch.1 Literature Review identifies a gap.
   - Ch.3 Methodology describes your unique approach to close it.
   - Ch.4 Results present the outcome.
   - Ch.5 claims this outcome answers the gap.

2. **RQ traceability:**
   - Ch.1: "RQ1: Does method X outperform baseline Y under constraint Z?"
   - Ch.4: Heading "4.2.1 Performance Comparison: Method X vs Baseline Y" (no rewording).
   - Ch.5: "RQ1 was answered via [comparison table 5]: X achieved ±% better accuracy…"

3. **Limitation honesty:**
   - Ch.3 methodology describes scope, participant/data size, design choice rationale.
   - Ch.5 explicitly names what you couldn't do and why (sample size, generalizability, confounds).

4. **Consistency across languages (if bilingual):**
   - Özet (Turkish) Ch.1–Ch.5 structure mirrors English Abstract word for word. See reference/yok-tr.md Section 2.

---

## 3. Chapter-by-Chapter Guidance

### Chapter 1: Introduction (target: 12–18% of total)

**Moves (in order):**
1. **Hook:** Context — why the problem matters (broader field, practical need, or theoretical gap).
2. **Problem statement:** Specific gap or unresolved question.
3. **Literature positioning:** "Prior work has shown X and Y, but no one has studied [your angle]."
4. **Explicit RQs:** Numbered (RQ1, RQ2, etc.). Testable, not rhetorical.
5. **Thesis outline:** One sentence per chapter ("Ch.2 reviews…").

**Discipline:** Active voice, present tense for established fact, future for your work ("This thesis explores…").

### Chapter 2: Literature Review (18–22%)

**Synthesis, not summary.** Group sources by theme, NOT by paper.

**Structure option A (thematic):**
```
2.1 Foundational Concept (3–4 sources in conversation)
2.2 Prior Approaches (contrast 2–3 methods)
2.3 Limitations and Gaps (what the literature misses)
```

**Structure option B (chronological with themes):**
```
2.1 Early Work (1990–2005)
  2.1.1 Methodological approaches in that era
  2.1.2 Key findings and limitations
2.2 Recent Developments (2006–present)
  2.2.1 Emerging methods
  2.2.2 Unresolved questions
```

**Anti-pattern:** "Author A says X. Author B says Y. Author C says Z." (annotated bibliography) → **FWD: Replace with synthesis.** One paragraph should reference ≥2 sources in substantive conversation.

**Paragraph formula:**  
Topic sentence + Evidence (cite EV-cards or [@surname2024]) + Interpretation + Gap statement + Bridge to next paragraph.

### Chapter 3: Methodology (22–28%)

**Replicability standard:** Another researcher must be able to reproduce your study using this chapter alone.

**Sections (adjust per design type):**
```
3.1 Study Design
    (observational, experimental, mixed, qualitative)
3.2 Participants / Data / Materials
    (recruitment, inclusion/exclusion, size justification, source)
3.3 Data Collection / Procedures
    (instruments, protocols, timeline, validation)
3.4 Data Analysis
    (statistical tests, thematic coding, software, version)
3.5 Validity Measures / Ethics
    (reliability/validity, ethical approval, informed consent)
```

**For ML-based theses:**
- Specify dataset(s): source, size, splits (train/val/test %), sampling strategy.
- Environment: Python version, libraries (versions!), hardware (GPU model if relevant).
- Hyperparameters: table of search range and final selection.
- Baselines: justify each baseline choice; why is it fair?
- Seeds: "N=5 independent runs with random seeds [list]."
- Ablations: what's being tested in each ablation, why?

**Dispatch methodology-advisor before drafting this chapter (DESIGN mode) and
again after drafting it (CRITIQUE mode)** — it is the kit's read-only methodology
expert and this chapter is exactly its INPUT CONTRACT's domain (classic empirical
design + ML experiment design):
- **What:** "Propose a methodology for these RQs" (DESIGN, before Section 3.1 is
  written) or "Audit this Methods draft — run the replicability test" (CRITIQUE,
  after `/draft methodology` produces `drafts/methodology.md`)
- **Mode:** DESIGN | CRITIQUE | QUESTION (methodology-advisor's INPUT CONTRACT enum)
- **Context:** RQs/hypotheses from PROJECT.md, field, data availability/constraints;
  for ML theses also task type, datasets under consideration, candidate baselines
- **Draft path (CRITIQUE only):** `drafts/methodology.md`

The agent returns (read-only, no edits): verdict (sound | fixable | redesign-needed)
or the recommended design, numbered issues/decisions, a validity-threat table, and
the matching reporting-guideline pointer. Apply its fixes before `/critique` —
reviewer-critic will independently re-score the same weaknesses if they reach a
full peer review unaddressed.

### Chapter 4: Results / Findings (18–25%)

**No interpretation; facts only.** All interpretation → Discussion.

**Organization per RQ:**
```
4.1 Results for RQ1
    4.1.1 [Specific outcome heading]
    [Table / Figure]
4.2 Results for RQ2
    [analogous structure]
```

**Discipline:**
- Heading text must match the RQ phrasing (word_budget.py --rq-trace checks this).
- Describe figures/tables in text (never: "see Figure 3").
- Report with precision: means ± std (over N runs), confidence intervals, p-values.
- For qualitative: theme labels + representative quotes with page numbers.

**ML theses:**
- Comparison table: method (rows) × criterion (columns); bold best per column.
- Include baseline results (necessary for fair comparison).
- Report N seeds, mean±std, statistical test of significance (if applicable).
- Ablation results (what happens when you remove component X?).

### Chapter 5: Discussion & Conclusion (18–25%)

**Structure:**
```
5.1 Interpretation of Findings (per RQ)
5.2 Comparison with Prior Work
5.3 Limitations
5.4 Practical Implications
5.5 Future Work
5.6 Conclusion (summary statement)
```

**5.1: Interpretation**
- Restate each RQ, answer it with your result.
- Explain *why* the result occurred.
- Use hedging language appropriate to evidence strength (demonstrates > indicates > suggests).

**5.2: Comparison**
- How do your results align with / diverge from the literature?
- If conflict exists, propose an explanation (context differences, methodological, sample).
- Cite both supporting and contradicting prior work; don't hide conflicts.

**5.3: Limitations**
- Name constraints: sample size, generalizability scope, design trade-offs, confounds.
- For each, describe its impact: "This limits our ability to [X], relevant for [scenario]."
- NOT: "We had a small sample" (obvious). INSTEAD: "N=20 limits power to detect medium effects (β>0.20)."

**5.4: Practical Implications**
- Who benefits from this work? How?
- What should practitioners do differently based on these results?
- What should policymakers or institutions consider?

**5.5: Future Work**
- Logical next steps emerging from your findings or unresolved limitations.
- Avoid vague ("Further research is needed").
- INSTEAD: "Future work should test whether [mechanism] generalizes to [new population], which would require [design change]."

**5.6: Conclusion**
- 3–5 sentences. Restate the thesis claim, main finding, and significance.
- One-sentence vision: "This work opens the possibility of [X]."

---

## 4. Turkish Theses (YÖK Compliance)

Full Turkish-specific requirements, guidelines for Özet↔Abstract equivalence, and how to ingest your institution's guideline are in **reference/yok-tr.md**. Key points:

- **Front-matter order** (non-negotiable in Türk univ.):
  1. Inner cover (iç kapak)
  2. Approval page (onay sayfası)
  3. Ethics declaration (etik beyan)
  4. Acknowledgments (teşekkür)
  5. Turkish summary (Özet) — if Turkish is the thesis language
  6. English summary (Abstract)
  7. Table of contents (İçindekiler)
  8. List of tables (Tablo listesi)
  9. List of figures (Şekil listesi)

- **Özet↔Abstract equivalence:** Same structure, same paragraph breaks, same keyword list (in respective languages). Not a free translation; a parallel rendering with identical claims and evidence markers.

- **Institute guideline:** Drop your PDF/DOCX guideline into `templates/institution/GUIDELINE-NOTES.md` (user manually extracts rules); this skill then references it as authoritative.

---

## 5. Defense Preparation

Full committee-question templates, answer frameworks, and presentation outlines are in **reference/defense.md**. Quick summary:

- **Likely questions by chapter:**
  - Ch.1 (gap & novelty): "Why is this problem important? What makes your approach different?"
  - Ch.2 (prior work): "Which prior work is most relevant? How does it compare to yours?"
  - Ch.3 (methods): "Why did you choose this design? What are the limitations?"
  - Ch.4 (results): "What surprised you? How reliable are these findings?"
  - Ch.5 (claims): "What's the take-home message? Who benefits from this?"

- **Presentation skeleton:** 12–15 slides — one per chapter + outcomes slide. See reference/defense.md for detailed outline.

---

## 6. Integrated Commands

### Check thesis structure:
```bash
# Verify RQ ↔ Chapter 4 heading ↔ Chapter 5 answer mapping
python scripts/word_budget.py --rq-trace

# Summary of structure and word budget
/status
```

### Audit Turkish Özet↔Abstract:
```bash
# Run style-auditor in TR mode
/critique  # or manual check against reference/yok-tr.md checklist
```

### Export structure for defense prep:
```bash
# Load defense templates
reference/defense.md  # answer skeletons by likely question
```

---

## References

- **Thesis types & architecture:** This file.
- **Turkish (YÖK) requirements:** `reference/yok-tr.md`
- **Defense prep:** `reference/defense.md`
- **Word budget & RQ tracing:** Execute `python scripts/word_budget.py --rq-trace`
- **Style guidance:** Academic-writing skill
- **Evidence card integration:** Evidence-cards skill
