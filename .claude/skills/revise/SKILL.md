---
name: revise
description: "Work through peer review findings one by one. For each Major/Minor issue from the latest reviews/round-N.md, the model proposes a concrete edit, you approve or request changes, and the revision is logged to reviews/changelog-round-N.md. When revisions touch citations, cite_audit.py is re-run. Produces a change log and optionally a draft response-to-reviewers letter."
disable-model-invocation: true
argument-hint: "<section-file>"
---

# /revise — Address Peer Review Findings

## Gate: Abort if Failed

1. **Check:** At least one file exists in `reviews/` matching `round-*.md` pattern.
   - If none exist: abort with "No review report found. Run `/critique` first to generate a review."

2. **Check:** The section file argument exists in `drafts/`.
   - Example: user runs `/revise methods.md` → file `drafts/methods.md` must exist.
   - If file missing: abort with "Section file '<section-file>' not found in drafts/. List available files: [list from drafts/]"

## Procedure

### Step 1: Identify the Latest Review Round

1. **List files in `reviews/`** matching `round-*.md` pattern (e.g., round-1.md, round-2.md).
2. **Find the latest:** Select the highest numbered round (e.g., if round-1.md and round-2.md exist, use round-2.md).
3. **Record the round number N** for the changelog.

### Step 2: Read the Review and Extract Issues

1. **Open `reviews/round-N.md`** (the latest review report).
2. **Extract all issues:**
   - List all items under "## MAJOR ISSUES" (numbered)
   - List all items under "## MINOR ISSUES" (numbered)
   - Extract Suggestions (bulleted)
3. **Filter by section:** Show only issues that reference the target section file (argument: `<section-file>`).
   - Example: If user runs `/revise methods.md`, show only issues with "Methods:" or "Section: Methods" in the reference.

### Step 3: Set Up Changelog

1. **Create or open** `reviews/changelog-round-N.md` (if it does not exist, create it).
   - Initialize with:
     ```markdown
     # Round N Changelog — Revisions Applied
     
     Date: [today's date]
     Section: [section-file]
     Reviewer round: round-N.md
     
     ## Changes Summary
     
     | Issue # | Category | Files Touched | Summary |
     |---------|----------|---------------|---------|
     
     ## Detailed Log
     ```

2. **Keep this file open** as you work through issues.

### Step 4: Work Through Major Issues First, Then Minor

For **each Major issue** (in order), then **each Minor issue**:

#### 4a. Display the Issue

Show the user:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAJOR Issue #N: [Title]
Section: [reference]
Reviewer said: [exact quote from review]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 4b: Propose a Concrete Edit

Depending on the issue type:

**If it's a clarity/wording issue:**
- Show the current text (excerpt from drafts/[section-file])
- This is style-auditor's domain (register/clarity — CLAUDE.md's dispatch
  table: "returns edit list, never rewrites"), not a freehand rewrite: dispatch
  style-auditor on the excerpt, then present ITS suggested edit for approval
  (or pose a question like "Should this be phrased as X or Y?" if the issue
  is structural/logical rather than pure clarity — those stay in this session).
- Example:
  ```
  Current (line 45–48):
  "The method involves several steps that lead to improved results."
  
  Proposed:
  "The method involves: (1) data preprocessing, (2) model training with early stopping,
  and (3) evaluation on held-out test set. This pipeline reduces overfitting and 
  improves generalization performance."
  ```

**If it's a missing section/detail:**
- Show what's missing (e.g., "Missing ablation study results")
- Propose the addition (provide a draft paragraph or table skeleton)
- Example:
  ```
  Missing: Ablation study results for attention mechanism.
  
  Proposed addition to Results section:
  "We evaluated the contribution of the attention mechanism by removing it from 
  the baseline model. Results show F1 score drops from 0.89 to 0.82, indicating 
  attention contributes ~7 percentage points to performance."
  ```

**If it's a structural/logical issue:**
- Identify the problem (e.g., "Conclusion claims novelty not demonstrated in Results")
- Propose a fix (reframe the claim, add evidence, or remove overclaim)
- Example:
  ```
  Issue: Conclusion claims "first application of CNN to bearing diagnostics" 
         but Methods acknowledges prior CNN work (smith2020).
  
  Fix options:
    A) Reframe to "first application of CNN with attention to bearing fault diagnosis"
       (if true, backed by your literature review)
    B) Remove novelty claim and focus on methodological contribution (your new attention module)
    C) Clarify as "extends prior CNN work (Smith, 2020) by incorporating attention mechanism"
  ```

#### 4c: Get User Approval

Ask the user:
```
Approve this fix? [y/n/edit/skip]
  y      → Apply edit to drafts/[section-file] and log it
  edit   → Propose an alternative
  n/skip → Mark as pending and move to next issue
```

