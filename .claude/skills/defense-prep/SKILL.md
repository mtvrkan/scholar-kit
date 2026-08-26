---
name: defense-prep
description: "Prepare for thesis defense/viva. Generates a committee-question bank organized by chapter (motivation challenges, method choices, validity threats, contribution boundary, future work), answer skeletons grounded in your actual thesis claims, a 12–15 slide presentation outline mapped to chapters, and common follow-up questions. Use after your thesis draft is complete but before the defense date."
disable-model-invocation: true
argument-hint: "(no arguments)"
---

# /defense-prep — Thesis Defense & Presentation Preparation

## Gate: Abort if Failed

1. **Check:** PROJECT.md `type` starts with `thesis`.
   - If not (e.g., type=IMRaD): abort with "Defense-prep is for theses only. Your project type is '<type>'."

2. **Check:** At least one draft file exists in `drafts/`.
   - If empty: abort with "No thesis chapters found. Draft at least introduction, methods, results, and conclusion before running defense-prep."

3. **Check:** File `outline/outline.md` exists.
   - If missing: abort with "No outline found. Run `/outline` to establish chapter structure first."

4. **Check (optional but recommended):** File `drafts/conclusion.md` exists (or a similar final-chapter file).
   - If missing: warn "Conclusion/final chapter not found. Defense prep will be less grounded in your actual findings."

## Procedure

### Step 1: Read the Thesis Structure

1. **Read `outline/outline.md`:**
   - Extract chapter titles and main RQs/claims per chapter
   - Identify the logical flow (e.g., Ch. 1: Motivation, Ch. 2: Literature, Ch. 3: Methods, Ch. 4: Results, Ch. 5: Discussion)

2. **Read `PROJECT.md`:**
   - Extract thesis type (BSc, MSc, PhD)
   - Extract field/discipline
   - Extract main research questions
   - Extract target institution (affects committee knowledge base)

3. **Read key draft sections:**
   - `drafts/introduction.md` or `drafts/chapter1.md` (motivation and RQs)
   - `drafts/methods.md` or `drafts/chapter3.md` (methodology)
   - `drafts/results.md` or `drafts/chapter4.md` (findings)
   - `drafts/conclusion.md` (implications and future work)
   - Extract: key claims, evidence, potential weak points, assumptions

### Step 2: Generate Committee-Question Bank

1. **Access thesis-structure skill reference:** `.claude/skills/thesis-structure/reference/defense.md`
   - This file contains:
     - Likely committee questions by chapter
     - Hard questions per thesis stage (BSc vs MSc vs PhD)
     - Validity threat questions
     - Contribution boundary questions
     - Future work questions

