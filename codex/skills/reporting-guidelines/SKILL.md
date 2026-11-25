---
name: reporting-guidelines
description: Use when finalizing a draft or running /submit-check. Selects the matching reporting guideline (CONSORT for RCTs, STROBE for observational, PRISMA-ScR for scoping reviews, CARE for case reports, COREQ/SRQR for qualitative) and runs its checklist. Each guideline maps items to manuscript locations for verification.
---

# Reporting Guidelines: Compliance Checklist

Research integrity depends on transparent, complete reporting. This skill matches your study design to the appropriate reporting standard and verifies checklist compliance.

---

## Step 1: Identify Your Study Type

> **Maintenance note:** this flowchart mirrors `paper-types/SKILL.md`'s
> "Quick Decision Tree" (same primary-data/design/scope questions, different
> purpose — guideline/checklist selection here vs. reference/rubric file
> selection there). Keep both in sync when either changes.

Use this flowchart to find your guideline:

```
Did you collect PRIMARY DATA (your own study)?
  
  YES (You did original research)
  │
  ├─ Randomized treatment assignment → RCT (CONSORT 2010)
  │
  ├─ No randomization:
  │  │
  │  ├─ Cohort / case-control / cross-sectional → OBSERVATIONAL (STROBE)
  │  │
  │  ├─ Single case with detailed timeline → CASE REPORT (CARE)
  │  │
  │  └─ Interviews / focus groups / ethnography → QUALITATIVE (COREQ or SRQR)
  │
  NO (You reviewed literature)
  │
  ├─ Mapping the field (breadth, what exists?) → SCOPING REVIEW (PRISMA-ScR)
  │
  ├─ Systematic search + synthesis → SYSTEMATIC REVIEW (PRISMA 2020)
  │
  └─ Narrative synthesis (selective scope) → No specific guideline required
```

---

## Step 2: Load Your Guideline

Click the matching reference file below:

| Study Type | Guideline | Reference File | Key Points |
|---|---|---|---|
| **Randomized Controlled Trial (RCT)** | CONSORT 2010 | [reference/consort.md](reference/consort.md) | 25 items; flow diagram; randomization transparency |
| **Observational (Cohort/Case-Control/Cross-sectional)** | STROBE | [reference/strobe.md](reference/strobe.md) | 22 items; design-specific variants; confounder specification |
| **Scoping Review** | PRISMA-ScR | [reference/prisma-scr.md](reference/prisma-scr.md) | 22 items; mapping table; breadth over depth |
| **Case Report** | CARE | [reference/care.md](reference/care.md) | 13 items; timeline; consent statement |
| **Qualitative (Interviews/Focus Groups)** | COREQ | [reference/coreq.md](reference/coreq.md) | 32 items; theme-quote-source chain; saturation |
| **Qualitative (Broader: Ethnography, Observation, etc.)** | SRQR | [reference/srqr.md](reference/srqr.md) | 21 items; researcher reflexivity; trustworthiness |

---

## Step 3: Run the Checklist

Each reference file provides:
1. **The full checklist** (items + definitions).
2. **A location map** (where each item appears in your manuscript).
3. **Common pitfalls** (what reviewers look for).

### Quick Check (5 Minutes)

Before detailed review, quickly verify:
- [ ] Does the checklist exist and match my study type?
- [ ] Have I addressed the "critical" items (flow diagram, consent, saturation, etc.)?
- [ ] Are there any items I haven't mentioned? (Mark them for revision.)

### Detailed Check (30 Minutes)

- [ ] Open your draft.
- [ ] For each checklist item, find where it's addressed (or note if missing).
- [ ] Mark ALL items as PASS, NEEDS REVISION, or MISSING.
- [ ] Plan revisions for MISSING/NEEDS REVISION items.

---

## Step 4: Use `/submit-check` to Auto-Run

The `/submit-check` command:
1. Reads your draft.
2. Detects study type.
3. Loads the matching checklist.
4. Reports compliance (PASS / NEEDS REVISION / MISSING).
5. Suggests fixes.

**Usage:**
```
/submit-check
```

---

## Mapping Checklist Items to Manuscript Sections

Each guideline reference file maps items to sections. Example from CONSORT:

| Item # | Item | Appears In |
|---|---|---|
| 1 | Title identifies as "randomized controlled trial" | Title |
| 2a | Structured abstract with all key elements | Abstract |
| 3a | Description of study design | Introduction + Methods |
| 4a | Scientific background and rationale | Introduction |
| 5 | Specific objectives and hypotheses | Introduction (end) |
| 6a | Description of trial design, including allocation ratio | Methods |
| 6b | Important changes to methods after trial commencement | Methods or Appendix |
| 7a | How sample size was determined | Methods |
| 7b | When interim analyses were planned | Methods |
| ... | (24 more items) | ... |

**Your task:** Verify every item has a "Appears In" location in your draft.

---

## Common Pitfalls by Guideline

### CONSORT (RCTs)

- **Missing flow diagram** → Include: enrolled, allocated, followed up, analyzed (with exclusion counts at each stage).
- **Unclear randomization** → Specify: method (random.org, sealed envelope), allocation concealment, who assigned.
- **No baseline characteristics table** → Add Table 1: Demographics, baseline outcome measures by group.

### STROBE (Observational)

- **Design not clearly labeled** → State explicitly: "This is a prospective cohort study" (not just "We followed patients").
- **Confounders not specified** → List confounders you measured and how you addressed them (matching, regression, etc.).
- **Missing flow diagram** → Show participant numbers at each stage (recruitment, inclusion/exclusion, analysis).

### CARE (Case Reports)

