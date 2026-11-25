---
name: submit-check
description: "Final pre-submission checklist. Verifies all gates (citations verified, reviews resolved), runs type-specific and reporting-guideline checks, validates word budgets and RQ traceability, audits bibliography hygiene, builds template-compliant outputs, and emits AI-disclosure and plagiarism-screening reminders. Produces SUBMIT-READY ✅ report or a blocking-items list."
disable-model-invocation: true
argument-hint: "(no arguments)"
---

# /submit-check — Final Pre-Submission Checklist

## Gates: Abort at First Failure (in order)

These gates MUST all pass; abort with explanation if any fail.

### Gate 1: verify-status.json Exists and result=PASS

1. **Check:** File `verify-status.json` exists in project root.
   - If missing: abort with "Citations not yet verified. Run `/verify-citations` first."

2. **Read verify-status.json** and check `result` field.
   - If `result != "PASS"`: abort with:
     ```
     Citation verification FAILED (result: FAIL).
     
     Counts from verify-status.json:
       • Fabricated citations: [N]
       • Retracted papers: [M]
       • Missing citations: [K]
       • Unresolved (ambiguous): [J]
     
     Resolution required. Run /verify-citations to fix or escalate issues.
     ```

### Gate 2: Latest Review Has No Open Major Issues

1. **Locate latest review:** List files in `reviews/` matching `round-*.md`; select the highest-numbered file.
   - If no review found: abort with "No peer review found. Run `/critique` first."

2. **Read the latest review file** and count items under "## MAJOR ISSUES".
   - If any Major issues remain: abort with:
     ```
     Open Major issues remain (count: N).
     
     Unresolved issues:
       [ ] Issue 1: [title from review]
       [ ] Issue 2: [title]
       ...
     
     Complete revisions via /revise before resubmitting.
     ```

3. **Verify via changelog** (optional): If `reviews/changelog-round-N.md` exists, check that all Major issues are marked as "resolved" or have a documented decision.

### Gate 3: PROJECT.md Exists and Complete

1. **Check:** File `PROJECT.md` exists.
   - If missing: abort with "No PROJECT.md found. Run `/new-project` or create one manually."

2. **Verify required bullets in PROJECT.md are filled (not "TBD"):**
   - `- **Type:**` — paper type (empirical-imrad, systematic-review, qualitative, thesis-msc, etc.)
   - `- **Output language:**` — output language (en, tr, both)
   - `- **Citation style:**` — citation style (apa7, ieee, chicago-author-date, etc.)
   - `- **Target venue:**` — journal or conference name
   - All must be non-empty and not "TBD".
   - If missing: abort with "PROJECT.md incomplete. Fill in: Type, Output language, Citation style, Target venue."

## Procedure (Pass All Gates First)

### Step 1: Type-Specific Checklist

1. **Read the paper type** from PROJECT.md's `- **Type:**` bullet.

2. **Locate the reference file via the canonical mapping table:**
   - Read `.claude/skills/paper-types/SKILL.md`'s "Canonical Type → File
     Resolution" table and look up the type's **Reference file** column.
   - Do NOT substitute `reference/[type].md` naively — most type keys do not
     match their reference filename 1:1 (e.g. `narrative-review`,
     `scoping-review`, `rct`, and `observational` all resolve to a different
     file than their own name would suggest; `thesis-*` types have no
     `reference/` file at all — use the thesis-structure skill instead).

3. **Run the type checklist** (displayed from the reference file).
   - Example for IMRaD:
     ```
     IMRaD Checklist:
       [ ] Introduction: RQ/hypothesis stated (not buried)
       [ ] Introduction: justification (why this RQ matters)
       [ ] Methods: design clearly described (experimental vs observational vs quasi-experimental)
       [ ] Methods: sample/population described (N, age, demographics if relevant)
       [ ] Methods: statistical test justification (why this test for this hypothesis?)
       [ ] Results: findings reported in neutral language (no interpretation here)
       [ ] Results: statistical reporting includes: test statistic, p-value, effect size, CIs
       [ ] Discussion: interpretation tied to hypothesis (did results confirm/refute?)
       [ ] Discussion: limitations acknowledged (internal + external validity threats)
       [ ] Discussion: implications stated (what do findings mean?)
       [ ] Conclusion: no claims beyond evidence
       [ ] Abstract: body length match (abstract claims ⊆ body claims)
     ```

