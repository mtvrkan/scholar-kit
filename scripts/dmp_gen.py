#!/usr/bin/env python3
"""dmp_gen.py — the Data Management Plan, derived from the registers rather than templated.

WHY THIS EXISTS
Horizon Europe requires a DMP, TÜBİTAK increasingly asks for one, and most are
written the same way: a template downloaded, filled with sentences that sound
like compliance, submitted, never read again. The reason is that the facts a DMP
asks for — what data, which licence, which format, where it will live, who may
have it — are scattered across a filesystem and a memory.

This project already holds those facts in two script-owned registers:
`analysis/datasets.jsonl` (source, version, licence, citation DOI, per-file
SHA-256) and `analysis/runs.jsonl`. So the plan is generated from them, and the
part that cannot be generated is named as a gap instead of being written over.

WHAT IT REFUSES
- **To claim FAIR compliance.** It reports the four letters one at a time and, for
  each, the record that evidences it — or the absence of one. "This project
  follows FAIR principles" is a sentence anyone can type; "F: evidenced by DOI
  10.x/y · A: no licence recorded" is a sentence that had to be earned.
- **To write a sentence for a dataset with no licence or no DOI.** Same rule as
  `compliance_gen.py availability`, for the same reason: the gap is the finding.
- **To invent costs, storage volumes or repository names.** The resources and
  preservation sections carry explicit blanks. A DMP is a commitment; a plausible
  commitment nobody made is worse than a blank one.
- **To know your funder's template.** The section list is the generic Science
  Europe core. `--sections <file>` replaces it with your funder's own, which YOU
  fill from their document.

USAGE
  python scripts/dmp_gen.py                       # the plan, as JSON
  python scripts/dmp_gen.py --write exports/dmp.md
  python scripts/dmp_gen.py --check               # only the gaps

Exit codes: 0 every dataset fully evidenced · 1 error · 2 gaps (or --check found any).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd, write_text_atomic

DEFAULT_DATASETS = "analysis/datasets.jsonl"
DEFAULT_RUNS = "analysis/runs.jsonl"
DEFAULT_PROTOCOL = "analysis/collection-protocol.md"

# Science Europe's core DMP structure — a public, funder-neutral standard, which
# is why shipping it is not the "specific institution's template content" that
# POSITIONING.md refuses. A funder's own section list replaces it via --sections.
CORE_SECTIONS = [
    "data_summary",
    "fair_findable",
    "fair_accessible",
    "fair_interoperable",
    "fair_reusable",
    "resources",
    "security_and_storage",
    "ethical_aspects",
    "other_policies",
]

# Formats a repository can still open in fifteen years, and formats that need the
# software that wrote them. Neither list is a verdict — a .mat file is a fact
# about the analysis, not a failing — but interoperability is exactly the letter
# of FAIR that a format decides.
OPEN_FORMATS = {".csv", ".tsv", ".txt", ".json", ".jsonl", ".xml", ".parquet",
                ".nc", ".h5", ".hdf5", ".fits", ".wav", ".png", ".tif", ".tiff",
                ".md", ".yaml", ".yml", ".edf", ".nii"}
CLOSED_FORMATS = {".xlsx", ".xls", ".sav", ".dta", ".mat", ".sas7bdat", ".rdata",
                  ".accdb", ".mdb", ".doc", ".docx", ".pdf"}

# A dataset whose record says this may not be redistributed. The DMP then names
# the access route instead of promising a deposit — the same line
# replication_pack.py draws.
RESTRICTED_SOURCES = {"own-survey", "own-scraped"}


def _formats(rec: dict) -> dict:
    open_f, closed_f, other = set(), set(), set()
    for f in rec.get("files", []):
        ext = Path(str(f.get("path", ""))).suffix.lower()
        if not ext:
            continue
        (open_f if ext in OPEN_FORMATS else closed_f if ext in CLOSED_FORMATS
         else other).add(ext)
    return {"open": sorted(open_f), "proprietary": sorted(closed_f),
            "unclassified": sorted(other)}


def fair_for(rec: dict) -> dict:
    """The four letters, each with the record that evidences it or the reason it
    is unevidenced. Deliberately never a score: three out of four is not 75%
    FAIR, it is a dataset nobody can reuse."""
    doi = (rec.get("citation") or {}).get("doi")
    lic = rec.get("license", "unknown")
    lic_ok = lic not in ("unknown", None, "") and bool(rec.get("license_verified"))
    fmts = _formats(rec)
    hashed = [f for f in rec.get("files", []) if f.get("sha256")]

    def state(ok: bool, evidence: str, gap: str) -> dict:
        return {"evidenced": ok, "because": evidence if ok else gap}

    return {
        "F": state(bool(doi),
                   f"citation DOI {doi}",
                   "no citation DOI in the register — dataset_db.py set-field "
                   "<id> citation '{\"doi\": \"...\"}'"),
        "A": state(lic_ok and bool(rec.get("url") or rec.get("source_id")),
                   f"licence {lic} (verified) at {rec.get('url') or rec.get('source_id')}",
                   "licence not recorded-and-verified, or no retrieval location — "
                   "'unknown' is not permission"),
        "I": state(bool(fmts["open"]) and not fmts["proprietary"],
                   f"open formats {fmts['open']}",
                   f"proprietary formats {fmts['proprietary']}"
                   if fmts["proprietary"] else "no files recorded"),
        "R": state(lic_ok and bool(hashed),
                   f"licence {lic} + {len(hashed)} file digests recorded",
                   "reuse needs both a verified licence and a provenance record "
                   "(per-file SHA-256)"),
    }


def summarise_dataset(rec: dict) -> dict:
    fair = fair_for(rec)
    files = rec.get("files", [])
    total_bytes = sum(int(f.get("bytes") or 0) for f in files)
    restricted = rec.get("source") in RESTRICTED_SOURCES or bool(rec.get("ethics"))
    gaps = [letter for letter, s in fair.items() if not s["evidenced"]]
    return {
        "id": rec.get("id"),
        "name": rec.get("name"),
        "source": rec.get("source"),
        "version": rec.get("version"),
        "license": rec.get("license", "unknown"),
        "license_verified": bool(rec.get("license_verified")),
        "citation_doi": (rec.get("citation") or {}).get("doi"),
        "files": len(files),
        "bytes": total_bytes or None,
        "formats": _formats(rec),
        "fair": fair,
        "unevidenced": gaps,
        "redistributable": not restricted,
        "access_route": (rec.get("url") or rec.get("source_id")) if not restricted else
        "not redistributable from this record — name the application route "
        "(the collection's own consent terms, or the board that must approve reuse)",
    }


def _sentence(d: dict) -> str | None:
    """One sentence per dataset, or none. A dataset missing its licence or its
    DOI gets no sentence at all — the gap is listed instead, because a plan that
    describes data it cannot honestly describe is the failure mode here."""
    if not d["citation_doi"] or not d["license_verified"]:
        return None
    if not d["redistributable"]:
        return (f"{d['name']} (v{d['version']}) was collected for this study and is "
                f"not redistributable under its own terms; access is by application.")
    return (f"{d['name']} (v{d['version']}) is available from {d['access_route']} "
            f"under {d['license']}, cited as https://doi.org/{d['citation_doi']}.")


def build(datasets: list[dict], runs: list[dict], sections: list[str],
          protocol_exists: bool) -> dict:
    summaries = [summarise_dataset(r) for r in datasets]
    sentences = [s for s in (_sentence(d) for d in summaries) if s]
    silent = [{"dataset": d["name"], "missing": [
        m for m, ok in (("citation DOI", bool(d["citation_doi"])),
                        ("verified licence", d["license_verified"])) if not ok]}
        for d in summaries if not _sentence(d)]

    envs = sum(1 for r in runs if r.get("environment"))
    body = {
        "data_summary": {
            "datasets": summaries,
            "total_files": sum(d["files"] for d in summaries),
            "runs_recorded": len(runs),
            "blank": None if summaries else
            "no dataset registered — /find-dataset or /collect-data first",
        },
        "fair_findable": {"per_dataset": {d["name"]: d["fair"]["F"] for d in summaries}},
        "fair_accessible": {"per_dataset": {d["name"]: d["fair"]["A"] for d in summaries}},
        "fair_interoperable": {"per_dataset": {d["name"]: d["fair"]["I"] for d in summaries}},
        "fair_reusable": {"per_dataset": {d["name"]: d["fair"]["R"] for d in summaries}},
        "resources": {
            "derived": f"{sum(d['bytes'] or 0 for d in summaries)} bytes across "
                       f"{sum(d['files'] for d in summaries)} registered files",
            "blank": ["storage cost over the project's lifetime",
                      "the person responsible for data management",
                      "long-term preservation budget after the project ends"],
        },
        "security_and_storage": {
            "derived": f"{sum(1 for d in summaries if d['files'])} datasets carry "
                       f"per-file SHA-256 digests in the register",
            "blank": ["where working copies live and how they are backed up",
                      "who has write access",
                      "the repository the final deposit goes to"],
        },
        "ethical_aspects": {
            "protocol": (DEFAULT_PROTOCOL if protocol_exists else
                         "no collection protocol on disk — /collect-data writes one"),
            "restricted": [d["name"] for d in summaries if not d["redistributable"]],
            "blank": ["the ethics approval reference, once your board issues it"],
        },
        "other_policies": {
            "blank": ["your institution's research data policy",
                      "your funder's open-data requirement and its embargo terms"],
        },
    }
    report = {
        "sections": sections,
        "body": {k: body.get(k, {"blank": ["not derivable from this project's records — "
                                           "answer it yourself"]}) for k in sections},
        "availability_sentences": sentences,
        "no_sentence_written_for": silent,
        "environment_records": envs,
        "gaps": sorted({letter for d in summaries for letter in d["unevidenced"]}),
        "note": ("generated from analysis/datasets.jsonl and analysis/runs.jsonl. "
                 "FAIR is reported letter by letter with its evidence; this file "
                 "never states that the project 'follows FAIR principles'."),
    }
    if not summaries:
        # A plan for a project with no registered data reporting "no problems" is
        # the silence-reads-as-pass failure this kit refuses everywhere else: it
        # is not that the data is fine, it is that there is no data to describe.
        report["result"] = "UNCHECKED"
        report["note"] = (
            "analysis/datasets.jsonl is empty — nothing was derived and nothing was "
            "checked. A data management plan written before the data is registered "
            "describes data nobody can verify; run /find-dataset or /collect-data "
            "first, or write the plan by hand knowing this tool contributed nothing.")
        return report
    report["result"] = "OK" if not silent and not report["gaps"] else "GAPS"
    return report


def render_markdown(report: dict) -> str:
    lines = ["# Data Management Plan", "",
             "<!-- Generated by scripts/dmp_gen.py from the dataset and run registers.",
             "     Every `TODO:` below is a commitment only you can make. -->", ""]
    titles = {
        "data_summary": "1. Data summary",
        "fair_findable": "2.1 Making data findable",
        "fair_accessible": "2.2 Making data openly accessible",
        "fair_interoperable": "2.3 Making data interoperable",
        "fair_reusable": "2.4 Increasing data re-use",
        "resources": "3. Allocation of resources",
        "security_and_storage": "4. Data security and storage",
        "ethical_aspects": "5. Ethical aspects",
        "other_policies": "6. Other issues",
    }
    for key in report["sections"]:
        lines.append(f"## {titles.get(key, key.replace('_', ' ').capitalize())}")
        lines.append("")
        section = report["body"][key]
        if key == "data_summary":
            for d in section.get("datasets", []):
                lines.append(f"- **{d['name']}** (`{d['id']}`, v{d['version']}, "
                             f"source `{d['source']}`) — {d['files']} files, "
                             f"licence {d['license']}"
                             f"{' (verified)' if d['license_verified'] else ' (UNVERIFIED)'}"
                             f", formats {', '.join(d['formats']['open'] + d['formats']['proprietary']) or 'none recorded'}")
            if section.get("blank"):
                lines.append(f"- TODO: {section['blank']}")
        elif key.startswith("fair_"):
            for name, state in section.get("per_dataset", {}).items():
                mark = "evidenced" if state["evidenced"] else "NOT evidenced"
                lines.append(f"- **{name}** — {mark}: {state['because']}")
            if not section.get("per_dataset"):
                lines.append("- TODO: no dataset registered yet")
        else:
            if section.get("derived"):
                lines.append(f"- {section['derived']}")
            for item in section.get("restricted", []):
                lines.append(f"- **{item}** is not redistributable; state the access route")
            if section.get("protocol"):
                lines.append(f"- Collection protocol: {section['protocol']}")
            for blank in section.get("blank", []):
                lines.append(f"- TODO: {blank}")
        lines.append("")
    if report["availability_sentences"]:
        lines += ["## Availability statement (derived)", ""]
        lines += [f"{s}" for s in report["availability_sentences"]] + [""]
    if report["no_sentence_written_for"]:
        lines += ["## Datasets no sentence was written for", "",
                  "<!-- Not an omission. A dataset with no verified licence or no "
                  "citation DOI cannot be honestly described here. -->", ""]
        for gap in report["no_sentence_written_for"]:
            lines.append(f"- **{gap['dataset']}** — missing: {', '.join(gap['missing'])}")
        lines.append("")
    return "\n".join(lines)


def load_sections(path: str | None) -> list[str]:
    if not path:
        return list(CORE_SECTIONS)
    p = Path(path)
    if not p.is_file():
        die(f"{path} does not exist — write your funder's section list into it, "
            f"or drop --sections to use the generic Science Europe core")
    try:
        spec = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    sections = spec.get("sections") if isinstance(spec, dict) else spec
    if not isinstance(sections, list) or not sections:
        die(f"{path} needs a non-empty 'sections' array")
    return [str(s) for s in sections]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--datasets", default=DEFAULT_DATASETS)
    ap.add_argument("--runs", default=DEFAULT_RUNS)
    ap.add_argument("--sections", help="your funder's own section list (JSON)")
    ap.add_argument("--write", metavar="FILE", help="render the plan to Markdown")
    ap.add_argument("--check", action="store_true", help="report only the gaps")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    for flag, value in (("--datasets", args.datasets), ("--runs", args.runs)):
        require_within_cwd(value, flag)
    if args.sections:
        require_within_cwd(args.sections, "--sections")
    if args.write:
        require_within_cwd(args.write, "--write")

    datasets = read_jsonl(args.datasets)
    runs = read_jsonl(args.runs)
    report = build(datasets, runs, load_sections(args.sections),
                   Path(DEFAULT_PROTOCOL).is_file())

    if args.check:
        emit({"result": report["result"], "gaps": report["gaps"],
              "no_sentence_written_for": report["no_sentence_written_for"],
              "unevidenced_by_dataset": {
                  d["name"]: d["unevidenced"]
                  for d in report["body"]["data_summary"].get("datasets", [])
                  if d["unevidenced"]},
              "note": report["note"]}, args.json_out)
        sys.exit(0 if report["result"] == "OK" else 2)

    if args.write:
        write_text_atomic(args.write, render_markdown(report))
        report["written"] = Path(args.write).as_posix()
    emit(report, args.json_out)
    sys.exit(0 if report["result"] == "OK" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
