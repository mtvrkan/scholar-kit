---
name: restyle
description: "Switch the manuscript's citation style (APA 7, IEEE, Chicago, Vancouver, Harvard, MLA 9, or a custom CSL) after drafting has already started, based on user feedback or a venue change. An INSTRUCTION to change this project's style — a QUESTION about what a style requires, or about what switching one involves, belongs to citation-styles. Triggers on: 'switch to APA', 'change citation style', 'use IEEE instead', 'restyle references', 'atıf stilini değiştir'."
disable-model-invocation: true
argument-hint: "<apa7|mla9|chicago-author-date|chicago-notes|ieee|vancouver|harvard|csl:<file>>"
---

# /restyle — Switch Citation Style Without Touching Drafts or the Bibliography

The kit's citation-styles skill already guarantees this is a **one-config-line
change** (Golden Rule 3: `bib/references.bib` stays untouched, in-text citations
are always pandoc `[@key]` syntax, style is applied only at render time via CSL).
This command is the safe, single-step wrapper around that mechanism — it exists
because users legitimately change their mind on style mid-project (a common
request: "I usually use APA, but let's see what other options make sense").

**Never hand-edit `bib/references.bib` or any draft file for a style change.**
If either seems necessary to satisfy the request, stop — that means the request
is not actually a style switch (e.g. a genuinely non-CSL-expressible convention),
and the citation-styles skill's Common Pitfalls table should be consulted instead.

## Procedure

### 1. Parse and Validate the Target Style

1. Take the argument as the target style key. If empty, ask the user to pick
   from the same 7-option list `new-project`'s wizard uses (APA 7 / IEEE /
   Chicago Author-Date / Vancouver-AMA / Harvard / MLA 9 / custom CSL).
2. **Validate the key** against `.claude/skills/citation-styles/SKILL.md`'s "CSL
   File Mapping" table. Valid enum keys: `apa7`, `mla9`, `chicago-author-date`,
   `chicago-notes`, `ieee`, `vancouver`, `harvard`, or `csl:<file>` for a
   user-supplied CSL.
   - Unrecognized key (e.g. a common misspelling or a style the kit doesn't
     ship, like "nature" or "acs") → do NOT guess a filename. Report the valid
     key list and ask the user to pick one, or to use `/ingest-template` first
     if they have the exact CSL file for their venue.

### 2. Resolve and Confirm the CSL File Exists

1. Resolve the key to its `.csl` filename via the mapping table (never derive
   it by lowercasing/reformatting the key — `apa7` is not `apa7.csl`).
2. For an enum key: confirm `templates/csl/<file>.csl` exists in this project.
   Missing → this is a kit installation problem, not a user error; report it
   plainly rather than silently proceeding with the old style.
3. For `csl:<file>`: confirm the user-supplied path exists (relative to project
   root, typically under `templates/ingested/` if it came from `/ingest-template`
   — TEMPLATE SUPREMACY still applies if `templates/ingested/template-profile.md`
   exists, so warn the user if their `/restyle` choice conflicts with an ingested
   template's own citation-style rule).

### 3. Read Current Style and Report the No-Op Case

1. Read PROJECT.md's `- **Citation style:**` bullet.
2. If it already equals the target key: report "Already using `<key>` — nothing
   to change" and stop. Do not touch the file or trigger a rebuild for a no-op.

### 4. Apply the Change

1. **Edit PROJECT.md** (Edit tool, in this session — PROJECT.md is not one of
   the hook-protected data files) to change only the
   `- **Citation style:**` bullet value, keeping the rest of the line's
   Markdown comment intact.
2. Do **not** touch `bib/references.bib`, any file under `drafts/`, or
   `outline/outline.md`. A style switch changes rendering only.

### 5. Sanity-Check, Don't Re-Verify

A style switch cannot introduce a missing/fabricated citation (the underlying
`[@key]` references and `bib/references.bib` entries are unchanged), so do
**not** re-run `citation-verifier` or `/verify-citations` — that would be pure
token waste for a change that cannot affect their result. Do run the cheap,
already-fast structural check to catch the one thing a style switch *can*
break — a target style with stricter/different required fields than the
bibliography currently satisfies:
```bash
python scripts/bib_doctor.py --bib bib/references.bib
```
Report any new field-completeness gaps (e.g. Vancouver expects PMID/volume
conventions some entries may lack) as advisory, non-blocking notes — these are
pre-existing bibliography gaps the switch merely makes newly relevant, not
something this command caused or must fix.

### 6. Offer to Rebuild

If `build/paper.pdf` or `build/paper.docx` already exists (a prior build under
the old style), tell the user the existing artifact still reflects the OLD
style and ask whether to rebuild now. If yes, dispatch `format-engineer` exactly
as `/submit-check` Step 6 does (same build/docx/pdf mode, same artifacts
directory) — this command does not build directly, to avoid duplicating that
agent's build-time cross-reference and numbering checks.

### 7. Report

```
Citation style: [old-key] -> [new-key]
CSL file: templates/csl/[resolved-file].csl
bib/references.bib: unchanged (47 entries)
Drafts: unchanged
Bibliography hygiene: ✓ clean (or: N advisory field-completeness notes)
Rebuild: [triggered format-engineer -> build/paper.pdf] | [skipped — no prior build found] | [declined by user]
```

## Common Mistakes This Command Prevents

| Mistake | Why /restyle avoids it |
|---|---|
| Manually rewriting `[@key]` citations into `(Author, 2024)` for the new style | In-text syntax never changes; only render-time CSL does. |
| Re-fetching or editing `bib/references.bib` entries | The bibliography is style-agnostic; only the CSL file changes how it renders. |
| Re-running the full citation-verifier gate | A style switch cannot create a fabricated/missing citation — nothing there to re-check. |
| Guessing a CSL filename from the style name | Always resolve via the citation-styles mapping table; never lowercase-derive. |
| Forgetting an already-built PDF/DOCX still shows the old style | Step 6 explicitly flags a stale prior build and offers to rebuild. |

## See Also

- `.claude/skills/citation-styles/SKILL.md` — the underlying mechanism and full CSL mapping table.
- `.claude/agents/format-engineer.md` — the build agent this command may dispatch.
- `scripts/bib_doctor.py` — the only check this command re-runs.
