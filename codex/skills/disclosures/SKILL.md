---
name: disclosures
description: "Generate an AI-use disclosure, CRediT authorship statement, and/or funding statement for the manuscript — the boilerplate sections most journals now require at submission. Triggers on: 'AI disclosure', 'author contributions', 'CRediT statement', 'funding statement', 'who contributed what', 'acknowledgments section'."
disable-model-invocation: true
argument-hint: "<ai|credit|funding|all>"
---

# /disclosures — AI-Use, Authorship, and Funding Statements

Templates three boilerplate statements journals increasingly require at
submission: an AI-use disclosure, a CRediT (Contributor Roles Taxonomy)
authorship statement, and a funding statement. All three are produced by
`scripts/compliance_gen.py`, which never invents a fact — every mode requires
its inputs explicitly (which AI tool, what it was used for, which authors did
what, which grants funded the work). If you don't have an input, ask the user
rather than guessing a plausible-sounding default; a wrong funding source or an
uncredited author is a real, reportable integrity problem, not a cosmetic one.

## Procedure

### 1. Determine Which Statement(s) to Generate

Argument `ai`, `credit`, `funding`, or `all` (default `all` if omitted — ask
the user to confirm scope rather than silently generating all three if the
request's intent was ambiguous).

### 2. AI-Use Disclosure

1. Ask (if not already known from context): which AI tool(s) were used, and
   for what specific tasks (e.g., "literature synthesis," "citation formatting,"
   "grammar checking") — not a vague "AI was used." Also ask who verified the
   citations/claims (usually the corresponding author).
2. Ask which venue-family framing fits: `icmje` (medical/health journals),
   `ieee` (engineering/CS), or `generic` (no specific framing). This changes
   only the opening sentence, not the substantive content.
3. Run:
   ```bash
   python scripts/compliance_gen.py ai-disclosure --tool "<tool>" --uses "<uses>" \
     --venue-family <family> [--verified-by "<name>"]
   ```
4. **Always relay the script's `warning` field to the user** — this statement
   is a starting point, not a guarantee that it satisfies the target venue's
   exact required wording. Point back to `/submit-check` Step 7's existing
   reminder to verify against the actual venue policy.

### 3. CRediT Authorship Statement

1. Ask for the full author list and, for each author, which of the 14 official
   CRediT roles they performed: Conceptualization, Data curation, Formal
   analysis, Funding acquisition, Investigation, Methodology, Project
   administration, Resources, Software, Supervision, Validation, Visualization,
   Writing – original draft, Writing – review & editing.
2. Do not assume a role from context (e.g., "you probably did Writing – original
   draft since you're the corresponding author") — ask, or confirm an inferred
   guess explicitly before including it.
3. Run:
   ```bash
   python scripts/compliance_gen.py credit --authors \
     '[{"name":"Jane Doe","roles":["Conceptualization","Software"]}, ...]'
   ```
   An unrecognized role name is rejected by the script (exit 1) rather than
   silently coerced — if that happens, ask the user which of the 14 official
   roles they meant.
4. The `unassigned_roles` field lists CRediT roles no author was assigned —
   informational only; not every project uses every role, but flag it in case
   a contribution (e.g., Funding acquisition) was simply forgotten.

### 4. Funding Statement

1. Ask whether the work received external funding.
   - If yes: for each funding source, ask the funder name, grant/award number
     (if any), and which author(s) it was awarded to.
   - If no: confirm explicitly — do not default to "no funding" just because
     the user didn't mention any; ask the direct question.
2. Run:
   ```bash
   python scripts/compliance_gen.py funding --grants \
     '[{"funder":"...", "grant_number":"...", "recipient":"..."}]'
   # or, for explicitly no funding:
   python scripts/compliance_gen.py funding --none
   ```

### 5. Write the Output

Append (or create) `drafts/compliance-statements.md` with one section per
statement generated:
```markdown
## AI Disclosure
<statement text>

## Author Contributions (CRediT)
<statement text>

## Funding
<statement text>
```
This is a supplementary file, not one of the hook-protected data files — write
it directly with the Edit/Write tool, same as any other `drafts/*.md` file.
Tell the user these sections belong in the manuscript's Acknowledgments/
Author Contributions/Funding front- or back-matter per their target venue's
own placement convention (`format-engineer` places them at build time — this
skill only generates the text, it does not itself build the manuscript).

## GATES SUMMARY

| Gate | Trigger | Action |
|------|---------|--------|
| AI tool or specific uses not known | Yes | ASK, don't guess a plausible-sounding default |
| Author role not confirmed by the user | Yes | ASK or explicitly confirm an inferred guess before including it |
| Funding status not stated by the user | Yes | ASK explicitly — never default to "no funding" |
| Unrecognized CRediT role name | Yes | Script rejects (exit 1); re-ask for one of the 14 official roles |

## See Also

- `scripts/compliance_gen.py --help` — the three subcommands and their exact flags.
- `.claude/skills/submit-check/SKILL.md` Step 7 — the existing AI-disclosure
  reminder this skill's output feeds into.
