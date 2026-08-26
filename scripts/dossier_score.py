#!/usr/bin/env python3
"""dossier_score.py — the promotion dossier's arithmetic, and the index claim nobody re-checks.

WHY THIS EXISTS
A doçentlik or promotion file is a points table: each publication lands in a
criterion, each criterion carries a point value, the values sum. All of it is
arithmetic, and all of it is done by hand at midnight against a PDF of criteria.

The error that costs a file is not the addition. It is the index claim: a paper
in an ESCI journal entered under the SCI-E criterion, usually honestly — the
journal was SCIE when the work started, or the author read a publisher's own
marketing page. A reviewer checks it against the Master Journal List and the
whole entry falls.

So the points come from a criteria file YOU fill, the publications come from an
export YOU hand over, and every venue's index is re-checked against this
project's own venue cache rather than trusted from the export.

WHAT IT KEEPS: nothing. There is no ledger, no history, no profile. Every run
starts from the two files you pass, and the script writes only where --write
points, inside the project directory. `POSITIONING.md` refuses cross-paper
memory; being a dossier tool turned out not to require any.

WHAT IT REFUSES
- **To recall a criterion or a point value.** Both come from `criteria.json` with
  the URL you read the table at. No file ⇒ UNCHECKED.
- **To decide the file is sufficient.** It reports counted points against the
  minimum the criteria file states, and stops there. Whether a dossier passes is
  a committee's decision and is not arithmetic.
- **To count an unverified venue.** A publication whose journal is not in the
  venue cache is reported in its own bucket with the command that resolves it —
  never counted, and never silently dropped either.
- **To improve an index.** A claimed SCI-E that the cache says is ESCI is
  reported as a mismatch, and the ESCI criterion is what it scores against.

USAGE
  python scripts/dossier_score.py --publications dossier/publications.bib
  python scripts/dossier_score.py --publications dossier/pubs.json --cv --write dossier/cv.md

Exit codes: 0 clean · 1 error · 2 findings (mismatch, unverified, unmatched) or UNCHECKED.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (die, emit, normalize_issn, normalize_title, parse_bibtex,
                        read_jsonl, require_within_cwd, write_text_atomic)

DEFAULT_CRITERIA = "dossier/criteria.json"
DEFAULT_VENUES = "sources/venues.jsonl"

# BibTeX entry types → the publication kinds a criteria table talks about.
BIB_TYPE = {"article": "article", "inproceedings": "conference", "conference": "conference",
            "incollection": "chapter", "inbook": "chapter", "book": "book",
            "phdthesis": "thesis", "mastersthesis": "thesis", "techreport": "report",
            "patent": "patent", "misc": "other"}


def load_criteria(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(spec, dict):
        die(f"{path} must hold a JSON object")
    if not spec.get("source_url"):
        die(f"{path} has no 'source_url' — a points table with no source is a "
            f"remembered points table, and this is the file that exists so nothing "
            f"is remembered")
    criteria = spec.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        die(f"{path} needs a non-empty 'criteria' array")
    for c in criteria:
        if not isinstance(c, dict) or "id" not in c or "points" not in c:
            die(f"{path}: every criterion needs at least 'id' and 'points'")
    return spec


def load_publications(path: Path) -> list[dict]:
    """A .bib, a JSON array, or a CSV with a header.

    ORCID is deliberately not parsed from its own JSON: its schema is deep,
    versioned and easy to half-support, and ORCID exports BibTeX itself. A parser
    that silently mis-reads half a record is worse than a documented export step.
    """
    suffix = path.suffix.lower()
    if suffix == ".bib":
        out = []
        for entry in parse_bibtex(path.read_text(encoding="utf-8", errors="replace")):
            f = entry["fields"]
            out.append({
                "title": f.get("title", ""), "year": _int(f.get("year")),
                "type": BIB_TYPE.get(entry["type"], "other"),
                "venue": f.get("journal") or f.get("booktitle") or f.get("publisher", ""),
                "issn": f.get("issn", ""), "doi": f.get("doi", ""),
                "authorship": f.get("authorship", ""), "index": f.get("index", ""),
            })
        return out
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("publications") or []
        if not isinstance(data, list):
            die(f"{path} must hold a JSON array of publications, or an object with a "
                f"'publications' array")
        return [dict(r, year=_int(r.get("year"))) for r in data if isinstance(r, dict)]
    if suffix in (".csv", ".tsv"):
        delim = "\t" if suffix == ".tsv" else ","
        rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig",
                                                  errors="replace").splitlines(),
                                   delimiter=delim))
        out = []
        for row in rows:
            low = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            out.append({
                "title": low.get("title", ""), "year": _int(low.get("year")),
                "type": low.get("type", "article"),
                "venue": low.get("venue") or low.get("journal", ""),
                "issn": low.get("issn", ""), "doi": low.get("doi", ""),
                "authorship": low.get("authorship", ""), "index": low.get("index", ""),
            })
        return out
    die(f"unsupported publication export {suffix!r} — give .bib, .json or .csv "
        f"(ORCID and Scopus both export BibTeX)")


def _int(value) -> int | None:
    try:
        return int(str(value).strip()[:4])
    except (TypeError, ValueError):
        return None


def venue_index(venues: list[dict], issn: str, title: str) -> dict | None:
    """The venue cache's record for this journal, or None.

    Matched the way venue_check.py matches: an ISSN beats a title, and a title is
    only consulted when the cached record carries no ISSN to disagree with.
    Staleness is REPORTED (checked_at travels with the record) rather than used
    to discard — a two-year-old WoS class is a fact with a date on it, and a
    dossier reviewer wants the date, not a silence.
    """
    issn_n, title_n = normalize_issn(issn or ""), normalize_title(title or "")
    for rec in venues:
        rec_issn = normalize_issn(rec.get("issn", "") or "")
        if issn_n and rec_issn:
            if rec_issn == issn_n:
                return rec
            continue
        rec_title = normalize_title(rec.get("display_name") or rec.get("title_query") or "")
        if title_n and rec_title == title_n:
            return rec
    return None


def _indexes_of(meta: dict) -> list[str]:
    out = []
    wos = (meta.get("wos_index") or "").upper()
    if wos and wos not in ("NONE", "UNKNOWN"):
        out.append(wos)
    if meta.get("scopus"):
        out.append("SCOPUS")
    if meta.get("tr_dizin"):
        out.append("TR_DIZIN")
    if meta.get("doaj"):
        out.append("DOAJ")
    return out


def matches(pub: dict, criterion: dict, indexes: list[str]) -> bool:
    spec = criterion.get("match") or {}
    wanted_type = spec.get("type")
    if wanted_type:
        allowed = [wanted_type] if isinstance(wanted_type, str) else list(wanted_type)
        if str(pub.get("type", "")).lower() not in [str(a).lower() for a in allowed]:
            return False
    wanted_index = spec.get("index")
    if wanted_index:
        if not any(str(w).upper() in indexes for w in wanted_index):
            return False
    wanted_q = spec.get("quartile")
    if wanted_q and str(pub.get("_quartile", "")).upper() not in [str(q).upper()
                                                                 for q in wanted_q]:
        return False
    wanted_auth = spec.get("authorship")
    if wanted_auth and str(pub.get("authorship", "")).lower() not in [
            str(a).lower() for a in wanted_auth]:
        return False
    year_min = spec.get("year_min")
    if year_min and (pub.get("year") or 0) < year_min:
        return False
    return True


def score(publications: list[dict], criteria: dict | None, venues: list[dict]) -> dict:
    rows, unverified, mismatches, unmatched = [], [], [], []
    counts: dict[str, int] = {}
    criteria_list = (criteria or {}).get("criteria") or []

    for original in publications:
        # A local copy: scoring must not write back into the caller's export.
        # The quartile is looked up here, and an earlier version stamped it onto
        # the input dict, so a second scoring run saw data the first one invented.
        pub = dict(original)
        meta = venue_index(venues, pub.get("issn", ""), pub.get("venue", ""))
        indexes = _indexes_of(meta) if meta else []
        if meta:
            pub["_quartile"] = meta.get("quartile") or ""
        claimed = (pub.get("index") or "").upper()
        row = {"title": str(pub.get("title", ""))[:110], "year": pub.get("year"),
               "type": pub.get("type"), "venue": pub.get("venue"),
               "verified_indexes": indexes,
               "verified_on": (meta or {}).get("checked_at"),
               "claimed_index": claimed or None}
        if not meta:
            row["state"] = "unverified"
            unverified.append({"venue": pub.get("venue"), "issn": pub.get("issn"),
                               "resolve_with": (
                                   f"python scripts/venue_check.py "
                                   f"{'--issn ' + pub['issn'] if pub.get('issn') else '--title ' + json.dumps(pub.get('venue', ''))}")})
        elif claimed and claimed not in indexes:
            row["state"] = "index_mismatch"
            mismatches.append({"title": row["title"], "claimed": claimed,
                               "verified": indexes,
                               "checked_at": meta.get("checked_at")})
        else:
            row["state"] = "verified"

        matched = next((c for c in criteria_list if matches(pub, c, indexes)), None)
        if matched:
            row["criterion"] = matched["id"]
            row["points"] = matched["points"]
        else:
            row["criterion"] = None
            row["points"] = 0
            if criteria_list:
                unmatched.append(row["title"])
        rows.append(row)

    counted_points = 0.0
    pending_points = 0.0
    per_criterion: dict[str, dict] = {}
    for c in criteria_list:
        per_criterion[c["id"]] = {"label": c.get("label"), "points_each": c["points"],
                                  "counted": 0, "pending": 0, "points": 0.0,
                                  "max_count": c.get("max_count"),
                                  "min_count": c.get("min_count")}
    for row in rows:
        cid = row["criterion"]
        if not cid:
            continue
        bucket = per_criterion[cid]
        if row["state"] == "unverified":
            bucket["pending"] += 1
            pending_points += row["points"]
            continue
        cap = bucket["max_count"]
        if cap is not None and bucket["counted"] >= cap:
            # Named, not just counted. A dossier tool that drops publications past
            # a cap without saying which ones has silently decided which of your
            # papers count — and the order it decided by is the order of your
            # export file, which is no order at all.
            bucket.setdefault("over_cap", 0)
            bucket["over_cap"] += 1
            bucket.setdefault("not_counted", []).append(row["title"])
            continue
        bucket["counted"] += 1
        bucket["points"] += row["points"]
        counted_points += row["points"]
        counts[cid] = counts.get(cid, 0) + 1

    problems = []
    if not publications:
        problems.append("the publication export holds no entries — nothing was "
                        "scored, and an empty run must not report the same as a "
                        "clean one")
    for cid, bucket in per_criterion.items():
        if bucket.get("not_counted"):
            problems.append(
                f"criterion {cid} caps at {bucket['max_count']}; "
                f"{len(bucket['not_counted'])} further publication(s) were NOT "
                f"counted, in export order rather than by merit: "
                f"{bucket['not_counted']}. Reorder your export if a different one "
                f"should take the slot")
    if mismatches:
        problems.append(f"{len(mismatches)} publication(s) claim an index the venue "
                        f"cache does not confirm — the single most common reason a "
                        f"dossier entry is struck out")
    if unverified:
        problems.append(f"{len(unverified)} venue(s) are not in sources/venues.jsonl — "
                        f"their points are held in 'pending', neither counted nor dropped")
    if unmatched:
        problems.append(f"{len(unmatched)} publication(s) match no criterion — either "
                        f"the criteria file is incomplete or these do not count")
    for cid, bucket in per_criterion.items():
        if bucket["min_count"] and bucket["counted"] < bucket["min_count"]:
            problems.append(f"criterion {cid} has {bucket['counted']} counted, the table "
                            f"states a minimum of {bucket['min_count']}")

    minimum = (criteria or {}).get("minimum_total")
    report = {
        "authority": (criteria or {}).get("authority"),
        "criteria_source": (criteria or {}).get("source_url"),
        "publications": len(publications),
        "rows": rows,
        "per_criterion": per_criterion,
        "points_counted": round(counted_points, 2),
        "points_pending_verification": round(pending_points, 2),
        "minimum_total": minimum,
        "index_mismatches": mismatches,
        "unverified_venues": unverified,
        "unmatched_publications": unmatched,
        "problems": problems,
        "note": ("counted points are stated against the minimum the criteria file "
                 "declares. Whether the dossier is sufficient is a committee's "
                 "decision and is not computed here. Nothing from this run is kept."),
    }
    report["result"] = "OK" if not problems else "FINDINGS"
    if criteria is None:
        report["result"] = "UNCHECKED"
        report["note"] = (
            "no criteria file — the publications were listed and their venues verified, "
            "but nothing was scored. Fill dossier/criteria.json from ÜAK's or your "
            "university's own published table; this kit will not recall a point value.")
    return report


def render_cv(report: dict, criteria: dict | None) -> str:
    """A CV grouped by the criteria table's own categories. Every line comes from
    the export you supplied — there is no 'selected publications' judgement and
    no invented affiliation, title or date."""
    lines = ["# Academic CV — publications", "",
             "<!-- Generated by scripts/dossier_score.py from the export you supplied.",
             "     Nothing here was recalled: no affiliation, no title, no date. -->", ""]
    by_criterion: dict[str, list[dict]] = {}
    for row in report["rows"]:
        by_criterion.setdefault(row["criterion"] or "uncategorised", []).append(row)
    labels = {c["id"]: c.get("label", c["id"])
              for c in (criteria or {}).get("criteria") or []}
    for cid, rows in by_criterion.items():
        lines.append(f"## {labels.get(cid, cid)}")
        lines.append("")
        for row in sorted(rows, key=lambda r: (r["year"] or 0), reverse=True):
            index = "/".join(row["verified_indexes"]) or "index unverified"
            lines.append(f"- {row['title']} — *{row['venue']}* "
                         f"({row['year'] or 'n.d.'}, {index})")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--publications", required=True, metavar="FILE",
                    help="your export: .bib, .json or .csv")
    ap.add_argument("--criteria", default=DEFAULT_CRITERIA)
    ap.add_argument("--venues", default=DEFAULT_VENUES)
    ap.add_argument("--cv", action="store_true", help="render an academic CV instead")
    ap.add_argument("--write", metavar="FILE", help="write the CV to a file")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    for flag, value in (("--publications", args.publications),
                        ("--criteria", args.criteria), ("--venues", args.venues)):
        require_within_cwd(value, flag)
    if args.write:
        require_within_cwd(args.write, "--write")
    pubs_path = Path(args.publications)
    if not pubs_path.is_file():
        die(f"{args.publications} does not exist — export your publication list first "
            f"(ORCID and Scopus both offer BibTeX)")

    criteria = load_criteria(Path(args.criteria))
    report = score(load_publications(pubs_path), criteria, read_jsonl(args.venues))

    if args.cv:
        text = render_cv(report, criteria)
        if args.write:
            write_text_atomic(args.write, text)
            emit({"written": Path(args.write).as_posix(),
                  "entries": len(report["rows"]),
                  "note": "nothing was kept outside this project directory"}, args.json_out)
            return
        print(text)
        return

    emit(report, args.json_out)
    sys.exit(0 if report["result"] == "OK" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