4. **For each checklist item:**
   - Scan the draft for the item (or ask: "Does your manuscript include this?")
   - Mark [✓] if present, [✗] if missing
   - If any [✗]: list them as "Type checklist failures"

### Step 2: Reporting Guideline Checklist

1. **Identify the reporting guideline** for the paper type.
   - IMRaD + RCT → CONSORT
   - IMRaD + observational → STROBE
   - Systematic review → PRISMA 2020
   - Qualitative → COREQ or SRQR
   - Case report → CARE
   - Scoping review → PRISMA-ScR
   - Other types: no mandatory guideline (note this)

2. **Locate the guideline reference** (if it exists):
   - `.claude/skills/reporting-guidelines/reference/[guideline].md`
   - File format: checklist item → "Must appear in section: [section name or figure]"
   - No file exists for full systematic-review PRISMA 2020 (only PRISMA-ScR for
     scoping reviews is covered) — for that case, fall back to the
     literature-review skill's PRISMA guidance and note the gap in the report
     rather than silently skipping the check.

3. **For each item in the guideline checklist:**
   - Ask or scan: "Does the draft include item X?" 
   - Desired sections for key items (examples):
     - Flow diagram: appears in Results or Introduction as a figure
     - PRISMA table (participant characteristics): Results section
     - Methods description detail: full page or more; not condensed
     - Search strategy: documented with: databases, date range, keywords, number of hits per DB
   - If item missing: note as "Reporting guideline gap"

4. **Report findings:**
   ```
   Reporting Guideline: [name] ([guideline items checked] of [total])
   
   Missing or incomplete items:
     • Item 3: Search strategy not reproducible (database names missing)
     • Item 12: Flow diagram missing (critical for systematic reviews)
   ```

### Step 3: Word Budget & RQ Traceability Check

1. **Run the word budget script:** `python scripts/word_budget.py --strict`
   Outputs total vs PROJECT.md budget, per-section counts vs type-expected
   proportions, and overage/underage per section.

2. **Run RQ traceability audit:** `python scripts/word_budget.py --rq-trace`
   Maps RQs (outline) → Results headings → Conclusion claims, and reports
   orphaned RQs (stated in the intro but never answered).

3. **Report findings:**
   ```
   Word budget:
     Total: [actual] / [budget] words ([+/- % deviation])
     By section: [intro: X / Y], [methods: A / B], [results: C / D], ...
   
   RQ Traceability:
     ✓ RQ1: "Can CNNs detect bearing faults?" → Results section: "Bearing Fault Detection" → Conclusion: "CNNs achieve 89% accuracy"
     ✗ RQ2: "What ablations improve performance?" → Mentioned in intro but no Results subsection
   ```

4. **If issues found:**
   - Word budget >110% or <90% of target: flag "Word budget outside acceptable range"
   - Missing RQ answer: flag "RQ stated but not answered in Results/Conclusion"

### Step 4: Turkish Thesis Special Check (If Applicable)

Only run if PROJECT.md's `- **Type:**` starts with `thesis` AND `- **Output language:**` is `tr` or `both`:

1. **Check:** File `drafts/ozet.md` (Turkish abstract) exists.
   - If missing: note "Turkish abstract (Özet) not found. Required for Turkish theses."

2. **Run Özet ↔ Abstract equivalence check** via style-auditor (if English abstract also exists):
   ```
   # Pseudo-procedure:
   Read drafts/ozet.md (Turkish abstract)
   Read drafts/abstract.md (English abstract, if exists)
   
   Check:
     • Claim counts match (both should cover same key findings)
     • Structure similar (both follow same logical progression)
     • No new claims in one without the other
   ```
   - Report: "✓ Özet ↔ Abstract equivalent" or "✗ Mismatches found: [list]"

### Step 5: Bibliography Hygiene

