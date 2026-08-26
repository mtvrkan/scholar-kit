#!/usr/bin/env python3
"""citation_triangulate.py — cross-check a bib entry's metadata against a SECOND
independent index (OpenAlex), corroborating doi2bib.py --verify's primary check
against doi.org/Crossref.

Why a second index: doi2bib.py --verify already field-diffs every DOI'd entry
against the authoritative CSL-JSON record from doi.org (Crossref/DataCite/etc,
whichever registration agency owns that DOI prefix) — that remains the primary,
blocking gate (Invariant 2). This script adds a SECOND, independent index
(OpenAlex, a free aggregator that ingests Crossref, PubMed, and other sources
with its own periodic re-harvesting) as a corroborating signal: if the two
indexes disagree, that is a genuine "check this by hand" flag even when the
primary Crossref-based check reports PASS, since OpenAlex occasionally has
stale or merged/duplicate records the registration authority itself does not.

This is deliberately advisory, not a second gate: OpenAlex is a downstream
aggregator, not a registration authority, so its disagreement never overrides
a Crossref PASS — it only adds confidence when the two agree, and flags a
"worth a human glance" case when they don't. WARN-only by default (`--strict`
opts into blocking).

(Semantic Scholar was evaluated as a third index and rejected for now: its
unauthenticated Graph API returns HTTP 429 immediately on a cold request with
no prior traffic from this environment, i.e. its free rate limit is already
exhausted at the shared-IP level — it cannot be relied on without an API key
this kit does not have. If a user provides one, a third `--s2-api-key`-gated
check could be added later following this same pattern.)

Network endpoint (whitelisted, read-only): api.openalex.org

Usage:
  python scripts/citation_triangulate.py [--bib bib/references.bib] [--entry key] [--strict] [--json]
Exit codes: 0 ok (or warnings, default) · 1 error · 2 warnings found AND --strict.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (clean_doi, die, emit, http_get_with_retry, normalize_title,
                        parse_bibtex, require_within_cwd, warn_missing_rapidfuzz)

try:
    import requests
except ImportError:
    requests = None

from doi2bib import _local_family_names  # reuse, not reimplement

UA = {"User-Agent": "scholar-kit/1.0 (mailto:scholar-kit@example.org)"}
TIMEOUT = 20
RETRIES = 2


def fetch_openalex_work(doi: str) -> dict:
    """OpenAlex's canonical per-work lookup: /works/doi:<doi>. Returns {} on a
    clean 404 (OpenAlex has no record — informational, not an error)."""
    url = f"https://api.openalex.org/works/doi:{clean_doi(doi)}"
    r = http_get_with_retry(url, retries=RETRIES, backoff=1.5, timeout=TIMEOUT, headers=UA)
    if r.status_code == 404:
        return {}
    r.raise_for_status()
    return r.json()


def _openalex_title(work: dict) -> str:
    return work.get("title") or work.get("display_name") or ""


def _openalex_year(work: dict):
    return work.get("publication_year")


def _openalex_first_author_family(work: dict) -> str:
    authorships = work.get("authorships") or []
    if not authorships:
        return ""
    name = ((authorships[0].get("author") or {}).get("display_name") or "").strip()
    # OpenAlex gives a full display name ("Tianqi Chen"), not family/given split
    # fields like Crossref's CSL-JSON — the family name is conventionally the
    # last whitespace-separated token.
    return name.split()[-1].lower() if name else ""


def _name_tokens(s: str) -> set[str]:
    """Lowercased, diacritic-free, dash-split name tokens.

    Three normalisations, each for a family of real names in this corpus:
      * NFKD + combining-mark strip — a bib file holding "Ozcelik" and OpenAlex
        holding "Özçelik" are the same person.
      * every Unicode dash mapped to "-" — OpenAlex serves U+2010 in
        "Baget‐Bernaldiz" where the bib file has an ASCII hyphen.
      * split on dashes and spaces — a compound or particled surname is indexed
        differently by everyone: local "van der Heijden" against OpenAlex
        "Heijden", local "Abreu-González" against "González", "dos Reis"
        against "Reis".
    """
    # "ı" is a letter in its own right, not a decomposable "i" — NFKD leaves it
    # alone, so a Turkish surname would keep a character the ASCII side cannot
    # match. Same for the soft "ğ" in some sources' pre-composed forms.
    s = s.lower().replace("ı", "i").replace("ğ", "g")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Split on anything that is not a letter: dashes of every Unicode flavour,
    # spaces, and the comma a BibTeX "Family, Given" field leaves attached.
    return {tok for tok in re.split(r"[^a-z]+", s) if len(tok) > 1}


def _first_author_agrees(work: dict, local_author_field: str) -> bool:
    """Do OpenAlex and the local entry name the same first author?

    Compares TOKEN SETS in both directions rather than one canonical family
    string. The last-whitespace-token heuristic that picks the OpenAlex family
    name fails outright on a family-name-first display ("Lu Li" for the author
    the bib file records as "Lu, Li"), so every token of the display name is
    offered, not just the last.

    Deliberately looser than doi2bib._local_family_names, and that helper is
    NOT changed to match: there the same comparison is the compensating check
    that separates a wrong-DOI attachment from a safe metadata correction, and
    loosening it would let a fabricated citation through as a "FIX". Here the
    check is a WARN-only second-index cross-check sitting behind an
    authoritative Crossref verification, so the cost of a missed nudge is small
    and the cost of noise — 12 warnings in 121 entries, none of them a real
    mismatch — is that the gate stops being read.
    """
    oa_name = ((work.get("authorships") or [{}])[0].get("author") or {}).get(
        "display_name") or ""
    if not oa_name:
        return True
    oa_tokens = _name_tokens(oa_name)
    local_tokens: set[str] = set()
    for fam in _local_family_names(local_author_field):
        local_tokens |= _name_tokens(fam)
    return bool(oa_tokens & local_tokens)


def _titles_agree(a: str, b: str) -> tuple[bool, float]:
    """OpenAlex frequently stores ONLY the base title for a colon-subtitled
    paper (e.g. "XGBoost", dropping ": A Scalable Tree Boosting System") with
    no subtitle field anywhere in its record to reconstruct from — unlike
    Crossref's CSL-JSON, there is nothing to concatenate here. A pure
    token_sort_ratio against the local (full) title then scores ~30 for a
    perfectly correct entry, which would make this check cry wolf on well-known,
    unproblematic papers. Accept either a high token_sort_ratio (near-identical
    full titles) OR a near-100 partial_ratio (one title is a clean prefix/
    substring of the other — the truncation signature) as agreement; a
    genuinely wrong paper scores low on both (empirically ~30-46 partial_ratio
    for an unrelated title, confirmed against a real OpenAlex XGBoost lookup)."""
    na, nb = normalize_title(a), normalize_title(b)
    try:
        from rapidfuzz import fuzz
        sort_sim = fuzz.token_sort_ratio(na, nb)
        partial_sim = fuzz.partial_ratio(na, nb)
    except ImportError:  # pragma: no cover
        warn_missing_rapidfuzz()
        exact = na == nb
        return exact, 100.0 if exact else 0.0
    agree = sort_sim >= 90 or partial_sim >= 95
    return agree, sort_sim


def triangulate_entry(entry: dict) -> dict:
    key = entry["key"]
    doi = (entry["fields"].get("doi") or "").strip()
    if not doi:
        return {"key": key, "status": "SKIPPED", "reason": "no DOI field"}
    try:
        work = fetch_openalex_work(doi)
    except requests.RequestException as e:
        return {"key": key, "status": "NETWORK_ERROR", "reason": str(e)}
    if not work:
        return {"key": key, "status": "NOT_IN_OPENALEX",
                "reason": "OpenAlex has no record for this DOI — informational, not an error"}

    disagreements = []
    oa_title = _openalex_title(work)
    if oa_title:
        agree, sim = _titles_agree(oa_title, entry["fields"].get("title", ""))
        if not agree:
            disagreements.append(f"title similarity only {sim:.0f} vs OpenAlex '{oa_title[:80]}'")

    oa_year = _openalex_year(work)
    local_year = None
    import re
    m = re.search(r"\d{4}", entry["fields"].get("year", ""))
    if m:
        local_year = int(m.group(0))
    if oa_year and local_year and abs(oa_year - local_year) > 1:
        disagreements.append(f"year {local_year} vs OpenAlex {oa_year}")

    oa_fam = _openalex_first_author_family(work)
    if oa_fam and not _first_author_agrees(work, entry["fields"].get("author", "")):
        disagreements.append(f"first author family vs OpenAlex '{oa_fam}' not found locally")

    if disagreements:
        return {"key": key, "status": "DISAGREE", "openalex_id": work.get("id"),
                "disagreements": disagreements}
    return {"key": key, "status": "AGREE", "openalex_id": work.get("id")}


def main():
    if requests is None:
        die("requests not installed — pip install requests")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bib", default="bib/references.bib")
    ap.add_argument("--entry")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any DISAGREE found (opt-in blocking; default is WARN-only)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.bib, "--bib")
    p = Path(args.bib)
    if not p.exists():
        die(f"{args.bib} does not exist")
    entries = parse_bibtex(p.read_text(encoding="utf-8"))
    if args.entry:
        entries = [e for e in entries if e["key"] == args.entry]
        if not entries:
            die(f"entry '{args.entry}' not found in {args.bib}")

    report = [triangulate_entry(e) for e in entries]
    disagree = [r for r in report if r["status"] == "DISAGREE"]
    summary = {
        "checked": len(report),
        "agree": sum(1 for r in report if r["status"] == "AGREE"),
        "disagree": len(disagree),
        "not_in_openalex": sum(1 for r in report if r["status"] == "NOT_IN_OPENALEX"),
        "network_error": sum(1 for r in report if r["status"] == "NETWORK_ERROR"),
        "skipped": sum(1 for r in report if r["status"] == "SKIPPED"),
        "entries": report,
    }
    emit(summary, True)
    sys.exit(2 if (args.strict and disagree) else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read the bib file — {e}")
    except UnicodeDecodeError as e:
        die(f"bib file is not valid UTF-8 — {e}")
