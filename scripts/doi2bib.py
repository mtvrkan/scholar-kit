#!/usr/bin/env python3
"""doi2bib.py — authoritative BibTeX from a DOI. The ONLY sanctioned writer of references.bib.

Modes:
  --doi 10.1234/xyz [--key custom2024key] [--append bib/references.bib]
      Fetch BibTeX via doi.org content negotiation (Accept: application/x-bibtex).
  --title-search "paper title" [--year 2023]
      Crossref works API lookup; returns candidate DOIs ranked by title similarity.
  --verify --bib bib/references.bib [--entry key]
      For every entry with a DOI: fetch the authoritative CSL-JSON record and
      field-diff title/year/first-author. Report PASS / FIX / FABRICATED / UNRESOLVED.

Network endpoints (whitelisted): doi.org, api.crossref.org.
Every fetched entry gains  verified = {true}  and  fetched_at  fields.
Exit codes: 0 ok · 1 error · 2 verification found problems.
"""
from __future__ import annotations

import argparse
import datetime
import html
import re
import sys
import urllib.parse
from pathlib import Path

# Optional dependency; guarded so a missing `requests` package surfaces as a
# clean die() message via main() instead of a raw ModuleNotFoundError before
# argparse even runs.
try:
    import requests
except ImportError:
    requests = None

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (DOI_RE, clean_doi, die, emit, file_lock, http_get_with_retry,
                        normalize_title, parse_bibtex, require_within_cwd,
                        serialize_bibtex, transliterate, warn_missing_rapidfuzz,
                        write_text_atomic)

UA = {"User-Agent": "scholar-kit/1.0 (mailto:scholar-kit@example.org)"}
TIMEOUT = 20
RETRIES = 2  # 1 retry after a transient network failure


def _get(url: str, **kwargs) -> requests.Response:
    return http_get_with_retry(url, retries=RETRIES, backoff=1.5,
                               timeout=kwargs.pop("timeout", TIMEOUT), **kwargs)


def _clean_and_validate_doi(doi: str) -> str:
    """Strip a doi.org URL prefix and reject a malformed DOI before it ever
    reaches the network — a typo'd or garbage DOI should fail fast with a
    clear message, not surface as a confusing HTTP error from doi.org."""
    clean = clean_doi(doi)
    if not DOI_RE.match(clean):
        die(f"'{doi}' is not a valid DOI (expected 10.NNNN/suffix) — check for typos")
    return clean


def _doi_url(doi: str) -> str:
    """DOI_RE permits URL-structural characters (#, ?, &) that real-world DOI
    suffixes can legally contain — spliced unescaped into the request URL,
    a "#"-containing DOI gets silently truncated at the fragment boundary by
    the HTTP client, so doi.org resolves a DIFFERENT, shorter DOI than the
    one requested, and that wrong record then gets written to references.bib
    marked verified:true. Percent-encode the DOI (preserving "/", which is
    structurally required and always safe here) before building the URL."""
    return "https://doi.org/" + urllib.parse.quote(doi, safe="/")


def unescape_html_entities(text: str) -> str:
    """Decode HTML entities that publishers deposit into bibliographic metadata.

    doi.org's BibTeX is generated from what the publisher registered, and
    publishers register HTML: a journal called "Diabetes Technology &
    Therapeutics" arrives as "Diabetes Technology &amp; Therapeutics" and,
    since nothing downstream decodes it, prints that way in the finished
    reference list. Ampersands in journal names are common enough
    ("Science & Justice", "Health & Place", "Cell & Bioscience") that this is
    a defect every manuscript with such a source inherits.

    Left to LaTeX escaping downstream: the result here is plain text with a
    real "&", which the BibTeX writer and pandoc handle correctly. Decoding
    twice would be the error to avoid — "&amp;amp;" is a publisher's mistake
    to report, not one to silently repair — so this unescapes once, not to a
    fixed point."""
    return html.unescape(text) if text else text


def fetch_bibtex(doi: str) -> str:
    doi = _clean_and_validate_doi(doi)
    r = _get(_doi_url(doi),
             headers={**UA, "Accept": "application/x-bibtex"},
             allow_redirects=True)
    if r.status_code == 404:
        die(f"DOI {doi} not found at doi.org — check for typos or use --title-search")
    r.raise_for_status()
    r.encoding = "utf-8"
    return unescape_html_entities(r.text.strip())


def fetch_csl(doi: str) -> dict:
    doi = _clean_and_validate_doi(doi)
    r = _get(_doi_url(doi),
             headers={**UA, "Accept": "application/vnd.citationstyles.csl+json"},
             allow_redirects=True)
    if r.status_code == 404:
        return {}
    r.raise_for_status()
    return r.json()