1. **Run bibliography doctor:**
   ```bash
   python scripts/bib_doctor.py --bib bib/references.bib
   ```
   (no `--strict` flag exists — the script already exits 2 on any problem, 0 if
   clean; that IS the strict check.) Checks: required fields per entry type
   (preprints need a locator `doi`/`url` instead of `journal`); DOI format and
   prefix normalization; duplicates (by DOI, or ≥95% title similarity); key
   normalization (surname+year+word, ascii lowercase — reported, not
   auto-renamed); `verified={true}` presence (flags any entry not produced by
   `doi2bib.py`). It does NOT judge whether a year is plausible — that is
   `temporal_check.py`'s job, run next.

2. **Report findings:**
   ```
   Bibliography check (N entries):
     ✓ All required fields present
     ✗ Duplicate entries: [key1], [key2]
     ✗ Invalid DOI format: [key]
     ⚠  Unusual year: [key] (year 2099)
   ```

3. **If issues found:** List them as "Bibliography hygiene issues."

4. **Optional, for a high-stakes submission:** `python scripts/citation_triangulate.py`
   cross-checks every DOI'd entry against a SECOND index (OpenAlex), corroborating
   the Crossref/doi.org check `doi2bib.py --verify` already ran. One network call
   per DOI'd entry, so recommend — don't require. Reports `AGREE`/`DISAGREE`/
   `NOT_IN_OPENALEX`; a `DISAGREE` never overrides a Crossref PASS (OpenAlex is an
   aggregator, not a registration authority) but is worth a human glance.

### Step 5b: Numeric, Evidence, Figure, Temporal, Claim, Failure-Mode & TR-Style Advisories (Non-Blocking)

These checks are informational and never abort. Each surfaces a defect class a
human would otherwise catch only by spot-checking prose against tables, figures,
dates and evidence cards by hand. None contribute to BLOCKING ISSUES — report
them under "Advisory (non-blocking)" in Step 9.

| Check | Reports |
|---|---|
| `consistency_check.py` | a prose number that disagrees with `analysis/counts.json`, or with another section |
| `evidence_funnel.py` | the cards → sources → included → cited → bib funnel, and evidence extracted but never cited |
| `figure_check.py` | a figure/table mentioned but absent, embedded but never referenced, renumbered or uncaptioned |
| `temporal_check.py` | a future-dated bib entry, and a card citing a year its own source predates |
| `claim_check.py` | a cited sentence claiming more than the card drawn from that same source, and uncited empirical assertions |
| `failure_scan.py` | the 7 AI-research failure modes, re-run after `/revise` |
| `tr_style_check.py` | Turkish register/convention drift, and Özet↔Abstract equivalence |
| `provenance.py --verify` | the attestation chain: a rewritten record (alarming), post-attestation drift (ordinary), or no ledger at all (**"not run", never "no problems"**) |
| `dataset_db.py verify` | *(empirical papers)* data that changed or vanished under its record, a licence never read, a missing citation DOI, human-subject data with no ethics reference |
| `experiment_db.py verify` | *(empirical papers)* a run edited after it was written, a run pointing at unregistered data, a run with no environment, a group with fewer than 3 seeds |
| `overlap_check.py` | *(if the author names their own earlier work)* passages this manuscript shares with their previous papers or thesis chapters — locations, never a percentage, and never a substitute for the institution's own tool |
| `leakage_check.py` | *(empirical papers)* the four checkable leaks — train/test id overlap, the same subject on both sides, duplicate rows across splits, a feature that determines the target. Its own limit belongs in the report: preprocessing fitted outside the fold is read from the manifest's declaration, never detected |

What each one means, what it deliberately does not check, and how to report a
SKIPPED or NOT_AUTOMATED status: [`reference/advisories.md`](reference/advisories.md).
Read it before writing the advisory section — several of these are easy to
report as more (or less) than they are. The chain's own two limits, which any
report of it must carry: [`reference/provenance.md`](reference/provenance.md).

### Step 6: Template-Compliant Build Test

1. **Check:** Does `templates/ingested/template-profile.md` exist?
   - Yes → TEMPLATE SUPREMACY: use template for build
   - No → use kit defaults (latex-thesis or docx-output)

