#!/usr/bin/env python3
"""evidence_funnel.py — the cards -> sources -> cited -> bibliography funnel.

Answers the recurring "I extracted 100+ evidence cards but the paper only has 19
references — is something broken?" question by making the (entirely legitimate)
narrowing explicit and, more importantly, by flagging the ONE case that IS a
problem: an evidence card whose source is never cited anywhere in the drafts
("extracted but never used").

The funnel has four legitimately-narrowing stages:
  1. evidence cards            (many cards per source: finding/method/stat/quote…)
  2. distinct sources          (cards grouped by their source key)
  3. included sources          (registry status == "included"; excluded/duplicate drop out)
  4. cited in-text             (sources actually referenced with [@key] in a draft)
  5. bibliography entries      (references.bib — one per cited source)

Only stages 4->5 must match; a gap there is a real defect (cite_audit.py owns
that gate). This script REPORTS the whole chain and lists orphan cards; it does
not block. cite_audit.py remains the blocking gate for missing/placeholder
citations.

Stage 2->3 is where the funnel used to lie, and the lie was paper-type shaped.
"Stages 1->4 narrow by design" is true of a narrative review or an IMRaD paper:
you read a hundred sources and quote twelve, and the eighty-eight that leave no
card were context, not data. In a SYSTEMATIC review it is exactly backwards.
There, "included" means the study passed the eligibility criteria the Methods
section prints, and every included study owes the synthesis its data. An
included study carrying no evidence card is one that survived screening and then
vanished — from the tables, the strata, the pooled estimate and the risk-of-bias
summary — while still being counted in the PRISMA box.

Found by running this tool on a real review: it printed
`98 cards -> 12 distinct sources -> 115 included -> 28 cited in-text` with
`orphan_sources: []` and no warning. 103 of the 115 included studies had no card
at all, three of them landmark trials that had been included from full text in an
earlier phase and never re-extracted after the search was widened. The funnel
reported the narrowing as legitimate because for its default paper type it is.

The same question runs in the other direction, and that one caught a defect too.
An extraction record whose study is in NO register entry is a study that was
retrieved, read and extracted while the PRISMA flow counted it nowhere — not as
included, not as excluded at full text. It happened: a Sri Lankan pilot was read,
judged eligible, extracted, and deliberately kept out of the pooled estimate for a
recorded reason, but its registration never ran. The eligibility reading said 97
includes, the registration log held 96, and the flow printed "included: 99" for
days while the honest number was 100. Nothing compared the two directories, so
nothing said so. `orphan_extractions` now does.

One refinement keeps this from becoming a lint nobody reads. A review that pools
does not put its 2x2 cells in prose cards; it keeps a structured extraction table,
one record per study, and the cards hold the qualitative material. Those studies
are extracted, just not carded — a real gap in the evidence chain (claim_check
cannot verify a number that binds to no card) but not a silent loss. Pass
`--extraction <dir>` and the uncarded includes split into `extracted_elsewhere`
and `no_record_anywhere`; the second list is the one that means a study vanished.
Without the flag every uncarded include is reported as unknown-status, because
assuming an extraction store that was never named would be the same silent
turning-off this file exists to prevent.

So `uncarded_included` is now always computed and reported, and PROJECT.md's
`Type` decides how it is FRAMED: a coverage defect for the synthesis types, a
neutral observation otherwise. The list is identical either way — the reader is
never shown a different set of facts, only a different reading of them. When the
type cannot be read, it is reported as unknown and framed as a defect, because a
check that silently turns itself off is the failure mode this whole file is about.

Usage:
  python scripts/evidence_funnel.py [--cards evidence/cards.jsonl]
      [--registry sources/registry.jsonl] [--drafts drafts/] [--bib bib/references.bib]
Exit codes: 0 always (report-only).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (die, emit, parse_bibtex, read_jsonl, read_paper_type,
                        require_within_cwd)
from cite_audit import extract_citations  # reuse the exact in-text [@key] extractor


def _resolve_bib_key(source: str, id_to_key: dict[str, str]) -> str:
    """A card's `source` is a bib_key, or (before one is assigned) an SRC id.
    Resolve an SRC id to its registry bib_key; a bib_key resolves to itself."""
    return id_to_key.get(source, source)


def build_funnel(cards_path: Path, registry_path: Path, drafts_dir: Path,
                 bib_path: Path, project_path: Path | None = None,
                 extraction_dir: Path | None = None) -> dict:
    cards = read_jsonl(cards_path) if cards_path.exists() else []
    registry = read_jsonl(registry_path) if registry_path.exists() else []

    # `scope: "background"` marks a source that is cited for context — a
    # reporting guideline, a statistical method, an epidemiological figure —
    # rather than screened as a candidate study. prisma_flow.py has honoured
    # this since background citations started inflating the identified box; this
    # file did not, and the disagreement only became visible once the coverage
    # check below started reporting "included studies that contributed nothing"
    # and named PRISMA 2020, QUADAS-2 and the Reitsma bivariate paper among them.
    # Two kit tools disagreeing about what "included" means is worse than either
    # answer: whichever a reader quotes, the other one contradicts it.
    background = [r for r in registry if r.get("scope") == "background"]
    registry = [r for r in registry if r.get("scope") != "background"]

    # registry SRC-id -> bib_key (only when a bib_key exists)
    id_to_key = {r["id"]: r["bib_key"] for r in registry
                 if r.get("id") and r.get("bib_key")}
    status_of = {}  # bib_key -> registry status (for included-count)
    src_status = {}  # any source identifier (id AND bib_key) -> status
    by_status = {}
    for r in registry:
        st = r.get("status", "?")
        by_status[st] = by_status.get(st, 0) + 1
        if r.get("bib_key"):
            status_of[r["bib_key"]] = st
            src_status[r["bib_key"]] = st
        if r.get("id"):
            src_status[r["id"]] = st

    by_type = {}
    card_sources = set()
    for c in cards:
        by_type[c.get("type", "?")] = by_type.get(c.get("type", "?"), 0) + 1
        if c.get("source"):
            card_sources.add(c["source"])

    included = sorted(k for k, s in status_of.items() if s == "included")
    registry_by_key = {r["bib_key"]: r for r in registry if r.get("bib_key")}

    # cited in-text
    cited = set()
    files = []
    if drafts_dir.exists():
        for f in sorted(drafts_dir.glob("**/*.md")):
            if f.name == "STATUS.md":
                continue
            files.append(f.as_posix())
            cited |= extract_citations(f.read_text(encoding="utf-8", errors="replace"))

    bib_keys = ({e["key"] for e in parse_bibtex(bib_path.read_text(encoding="utf-8"))}
                if bib_path.exists() else set())

    # Uncited cards split by whether the gap is ACTIONABLE or EXPECTED:
    #   * own-result cards are presented in figures/tables, never [@key]-cited —
    #     their absence from `cited` is by design, not waste.
    #   * cards from a deliberately excluded/duplicate source (e.g. a retracted
    #     paper discussed by name, not cited) are also expected to be uncited.
    #   * everything else — a card from an INCLUDED source that still never made
    #     it into the prose — is the real signal: extraction that never reached
    #     the paper.
    orphan_cards, expected_uncited = [], []
    for c in cards:
        src = c.get("source")
        if not src:
            continue
        if _resolve_bib_key(src, id_to_key) in cited:
            continue
        rec = {"id": c.get("id"), "source": src, "type": c.get("type")}
        # Own work (own-result cards, or any card sourced to the own-analysis /
        # own-data anchor) is presented in the paper's own Methods/Results, never
        # [@key]-cited. Excluded/duplicate sources are deliberately uncited too.
        is_own = c.get("type") == "own-result" or src.lower().startswith("own")
        if is_own or src_status.get(src) in ("excluded", "duplicate"):
            expected_uncited.append(rec)
        else:
            orphan_cards.append(rec)

    orphan_sources = sorted({o["source"] for o in orphan_cards})

    # Stage 2->3, the direction this funnel used to skip: which INCLUDED sources
    # produced no evidence card at all? A card's `source` is a bib_key or the
    # SRC id it was written under before one existed, so both spellings count as
    # carried — matching on one alone would report a study as uncarded purely
    # because its cards predate its bib_key.
    carded = set(card_sources) | {_resolve_bib_key(s_, id_to_key) for s_ in card_sources}
    key_to_id = {v: k for k, v in id_to_key.items()}
    uncarded_included = sorted(
        k for k in included if k not in carded and key_to_id.get(k, k) not in carded
    )

    # Studies whose data lives in a structured extraction store rather than in
    # cards. Matched on every identifier a project might name the file by — its
    # stem, or an id/doi field inside it — because the kit does not own this
    # directory's naming and must not require one.
    extracted_ids: set[str] = set()
    if extraction_dir and extraction_dir.is_dir():
        for f in sorted(extraction_dir.glob("*.json")):
            extracted_ids.add(f.stem.lower())
            try:
                rec = json.loads(f.read_text(encoding="utf-8", errors="replace"))
            except (ValueError, OSError):
                continue
            if isinstance(rec, dict):
                for field in ("id", "study_id", "bib_key", "pmid", "db_id", "doi"):
                    val = rec.get(field)
                    if isinstance(val, str) and val.strip():
                        extracted_ids.add(val.strip().lower().replace("pmid:", ""))

    def _has_extraction(bib_key: str) -> bool:
        r = registry_by_key.get(bib_key, {})
        cands = {bib_key, r.get("id"), r.get("doi"),
                 (r.get("db_id") or "").replace("PMID:", "")}
        return any(c and str(c).lower() in extracted_ids for c in cands)

    # Cikarim var, kayit yok: akisin hicbir kutusunda sayilmayan calisma.
    orphan_extractions = []
    if extraction_dir and extraction_dir.is_dir():
        known = set()
        for r in registry + background:
            for field in ("bib_key", "id", "doi", "db_id"):
                val = r.get(field)
                if isinstance(val, str) and val.strip():
                    known.add(val.strip().lower().replace("pmid:", ""))
        for f in sorted(extraction_dir.glob("*.json")):
            ids = {f.stem.lower()}
            try:
                rec = json.loads(f.read_text(encoding="utf-8", errors="replace"))
            except (ValueError, OSError):
                rec = {}
            if isinstance(rec, dict):
                for field in ("id", "study_id", "bib_key", "pmid", "db_id", "doi"):
                    val = rec.get(field)
                    if isinstance(val, str) and val.strip():
                        ids.add(val.strip().lower().replace("pmid:", ""))
            if not (ids & known):
                orphan_extractions.append(f.name)

    extracted_elsewhere, no_record_anywhere = [], []
    for k in uncarded_included:
        (extracted_elsewhere if _has_extraction(k) else no_record_anywhere).append(k)

    # The axis that actually decides whether a study reached the synthesis of a
    # review that pools. Cards and extraction records answer different
    # questions, and the first version of this check conflated them: it asked
    # "no card AND no extraction record" and so reported nothing for the very
    # studies that prompted it. Three landmark trials had been read in full and
    # carded during a purposive phase, then never re-extracted once the search
    # was widened — richly carded, absent from every stratum, pooled estimate
    # and QUADAS-2 table. Carded-but-unextracted is not a lesser version of
    # uncarded; for a pooling review it is the worse one, because the prose
    # discusses the study by name and the numbers never include it.
    unextracted_included = ([k for k in included if not _has_extraction(k)]
                            if extraction_dir else [])

    ptype = read_paper_type(project_path) if project_path else ""
    # Types whose Methods section promises that every included study contributed.
    # meta-analysis is not a separate PROJECT.md type — it ships as
    # systematic-review — so the pair below is the whole synthesis family.
    SYNTHESIS_TYPES = ("systematic-review", "scoping-review")
    coverage_is_required = (ptype in SYNTHESIS_TYPES) or not ptype

    funnel = (f"{len(cards)} cards -> {len(card_sources)} distinct sources -> "
              f"{len(included)} included -> {len(cited)} cited in-text -> "
              f"{len(bib_keys)} bib entries")

    notes = []
    if len(cards) and len(card_sources):
        notes.append(f"{len(cards)} cards over {len(card_sources)} sources "
                     f"= {len(cards)/len(card_sources):.1f} cards/source (normal: one source "
                     f"yields many finding/method/statistic/quote cards).")
    if orphan_cards:
        notes.append(f"{len(orphan_cards)} card(s) from {len(orphan_sources)} INCLUDED source(s) are "
                     f"extracted but never cited in any draft — review whether they belong in "
                     f"the paper or were superseded.")
    if orphan_extractions:
        notes.append(
            f"REGISTER GAP: {len(orphan_extractions)} extraction record(s) name a study "
            f"the register does not contain: {', '.join(orphan_extractions[:8])}"
            + (" …" if len(orphan_extractions) > 8 else "")
            + ". A study that was retrieved, read and extracted but never registered is "
            "counted in no PRISMA box at all — neither included nor excluded at full "
            "text — so the flow understates the review by exactly these studies. Either "
            "register them through the register's own writer, or say why the extraction "
            "exists for a study the review does not claim to have assessed.")
    if uncarded_included and coverage_is_required:
        why = (f"paper type is '{ptype}'" if ptype
               else "PROJECT.md's Type could not be read, so coverage is assumed to matter")
        if extraction_dir:
            if unextracted_included:
                notes.append(
                    f"COVERAGE GAP: {len(unextracted_included)} of {len(included)} included "
                    f"source(s) have no record in {extraction_dir.as_posix()} — they count in "
                    f"the PRISMA 'included' box and contribute to no table, stratum, pooled "
                    f"estimate or risk-of-bias summary ({why}). A carded study is not exempt: "
                    f"cards carry prose, and a study discussed by name whose numbers are in no "
                    f"pool is the harder version of this gap to notice, not the milder one. "
                    f"Studies: {', '.join(unextracted_included[:12])}"
                    + (" …" if len(unextracted_included) > 12 else ""))
            if no_record_anywhere:
                notes.append(
                    f"COVERAGE GAP: {len(no_record_anywhere)} of {len(included)} included "
                    f"source(s) have neither an evidence card nor a record in "
                    f"{extraction_dir.as_posix()} — they passed eligibility and then "
                    f"contributed nothing to any table, stratum, pooled estimate or "
                    f"risk-of-bias summary, while still counting in the PRISMA 'included' "
                    f"box ({why}). Each is either un-extracted work or a study that should "
                    f"not be counted as included, and neither shows up anywhere else.")
            if extracted_elsewhere:
                notes.append(
                    f"{len(extracted_elsewhere)} included source(s) carry no evidence card "
                    f"but do have an extraction record — normal for a review that pools, "
                    f"since 2x2 cells belong in a structured table rather than in prose. "
                    f"Worth knowing anyway: a number that binds to no card cannot be "
                    f"checked by claim_check.py, so those studies sit outside the evidence "
                    f"chain the citation gate enforces.")
        else:
            notes.append(
                f"COVERAGE GAP: {len(uncarded_included)} of {len(included)} included source(s) "
                f"have no evidence card at all — they passed eligibility and then contributed "
                f"nothing to the synthesis, while still counting in the PRISMA 'included' box "
                f"({why}). If this review keeps its extraction in a structured table rather "
                f"than in cards, pass --extraction <dir> so this splits into studies that are "
                f"extracted-elsewhere and studies with no record anywhere; without it the two "
                f"cannot be told apart and are reported together.")
    elif uncarded_included:
        notes.append(
            f"{len(uncarded_included)} of {len(included)} included source(s) carry no evidence "
            f"card. For paper type '{ptype}' that is normal — an included source may be cited "
            f"as context without being extracted — so this is reported, not flagged.")
    if expected_uncited:
        notes.append(f"{len(expected_uncited)} uncited card(s) are expected "
                     f"(own-result cards shown in figures/tables, or cards from an "
                     f"excluded/retracted source) — not a problem.")
    # cited-but-no-card and cited-but-no-bib are cite_audit's territory; surface a pointer only.
    cited_no_bib = sorted(cited - bib_keys)
    if cited_no_bib:
        notes.append(f"{len(cited_no_bib)} cited key(s) have no bib entry — run cite_audit.py "
                     f"(this IS a blocking defect).")

    return {
        "funnel": funnel,
        "cards": {"total": len(cards), "distinct_sources": len(card_sources), "by_type": by_type},
        "registry": {"total": len(registry), "by_status": by_status,
                     "included": len(included),
                     "background_excluded": len(background)},
        "cited_in_text": len(cited),
        "bib_entries": len(bib_keys),
        "orphan_cards": orphan_cards,
        "orphan_sources": orphan_sources,
        "paper_type": ptype,
        "coverage_required": coverage_is_required,
        "uncarded_included": uncarded_included,
        "extraction_dir": extraction_dir.as_posix() if extraction_dir else None,
        "extracted_elsewhere": extracted_elsewhere if extraction_dir else [],
        "no_record_anywhere": no_record_anywhere if extraction_dir else [],
        "unextracted_included": unextracted_included,
        "orphan_extractions": orphan_extractions,
        "expected_uncited": expected_uncited,
        "files_scanned": files,
        "notes": notes,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cards", default="evidence/cards.jsonl")
    ap.add_argument("--registry", default="sources/registry.jsonl")
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--bib", default="bib/references.bib")
    ap.add_argument("--project", default="PROJECT.md")
    ap.add_argument("--extraction", default=None,
                    help="directory of per-study extraction JSON, when the review "
                         "keeps 2x2 data in a table rather than in cards")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    for label, val in (("--cards", args.cards), ("--registry", args.registry),
                       ("--drafts", args.drafts), ("--bib", args.bib),
                       ("--project", args.project)):
        require_within_cwd(val, label)
    if Path(args.drafts).exists() and not Path(args.drafts).is_dir():
        die(f"--drafts {args.drafts} is not a directory")
    if args.extraction:
        require_within_cwd(args.extraction, "--extraction")
    emit(build_funnel(Path(args.cards), Path(args.registry),
                      Path(args.drafts), Path(args.bib), Path(args.project),
                      Path(args.extraction) if args.extraction else None), True)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read input files — {e}")
    except UnicodeDecodeError as e:
        die(f"an input file is not valid UTF-8 — {e}")