- **No informed consent** → Must include: "Written informed consent was obtained on [date]" or explanation of why not obtainable.
- **Timeline vague** → Use dates or "Day 1, Day 2…"; table format helps.
- **De-identification unclear** → Specify what was removed/masked (name, MRN, specific location) while retaining clinically relevant detail.

### COREQ (Qualitative - Interviews/FG)

- **Quotes missing page numbers** → Every quote must have source ID + page/timestamp.
- **Saturation not discussed** → State when/why data collection stopped.
- **Analysis process opaque** → Describe: coding approach (deductive/inductive), multi-coder agreement, tool used (NVivo, etc.).

### SRQR (Qualitative - Broader)

- **Researcher positionality missing** → State researchers' background, credentials, potential biases.
- **Trustworthiness strategies not mentioned** → Describe: member checking, peer debriefing, triangulation, negative case analysis.
- **Findings presented without context** → Use thick description; show how findings emerged from data.

### PRISMA-ScR (Scoping Review)

- **Search strategy not fully documented** → Include exact queries per database, hits per database, dates searched.
- **Mapping table missing** → Show studies × key dimensions (design, population, findings, themes).
- **Scope not justified** → Explain why this breadth (what gap does it fill?).

---

## Checklist Compliance Decision Tree

For each item:

```
Is this item addressed in your draft?
  
  YES → Is it fully explained and defensible?
    YES → PASS ✓
    NO  → NEEDS REVISION (elaborate, clarify)
  
  NO → Can it be omitted (marked "not applicable") with justification?
    YES → PASS (with justification note)
    NO  → MISSING (must be added)
```

---

## Revision Strategy

### Priority 1 (Critical Items — Must Fix)

These items are fundamental to study credibility:
- **CONSORT:** Flow diagram, randomization description, allocation concealment.
- **STROBE:** Study design clearly stated, confounders specified, flow diagram.
- **CARE:** Informed consent, timeline, de-identification.
- **COREQ/SRQR:** Quote-source chain (page numbers), saturation, reflexivity.
- **PRISMA-ScR:** Search strategy fully documented, mapping table.

### Priority 2 (Important — Should Fix)

These strengthen the paper but missing them won't block publication (though reviewers will request revision):
- **CONSORT:** Baseline characteristics table, dropout reasons, adverse events.
- **STROBE:** Loss-to-follow-up description, bias discussion.
- **CARE:** Limitations section, positioning vs literature.
- **COREQ/SRQR:** Member checking, peer debriefing.
- **PRISMA-ScR:** Risk-of-bias assessment (if applicable), GRADE certainty.

### Priority 3 (Nice-to-Have — Can Address in Revision)

- Extended discussion of limitations.
- Supplementary material (codebook, full search strategy in appendix).
- Post-hoc subgroup analyses.

---

## Using This Skill + `/submit-check` Together

| Scenario | Action |
|----------|--------|
| You've drafted Methods and want to spot-check compliance | Read the relevant checklist reference file (e.g., [reference/consort.md](reference/consort.md)) |
| You're ready to finalize and want a systematic audit | Run `/submit-check`; it auto-runs the full checklist |
| Reviewers requested items you didn't include | Cross-reference the reviewer comment with the checklist; see where it should appear |
| You're uncertain if an item "counts" | Read that item's explanation in the reference file; it clarifies what counts as sufficient |

---

## Quick Reference: Checklist Items by Category

### All Guidelines Include These Themes

| Theme | Example Item |
|-------|---|
| **Title clarity** | Is the study type evident from title? |
| **Abstract completeness** | Does abstract summarize objectives, methods, results, conclusions? |
| **Objective/RQ clarity** | Is the research question stated explicitly? |
| **Methods transparency** | Can readers replicate the study? |
| **Ethical compliance** | Is informed consent/ethics approval documented? |
| **Results presentation** | Are findings presented completely (not selectively)? |
| **Limitations honesty** | Are limitations acknowledged? |
| **Implications** | What does this study mean for practice/theory? |

---

## Reporting Guideline Selection Matrix

| Design | Primary Guideline | Secondary Refs (if hybrid) |
|---|---|---|
| RCT | CONSORT | — |
| Cohort | STROBE | (Observational variant) |
| Case-control | STROBE | (Observational variant) |
| Cross-sectional | STROBE | (Observational variant) |
| Single case | CARE | — |
| Qualitative interviews | COREQ | (or SRQR if ethnography combined) |
| Qualitative + observation | SRQR | (or COREQ if primarily interviews) |
| Scoping review | PRISMA-ScR | — |
| Systematic review | PRISMA 2020 | (See literature-review skill) |

---

## Next Steps

1. **Identify** your study type (use flowchart above).
2. **Open** the matching reference file (consort.md, strobe.md, etc.).
3. **Run** the detailed checklist against your draft.
4. **Mark** items: PASS / NEEDS REVISION / MISSING.
5. **Prioritize** revisions (Critical items first).
6. **Use `/submit-check`** for final automated verification.

---

## References

Each reference file below contains the official checklist plus guidance:
- [reference/consort.md](reference/consort.md) — CONSORT 2010 (RCTs)
- [reference/strobe.md](reference/strobe.md) — STROBE (Observational)
- [reference/prisma-scr.md](reference/prisma-scr.md) — PRISMA-ScR (Scoping Reviews)
- [reference/care.md](reference/care.md) — CARE (Case Reports)
- [reference/coreq.md](reference/coreq.md) — COREQ (Qualitative Interviews/FG)
- [reference/srqr.md](reference/srqr.md) — SRQR (Qualitative Broader)

**Official sources:**
- CONSORT: consort-statement.org
- STROBE: strobe-statement.org
- PRISMA-ScR: prisma-statement.org
- CARE: care-statement.org
- COREQ: equator-network.org
- SRQR: equator-network.org