2. **Dispatch format-engineer for final build test:**
   - **What:** `pdf` or `docx` (per PROJECT.md's target format — format-engineer's
     INPUT CONTRACT enum is `pdf | docx | xlsx | template-analysis`; there is no
     separate "final-build" mode)
   - **Confirm:** this is a final build, not a draft preview — gates are PASS,
     Major issues = 0, all checklists complete (format-engineer's INPUT CONTRACT
     explicitly asks for this confirmation to distinguish final builds from
     draft-preview builds, which are exempt from gate checks)
   - **Artifacts:** build/paper.pdf (LaTeX) or build/paper.docx (Word)
   - **Output:** Build status (OK / FIXED / BLOCKED) + any warnings

3. **Agent will:**
   - Compile or render the full manuscript
   - Verify cross-references resolve (Figure 1, Section 2, etc.)
   - Verify figure/table numbering is continuous
   - Verify bibliography renders correctly in the chosen style
   - Check front matter (title page, abstract page if required by template)
   - Fix minor build errors (broken cross-refs, missing figures)

4. **Attest the artifact** on a successful build only, so the chain ends where the
   submission does and any later rebuild shows up as drift:
   `python scripts/provenance.py --record build --path build/paper.pdf --note "submit-check"`

5. **Report to user:**
   ```
   Build test:
     Status: ✅ OK
     Output: build/paper.pdf
     Verification:
       ✓ Cross-references resolve
       ✓ Figures/tables numbered continuously
       ✓ Bibliography renders in [IEEE style]
       ✓ Front matter complete
   ```

### Step 7: AI Disclosure Reminder

If `drafts/compliance-statements.md` doesn't exist yet, mention `/disclosures`
can generate the AI-disclosure, CRediT authorship, and funding statement text
below — still the user's responsibility to verify against the actual venue
policy (Scholar-Kit does not guarantee compliance; see the reminder itself).

Display this to user (non-blocking, but mandatory reminder):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  AI-DISCLOSURE REMINDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your institution and target venue have specific policies on AI use in academic writing.
Scholar-Kit WILL NOT verify compliance for you. YOUR RESPONSIBILITY:

1. **Check your institution's AI policy:**
   - Does your university allow generative AI in coursework/theses?
   - Any special approval required? (e.g., ethics committee sign-off)
   - Consult: [institution name] student handbook or research integrity office

2. **Check your target venue's AI policy:**
   - Journal website: Author Guidelines section
   - Look for: "Generative AI", "ChatGPT", "LLM", "disclosure requirement"
   - Common venues' stances:
     • Nature, Science: AI use must be disclosed; limitations discussed
     • Many medical journals: AI-generated abstracts not permitted
     • CS conferences (NeurIPS, ICML): increasing disclosure requirements
     • Some journals: full ban on AI writing tools

3. **Include a disclosure statement if required:**
   - Example disclosure for acknowledgments or end of methods:
     ```
     AI Disclosure: This manuscript was prepared with assistance from Claude 
     (Anthropic), used for: [literature synthesis / figure caption drafting / 
     terminology checking]. All citations verified by [author name]. No data or 
     results are AI-generated. [Author name] takes full responsibility for all 
     claims and any errors.
     ```

Recommend: Check with your advisor/editor BEFORE submitting if unsure.
```

### Step 8: Plagiarism Screening Reminder

Display (non-blocking):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 PLAGIARISM SCREENING — YOUR RESPONSIBILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scholar-Kit DOES NOT run plagiarism checks (Turnitin, iThenticate, etc.).
Before final submission:

1. Your institution likely requires institutional similarity screening
   • Check with: Graduate office / department secretary
   • Common tools: Turnitin (most US/UK universities), iThenticate (many international)
   • Acceptable similarity: varies by discipline (typically 10–20% for new writing)

2. What you should check:
   • Direct quotes: ensure properly cited and within quote marks
   • Paraphrases: distinct from source wording; citation included
   • Code/algorithms: if from papers, cited or in supplemental materials
   • Figure/table captions: original language; citations if adapted from sources

3. In Scholar-Kit:
   • All sources registered in sources/registry.jsonl
   • All evidence cards tagged with source ID and page
   • Verbatim quote discipline enforced (page numbers required)
   • Use the /export-excel --sheet screening to audit source attribution

Recommendation: Run institutional plagiarism check at final stage (after acceptance decisions if revisions required).
```