def crossref_title_search(title: str, year: int | None = None, rows: int = 5) -> list[dict]:
    params = {"query.bibliographic": title, "rows": rows}
    if year:
        params["filter"] = f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31"
    r = _get("https://api.crossref.org/works", params=params, headers=UA)
    r.raise_for_status()
    items = r.json().get("message", {}).get("items", [])
    out = []
    try:
        from rapidfuzz import fuzz
        score = lambda a, b: fuzz.token_sort_ratio(a, b)
    except ImportError:  # pragma: no cover
        warn_missing_rapidfuzz()
        score = lambda a, b: 100 if normalize_title(a) == normalize_title(b) else 50
    for it in items:
        cand_title = (it.get("title") or [""])[0]
        out.append({
            "doi": it.get("DOI"),
            "title": cand_title,
            "year": (it.get("issued", {}).get("date-parts") or [[None]])[0][0],
            "container": (it.get("container-title") or [""])[0],
            "similarity": round(score(title, cand_title), 1),
        })
    return sorted(out, key=lambda x: -x["similarity"])


def make_key(entry_fields: dict, fallback: str) -> str:
    """surname + year + first significant title word, ascii-lowered.

    Names/titles are transliterated (not dropped) before ASCII-folding, so
    "Şahin" -> "sahin", not the silently-truncated "ahin" a raw filter
    would produce for a Turkish-first academic tool.
    """
    author = transliterate(entry_fields.get("author", ""))
    surname = re.split(r"[,\s]", author.strip())[0] if author else "anon"
    year = re.search(r"\d{4}", entry_fields.get("year", "") or entry_fields.get("date", "") or "")
    stop = {"a", "an", "the", "on", "of", "for", "and", "in", "to", "with"}
    title = transliterate(entry_fields.get("title", ""))
    word = next((w for w in re.findall(r"[a-zA-Z]{3,}", normalize_title(title))
                 if w not in stop), "work")
    key = f"{surname.lower()}{year.group(0) if year else 'nd'}{word}"
    key = re.sub(r"[^a-z0-9]", "", key.lower())
    return key or fallback


def _backfill_from_csl(entry: dict, doi: str):
    """doi.org BibTeX sometimes ships empty title/author/year fields — repair from CSL-JSON."""
    if (entry["fields"].get("title") and entry["fields"].get("author")
            and entry["fields"].get("year")):
        return
    try:
        csl = fetch_csl(doi)
    except requests.RequestException:
        return
    if not entry["fields"].get("title") and csl.get("title"):
        entry["fields"]["title"] = csl["title"]
    if not entry["fields"].get("author") and csl.get("author"):
        entry["fields"]["author"] = " and ".join(
            f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
            for a in csl["author"] if a.get("family"))
    if not entry["fields"].get("year"):
        y = _csl_year(csl)
        if y:
            entry["fields"]["year"] = str(y)


CANONICAL_BIB = Path("bib") / "references.bib"


def off_canon_bib_warning(target: Path) -> str:
    """Warn when --append writes a bibliography nothing else in the kit reads.

    cite_audit, bib_doctor, citation_triangulate, evidence_funnel, both build
    scripts and run_evals all default to `bib/references.bib`. Appending
    somewhere else succeeds silently and produces a second bibliography that
    no other tool ever opens: the manuscript then builds with a reference list
    missing every entry that landed in the stray file, while cite_audit calls
    those same citations "missing" — two symptoms whose shared cause is
    invisible from either one. This is a WARNING, not a block: a per-chapter
    bib or a replication-pack copy is a legitimate target. Silence was the bug.
    """
    if target.suffix.lower() != ".bib":
        return ""
    try:
        same = target.resolve() == CANONICAL_BIB.resolve()
    except OSError:                                  # unresolvable path
        same = False
    if same:
        return ""
    # Only warn where the canonical layout is actually in use — a project that
    # keeps its bibliography elsewhere entirely should not be nagged.
    if not (CANONICAL_BIB.exists() or CANONICAL_BIB.parent.is_dir()):
        return ""
    return (f"{target.as_posix()} is NOT the bibliography the kit reads. "
            f"cite_audit, bib_doctor and both build scripts default to "
            f"{CANONICAL_BIB.as_posix()}; entries appended here are invisible "
            f"to all of them. Append to {CANONICAL_BIB.as_posix()} unless you "
            f"deliberately want a separate file.")


