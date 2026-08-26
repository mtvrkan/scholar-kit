#!/usr/bin/env python3
"""venue_fit.py — target-venue shortlist derived from the project's OWN reference list.

Where does the literature you actually cite get published? That distribution is
the most defensible venue signal a project already owns: it is measured from
your registry, needs no external ranking, and cannot be fabricated. A venue that
published six of your forty included sources is, demonstrably, a venue whose
readership works on your problem.

WHAT THIS MEASURES — and what it does not:
  It measures topical proximity between a venue and your own reference list.
  It does NOT estimate acceptance probability, does NOT rank journal quality,
  and does NOT recommend where to submit. Scope match is one input to that
  decision; fit with the paper's contribution, aims-and-scope text, turnaround
  time and your institution's index requirements are the others, and this tool
  sees none of them. The output is deliberately a COUNT you can audit, not a
  composite score that would look authoritative while hiding its weights.

It also runs the same distribution backwards, which is the half nobody looks at:
sources you cite that sit in predatory-flagged or wholly unindexed venues. That
is a defect in the reference list, surfaced here because this is the only place
the registry and the venue cache are read together.

Index metadata is never fetched: it is read from `venue_meta` already on the
registry records, or from the `venue_check.py` cache. Venues with no cached
metadata are reported as `unknown` with the command that would resolve them —
never guessed at.

Usage:
  python scripts/venue_fit.py
  python scripts/venue_fit.py --status included --top 15
  python scripts/venue_fit.py --registry sources/registry.jsonl --venues sources/venues.jsonl
Output: single JSON object. Exit codes: 0 ok (advisory only) · 1 error.
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (die, emit, normalize_issn, normalize_title, read_jsonl,
                        require_within_cwd, warn_missing_rapidfuzz)

# Statuses that represent "a source this paper stands on". `candidate` is
# excluded by default: a venue that merely turned up in a search says nothing
# about where the work belongs.
DEFAULT_STATUSES = ("included",)
FALLBACK_STATUSES = ("included", "screened")

MERGE_THRESHOLD = 93  # same bar venue_check.py uses for title identity

# Common venue-name noise. Stripped only for GROUPING; the display name is
# always a real string taken from a record, never a reconstructed one.
_PREFIXES = ("proceedings of the ", "proceedings of ", "proc of the ", "proc of ",
             "proc. of the ", "proc. of ", "proceedings ", "in proceedings of ")


def group_key(venue: str) -> str:
    """Normalized grouping key for a venue name.

    `normalize_title` already folds case, punctuation and diacritics; the
    conference-proceedings prefixes are stripped on top of it so that
    "Proceedings of the International Conference on X" and "International
    Conference on X" are one venue rather than two singletons.
    """
    key = normalize_title(venue or "")
    for p in _PREFIXES:
        if key.startswith(p):
            key = key[len(p):]
            break
    return key.strip()


def _scorer():
    try:
        from rapidfuzz import fuzz
        return lambda a, b: fuzz.token_sort_ratio(a, b)
    except ImportError:  # pragma: no cover - exercised only without rapidfuzz
        warn_missing_rapidfuzz()
        return lambda a, b: 100 if a == b else 0


def merge_variants(keys: list[str]) -> tuple[dict[str, str], list[dict]]:
    """Map each grouping key to a canonical key, folding near-identical spellings.

    Returns (mapping, merges). Every merge is REPORTED rather than applied
    silently: a wrong merge inflates one venue's count at another's expense, and
    the count is the entire output. The user has to be able to see it and say no.

    The canonical key is the LONGEST spelling, ties broken lexicographically, so
    the result does not depend on dict/input order: a full name absorbs its
    abbreviations rather than the reverse, which keeps the reported group name
    the one a reader can look up.
    """
    score = _scorer()
    canon: dict[str, str] = {}
    merges: list[dict] = []
    # Longest first: a canonical full name absorbs its abbreviated variants
    # rather than the other way round.
    for key in sorted(keys, key=lambda k: (-len(k), k)):
        for existing in canon.values():
            if existing == key:
                canon[key] = existing
                break
            if score(key, existing) >= MERGE_THRESHOLD:
                canon[key] = existing
                merges.append({"merged": key, "into": existing})
                break
        else:
            canon[key] = key
    return canon, merges


def _index_of(rec: dict) -> dict:
    """Index metadata carried on a registry record, if any."""
    vm = rec.get("venue_meta")
    return vm if isinstance(vm, dict) else {}


def build_venue_cache(venue_records: list[dict]) -> tuple[dict[str, dict], dict[str, dict]]:
    """(by normalized ISSN, by grouping key) views of the venue_check cache."""
    by_issn, by_key = {}, {}
    for rec in venue_records:
        issn = normalize_issn(rec.get("issn") or "")
        if len(issn) == 8:
            by_issn[issn] = rec
        for name in (rec.get("display_name"), rec.get("title_query")):
            key = group_key(name or "")
            if key:
                by_key.setdefault(key, rec)
    return by_issn, by_key


def _pick_index(recs: list[dict], by_issn: dict, by_key: dict, key: str) -> tuple[dict, str]:
    """Index metadata for a venue group, and where it came from.

    Registry-carried `venue_meta` wins over the cache: it was attached when the
    source was registered, alongside the ISSN that identified it.
    """
    for rec in recs:
        vm = _index_of(rec)
        if vm:
            return vm, "registry"
    for rec in recs:
        issn = normalize_issn(rec.get("issn") or _index_of(rec).get("issn") or "")
        if len(issn) == 8 and issn in by_issn:
            return by_issn[issn], "venue-cache"
    if key in by_key:
        return by_key[key], "venue-cache"
    return {}, "unknown"


def _index_summary(meta: dict) -> dict:
    return {
        "wos_index": meta.get("wos_index"),
        "quartile": meta.get("quartile"),
        "scopus": bool(meta.get("scopus")),
        "tr_dizin": bool(meta.get("tr_dizin")),
        "doaj": bool(meta.get("doaj")),
        "predatory_flag": bool(meta.get("predatory_flag")),
    }


def _is_unindexed(idx: dict) -> bool:
    return not (idx["scopus"] or idx["tr_dizin"] or idx["doaj"] or idx["quartile"]
                or idx["wos_index"] not in (None, "", "NONE", "unknown"))


def _years(recs: list[dict]) -> dict:
    years = []
    for r in recs:
        try:
            y = int(r.get("year"))
        except (TypeError, ValueError):
            continue
        if 1500 < y < 2200:
            years.append(y)
    if not years:
        return {"newest": None, "median": None, "with_year": 0}
    return {"newest": max(years), "median": int(statistics.median(years)),
            "with_year": len(years)}


def analyze(registry_path: Path, venues_path: Path, statuses: tuple[str, ...],
            top: int) -> dict:
    records = read_jsonl(registry_path)
    if not records:
        return {"status": "empty",
                "note": f"{registry_path} holds no sources — nothing to derive a "
                        f"venue distribution from",
                "shortlist": [], "concerns": []}

    wanted = set(statuses)
    selected = [r for r in records if (r.get("status") or "") in wanted]
    status_note = None
    if not selected and set(statuses) == set(DEFAULT_STATUSES):
        # No full-text decisions yet. Screened sources are a weaker but usable
        # signal — used only with the substitution stated in the output.
        selected = [r for r in records if (r.get("status") or "") in set(FALLBACK_STATUSES)]
        if selected:
            wanted = set(FALLBACK_STATUSES)
            status_note = ("no sources are 'included' yet — the distribution below "
                           "is over 'screened' sources and will shift once full-text "
                           "decisions are made")

    with_venue = [r for r in selected if (r.get("venue") or "").strip()]
    groups: dict[str, list[dict]] = {}
    for rec in with_venue:
        groups.setdefault(group_key(rec["venue"]), []).append(rec)

    canon, merges = merge_variants(list(groups))
    merged: dict[str, list[dict]] = {}
    for key, recs in groups.items():
        merged.setdefault(canon.get(key, key), []).extend(recs)

    by_issn, by_key = build_venue_cache(read_jsonl(venues_path))

    shortlist, concerns, unresolved = [], [], []
    total = len(with_venue)
    for key, recs in merged.items():
        meta, provenance = _pick_index(recs, by_issn, by_key, key)
        idx = _index_summary(meta)
        # Display name: the most frequent literal spelling in the registry, then
        # the shortest, then alphabetically first (max() returns the first
        # maximal element of an alphabetically sorted list). Never synthesized —
        # every venue string in the output came verbatim from a record.
        names = [r["venue"].strip() for r in recs]
        display = max(sorted(set(names)), key=lambda n: (names.count(n), -len(n)))
        entry = {
            "venue": display,
            "own_refs": len(recs),
            "share": round(len(recs) / total, 4) if total else 0.0,
            "years": _years(recs),
            "index": idx,
            "index_provenance": provenance,
            "source_ids": sorted(r.get("id") for r in recs if r.get("id"))[:10],
        }
        if provenance == "unknown":
            entry["resolve_with"] = f'python scripts/venue_check.py --title "{display}"'
            unresolved.append(display)
        shortlist.append(entry)

        if idx["predatory_flag"]:
            concerns.append({"venue": display, "own_refs": len(recs),
                             "concern": "predatory_flag",
                             "detail": "venue_check flagged this venue; sources cited "
                                       "from it should be re-examined before submission"})
        elif provenance != "unknown" and _is_unindexed(idx):
            concerns.append({"venue": display, "own_refs": len(recs),
                             "concern": "unindexed",
                             "detail": "present in no index this kit can see — not proof "
                                       "of a problem, but worth a deliberate decision"})

    shortlist.sort(key=lambda e: (-e["own_refs"], -(e["years"]["newest"] or 0), e["venue"]))
    concerns.sort(key=lambda c: (-c["own_refs"], c["venue"]))

    out = {
        "status": "ok",
        "measures": ("topical proximity between a venue and this project's own "
                     "reference list — NOT acceptance probability, journal quality, "
                     "or a submission recommendation"),
        "statuses_counted": sorted(wanted),
        "sources_total": len(records),
        "sources_counted": len(selected),
        "sources_with_venue": total,
        "sources_without_venue": len(selected) - total,
        "distinct_venues": len(merged),
        "shortlist": shortlist[:top],
        "shortlist_truncated": max(0, len(shortlist) - top),
        "merged_variants": merges,
        "concerns": concerns,
        "unresolved_venues": len(unresolved),
    }
    if status_note:
        out["status_note"] = status_note
    if unresolved:
        out["note"] = (f"{len(unresolved)} venue(s) have no cached index metadata — "
                       f"run the `resolve_with` command on the entries that matter")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", default="sources/registry.jsonl")
    ap.add_argument("--venues", default="sources/venues.jsonl")
    ap.add_argument("--status", action="append",
                    help="registry status to count (repeatable; default: included)")
    ap.add_argument("--top", type=int, default=20, help="shortlist length (default 20)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.registry, "--registry")
    require_within_cwd(args.venues, "--venues")
    if args.top < 1:
        die("--top must be at least 1")
    statuses = tuple(args.status) if args.status else DEFAULT_STATUSES
    emit(analyze(Path(args.registry), Path(args.venues), statuses, args.top), True)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a data file — {e}")


