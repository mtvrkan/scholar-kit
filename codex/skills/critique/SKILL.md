---
name: critique
description: "Run a fresh-context peer review simulation against your draft. Reads the manuscript without drafting history, scores it using a type-specific rubric (IMRaD, systematic review, qualitative, etc.), and returns Major/Minor issues with section references and a mock accept/reject decision. Use after citations are verified (/verify-citations with result=PASS). Produces reviews/round-N.md. Add --panel for a multi-persona editorial panel instead of one reviewer, or --calibrate to check how stable the reviewer's judgment is on this draft."
disable-model-invocation: true
argument-hint: "[--panel] [--calibrate]"
---

# /critique — Fresh-Context Peer Review

## Gates: Abort if Any Failed

These must all pass; abort at the first failure with a clear explanation.

### Gate 1: verify-status.json Exists and result=PASS

1. **Check:** File `verify-status.json` exists in the project root.
   - If missing: abort with "Citation verification not yet run. Execute `/verify-citations` first."

2. **Read verify-status.json** and check the `result` field.
   - If `result != "PASS"`: abort with:
     ```
     Citations not yet verified (result: FAIL).
     Resolve issues via /verify-citations, then re-run /critique.
     Unresolved: [number from verify-status.json]
     Fabricated: [number]
     Retracted: [number]
     ```

### Gate 2: At Least One Draft Section Exists

1. **Check:** The `drafts/` directory contains at least one `.md` file.
   - If empty: abort with "No draft sections found in drafts/. Create a draft first (e.g., /draft introduction)."

### Gate 3: Outline Exists

1. **Check:** File `outline/outline.md` exists.
   - If missing: abort with "No outline found. Run `/outline` to build the manuscript structure first."

## Procedure

### Step 1: Identify the Paper Type and Rubric