2. **Organize questions by chapter:**
   - For each chapter in your outline, generate chapter-specific questions grounded in YOUR thesis claims
   - Categories per chapter:

   **Chapter 1 (Introduction/Motivation)**
   - "Why does this problem matter?" / "What's the broader impact?"
   - "How is your RQ different from prior work?" (requires your literature positioning)
   - "What assumptions underlie your framing?" (e.g., if you assume a problem is widespread, how do you know?)

   **Chapter 2 (Literature Review)**
   - "What major gaps did you find?" (your gap analysis)
   - "Are there any recent papers you missed?" (especially last 6 months)
   - "How does your work fit into the existing taxonomy?"

   **Chapter 3 (Methods)**
   - "Why this method over alternatives?" (justification)
   - "What could go wrong with your approach?" (validity threats, limitations you didn't mention)
   - "How replicable is this?" (can someone reproduce it with your description?)
   - For ML theses: "Why these baselines? Any cherry-picked?" "How did you split train/val/test?" "How do you know your model didn't overfit?"
   - "Ethical considerations?" (data collection, consent, bias, reproducibility)

   **Chapter 4 (Results)**
   - "What surprised you?" (signals deep understanding)
   - "How do you interpret [counter-intuitive result]?" (if any)
   - "Statistical significance vs practical significance — do your results matter outside the lab/dataset?"
   - "Limitations of the data?" (sample size, bias, representativeness)

   **Chapter 5 (Discussion/Conclusion)**
   - "What's the ONE thing someone should take away from your thesis?" (tests clarity of contribution)
   - "How would you extend this?" (future work — not vague)
   - "What would invalidate your main claim?" (intellectual honesty)
   - "If you had more time/budget, what's next?" (realistic scope)

   **Boundary/Scope Questions (any chapter)**
   - "What's OUT of scope and why?" (boundary setting)
   - "How does this contribute to the field?" (novelty vs incremental)
   - "Who benefits from this work?" (impact/audience)

3. **Add difficulty tiers:**
   - 🟢 **Easy:** factual recall (e.g., "What's the dataset size?")
   - 🟡 **Medium:** explanation (e.g., "Why did you choose logistic regression?")
   - 🔴 **Hard:** critical/synthesis (e.g., "How would your results change if the assumption X were violated?")

### Step 3: Generate Answer Skeletons

For each hard (🔴) question, draft a 1–2 minute answer skeleton:

**Format:**
```
Q: [Question]
Intent: [What is the committee testing for? — evidence of understanding, depth, integrity]

Your answer skeleton:
  1. Restate/clarify the question (buys you thinking time)
  2. [1 sentence] Direct answer
  3. [2–3 sentences] Justification/evidence from your thesis
  4. [1 sentence] Broader implication or connection to RQ
  5. [Optional] "Happy to elaborate on [specific aspect] if helpful"

Pitfall to avoid: [Common wrong answer or unclear phrasing]
```

**Examples:**

```
Q: How would your model perform on a different dataset?
Intent: Testing generalizability of findings; whether you understand the limits of your work.

Your answer skeleton:
  1. "Good question — I assume you mean a dataset from a different domain?"
  2. "It would likely perform worse due to domain shift."
  3. "Our model was trained on [dataset X, properties: ...]. A dataset with different [property Y] 
     would have different class distributions / image characteristics / sample demographics. 
     We did not evaluate cross-domain transfer because [constraint: time / funding / not in scope]."
  4. "This is why I recommend [future work direction]."
  5. "I have a slide on this under Limitations and Future Work if you'd like to discuss further."

Pitfall: DO NOT say "I don't know" without context. DO say "We didn't test that, but here's my reasoning..."
```

```
Q: Why didn't you use [simpler/alternative] method?
Intent: Probing whether you explored alternatives or settled too early.

Your answer skeleton:
  1. "Clarify: do you mean [method A] or [method B]?"
  2. "We tested [method A] in our ablation study. [State result: beat/lost to baseline by X%]"
     OR "We didn't test it, but here's why we expect it would underperform: [reasoning]"
  3. "The trade-off is [accuracy vs training time / interpretability vs performance]. 
     We optimized for [your criterion] because [RQ / application requirement]."
  4. "If the criterion shifts — e.g., if interpretability became critical — then [method A] might be better."

Pitfall: DO NOT dismiss alternatives without evidence. DO compare fairly.
```

### Step 4: Generate Presentation Outline

Create a 12–15 slide outline for a 15–20 minute defense presentation (typical):

```markdown
# Defense Presentation Outline (15 minutes, ~12 slides)

## Slide 1: Title Slide (< 1 min)
- Thesis title
- Your name, institution
- Date

## Slide 2: Motivation (1.5 min)
- "Why does this matter?"
- 1–2 key statistics or examples from intro
- Your RQs (2–3 bullets)

## Slide 3: Literature Positioning (1.5 min)
- 2–3 key prior works (title + author + year)
- Your contribution in relation to them (e.g., "Extends [work X] by adding [novelty Y]")
- The gap you're filling

## Slide 4: Research Questions (0.5 min)
- RQ1, RQ2, RQ3 stated clearly
- Hypotheses (if applicable)

## Slide 5–6: Methods (2–3 min)
- Slide 5: High-level approach (flowchart or block diagram)
  ├─ Participants/Dataset
  ├─ Procedure
  └─ Analysis strategy
- Slide 6 (if needed): Key details
  ├─ Tools/platforms
  ├─ Data characteristics
  └─ (For ML: model architecture sketch, training protocol)

## Slide 7–8: Results (2–3 min)
- Slide 7: Primary finding(s)
  ├─ Key table or graph showing main result
  ├─ Effect size / performance metric
  └─ Statistical test (if applicable)
- Slide 8: Secondary finding(s) or breakdown
  ├─ Subgroup analyses
  ├─ Sensitivity tests
  └─ (For ML: learning curves, ablation results)

## Slide 9: Interpretation & Implications (1 min)
- What does this mean?
- Alignment with hypothesis / RQ
- Practical implications

## Slide 10: Limitations (1 min)
- 3–4 key limitations (be honest, show awareness)
- Each: what it is + why it matters + how it affects conclusions

## Slide 11: Future Work (0.5 min)
- 2–3 concrete next steps (not vague)
- E.g., "Replicate with larger sample" or "Test on domain Y"

## Slide 12: Key Takeaway (0.5 min)
- "In one sentence, my thesis contributes: ___"

## Slide 13 (optional): Backup Slide
- Detailed result you might need to explain
- Or: methodological detail if questioned
```

### Step 5: Generate Common Follow-Up Questions

After presenting, committees often ask quick follow-ups. Prepare 2–3 sentence answers for:

```
Likely Follow-Ups:

1. "How does your work apply to [real-world scenario]?"
   → Translate from thesis world to practitioner world

2. "What would change your main conclusion?"
   → Show you've thought about boundary conditions

3. "How much time/money did this take?"
   → Scope and resource efficiency (especially for BSc/MSc)

4. "Who disagrees with you, and why?"
   → Awareness of alternative viewpoints in literature

5. "If you published this, which journal?"
   → Shows you understand venue fit and impact level

6. "What part of this could someone with less expertise contribute?"
   → Intellectual honesty about what's novel vs. standard
```

### Step 6: Write Defense-Prep Report

Create `reviews/defense-prep.md` with this structure:

```markdown
# Defense Preparation Packet
Date: [today]
Thesis: [title]
Committee: [names if known]

## Part 1: Question Bank by Chapter

### Chapter 1: Motivation
[List of 5–8 questions, organized by difficulty level]
- 🟢 Recall questions
- 🟡 Explanation questions
- 🔴 Hard questions (with answer skeletons)

### Chapter 2: Literature
[Similar structure]

[Repeat for each chapter]

### Boundary & Synthesis Questions
[Questions spanning multiple chapters]

---

## Part 2: Answer Skeletons (Hard Questions Only)

### Q1: [Hard question]
**Intent:** [What committee is probing for]

**Skeleton:**
1. Restate
2. Direct answer
3. Justification
4. Broader implication
5. Bridge

**Pitfall to avoid:** [...]

---

## Part 3: Presentation Outline (12 slides, 15 min)

[Slide-by-slide outline as above]

---

## Part 4: Common Follow-Ups & Answers

1. [Follow-up 1] → [1–2 sentence answer]
2. [Follow-up 2] → [1–2 sentence answer]
...

---

## Part 5: Tips & Reminders

- Arrive 10 min early; test tech (slides, audio if applicable)
- Speak clearly, especially technical terms (committee may not be specialists in your subfield)
- Pause after questions to think, don't rush
- If you don't know: "That's a great question. I didn't explore that, but here's how I'd approach it..."
- Thank committee at the start and end
- Expect 30–60 min total (presentation + questions)
```

### Step 7: Summary to User

Display:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Defense-Prep Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output: reviews/defense-prep.md

Contents:
  ✓ Question bank: M questions across N chapters
    └─ 🟢 Easy (factual): X questions
    └─ 🟡 Medium (explanation): Y questions
    └─ 🔴 Hard (critical): Z questions with answer skeletons

  ✓ Presentation outline: 12-slide format (15 min talk)
    └─ Mapped to your chapters
    └─ Timing notes per slide

  ✓ Follow-up strategy: 6 common asks with brief answers

Recommendations before defense:
  1. Practice the presentation with a friend (time yourself)
  2. Do a mock defense: have someone ask questions from the bank
  3. Revise answer skeletons based on your comfort level
  4. Visit the defense room beforehand (tech check)
  5. Get a good night's sleep!

Committee typically evaluates:
  • Understanding of your own work (can you explain choices?)
  • Intellectual integrity (do you know limitations?)
  • Contribution clarity (what's the so-what?)
  • Ability to think on your feet (answering unexpected questions)

Good luck! 🎓
```

## Reference

- **Thesis-structure skill reference:** `.claude/skills/thesis-structure/reference/defense.md` (question bank templates by thesis stage)
- **Input files:** 
  - `PROJECT.md` (thesis type, field)
  - `outline/outline.md` (chapter structure and RQs)
  - `drafts/introduction.md`, `drafts/methods.md`, `drafts/results.md`, `drafts/conclusion.md`
- **Output artifact:** `reviews/defense-prep.md` (comprehensive defense packet)
- **Related:** All chapter drafts (read for grounding questions in actual content)

---
*Defense is not a gotcha — it's a conversation with experts who want to understand your work. Preparation builds confidence; confidence makes for a great defense.*
