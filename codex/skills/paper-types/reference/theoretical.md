# Theoretical & Conceptual Papers

## Argument Architecture (Toulmin Model)

Theoretical papers build argument chains. The **Toulmin model** maps the anatomy of an argument:

```
CLAIM (what you assert)
  ↓
GROUNDS (evidence or facts supporting it)
  ↓
WARRANT (the reasoning that connects grounds to claim; often unstated, needs to be made explicit)
  ↓
BACKING (why the warrant is reliable)
  ↓
QUALIFIER (hedging: "usually," "probably," "in most cases")
  ↓
REBUTTAL (counterarguments and their refutation)
```

### Example

**Claim:** "Machine learning models reproduce societal biases present in training data."

**Grounds:** 
- Study 1 showed facial recognition performs worse on darker skin tones (98% accuracy on light skin, 85% on dark skin).
- Study 2 found resume-screening ML models rated identical resumes differently based on inferred gender.

**Warrant:** If the training data reflects historical discrimination (e.g., hiring records biased against women), the model learns those patterns and perpetuates them at scale.

**Backing:** This warrant is grounded in how supervised learning works: models optimize to match patterns in training data, whether those patterns represent truth or prejudice.

**Qualifier:** "In most cases, models will reproduce training-data bias unless explicitly addressed."

**Rebuttal:** "Some argue that ML is more objective than human judgment. However, this confuses objectivity (measuring what you intend) with fairness; ML can be objective yet biased."

---

## Proposition–Evidence Map (CRITICAL)

Before drafting, create a map of each main proposition and its evidence base.

### Template

```
Proposition 1: [Main claim]
  Evidence A: [Citation or argument]
  Evidence B: [Citation or argument]
  Counterevidence / Limitation: [Address alternative view]
  Conclusion: [What does this establish?]

Proposition 2: [Next main claim]
  [evidence, counterevidence, conclusion]

[Continue for all major claims]
```

### Example: Theoretical paper on learning transfer in deep networks

```
Proposition 1: Transfer learning (pre-training on large datasets) improves downstream task performance.
  Evidence A: ImageNet pre-training on vision models shows 5-10% accuracy gains on smaller target datasets (cite: Krizhevsky et al., 2012; He et al., 2015)
  Evidence B: BERT pre-training improves NLP benchmark scores across tasks (cite: Devlin et al., 2019)
  Counterevidence: Occasionally pre-training on dissimilar data hurts performance (cite: irrelevant domain example)
  Limitation: Most successes are within-domain transfer (vision to vision, NLP to NLP); cross-domain remains less clear
  Conclusion: Transfer learning is empirically effective within domains; mechanism remains theoretical

Proposition 2: Transfer learning works because pre-training learns general features that generalize.
  Evidence A: Feature visualization shows similar filters learned across tasks (cite: Yosinski et al., 2014)
  Evidence B: Fine-tuning only final layers still improves performance, suggesting learned representations are reusable
  Counterevidence: Some argue transfer just prevents overfitting on small datasets (regularization effect)
  Conclusion: Mechanism plausible but not definitively established; both feature-reuse and regularization likely play roles

[Continue with additional propositions...]
```

---

## Structure & Content Guidance

### Introduction
- **Problem:** What is being theorized or conceptualized? What's the gap?
- **Scope:** Boundaries of the analysis (e.g., "We focus on supervised learning; unsupervised methods are beyond scope").
- **Thesis:** State your main argument upfront (e.g., "We propose a framework for understanding when transfer learning fails").
- **Roadmap:** "In Section 2, we review existing theory; in Section 3, we present an alternative model; in Section 4, we test its predictions."
- Length: 2–3 pages.

### Main argument sections (2–4 sections)
- **Section title:** Reflects the proposition (e.g., "On the Necessity of Feature Reuse for Transfer Success").
- **Proposition:** State the claim clearly at the outset.
- **Development:** Provide grounds (evidence, citations) and warrant (reasoning).
- **Counterargument:** Anticipate objections; show why they're insufficient.
- **Implication:** What does this section establish for the overall thesis?
- Length per section: 2–4 pages.

### Synthesis / Integrative section
- **How do the propositions fit together?** Show the logical chain.
- **Revised model or framework:** Present your theoretical contribution (diagram or verbal model).
- **Predictions or implications:** What does the theory predict? What would falsify it?
- Length: 2–3 pages.

### Discussion
- **Limitations of the theory:** What does it not explain? Where is it weakest?
- **Comparison to prior theories:** How does your framework differ from existing ones (cite them)?
- **Empirical predictions:** What experiments or observations would test the theory?
- **Scope and generalizability:** To what contexts, domains, or systems does the theory apply?
- Length: 2–3 pages.