1. **Read PROJECT.md** in the project root.
   - Extract the `- **Type:**` bullet value (one of the 15 enum keys listed in
     PROJECT.md's own comment, e.g. "empirical-imrad", "case-report", "thesis-msc")

2. **Locate the rubric file via the canonical mapping table:**
   - Read `.claude/skills/paper-types/SKILL.md`'s "Canonical Type → File
     Resolution" table and look up the `type` value's **Rubric file** column.
   - Do NOT substitute `rubrics/<type>.md` naively — most type keys do not
     match their rubric filename 1:1 (e.g. `case-report`, `rct`, and
     `observational` all resolve to `rubrics/imrad.md`; every `thesis-*`
     type resolves to `rubrics/thesis.md`).
   - If the type value isn't in the table: abort with "Type '<type>' not recognized. Verify PROJECT.md's Type bullet matches one of the paper-types enum keys."

### Step 2: Determine the Review Round Number

1. **Count existing reviews:** List files in `reviews/` directory matching `round-*.md` pattern.
   - If none exist: N = 1 → `reviews/round-1.md`
   - If `round-1.md`, `round-2.md` exist: N = 3 → `reviews/round-3.md`

### Step 2b: Failure-Mode Pre-Scan

Run `python scripts/failure_scan.py` before dispatching the reviewer. It decides
the machine-decidable half of the 7-mode AI-research failure-mode checklist
(Lu et al. 2026) — implausibly exact metrics, own-result numbers backed by no
`analysis/` artefact, unanchored "surprisingly", Methods hyperparameters that
match no run config, hindsight phrasing — and reports each mode's status.

This runs BEFORE the dispatch, not after, because its findings are **inputs to
the review**: a reviewer told "0.87 is narrated in Results but appears in no
artefact" investigates it; a reviewer reading the same sentence cold has no way
to know. Pass the findings into Step 4's brief.

Read the statuses, not just the count:
- `FLAGGED` — include each finding in the reviewer brief.
- `SKIPPED` — note the reason. A type-based skip on a manuscript that *does*
  report measurements means `PROJECT.md`'s Type is wrong; fix that first.
  A `no analysis/ artefacts` skip is itself worth raising as a reproducibility
  finding for a quantitative paper.
- `NOT_AUTOMATED` (M4, shortcut reliance) — no tell exists for this mode. Put
  its questions from the reference doc into the brief explicitly; under
  `--panel` they belong to the devil's-advocate persona.
- `DELEGATED` (M2) — already covered by Gate 1; do not re-litigate it.

Never treat a `CLEAR` as clearance of the mode — it clears the *tell*. The
questions each mode still needs a human to answer, the three verdicts
(CLEAR / SUSPECTED / INSUFFICIENT EVIDENCE) and why INSUFFICIENT EVIDENCE is
not a pass: [reference/failure-modes.md](reference/failure-modes.md).

### Step 3: Prepare Input for reviewer-critic Subagent

Gather the following information:

1. **Draft source:**
   - If the project has an assembled manuscript (e.g., `build/manuscript.md` or similar): use that.
   - Otherwise: ordered list of section files from `drafts/` directory (introduction.md, methods.md, results.md, discussion.md, conclusion.md, in that order).

2. **Outline:** `outline/outline.md` (the reviewer will cross-reference RQs stated in outline with findings in the draft).

3. **Rubric path:** The full path to the rubric file (e.g., `.claude/skills/paper-types/rubrics/imrad.md`).

4. **Round number:** N (from Step 2).

5. **Confirm gate state:** Report that verify-status.json result = PASS.

6. **Failure-mode pre-scan findings:** the FLAGGED items from Step 2b (each with
   its mode, file and sentence), plus M4's ablation questions, plus any SKIPPED
   mode whose reason is worth the reviewer's attention.

### Step 4: Dispatch reviewer-critic Subagent

Provide this input contract to the agent:

- **What:** "Review this manuscript as a skeptical peer reviewer. You have no drafting history or rationalizations — score against the type rubric and report Major/Minor issues with section references."
- **Manuscript:** Draft files or assembled manuscript from drafts/
- **Outline:** outline/outline.md
- **Type:** [from PROJECT.md]
- **Rubric:** Path to rubrics/<type>.md file
- **Round:** N
- **Verification gate:** Confirm verify-status.json = PASS
- **Failure-mode pre-scan:** FLAGGED findings from Step 2b + M4's ablation
  questions. Instruct the reviewer to adjudicate each one rather than restate
  it: a tell is a lead to investigate, not a finding to copy into the report.

The agent will:
- Read PROJECT.md (RQs, promised claims)
- Read outline (expected structure and claims)
- Read the full draft in one pass (as a reviewer would)
- Score against rubric dimensions (contribution clarity, argument integrity, methods-results-conclusion coherence, positioning vs literature, comparison quality, abstract↔body consistency, title fit, limitations honesty, figure/table sufficiency, statistical reporting)
- Hunt classic failure modes: overclaiming, RQ unanswered, conclusions absent from results, uncited assertions, missing limitations, comparison tables without criteria
- Classify findings as Major (blocks acceptance) vs Minor (fixable) vs Suggestion
- Assign a mock decision: Accept / Minor Revision / Major Revision / Reject

### Step 5: Receive Agent Return

The agent returns the full review in this structure (it becomes `reviews/round-N.md`):
- Rubric scores table (dimension → score 1–5 → brief note)
- MAJOR issues: numbered, each with section reference + what + why it blocks + what would fix
- MINOR issues: numbered, brief
- Suggestions: bulleted
- Mock decision (Accept / Minor / Major / Reject) + 3-line rationale

### Step 6: Write Review to Disk

1. **Write the full review** (as returned by the agent) to `reviews/round-N.md`.
   - File format: Markdown with clear section headings (## RUBRIC SCORES, ## MAJOR ISSUES, etc.)

2. **Make the count machine-readable.** The first line of the `## MAJOR ISSUES`
   section must be exactly `Major issues: N`, where N is the number of Major
   issues — `Major issues: 0` when there are none. Write it yourself if the
   agent's return did not carry it; it is a transcription of the agent's own
   verdict, never a re-judgment of it.

   `phase_gate.py` reads that line to decide whether the formatting/build gate
   opens. Without it the hook falls back to counting numbered items in the
   section — and a fallback counts the *shape* of the section, not its meaning.
   Measured across nine consecutive review rounds of one manuscript, the
   pre-2026-08-23 fallback (`^\d+\.` only) was wrong on eight of them, in both
   directions:

   - **Under-counted to zero** whenever the reviewer bolded its item numbers
     (`**1. …`) or used `### 1.` headings — the line no longer starts with a
     digit, so the item is invisible. Four real Major issues read as none, and
     the gate would have opened.
   - **Over-counted** a zero-Major review whose section read `**Yok.**` followed
     by eight numbered items enumerating what the reviewer *looked for and did
     not find* — scored as 8, blocking a build that had none.

   The under-counting direction is the dangerous one: it does not announce
   itself, and a gate that silently returns zero looks exactly like a gate that
   passed. The hook was hardened the same day (it now recognises all three
   numbering styles and refuses — rather than guessing zero — when a
   substantial section yields no parseable items), but hardening a heuristic is
   not the fix. **Writing the number is.**

### Step 7: Convert Major Issues to TODO List

1. **Extract all Major issues** from the review (numbered items under "## MAJOR ISSUES").

2. **Build a numbered TODO list** and append to `drafts/STATUS.md`:
   ```markdown
   ## Round N Review TODOs
   
   [ ] Issue 1: [description] (Section: [ref]) — Priority: MAJOR
   [ ] Issue 2: [description] (Section: [ref]) — Priority: MAJOR
   ```

3. **Save STATUS.md**.

### Step 8: Summary to User

Display a summary in the session:

```
📋 Critique Round N Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RUBRIC SCORES:
  Contribution clarity & novelty:  [score]/5
  Argument integrity:               [score]/5
  Methods-results-conclusion:       [score]/5
  Positioning vs literature:        [score]/5
  Comparison quality:               [score]/5
  Abstract ↔ body consistency:      [score]/5
  Title fit:                        [score]/5
  Limitations honesty:              [score]/5
  Figure/table sufficiency:         [score]/5
  Statistical reporting:            [score]/5

FINDINGS:
  Major issues:    N (block acceptance)
  Minor issues:    M (fixable clarity/structure)
  Suggestions:     K (nice-to-haves)

MOCK DECISION: [Accept / Minor Revision / Major Revision / Reject]
Rationale: [3-line summary]

NEXT STEPS:
  1. Review Major issues in reviews/round-N.md
  2. Use /revise to work through them one by one
  3. Update drafts/STATUS.md with changes
  4. Re-run /critique if needed
```

## Panel Mode (`--panel`)

A single `reviewer-critic` dispatch is one perspective; a real editorial board
catches things one reviewer misses precisely because reviewers disagree.
Panel mode dispatches `reviewer-critic` **4 times in parallel** (4 separate
`Agent` calls in one message — each is an independent fresh-context instance,
same as any single dispatch), each with a distinct PERSONA paragraph prepended
to Step 4's "What" field — the agent's own contract, rubric, and output
structure are unchanged; only the framing differs:

1. **Methodology persona:** "Review primarily as a methodology expert — weight
   design validity, statistical correctness, and reproducibility heavily;
   other dimensions get lighter scrutiny than usual."
2. **Domain persona:** "Review primarily as a domain expert in [field, from
   PROJECT.md/target venue] — weight whether the work is correctly positioned
   against the domain's actual state of the art and whether domain-specific
   claims are accurate."
3. **Generalist persona:** "Review as an informed reader OUTSIDE this
   subfield — weight clarity, whether a non-specialist could follow the
   argument, and whether jargon/notation is adequately explained."
4. **Devil's-advocate persona:** "Actively look for reasons to REJECT this
   paper. Assume the authors may be overselling weak results. Do not extend
   benefit of the doubt on an ambiguous claim — if a claim COULD be read as
   overclaiming, treat it as overclaiming. Your job is the strongest possible
   case against acceptance, not a balanced one."

All 4 receive the identical manuscript, outline, rubric, and round number.

### Synthesis (done in THIS session, not delegated)

1. **Merge Major/Minor/Suggestion lists across all 4 panelists.** Two items
   from different panelists that name the same section and the same
   underlying problem are one merged item — attribute it to every panelist
   who raised it (e.g., "Major issue 3 (raised by: methodology, devil's-advocate)").
   Do not invent a merged item that isn't traceable to at least one panelist's
   actual text — synthesis summarizes what the panel found, it never adds a
   critique of its own.
2. **Apply the anti-sycophancy rule:** if the devil's-advocate panelist's own
   decision is Major Revision or Reject, OR the devil's-advocate panelist
   reported ANY Major issue, the PANEL's overall decision cannot be better
   than Major Revision — regardless of what the other 3 panelists concluded.
   This exists because a lone harsh reviewer is exactly the signal a
   single-reviewer process is most likely to average away; the rule prevents
   that.
3. **Otherwise**, the overall decision is the most conservative (least
   favorable) decision among the remaining 3 panelists — standard editorial
   convention: one reviewer's Major Revision is not overridden by two Accepts.
4. **Write `reviews/round-N.md`** in the exact same structure a single-reviewer
   run produces (`## RUBRIC SCORES`, `## MAJOR ISSUES`, `## MINOR ISSUES`,
   `## SUGGESTIONS`, `## DECISION` — submit-check's gate string-matches these
   headings unchanged), plus one additional appended section:
   `## PANEL BREAKDOWN` — each panelist's own decision and Major-issue count,
   so a reader can see the panel's internal spread, not just the merged
   result.

## Calibration Mode (`--calibrate`)

Two different questions, two modes. Neither gates anything and neither feeds
`/revise`'s TODO list — both are diagnostic.

| Invocation | Question answered |
|---|---|
| `--calibrate` | **Stability:** is reviewer-critic's read of THIS draft consistent? |
| `--calibrate --gold <file>` | **Accuracy:** what is reviewer-critic's error profile against papers whose real outcome you already know? |

### Stability (no gold set)

Dispatch the STANDARD (single persona, no panel framing) `reviewer-critic`
**3 times in parallel** on the SAME draft/outline/rubric, then report how much
the judgment varies. A draft that gets 3 different decisions across 3 fresh
reads has genuinely ambiguous issues worth a human's attention before any
single run's verdict is relied on.

1. Dispatch 3 independent `reviewer-critic` calls, no persona variation.
2. Write each run's report to `reviews/calibration/run-N.md`, then compute the
   comparison with the script rather than by reading them yourself:

   ```bash
   python scripts/review_stability.py reviews/calibration/run-*.md
   ```

   Report its numbers, not a re-reading of them:
   ```
   Run 1: Major Revision (4 Major issues)
   Run 2: Major Revision (3 Major issues)
   Run 3: Minor Revision (1 Major issue)

   Decision agreement: 2/3 runs agreed (Major Revision)   ← decision.agreement
   Major-issue count range: 1-4 (treat any single round-N.md's Major count as a
   lower bound, not a precise figure)                     ← major_issues.min/max
   Sections all three runs flagged: <flagged_sections.agreement>, disagreed
   about: <flagged_sections.unstable>
   ```

   The script exists because a comparison performed by the model on its own
   three outputs is not a measurement of that model. Quote `lowest_agreement`
   with the note the payload carries — a reviewer that is consistently wrong
   scores 1.00.
3. **Write `reviews/calibration-report.md`** (overwritten each run, NOT part of
   the `round-N.md` sequence — `/submit-check` and `/revise` must never pick it
   up as a real review round). Include `review_stability.py`'s JSON payload and
   all 3 runs' full Major-issue lists side by side rather than deduplicating:
   auto-merging hides exactly the disagreement this mode exists to surface.
   The per-run reports stay in `reviews/calibration/` for the same reason.

Stability is not accuracy. A reviewer that is consistently wrong scores
perfectly here. For accuracy you need labelled papers — the next section.

### Accuracy against a gold set (`--gold <file>`)

Full protocol, gold-label isolation rules, tier selection, and how to read the
output: **[reference/calibration.md](reference/calibration.md)**. Read it before
running this — the isolation rule is the whole reason the numbers mean anything,
and it is easy to break by accident.

The three load-bearing points, restated here because breaking any of them
invalidates the run:

1. **The gold set is user-supplied and never bundled.** The kit ships no
   labelled papers; fabricating expected accept/reject labels for real drafts
   would be worse than not measuring at all.
2. **Labels must never enter a reviewer's context.** Do not read the gold file
   into this session before the panels run, do not name the expected outcome in
   a dispatch brief, and do not write labels into the verdict records. Dispatch
   with the paper only; write verdicts carrying `id` / `run` / `decision` /
   `major_issues` and nothing else. `calibration_score.py` refuses to score a
   verdict record carrying a label-shaped field — that refusal is a backstop,
   not permission to be careless upstream.
3. **The join happens in the script, after verdicts are frozen to disk.**

Procedure: validate the gold set → dispatch fresh panels per paper (full tier:
3 or 5 runs each; directional: exactly 1) → write
`reviews/calibration/verdicts.jsonl` → run

```bash
python scripts/calibration_score.py --gold <file> \
    --verdicts reviews/calibration/verdicts.jsonl --tier full
```

→ present the report with **every** caveat it emits, verbatim. The caveats are
not decoration: FNR is the over-harsh rate and FPR the lenient rate under this
script's fixed positive class, and quoting either without that framing inverts
its meaning.

## Reference

- **Subagent:** reviewer-critic (opus model, fresh-context peer review with rubric scoring)
- **Rubric location:** resolved via paper-types/SKILL.md's "Canonical Type → File Resolution" table — never `rubrics/<type>.md` by naive substitution
- **Output artifact:** `reviews/round-N.md` (full review report); `--calibrate`
  instead writes `reviews/calibration-report.md`, a diagnostic, not a review round
- **Downstream:** `/revise` (addresses Major/Minor issues), `/submit-check` (checks all Major items resolved)
- **Scripts:** `python scripts/failure_scan.py` (Step 2b pre-scan; WARN-only) ·
  `python scripts/review_stability.py` (`--calibrate` stability: decision,
  issue-count range and flagged sections across the 3 runs — deterministic, so
  the comparison is not the model reading its own reports) ·
  `python scripts/calibration_score.py` (`--calibrate --gold` accuracy scoring;
  refuses a verdict record carrying a gold-label field)
- **Reference files:** [reference/failure-modes.md](reference/failure-modes.md)
  (the 7 modes, their human questions, and the three verdicts) ·
  [reference/calibration.md](reference/calibration.md) (gold-label isolation,
  the two tiers, and how to read FNR/FPR without inverting them)
- **Skill references:** paper-types (rubrics), comparative-analysis (comparison quality criteria), academic-writing (paragraph/argument architecture + claim-strength ladder), ml-research (ablation design for M4)

---
*Fresh-context review breaks self-defense bias: the reviewer knows the RQs but not your revisions or rationalizations.*
