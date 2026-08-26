---
name: verify-citations
description: "Verify bibliographic integrity before finalization. Checks in-text citations against bibliography, validates entries against authoritative records (DOI/Crossref), detects fabricated/retracted papers, and flags missing citations. Applies safe auto-fixes (year/title corrections); escalates ambiguous cases and fabrications to the user. Produces verify-status.json (consumed by /critique and /submit-check). Use when a draft is ready to move to peer review."
disable-model-invocation: true
argument-hint: "(no arguments)"
---

# /verify-citations — Bibliographic Integrity Gate

## Gate: Abort if Failed

- **Check:** At least one file exists in `drafts/`. 
  - If empty: abort with "No draft found in drafts/. Draft and save a section first (e.g., /draft introduction)."
- **Check:** `bib/references.bib` exists and is not empty.
  - If missing/empty: abort with "No bibliography file. Run a literature review first (/lit-review) or add sources manually."

## Procedure

### Step 1: Prepare Input for citation-verifier Subagent

Gather the following before dispatching:

1. **Draft paths:** List all files in `drafts/` (e.g., introduction.md, methods.md, results.md)
2. **Bibliography path:** `bib/references.bib`
3. **Registry path:** `sources/registry.jsonl`
4. **Output location:** `reviews/verify-round-N.md` where N = next verification round number (count existing reviews/verify-*.md files and add 1; if none exist, N=1)
5. **Venue claims:** Search the draft text for claims about publication venue indices (e.g., "published in an SCIE-indexed journal", "high-impact venue"). Record these as "venue_claims_in_text: true" or "false".

### Step 2: Dispatch citation-verifier Subagent

Provide this input contract to the agent:
- **What:** "Verify all bibliographic entries in this manuscript against authoritative records. Detect fabricated citations, retracted papers, missing entries, and registry discipline breaches."
- **Paths:** drafts/, bib/references.bib, sources/registry.jsonl, and where to write the report (reviews/verify-round-N.md)
- **Venue claims:** Whether the text asserts index status claims that need re-checking
- **Expected output:** verify-status.json (gate file) and a detailed report on disk

The agent will run:
- `python scripts/cite_audit.py --json` (text ↔ bib cross-diff)
- `python scripts/doi2bib.py --verify --bib bib/references.bib` (authoritative record check per entry)
- Retraction checks (scholar-sidekick or Crossref lookups)
- Venue re-checks if venue claims exist in text

### Step 3: Receive Agent Return & Write Its Report

citation-verifier has no Write tool — it returns content, you write it. The agent returns:
- **Full per-entry report body**, ready to write verbatim to `reviews/verify-round-N.md`
- **verify-status.json fields:** `result` (PASS|FAIL), `checked`, `fabricated`, `retracted`, `missing`, `unresolved`, `fixable`, `live_recheck` (`doi2bib_confirmed`/`cite_audit_confirmed` booleans + the `bib_checked`/`drafts_checked` paths actually used — written by the script itself, not the agent)
- **Safe-fix list:** FIX patches that are auto-applicable (year corrections, title field whitespace, author name normalization, venue_meta updates)

verify-status.json is script-owned (Invariant 6, like registry/cards/venues/
references.bib) — write it via `scripts/write_verify_status.py`, never a raw
`Write` (protect_data_files.py blocks direct Write/Edit/Bash-redirect of this
file). The script also rejects an internally inconsistent PASS (any of
fabricated/retracted/missing/unresolved > 0, or checked <= 0) before writing,
so a copy-paste error in transcribing the agent's fields fails loudly instead
of silently producing a bad gate file. Before writing a PASS it additionally
re-runs `doi2bib.py --verify` and `cite_audit.py` live against the current
`bib/references.bib`/`drafts/` and refuses to write if that independent
recheck disagrees (real fabrication found, or a citation key with no
matching bib entry) — this can't be skipped via a flag, only degrades
gracefully when network/files are unavailable. It does NOT re-derive
retraction or orphan-citation judgment calls; those stay agent-reported.
When `--bib`/`--drafts` don't point at anything on disk (a genuinely fresh
project, or a wrong path), the recheck can't run at all — that fact is
recorded in `live_recheck.doi2bib_confirmed`/`cite_audit_confirmed` (both
`false`) plus a stderr `WARN`, so a PASS reached this way is visibly *not*
independently corroborated instead of looking identical to a confirmed one.

Write the report body to `reviews/verify-round-N.md` now (N from Step 1).

### Step 4: Handle Results Based on Status

#### If `result: "PASS"`
- Go to **Step 5** and write the gate file there — one place issues that command, so a
  reader cannot end up running it twice or reading two drifting spellings of it.
- Then log to console: "✅ Citation verification passed: N entries checked, 0 issues. verify-status.json written."
- **End workflow.** User may proceed to `/critique`.

#### If `result: "FAIL"` with fixable issues
- Show user the safe-fix list (year corrections, author normalization, etc.)
- **Auto-apply safe fixes:**
  ```bash
  python scripts/bib_doctor.py --fix
  ```
