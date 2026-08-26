#!/usr/bin/env python3
"""venue_check.py — journal/venue index status: WoS class, Scopus, TR Dizin, DOAJ, quartile, SJR.

Layered lookup (cheapest first):
  1. Local datasets in data/ (refreshed by INSTALL.sh --update-data):
       data/scimago.csv       SCImago SJR list (semicolon CSV; quartile + SJR + ISSN)
       data/scopus.csv        Scopus source list (normalized CSV: title,issn,eissn,active)
       data/doaj.csv          DOAJ journal dump (title,issn,eissn)
       data/trdizin.csv       optional manual TR Dizin list (title,issn)
       data/wos.csv           optional manual WoS MJL export (title,issn,index) — SCIE|SSCI|AHCI|ESCI
  2. OpenAlex API cross-check (free): ISSN → venue metadata.
  3. Anything still unknown is reported "unknown" — the agent may then WebFetch
     mjl.clarivate.com and record the answer via --set-wos.

Usage:
  python scripts/venue_check.py --issn 0888-3270 [--cache sources/venues.jsonl]
  python scripts/venue_check.py --title "Mechanical Systems and Signal Processing"
  python scripts/venue_check.py --issn 0888-3270 --set-wos SCIE   # record agent-found MJL result
Output: single JSON venue_meta object; cached into sources/venues.jsonl (30-day TTL).
Exit codes: 0 ok · 1 error.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import sys
from pathlib import Path

# Optional dependency; guarded so a missing `requests` package surfaces as a
# clean die() message via main() instead of a raw ModuleNotFoundError before
# argparse even runs.
try:
    import requests
except ImportError:
    requests = None

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (die, emit, file_lock, normalize_issn, normalize_title,
                        read_jsonl, require_within_cwd, warn_missing_rapidfuzz, write_jsonl)

DATA_DIR = Path(__file__).parent.parent / "data"
UA = {"User-Agent": "scholar-kit/1.0 (mailto:scholar-kit@example.org)"}
TIMEOUT = 20
CACHE_TTL_DAYS = 30


def _read_csv(path: Path, delimiter=None) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    if not lines:
        return []  # empty/placeholder file — degrade to "no local data" rather than crash
    if delimiter is None:
        delimiter = ";" if lines[0].count(";") > lines[0].count(",") else ","
    return list(csv.DictReader(lines, delimiter=delimiter))


def _row_issns(row: dict) -> set[str]:
    issns = set()
    for k, v in row.items():
        if k and "issn" in k.lower() and v:
            for part in str(v).replace(";", ",").split(","):
                n = normalize_issn(part)
                if len(n) == 8:
                    issns.add(n)
    return issns


def _row_title(row: dict) -> str:
    for k in row:
        if k and k.lower().strip() in ("title", "source title", "journal", "sourcetitle", "journal title"):
            return row[k] or ""
    return ""


def _match(rows: list[dict], issn: str, title: str) -> dict | None:
    if issn:
        for row in rows:
            if issn in _row_issns(row):
                return row
    if title:
        want = normalize_title(title)
        try:
            from rapidfuzz import fuzz
            best, best_score = None, 0
            for row in rows:
                s = fuzz.token_sort_ratio(want, normalize_title(_row_title(row)))
                if s > best_score:
                    best, best_score = row, s
            if best_score >= 93:
                return best
        except ImportError:  # pragma: no cover
            warn_missing_rapidfuzz()
            for row in rows:
                if normalize_title(_row_title(row)) == want:
                    return row
    return None


def lookup_local(issn: str, title: str) -> dict:
    meta = {}
    sj = _match(_read_csv(DATA_DIR / "scimago.csv"), issn, title)
    if sj:
        q = next((v for k, v in sj.items() if k and k.lower().strip() in ("sjr best quartile", "sjr quartile", "quartile")), None)
        sjr = next((v for k, v in sj.items() if k and k.lower().strip() == "sjr"), None)
        meta["quartile"] = (q or "").strip() or None
        if sjr:
            meta["sjr"] = str(sjr).strip()
        meta["scimago"] = True
    if _match(_read_csv(DATA_DIR / "scopus.csv"), issn, title):
        meta["scopus"] = True
    if _match(_read_csv(DATA_DIR / "doaj.csv"), issn, title):
        meta["doaj"] = True
    if _match(_read_csv(DATA_DIR / "trdizin.csv"), issn, title):
        meta["tr_dizin"] = True
    wos = _match(_read_csv(DATA_DIR / "wos.csv"), issn, title)
    if wos:
        idx = next((v for k, v in wos.items() if k and "index" in k.lower()), "")
        meta["wos_index"] = (idx or "").strip().upper() or None
    return meta


def _best_title_match(results: list[dict], title: str) -> dict | None:
    """OpenAlex full-text `search` ranks by relevance, not title identity, so a
    short/single-token query like "Bioengineering" can rank a larger, differently
    -named journal ("Biotechnology and Bioengineering") first. Blindly taking
    results[0] then attaches the WRONG venue's metadata (quartile, ISSN, WoS/
    Scopus index status) to the queried journal. Re-rank candidates by actual
    title similarity and reject anything that is not a close match."""
    if not results:
        return None
    want = normalize_title(title)
    try:
        from rapidfuzz import fuzz
        score = lambda a, b: fuzz.token_sort_ratio(a, b)
    except ImportError:  # pragma: no cover
        warn_missing_rapidfuzz()
        score = lambda a, b: 100 if a == b else 0
    best, best_score = None, -1.0
    for r in results:
        s = score(want, normalize_title(r.get("display_name") or ""))
        if s > best_score:
            best, best_score = r, s
    return best if best_score >= 90 else None


def lookup_openalex(issn: str, title: str) -> dict:
    try:
        if issn:
            n = normalize_issn(issn)
            url = f"https://api.openalex.org/sources/issn:{n[:4]}-{n[4:]}"
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
        elif title:
            # per-page: 5 (not 1) so _best_title_match can re-rank by title
            # identity instead of trusting OpenAlex's relevance-ranked top hit.
            r = requests.get("https://api.openalex.org/sources",
                             params={"search": title, "per-page": 5}, headers=UA, timeout=TIMEOUT)
        else:
            return {}
        if r.status_code == 404:
            return {}
        r.raise_for_status()
        data = r.json()
        if "results" in data:
            match = _best_title_match(data.get("results") or [], title)
            if not match:
                return {}
            data = match
        return {
            "openalex_id": data.get("id"),
            "display_name": data.get("display_name"),
            "issn_all": data.get("issn") or [],
            "doaj": data.get("is_in_doaj", None),
            "works_count": data.get("works_count"),
            "publisher": (data.get("host_organization_name") or None),
        }
    except requests.RequestException as e:
        return {"openalex_error": str(e)}


def assess_predatory(meta: dict, datasets_available: bool = True) -> bool:
    """Heuristic red flag: journal is in NO recognized index/dataset we can see,
    yet exists (OpenAlex knows it) with substantial output. Not proof — a prompt
    for the agent to check Beall-style lists and the venue-quality skill.
    Never fires when no local index datasets exist (cannot distinguish
    'unindexed' from 'no data to check against')."""
    if not datasets_available:
        return False
    indexed = any([meta.get("scopus"), meta.get("scimago"), meta.get("doaj"),
                   meta.get("tr_dizin"), meta.get("wos_index") not in (None, "NONE", "unknown")])
    known = bool(meta.get("openalex_id"))
    return known and not indexed and (meta.get("works_count") or 0) > 100


def cache_get(cache_path: Path, issn: str, title: str) -> dict | None:
    for rec in read_jsonl(cache_path):
        rec_issn = normalize_issn(rec.get("issn", "") or "")
        # A queried ISSN is authoritative over any record that HAS an ISSN: a
        # title-string coincidence must never override an explicit ISSN mismatch
        # (e.g. two differently-indexed journals sharing a reused title). Only
        # fall back to title matching when the record itself carries no ISSN to
        # compare against, or when the caller didn't query by ISSN at all.
        if issn and rec_issn:
            if rec_issn != issn:
                continue
        elif title and normalize_title(rec.get("display_name") or rec.get("title_query") or "") == normalize_title(title):
            pass
        else:
            continue
        try:
            # `.get(..., default)` only substitutes the default when the key is
            # ABSENT — a hand-edited/corrupt cache row with `"checked_at": null`
            # still returns None, which `fromisoformat` raises TypeError (not
            # ValueError) on; `or` catches both the missing-key and null cases.
            age = (datetime.date.today()
                   - datetime.date.fromisoformat(rec.get("checked_at") or "1970-01-01")).days
        except (ValueError, TypeError):
            age = 10**6
        if age <= CACHE_TTL_DAYS:
            return rec
    return None


def cache_put(cache_path: Path, rec: dict):
    """Replace any cached record with the same identity (same non-empty ISSN,
    or same non-empty normalized title) — one venue, one cache row."""
    new_issn = normalize_issn(rec.get("issn", "") or "")
    new_title = normalize_title(rec.get("display_name", "") or rec.get("title_query", "") or "")

    def same_venue(r: dict) -> bool:
        r_issn = normalize_issn(r.get("issn", "") or "")
        if new_issn and r_issn and r_issn == new_issn:
            return True
        r_title = normalize_title(r.get("display_name", "") or r.get("title_query", "") or "")
        return bool(new_title) and r_title == new_title

    # file_lock around the WHOLE read -> filter -> write cycle: registry_db.py/
    # evidence_db.py/doi2bib.py all serialize their read-modify-write this way;
    # this one didn't (reproduced live: 10 concurrent venue_check.py calls lost
    # 2 of 10 rows to last-writer-wins — write_jsonl()'s atomic os.replace()
    # only prevents a torn/partial file, it does not prevent two writers both
    # computing "records minus mine" from the same stale read and one clobbering
    # the other's addition).
    with file_lock(cache_path):
        records = [r for r in read_jsonl(cache_path) if not same_venue(r)]
        records.append(rec)
        write_jsonl(cache_path, records)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--issn")
    ap.add_argument("--title")
    ap.add_argument("--cache", default="sources/venues.jsonl")
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--offline", action="store_true", help="skip OpenAlex (local datasets only)")
    ap.add_argument("--set-wos", dest="set_wos", choices=["SCIE", "SSCI", "AHCI", "ESCI", "none"],
                    help="record an agent-verified WoS class into the cache")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.cache, "--cache")
    if not args.issn and not args.title:
        die("pass --issn and/or --title")
    issn = normalize_issn(args.issn) if args.issn else ""
    if args.issn and len(issn) != 8:
        die(f"'{args.issn}' is not a valid ISSN (need 8 chars, got '{issn}')")
    cache_path = Path(args.cache)

    if args.set_wos:
        rec = cache_get(cache_path, issn, args.title or "") or \
              {"issn": args.issn or "", "display_name": args.title or ""}
        # Always uppercase — including "none" -> "NONE" — to match assess_predatory()'s
        # check (`wos_index not in (None, "NONE", "unknown")`). Storing lowercase "none"
        # here made `"none" not in (None, "NONE", "unknown")` evaluate True, so a venue
        # EXPLICITLY confirmed absent from WoS was treated as "indexed", suppressing the
        # predatory-journal heuristic in exactly the case it's meant to catch.
        rec["wos_index"] = args.set_wos.upper()
        rec["wos_source"] = "mjl-webfetch"
        rec["checked_at"] = datetime.date.today().isoformat()
        cache_put(cache_path, rec)
        emit({"status": "recorded", "venue": rec}, True)
        return

    if not args.no_cache:
        hit = cache_get(cache_path, issn, args.title or "")
        if hit:
            emit({**hit, "cache": "hit"}, True)
            return

    meta = {"issn": args.issn or None, "title_query": args.title or None}
    meta.update(lookup_local(issn, args.title or ""))
    oa_errored = False
    if not args.offline:
        if requests is None:
            die("requests not installed — pip install requests (or pass --offline)")
        oa = lookup_openalex(issn, args.title or "")
        # A transient network failure (proxy/DNS/timeout) must NOT be persisted:
        # caching it (with a fresh checked_at) poisoned the 30-day TTL, so every
        # later lookup — even after the network recovered — returned the failed
        # record. Merge the result for THIS response, but skip the cache write
        # when the lookup errored so the failure never outlives the process.
        oa_errored = "openalex_error" in oa
        meta.update({k: v for k, v in oa.items() if v is not None})
    meta.setdefault("wos_index", "unknown")
    meta.setdefault("scopus", False)
    meta.setdefault("tr_dizin", False)
    meta.setdefault("doaj", False)
    meta.setdefault("quartile", None)
    datasets = [f.name for f in DATA_DIR.glob("*.csv")] if DATA_DIR.exists() else []
    meta["predatory_flag"] = assess_predatory(meta, datasets_available=bool(datasets))
    meta["checked_at"] = datetime.date.today().isoformat()
    meta["datasets_available"] = datasets
    if not datasets:
        meta["note"] = "no local index datasets — run INSTALL.sh --update-data for quartile/Scopus coverage"
    if oa_errored:
        meta["cache"] = "not-cached (OpenAlex lookup failed — transient, not persisted)"
    else:
        cache_put(cache_path, meta)
    emit(meta, True)


if __name__ == "__main__":
    try:
        main()
    except TimeoutError as e:
        die(f"timed out waiting for another process to release the data-file lock — {e}")
    except OSError as e:
        die(f"failed to write the data file — {e}")
