# Step 5b advisories — what each check reports, and how to read it

These checks are informational and never abort. Each surfaces a defect class a
human would otherwise catch only by spot-checking prose against tables, figures,
dates and evidence cards by hand. None contribute to BLOCKING ISSUES — report
them under "Advisory (non-blocking)" in Step 9.

Moved here from SKILL.md's body when the file reached its 520-line cap; the
progressive-disclosure design (CONTRIBUTING.md) is that the body names the checks
and this file explains them. Nothing was dropped in the move.

1. **`python scripts/consistency_check.py`** — reports any prose number
   (features, models, samples, XAI methods, findings, …) that disagrees with
   `analysis/counts.json`, or is stated with different values across sections
   (e.g. Abstract "four models" vs Results "three"). Example warning:
   `n_findings stated as 99 in results.md but analysis/counts.json says 80`.
   Clean: `✓ No numeric inconsistencies detected`.

2. **`python scripts/evidence_funnel.py`** — reports the cards → sources →
   included → cited → bib-entries funnel (a large card-to-reference narrowing
   is normal, not a defect) and `orphan_cards`: evidence extracted from an
   INCLUDED external source never cited in any draft. Example:
   `103 cards → 23 sources → 20 included → 19 cited → 19 bib entries; 2 source(s)
   extracted but never cited: SRC-0008, SRC-0024 — drop or add the citation.`
   Clean: `✓ Every included source's evidence was used`.

3. **`python scripts/figure_check.py`** — reports a "Figure N"/"Table N"
   mentioned in prose with no matching embedded figure (`missing`); a
   figure/table embedded but never referenced by number anywhere in the prose
   (`orphaned`); a reused number (`duplicate_numbers`); a numbering-sequence gap
   (`sequence_gaps`); and a figure missing an `analysis/captions.md` entry
   (`uncaptioned_figures`). Example: `Figure 4 is embedded (results.md) but
   never mentioned by number in any draft`. Checks existence/numbering only, NOT
   whether a figure's pixels still match its caption/prose claims — for a
   high-stakes submission recommend (don't require) a `qa-auditor` dispatch with
   stage `figures`, which visually inspects each PNG against its source data.

4. **`python scripts/temporal_check.py`** — flags a future-dated or
   impossibly-fetched bibliography entry (typo protection, e.g. 2026 mistyped as
   2016 or the reverse), and an evidence card whose claim mentions a year
   postdating its own source by more than one year (possible anachronistic
   citation). Example: `EV-0042: mentions year 2024, but its source
   'kaya2019deep' was published in 2019`.

5. **`python scripts/claim_check.py`** — the only check here that questions what
   a *verified* citation is being used to say. `overclaim`: a cited sentence
   sits HIGHER on the claim-strength ladder than the evidence card drawn from
   that same source — e.g. `prose is causal ('causes') but EV-0031 is only
   associative ('associated with')`. Weaker-than-source is never flagged; only
   the upward move misrepresents. Sources with no card are skipped, not
   guessed — coverage depends on cards, which item 2 reports.
   `uncited_assertions`: an empirical sentence (statistic, or rung-4+ causal
   claim) with no citation, no own-work marker ("we", "bu çalışmada") and no
   Table/Figure pointer; own-work section files are skipped for this half.
   Ladder semantics: `.claude/skills/academic-writing/reference/claim-strength.md`.

6. **`python scripts/failure_scan.py`** — the 7-mode AI-research failure-mode
   checklist (Lu et al. 2026), re-run as the *final* pass: `/critique` ran it
   pre-review, this catches what `/revise` introduced since. Report each mode's
   STATUS, not just the count — `SKIPPED: no analysis/ artefacts` on a
   quantitative paper is itself a reproducibility finding, and `NOT_AUTOMATED`
   (M4, shortcut reliance) means no machine ever checked it. A mode already
   adjudicated in `reviews/round-N.md` is resolved; say so, don't re-raise it.
   Semantics: `.claude/skills/critique/reference/failure-modes.md`.

7. **`python scripts/tr_style_check.py`** — Turkish output only. Deterministic
   register/convention lint: mixed decimal separators, `25%` where Turkish
   writes `%25`, `v.b.`→`vb.`, conversational tokens, **term unity** (one
   concept under two names), voice mixing, and **Özet↔Abstract** equivalence
   (numbers — separators normalized first — keyword counts, length ratio).
   Where convention is genuinely contested it flags the *mixture*, never the
   choice; report it that way. Not a grammar checker — agreement, participles
   and postpositions stay with `style-auditor`. A noisy `term_unity` means the
   per-project glossary (`templates/tr-terminology.json`) needs pruning to this
   domain; that is a fix, not a dismissal.

8. **`python scripts/provenance.py --verify`** — the attestation chain, not the
   manuscript. Its three outcomes are reported differently and its two limits
   are stated by name: [`provenance.md`](provenance.md).

9. **`python scripts/dataset_db.py verify`** — empirical papers only; skip with
   `SKIPPED: no dataset register` on a review or theoretical paper and say so
   rather than omitting the line. Four findings, and they are not the same kind
   of thing: **DRIFT** (the data changed under its record — usually an ordinary
   re-export, occasionally not), **MISSING** (the file that produced the numbers
   is gone), and **INCOMPLETE** (a licence never read, no citation DOI,
   human-subject data with no ethics reference). Report DRIFT and MISSING as data
   findings and INCOMPLETE as a *methods-section* finding: each INCOMPLETE item is
   a sentence the paper cannot honestly write.

10. **`python scripts/experiment_db.py verify`** — empirical papers with model
    training. Reports a run whose `config_hash` no longer matches its
    configuration (the record was edited after it was written), a run pointing at
    a dataset outside the register, a run with no environment fingerprint, and any
    (experiment, model) group with fewer than 3 seeds. The last one is the one to
    report carefully: a single seed is not a defect in the run, it is a limit on
    what the paper may claim from it. Pair it with
    `experiment_db.py trace <number>` for any headline figure in the results
    section — a number with no matching run came from somewhere the register
    cannot see.

11. **`python scripts/leakage_check.py --splits analysis/splits.json --data <features>`**
    — empirical papers with a train/test split. Four leaks that are arithmetic:
    id overlap between train and test, the same subject/group on both sides,
    byte-identical rows under different ids, and a feature that maps one-to-one
    onto the target. Two reporting rules: a **skipped** check (a declared
    `group_column` with no `--data`) is reported as skipped, never folded into
    "clean"; and the tool's own limit goes in the report verbatim — preprocessing
    fitted outside the fold is taken from the manifest's *declaration* and is
    never detected, so a CLEAN result is a statement about four leaks, not about
    the experiment's validity.

12. **`python scripts/overlap_check.py --against <their own earlier work>`** — only
    when the author names files to compare against; there is nothing to run
    otherwise, and that is reported as `SKIPPED: no earlier work named`, never as
    "no overlap". It reports **locations, not a score** — do not convert its
    findings into a percentage, do not compare them to an institutional threshold,
    and repeat its own sentence in the report: this is not a plagiarism check and
    does not replace Turnitin/iThenticate, which compare against corpora it cannot
    see. Reused methods text is often legitimate; what the author needs is to know
    where it is, cite their earlier work, and follow the venue's text-recycling
    policy.