- Log each applied fix to console (e.g., "smith2020 → year: 2021 [via Crossref]")
- **Re-run verifier** after fixes by repeating Steps 1–3 (or ask agent to do a second pass)
- Continue until `result: PASS` or proceed if user accepts remaining unresolved items

#### If `result: "FAIL"` with FABRICATED or RETRACTED entries
- **Show user each problematic entry:**
  ```
  [FABRICATED] smith2020laser
    In text: "Smith (2020) demonstrated laser fusion via novel approach"
    DOI: 10.1234/example
    Bibliography: title = "A Novel Approach to Laser Fusion"
    Crossref says: title = "Laser Fusion: Historical Overview" (year 2019, different DOI)
    → Bibliography title ≠ Crossref record. Real citation likely misidentified.
  ```

- **For each FABRICATED entry, offer replacement workflow:**
  1. Search for the legitimate source: ask user "Is this actually smith2019 (historical overview)? Or should we search for a 2020 paper?"
  2. If user has a correction: dispatch literature-scout to find the real paper, then
     `python scripts/doi2bib.py --doi <real-doi> --append bib/references.bib` for the
     replacement entry. Never hand-edit the bib file — `protect_data_files.py` blocks
     it, and the block is correct: an entry nobody can trace back to a DOI fetch is
     exactly what this gate exists to catch.
  3. If the entry should be removed, do it in this order — **prose first, bib second**:
     ```bash
     # 1. Edit drafts/: repoint [@smith2020laser] at the real key, or delete the claim.
     # 2. Then retract the entry:
     python scripts/bib_doctor.py --retract smith2020laser
     ```
     `--retract` refuses while the key is still cited anywhere in `drafts/`, which is
     what keeps a wrong citation from quietly becoming a missing one. If the user
     deliberately wants the reverse order, `--force` allows it and the JSON records
     that it was used.
  4. Copy the `removed_bibtex` field from the command's JSON output into
     `reviews/verify-round-N.md`, under the reason for the retraction. `references.bib`
     has no history of its own — this is the only surviving record of what the entry said.
  5. Re-run verifier

- **For RETRACTED entries:**
  - Show: "[RETRACTED] smith2020ethics — retraction notice: [brief reason], retraction DOI: [link]"
  - Offer: "Replace with [suggested alternative] or remove claim?"
  - User decides. Same two sanctioned paths as above: `doi2bib.py --append` for a
    replacement, `bib_doctor.py --retract <key>` for the removal, prose edited first.
  - Also mark the source in the register so a later search does not re-surface it as a
    candidate: `python scripts/registry_db.py set-status <id> excluded` with the
    candidate: `python scripts/registry_db.py set-status <rec_id> excluded --reason "retracted: <notice DOI>"`.
  - Re-run verifier

### Step 5: Write verify-status.json via write_verify_status.py

Once verification passes, run:
```bash
python scripts/write_verify_status.py --result PASS --checked 47 \
  --fabricated 0 --retracted 0 --missing 0 --unresolved 0 --fixable 0
```

This writes (atomically, with the timestamp filled in automatically):
```json
{
  "result": "PASS",
  "checked": 47,
  "fabricated": 0,
  "retracted": 0,
  "missing": 0,
  "unresolved": 0,
  "fixable": 0,
  "timestamp": "2026-07-04"
}
```

This file is the gate consumed by `/critique` and `/submit-check`. A direct
`Write`/`Edit`/Bash-redirect to `verify-status.json` is blocked by
`protect_data_files.py` — this script is the only sanctioned path.

## Summary to User

Upon completion (PASS):
```
✅ Verify-citations complete.
   • 47 entries checked
   • 0 fabricated, 0 retracted, 0 missing, 0 unresolved
   • verify-status.json written
   • Next: /critique for peer review
```

Upon completion (FAIL, manual review needed):
```
⚠️  Verify-citations requires your input.
   • N entries checked
   • M unresolved (ambiguous title/author — needs human judgment)
   • L fabricated (real DOI + mismatched metadata — needs source hunt or removal)
   • K retracted (removed from literature — find replacement or remove claim)
   
   Actions:
   1. Review ambiguous entries above
   2. Search for replacement sources (dispatch literature-scout or search manually)
   3. Update drafts/ and bib/references.bib accordingly
   4. Re-run /verify-citations
```

## Reference

- **Subagent:** citation-verifier (sonnet model — upgraded from haiku since this is the
  anti-fabrication gate; mechanical comparison + obstacle escalation)
- **Scripts:** 
  - `python scripts/cite_audit.py --json` — in-text ↔ bib diff report
  - `python scripts/doi2bib.py --verify --bib bib/references.bib` — per-entry field validation
  - `python scripts/bib_doctor.py --fix` — auto-apply safe patches
  - `python scripts/venue_check.py --issn <issn>` — index status re-check
- **Skill reference:** citation-styles (understanding BibTeX structure), literature-review (source discipline)
- **Output artifact:** `verify-status.json` (gate for /critique and /submit-check)

---
*Zero-fabrication citation policy: Nothing ships past this gate unverified.*