def cmd_fetch(args):
    try:
        bib = fetch_bibtex(args.doi)
    except requests.RequestException as e:
        die(f"network error fetching DOI {args.doi}: {e}")
    entries = parse_bibtex(bib)
    if not entries:
        die(f"doi.org returned unparseable BibTeX for {args.doi}: {bib[:200]}")
    entry = entries[0]
    _backfill_from_csl(entry, args.doi)
    entry["key"] = args.key or make_key(entry["fields"], entry["key"])
    entry["fields"]["verified"] = "true"
    entry["fields"]["fetched_at"] = datetime.date.today().isoformat()
    text = serialize_bibtex(entry)
    if args.append:
        p = Path(args.append)
        off_canon = off_canon_bib_warning(p)
        with file_lock(p):
            existing_raw = p.read_text(encoding="utf-8") if p.exists() else ""
            existing = parse_bibtex(existing_raw)
            # clean_doi() (not a bare .lower()) so a bib holding
            # "https://doi.org/10.x" recognizes an incoming bare "10.x" as the
            # same DOI — registry_db.is_duplicate and bib_doctor already
            # normalize this way; a bare-.lower() comparison here missed that
            # prefix mismatch and let a genuine duplicate get appended twice.
            new_doi = clean_doi(entry["fields"].get("doi") or "").lower()
            if new_doi and any(
                    clean_doi(e["fields"].get("doi") or "").lower() == new_doi
                    for e in existing if e["fields"].get("doi")):
                out = {"status": "duplicate", "key": entry["key"],
                       "message": f"DOI already in {args.append} — nothing appended"}
                if off_canon:
                    out["off_canon_bib"] = off_canon
                emit(out, args.json_out)
                return
            if any(e["key"] == entry["key"] for e in existing):
                base, n = entry["key"], 2
                while any(e["key"] == entry["key"] for e in existing):
                    entry["key"] = f"{base}{n}"
                    n += 1
            text = serialize_bibtex(entry)
            # Atomic (temp-file + os.replace), not a raw open("a") append — a
            # crash/disk-full mid-write must never leave a truncated entry
            # that parse_bibtex() then silently drops or mis-parses.
            write_text_atomic(p, existing_raw + text + "\n\n")
        out = {"status": "appended", "key": entry["key"], "file": args.append}
        if off_canon:
            out["off_canon_bib"] = off_canon
        emit(out, args.json_out)
    elif args.json_out:
        emit({"key": entry["key"], "bibtex": text}, True)
    else:
        print(text)


def cmd_title_search(args):
    try:
        results = crossref_title_search(args.title_search, args.year)
    except requests.RequestException as e:
        die(f"network error querying Crossref: {e}")
    if not results:
        die(f"Crossref returned no candidates for '{args.title_search}' — try fewer/other words")
    emit(results, True)


def _first_author_family(csl: dict) -> str:
    authors = csl.get("author") or []
    return (authors[0].get("family", "") if authors else "").lower()


def _local_family_names(author_field: str) -> set[str]:
    """Parse a BibTeX author field ("Kaya, Ahmet and Yilmaz, Berk") into a set
    of lowercased family names for exact-token comparison.

    The prior check was `fam not in author_field.lower()` — a raw substring
    test, not anchored to actual name tokens. That produced false NON-matches
    (a real mismatch gets missed) in two concrete ways: the " and " joiner
    itself contains "an", so any DOI whose real first author family is
    literally "An" (a common surname) always "matched" any multi-author
    entry regardless of who the real authors are; and short/common surnames
    like "ng" or "li" match as a substring inside unrelated longer names
    ("Zhang", "Milan"). This is the ONE compensating check meant to catch a
    wrong-DOI attachment when title similarity alone lands in the ambiguous
    "FIX" band (70-97) — false matches there silently let a fabricated/
    wrong-paper citation through as a "safe" metadata correction instead of
    FABRICATED."""
    names = set()
    for chunk in re.split(r"\s+and\s+", author_field.lower()):
        chunk = chunk.strip()
        if not chunk:
            continue
        family = chunk.split(",")[0].strip()
        if family:
            names.add(family)
    return names


def _csl_year(csl: dict):
    parts = (csl.get("issued") or {}).get("date-parts") or [[None]]
    return parts[0][0]


def _csl_full_title(csl: dict) -> str:
    """Reconstruct the full title as doi.org BibTeX content-negotiation returns
    it (a single "Title: Subtitle" field), so cmd_verify's title comparison does
    not false-FABRICATE when a publisher (e.g. ACM/Crossref) splits it into
    separate CSL "title" + "subtitle" fields ("XGBoost" / "A Scalable Tree
    Boosting System")."""
    title = csl.get("title", "") or ""
    subtitle = csl.get("subtitle") or []
    if subtitle:
        title = title + ": " + ": ".join(subtitle)
    return title