### Conclusion
- **Restatement of thesis:** Remind reader of the main argument.
- **Significance:** Why does this theory matter? What changes if we accept it?
- **Future work:** What should the field investigate next based on this theory?

---

## Types of Theoretical Contributions

### 1. New framework or model
- Proposes an organizing principle for understanding a phenomenon.
- Example: "A three-stage model of organizational change" or "A taxonomy of ML failure modes."
- Contribution: Clarity, prediction, or parsimony.

### 2. Reconciliation of conflicting theories
- Existing theories X and Y seem contradictory; you show how they're compatible or under what conditions each applies.
- Example: "Integrating behavioral and cognitive theories of motivation."
- Contribution: Synthesis, complexity management.

### 3. Extension or refinement of an existing theory
- Theory X is useful but incomplete; you extend it to a new domain or add conditions.
- Example: "Transfer learning theory extended to cross-domain scenarios."
- Contribution: Broader applicability, added nuance.

### 4. Critique and alternative
- Existing theory is flawed; you propose an alternative that better explains the evidence.
- Example: "Why traditional feature-engineering logic fails in deep learning, and an alternative account."
- Contribution: Correction, new perspective.

### 5. Conceptual clarification
- A concept in the field is muddy; you clarify it rigorously.
- Example: "What do we actually mean by 'interpretability' in machine learning?" 
- Contribution: Precision, productive debate.

---

## Writing Style for Theoretical Work

### Tense
- **Present tense for general claims:** "Theory X posits that…"; "Our model predicts that…"
- **Past tense for specific prior work:** "Smith (2020) showed that…"

### Hedging (appropriately pitched)
- Theoretical work must acknowledge uncertainty.
- **Appropriate:** "This framework suggests…"; "If we accept assumption Z, then X implies Y."
- **Weak:** "It might possibly indicate that maybe…" (too much hedging).
- **Overconfident:** "It is clear that X causes Y" (not enough).
- **Balance:** "On current evidence, X likely causes Y, though Z remains unclear."

### Definitions and terminology
- Define key terms explicitly on first use.
- **Example:** "By 'transfer learning' we mean the use of parameters trained on one task to initialize training on a second, related task."
- Use consistent terminology throughout (not "transfer learning" and "fine-tuning" interchangeably unless you've defined their relationship).

### Use of visuals
- Diagrams can clarify complex arguments.
- **Concept maps:** Show relationships among ideas (nodes + arrows).
- **Process models:** Timeline or sequence of events/stages.
- **Taxonomy trees:** Hierarchical categorization.
- Caption must explain what the figure contributes to the argument.

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Propositions unsupported (claim without grounds) | For each claim, cite evidence or show reasoning explicitly |
| Circular reasoning (assume what you're trying to prove) | Check that each step adds something new; avoid re-asserting the same claim |
| Strawman rebuttals (mischaracterize opposing views) | Cite the strongest version of competing theories; engage fairly |
| Vague warrant (reasoning is implicit or unclear) | Make explicit: "We reason that X because Y, which connects to our claim as follows: Z" |
| Overconfidence (no hedging, ignores limitations) | Use qualifiers; acknowledge uncertainty; state where theory is weakest |
| Too abstract (propositions untethered from reality) | Ground theory in examples; show how it explains observable phenomena |
| Ignores prior theory (presents ideas as novel when they exist) | Literature review: What has others said? What's your new contribution? |
| No predictions (theory doesn't enable any falsifiable claims) | Propose an experiment or observation that would support or challenge your theory |

---

## Falsifiability Test (Popper)

A strong theoretical paper proposes claims that are **testable**—i.e., there exists an observation that would prove the theory wrong.

**Example (weak):**
"Neural networks are powerful because they have hidden layers."
- How would you prove this wrong? Vague.

**Example (strong):**
"Neural networks with hidden layers outperform logistic regression on non-linearly separable problems. If we find a dataset that is non-linearly separable but neural networks perform worse than regression, the theory is falsified."
- Clear prediction; testable.

---

## Theoretical Paper Length

**Typical:** 5000–7000 words (varies by venue and complexity).
- Introduction: 800–1000 words
- Main argument sections (2–4): 1500–2500 words total
- Synthesis/integrative section: 1000–1200 words
- Discussion: 1000–1500 words
- Conclusion: 400–500 words

---

## References & Resources

- **Toulmin, S. (2003).** The Uses of Argument (2nd ed.). Cambridge University Press. Classic framework.
- **Kuhn, T. S. (1962).** The Structure of Scientific Revolutions. Foundational on theory and paradigm shifts.
- **Popper, K. (1959).** The Logic of Scientific Discovery. On falsifiability.
- **Journal examples:** *Theory & Society*, *Philosophy of Science*, *British Journal of Philosophy of Science*, *Theoretical Computer Science* (for CS-theoretical work).