### Step 9: Final Status Report

Compile all results:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUBMIT-READY CHECKLIST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Gates (all PASS):
  ✅ Citation verification: PASS (verify-status.json)
  ✅ Peer review Major issues: 0 open
  ✅ PROJECT.md complete

Type-specific checklist ([type]):
  ✅ N/N items present
  (or list any missing items)

Reporting guideline ([guideline]):
  ✅ M/M items present
  (or list any missing/incomplete items)

Word budget:
  ✅ [Total] words ([+/- X% from budget])
  (or list imbalances)

RQ Traceability:
  ✅ All RQs answered in Results/Conclusion
  (or list orphaned RQs)

Bibliography hygiene:
  ✅ All N entries pass sanitization
  (or list issues)

Advisory (non-blocking):
  ✅ Numeric consistency: no inconsistencies detected
  ✅ Evidence funnel: every included source's evidence was used
  ✅ Figures/tables: numbered, referenced, and captioned consistently
  ✅ Temporal check: no inconsistencies detected
  ✅ Claim strength: no overclaims or uncited assertions
  ✅ Failure modes: no tells (M2 delegated, M4 not automated)
  (or list consistency_check.py / evidence_funnel.py / figure_check.py / temporal_check.py /
   claim_check.py / failure_scan.py / tr_style_check.py warnings — these never block)

Build test:
  ✅ Output ready: build/paper.[pdf|docx]
  (or list build failures)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ SUBMIT-READY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your manuscript is ready for submission to [target_venue].

Final steps (outside Scholar-Kit):
  1. ⚠️  Verify AI policy with institution and venue (see reminder above)
  2. 📋 Run plagiarism screening (Turnitin / iThenticate)
  3. 📤 Submit to target venue
  4. 📁 Save a copy locally and to version control

Build artifacts:
  • PDF: build/paper.pdf
  • DOCX: build/paper.docx
  • Bibliography: bib/references.bib
  • Evidence: evidence/cards.jsonl (for reviewers if open-science supported)
```

Or if issues remain:

```
⚠️  BLOCKING ISSUES — CANNOT SUBMIT YET

Fix required before proceeding:
  ✗ [Issue 1]: [description]
  ✗ [Issue 2]: [description]
  ...

Next steps:
  1. [Fix action 1]
  2. [Fix action 2]
  3. Re-run /submit-check
```

## Reference

- **Gate files:** 
  - `verify-status.json` (citations verified)
  - `reviews/round-N.md` (latest peer review)
  - `PROJECT.md` (project metadata)
- **Scripts:**
  - `python scripts/word_budget.py --strict` (budget check) and separately
    `python scripts/word_budget.py --rq-trace` (RQ↔heading trace) — these are
    mutually exclusive modes, NOT combinable flags (`--rq-trace` ignores
    `--strict` entirely and always exits 2 on any untraced RQ)
  - `python scripts/bib_doctor.py --bib bib/references.bib` (exit 2 = problems found, no `--strict` flag needed)
  - `python scripts/consistency_check.py` (non-blocking; add `--strict` yourself only if you want it to gate)
  - `python scripts/evidence_funnel.py` (non-blocking, report-only)
  - `python scripts/figure_check.py` (non-blocking; add `--strict` yourself only if you want it to gate)
  - `python scripts/temporal_check.py` (non-blocking; add `--strict` yourself only if you want it to gate)
  - `python scripts/claim_check.py` and `python scripts/failure_scan.py` (both non-blocking; add `--strict` yourself only if you want either to gate)
  - `python scripts/tr_style_check.py` (Turkish output only; non-blocking)
  - (format-engineer runs build via `latex_build.sh` and `docx_build.sh`)
- **Reference files:**
  - `.claude/skills/paper-types/reference/<resolved-via-mapping-table>.md` (type checklist)
  - `.claude/skills/reporting-guidelines/reference/[guideline].md` (reporting items)
- **Output artifacts:**
  - `build/paper.pdf` or `build/paper.docx`
  - Console report (SUBMIT-READY or blocking-items list)

---
*Final gate before the world sees your work. All checks pass, all reminders acknowledged, all artefacts built.*