def cmd_verify(args):
    p = Path(args.bib)
    if not p.exists():
        die(f"{args.bib} does not exist")
    entries = parse_bibtex(p.read_text(encoding="utf-8"))
    if not entries:
        # A bib file that exists but yields zero parseable entries (empty,
        # truncated, or corrupt) must NOT report PASS with checked=0 — that
        # silently passed the citation gate on a broken bibliography. Nothing
        # was verified, so this is an error, not a pass.
        die(f"{args.bib} contains no parseable BibTeX entries — nothing to verify "
            f"(is the file empty or corrupt?)")
    if args.entry:
        entries = [e for e in entries if e["key"] == args.entry]
        if not entries:
            die(f"entry '{args.entry}' not found in {args.bib}")
    report, worst = [], "PASS"
    for e in entries:
        doi = e["fields"].get("doi", "").strip()
        if not doi:
            report.append({"key": e["key"], "status": "UNRESOLVED",
                           "reason": "no DOI field — run doi2bib.py --title-search or mark verified:false"})
            worst = "FAIL"
            continue
        try:
            csl = fetch_csl(doi)
        except requests.RequestException as ex:
            report.append({"key": e["key"], "status": "UNRESOLVED", "reason": f"network: {ex}"})
            worst = "FAIL"
            continue
        if not csl:
            report.append({"key": e["key"], "status": "FABRICATED",
                           "reason": f"DOI {doi} resolves to nothing at doi.org"})
            worst = "FAIL"
            continue
        problems, fixes = [], {}
        # Compare against the reconstructed full "Title: Subtitle" (see
        # _csl_full_title) — comparing local_title only against csl["title"]
        # flags a correctly-fetched ACM/Crossref entry as FABRICATED on a false
        # title mismatch when the publisher split the colon-title into subtitle.
        auth_title_full = _csl_full_title(csl)
        auth_title = normalize_title(auth_title_full)
        local_title = normalize_title(e["fields"].get("title", ""))
        try:
            from rapidfuzz import fuzz
            sim = fuzz.token_sort_ratio(auth_title, local_title)
        except ImportError:  # pragma: no cover
            warn_missing_rapidfuzz()
            sim = 100 if auth_title == local_title else 0
        if sim < 70:
            problems.append(f"title mismatch (similarity {sim:.0f}) — DOI belongs to '{auth_title_full[:80]}'")
        elif sim < 97:
            fixes["title"] = auth_title_full
        auth_year, local_year = _csl_year(csl), None
        m = re.search(r"\d{4}", e["fields"].get("year", ""))
        if m:
            local_year = int(m.group(0))
        if auth_year and local_year and auth_year != local_year:
            fixes["year"] = str(auth_year)
        fam = _first_author_family(csl)
        if fam and fam not in _local_family_names(e["fields"].get("author", "")):
            problems.append(f"first author mismatch — authoritative record says '{fam}'")
        if problems:
            report.append({"key": e["key"], "status": "FABRICATED", "reason": "; ".join(problems)})
            worst = "FAIL"
        elif fixes:
            report.append({"key": e["key"], "status": "FIX", "patch": fixes})
            if worst == "PASS":
                worst = "FIX"
        else:
            report.append({"key": e["key"], "status": "PASS"})
    summary = {"result": worst, "checked": len(report),
               "pass": sum(1 for r in report if r["status"] == "PASS"),
               "fix": sum(1 for r in report if r["status"] == "FIX"),
               "fabricated": sum(1 for r in report if r["status"] == "FABRICATED"),
               "unresolved": sum(1 for r in report if r["status"] == "UNRESOLVED"),
               "entries": report}
    emit(summary, True)
    sys.exit(0 if worst == "PASS" else 2)


def main():
    if requests is None:
        die("requests not installed — pip install requests")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doi")
    ap.add_argument("--key")
    ap.add_argument("--append", metavar="BIBFILE")
    ap.add_argument("--title-search", dest="title_search")
    ap.add_argument("--year", type=int)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--bib", default="bib/references.bib")
    ap.add_argument("--entry")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    if args.append:
        require_within_cwd(args.append, "--append")
    require_within_cwd(args.bib, "--bib")
    if args.verify:
        cmd_verify(args)
    elif args.doi:
        cmd_fetch(args)
    elif args.title_search:
        cmd_title_search(args)
    else:
        die("nothing to do — pass --doi, --title-search, or --verify (see --help)")


if __name__ == "__main__":
    try:
        main()
    except TimeoutError as e:
        die(f"timed out waiting for another process to release the bib-file lock — {e}")
    except OSError as e:
        die(f"failed to write the bib file — {e}")
    except UnicodeDecodeError as e:
        die(f"bib file is not valid UTF-8 — {e}")