Supported user responses:
- **"hepsini uygula"** (Turkish: "apply all") — apply all proposed changes for remaining issues in this section without further approval
- **"skip"** or **"n"** — move to next issue without applying this one
- **"edit"** — show an alternative or ask user to paste their version

#### 4d: Apply the Edit

If approved:

1. **Edit `drafts/<section-file>`** with the proposed change.
   - For small edits: inline replacement
   - For larger edits (new paragraph, table): insert at the location specified by the reviewer reference

2. **Log the change immediately** to `reviews/changelog-round-N.md`:
   ```markdown
   ### Issue #3 (MAJOR): Missing Ablation Study Results
   
   **File touched:** drafts/results.md
   **Change:** Added ~100 words on attention module ablation results
   **Why:** Reviewer noted lack of justification for architectural choice
   **Lines:** inserted after line 125 (Results subsection "Ablation Studies")
   **Change text:**
   [Exact text of the insertion, or "Reworded existing paragraph"]
   ```

3. **If the edit touches citations** (e.g., changed a referenced result or added a new claim):
   - Run `python scripts/cite_audit.py --quick` to check for undefined keys
   - If undefined keys found: note them in the changelog with a TODO for the user
   - Example: "⚠️  New claim requires citation source. Suggested: search for 'attention mechanism visual inspection' and add to registry."

4. **If the edit touches a claim's wording** — which "reframe the claim",
   "remove overclaim" and "strengthen framing" fixes always do — run
   `python scripts/claim_check.py --check overclaim`. Revision is exactly where
   a claim silently climbs the ladder: a reviewer asking for a stronger
   contribution is answered by upgrading a verb rather than by adding evidence.
   - An `overclaim` hit names the card whose source no longer supports the new
     wording. Read that card's `claim` text before deciding.
   - Legitimate resolutions: restore the weaker verb, cite a source that does
     support the stronger one, or record in the changelog why the stronger verb
     is licensed (your own data, an established mechanism, an uncarded source).
   - Never resolve it by deleting the citation — that converts a visible
     overclaim into an invisible uncited assertion.
   - Ladder semantics: `.claude/skills/academic-writing/reference/claim-strength.md`

#### 4e: Move to Next Issue

Repeat 4a–4e until all Major issues in the section are addressed, then repeat for Minor issues.

### Step 5: Summary of Changes

After working through all issues for the section, display:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REVISIONS COMPLETE: [section-file]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Changes applied:
  • Major issues: X resolved, Y pending
  • Minor issues: A resolved, B pending
  • Files modified: drafts/[section-file]
  • Changelog: reviews/changelog-round-N.md

Next steps:
  1. Revise other sections (/revise [next-section])
  2. Once all sections done, optionally draft a response-to-reviewers letter
  3. Re-run /verify-citations if new citations were added
  4. Re-run /critique if major structural changes were made
```

### Step 6 (Optional): Draft Response-to-Reviewers Letter

If all Major issues are resolved (or user requests it), offer to draft a response-to-reviewers letter:

```
Draft a response-to-reviewers letter? [y/n]
  
  y → Generate from changelog; save to responses/response-round-N.md
  n → Skip; you can draft manually later
```

If yes:

1. **Generate template:**
   ```markdown
   # Response to Reviewers — Round N
   
   Dear Editors and Reviewers,
   
   We thank the reviewers for their careful reading and constructive feedback.
   Below we address each major point and detail the changes made to the manuscript.
   
   ## Response to Reviewer Comments
   
   ### Major Issue 1: [Title from review]
   **Reviewer:** [issue text]
   **Our response:** We have [addressed / revised / added] [specific change].
   [Cite changelog item.]
   
   ### Major Issue 2: ...
   
   [Similar structure for each Major issue]
   
   ### Minor Issues
   We have incorporated the following minor improvements:
   - [Issue 1: change made]
   - [Issue 2: change made]
   ...
   
   We believe these revisions address all concerns and strengthen the manuscript.
   
   Sincerely,
   [Author name(s)]
   ```

2. **Fill in each issue** from the changelog with the actual text of revisions.
3. **Save to** `reviews/response-round-N.md`.
4. **Remind user:** "Review and personalize the response letter before submitting with your revision."

## Reference

- **Gate file:** `reviews/round-N.md` (latest peer review report)
- **Output artifacts:** 
  - Modified section files in `drafts/`
  - `reviews/changelog-round-N.md` (detailed change log)
  - `reviews/response-round-N.md` (optional; response to reviewers)
- **Scripts:**
  - `python scripts/cite_audit.py --quick` — check for undefined citations after edits
  - `python scripts/claim_check.py --check overclaim` — check that reworded claims still sit on the rung their source supports
- **Skill references:** academic-writing (clarity/register guidance + [claim-strength.md](../academic-writing/reference/claim-strength.md)), comparative-analysis (comparison fairness), paper-types (type-specific structure rules)

---
*Revisions are tracked and attributed; response-to-reviewers is drafted from the changelog.*
