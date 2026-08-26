#!/usr/bin/env python3
"""replication_pack.py — the deposit-ready package, assembled from what is already recorded.

WHY THIS EXISTS
Journals increasingly require a replication package, and the usual one is a zip
of whatever was on the desktop: three scripts, a CSV, no environment, no run
order, and a README written from memory the night before submission. Everything
that package should contain is already recorded in this project — the dataset
register knows the data and its licence, the run register knows the seeds and the
environment, `analysis/` holds the scripts and figures. This assembles it.

WHAT IT REFUSES
- **To redistribute data it was told not to.** A dataset whose record says human
  subjects, PII, or a licence that forbids redistribution is NEVER copied into the
  package. It is listed with its access route instead — which is what an honest
  package does, and the alternative is a data-protection incident with a DOI on it.
- **To claim reproducibility it cannot see.** A package built from runs with no
  environment, or from a register with no seeds, is reported as INCOMPLETE with
  the specific gaps named. "Replication package" is a claim, and this script says
  what is behind it rather than producing a directory that looks convincing.
- **To copy the data at all, by default.** Data files are large, often licensed,
  and usually deposited separately (Zenodo, the host's own DOI). `--build` copies
  code, figures, tables and metadata; the data is manifested with checksums so a
  recipient can verify what they downloaded elsewhere is what the paper used.

USAGE
  python scripts/replication_pack.py            # plan: what would go in, what is missing
  python scripts/replication_pack.py --build    # write exports/replication/

Exit codes: 0 complete · 1 error · 2 assembled, but with gaps that a reader of the
package would notice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (die, emit, read_jsonl, require_within_cwd, unprotect,
                        write_text_atomic)

DEFAULT_OUT = "exports/replication"
# Secondary-review replication material, carried when present. Paths are kept
# verbatim inside the package so a recipient can drop it beside the scripts and
# re-run them unchanged.
REVIEW_RECORDS = ("sources/registry.jsonl", "sources/search-log.jsonl",
                  "sources/venues.jsonl", "evidence/cards.jsonl")
# Everything the review wrote by hand ALONGSIDE those registers: the protocol, the
# per-round search narratives, and the authority files an outside body's limits were
# read from (Invariant 9). Globbed rather than listed, because their names are the
# round's own — a fixed list would silently drop the file a later round adds.
REVIEW_RECORD_GLOBS = ("sources/*.md", "sources/authority/*.md")
CODE_SUFFIXES = (".py", ".r", ".R", ".ipynb", ".sh", ".sql", ".yaml", ".yml", ".toml")
ARTIFACT_DIRS = ("figures", "tables")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def restricted(dataset: dict) -> str | None:
    """Why this dataset must not be copied into a public package, or None."""
    ethics = dataset.get("ethics", {})
    if ethics.get("human_subjects"):
        return "human-subjects data"
    if ethics.get("pii") in ("present", "pseudonymised"):
        return f"personal data ({ethics['pii']})"
    licence = (dataset.get("license") or "unknown").lower()
    if licence == "unknown":
        return "licence unknown — redistribution is not permitted by default"
    if any(token in licence for token in ("nd", "no-derivatives", "research-only",
                                          "non-redistributable")):
        return f"licence {dataset['license']} restricts redistribution"
    return None


def collect(analysis: Path) -> dict:
    code, artifacts = [], []
    if analysis.is_dir():
        for path in sorted(analysis.rglob("*")):
            if not path.is_file() or "data" in path.relative_to(analysis).parts[:1]:
                continue
            if path.suffix in CODE_SUFFIXES:
                code.append(path)
            elif path.parent.name in ARTIFACT_DIRS or path.name in ("captions.md", "RUNLOG.md",
                                                                    "counts.json", "env.json",
                                                                    "splits.json"):
                artifacts.append(path)
    return {"code": code, "artifacts": artifacts}


SECONDARY_TYPES = ("systematic-review", "narrative-review", "scoping-review",
                   "theoretical")


def review_records() -> list[Path]:
    """The review's own replication material that exists, deduplicated and sorted."""
    found = {Path(rel) for rel in REVIEW_RECORDS if Path(rel).is_file()}
    for pattern in REVIEW_RECORD_GLOBS:
        found.update(p for p in Path().glob(pattern) if p.is_file())
    return sorted(found, key=lambda p: p.as_posix())


def paper_type(project: Path) -> str:
    if project.is_file():
        for line in project.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("- **Type:**"):
                value = line.split("**", 2)[-1].strip(": ").strip()
                return re.sub(r"<!--.*?-->", "", value, flags=re.S).strip().lower()
    return ""


def plan(datasets: list[dict], runs: list[dict], analysis: Path, bib: Path,
         secondary: bool = False) -> dict:
    found = collect(analysis)
    includable, referenced = [], []
    for d in datasets:
        reason = restricted(d)
        entry = {"id": d.get("id"), "name": d.get("name"),
                 "license": d.get("license", "unknown"),
                 "doi": (d.get("citation") or {}).get("doi"),
                 "files": [f.get("path") for f in d.get("files", [])]}
        if reason:
            entry["excluded_because"] = reason
            entry["access"] = ("The record above names where it came from; the "
                               "data itself is not copied.")
            referenced.append(entry)
        else:
            includable.append(entry)

    gaps = []
    # A secondary review runs no experiments on data of its own, so an empty run
    # or dataset register is its normal state, not a gap. Reporting it as one
    # trains the reader to skip the gap list — and the gaps that DO matter for a
    # review (a missing search log, an unrecorded exclusion reason) are the ones
    # that would then go unread. What replaces them is checked below.
    if not runs and not secondary:
        gaps.append("no run records — analysis/runs.jsonl is empty or absent, so the "
                    "package cannot state which seeds and configurations produced the "
                    "results (/experiment)")
    if runs and not any(r.get("env") for r in runs):
        gaps.append("no environment recorded on any run — env_capture.py output belongs "
                    "in each run's 'env' field")
    if not found["code"]:
        gaps.append("no analysis code found under analysis/ — a package with no code "
                    "is a data deposit, and should be described as one")
    if not datasets and not secondary:
        gaps.append("no dataset register — the package cannot say what data the results "
                    "came from (/find-dataset, /collect-data)")
    if secondary:
        for rel, why in (("sources/search-log.jsonl",
                          "the searches cannot be re-run as they were run"),
                         ("sources/registry.jsonl",
                          "the include/exclude decisions and their reasons are missing"),
                         ("evidence/cards.jsonl",
                          "the extracted evidence behind the synthesis is missing")):
            if not Path(rel).is_file():
                gaps.append(f"{rel} not found — {why}")
    if not bib.is_file():
        gaps.append(f"{bib.as_posix()} not found — a package normally carries the "
                    f"bibliography of the paper it belongs to")
    return {"code": [p.as_posix() for p in found["code"]],
            "artifacts": [p.as_posix() for p in found["artifacts"]],
            "datasets_included": includable, "datasets_referenced_only": referenced,
            "runs": len(runs), "gaps": gaps,
            "note": ("data files are never copied by --build: they are large, often "
                     "licensed, and normally deposited separately. Their checksums are "
                     "in the manifest so a recipient can verify that what they "
                     "downloaded is what the paper used")}


def readme_text(project: Path, plan_result: dict, runs: list[dict],
                secondary: bool = False) -> str:
    title = "this study"
    if project.is_file():
        for line in project.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("- **Title (working):**"):
                value = line.split("**", 2)[-1].strip(": ").strip()
                # A PROJECT.md title line often carries trailing <!-- ... --> notes
                # recording why the title changed. Those belong to the project file,
                # not to the deposit's README heading — strip them, or the package
                # ships its own revision history as part of the paper's name.
                value = re.sub(r"<!--.*?-->", "", value, flags=re.S).strip()
                if value and value != "TBD":
                    title = value
                break
    seeds = sorted({r.get("seed") for r in runs if r.get("seed") is not None})
    # Only runs that actually recorded an environment count: an empty hash
    # from a run with no `env` would otherwise report "1 environment" for a
    # package that records none.
    envs = {r["env"]["hash"] for r in runs if (r.get("env") or {}).get("hash")}
    lines = [
        f"# Replication package — {title}",
        "",
        "Generated by `scripts/replication_pack.py` from this project's own dataset "
        "and run registers. Every claim below is derived from a record; nothing here "
        "was written from memory.",
        "",
        "## Data",
        "",
    ]
    for d in plan_result["datasets_included"]:
        doi = f" · DOI {d['doi']}" if d.get("doi") else ""
        lines.append(f"- **{d['name']}** ({d['id']}) — licence {d['license']}{doi}. "
                     f"Checksums in `MANIFEST.json`.")
    for d in plan_result["datasets_referenced_only"]:
        lines.append(f"- **{d['name']}** ({d['id']}) — **not included**: "
                     f"{d['excluded_because']}. {d.get('access', '')}")
    if not plan_result["datasets_included"] and not plan_result["datasets_referenced_only"]:
        lines.append("- (no dataset registered)"
                     if not secondary else
                     "- No dataset: this is a secondary review, whose evidence is the "
                     "published literature. What stands in its place is the review's "
                     "own record, below.")
    if secondary:
        shipped = [p.as_posix() for p in review_records()]
        lines += ["", "## The review's record", ""]
        lines += ["The package's replication material is the review's own registers. "
                  "Each is the file the review actually wrote to, not a summary of it:",
                  ""]
        descriptions = {
            "sources/search-log.jsonl": "every query, with its date, source and hit count",
            "sources/registry.jsonl": "every record, its stage and its exclusion reason",
            "sources/venues.jsonl": "the index status claimed for each venue",
            "sources/protocol.md": "the rules, with the dates they were written",
            "evidence/cards.jsonl": "the extracted evidence each claim in the paper binds to",
        }
        def describe(rel: str) -> str:
            if rel in descriptions:
                return descriptions[rel]
            if rel.startswith("sources/authority/"):
                return ("an outside body's own limits, with the URL and the date they "
                        "were read from it")
            return "a search round's narrative, written as it ran"

        lines += [f"- `{rel}` — {describe(rel)}" for rel in shipped]
        if not shipped:
            lines.append("- **(none found)** — see the gaps at the end of this file.")
    lines += [
        "",
        "## Code",
        "",
        "Run in file-name order unless a script header says otherwise:",
        "",
    ]
    lines += [f"- `{p}`" for p in plan_result["code"]] or ["- (no code found)"]
    # A review has no runs, so "0 recorded run(s), seeds —" and "no environment was
    # recorded" are not findings about it; printed anyway they read as two failures
    # in a package that has neither obligation.
    if not secondary:
        lines += [
            "",
            "## Environment",
            "",
            (f"Captured per run by `scripts/env_capture.py`; {len(envs)} distinct "
             f"environment fingerprint(s) across {len(runs)} run(s). See `ENVIRONMENT.json`."
             if envs else
             "**No environment was recorded for any run.** The results in this package "
             "cannot be tied to package versions — see the section below."),
            "",
            "## Runs",
            "",
            f"{len(runs)} recorded run(s), seeds {seeds if seeds else '—'}. Each run's "
            f"dataset, configuration hash, metrics and environment are in `runs.jsonl`.",
        ]
    lines += [
        "",
        "## Verifying what you received",
        "",
        "```bash",
        "python -c \"import hashlib,json,pathlib;"
        "m=json.load(open('MANIFEST.json'));"
        "print([f for f,h in m['files'].items() "
        "if hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest()!=h])\"",
        "```",
        "",
        "An empty list means every file matches the manifest.",
        "",
    ]
    if plan_result["gaps"]:
        lines += ["## What this package does NOT establish", ""]
        lines += [f"- {g}" for g in plan_result["gaps"]] + [""]
    return "\n".join(lines)


def build(out: Path, plan_result: dict, runs: list[dict], datasets: list[dict],
          project: Path, bib: Path, secondary: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    copied, manifest = [], {}

    def _copy(src: Path, dest: Path) -> None:
        # copy2 carries the SOURCE's mode bits. A protected register (references.bib,
        # cards.jsonl) is read-only on disk, so the copy is read-only too and the NEXT
        # build dies with EACCES on its own previous output — the package would be
        # buildable exactly once. Drop the stale copy first, then restore write
        # permission on the new one: inside the deposit these are ordinary files.
        # unprotect() before the unlink, not only after the copy — Windows refuses
        # to DELETE a read-only file at all, so a stale protected copy from the
        # previous build blocks the rebuild even though we never write to it.
        unprotect(dest)
        dest.unlink(missing_ok=True)
        shutil.copy2(src, dest)
        unprotect(dest)

    for rel in plan_result["code"] + plan_result["artifacts"]:
        src = Path(rel)
        dest = out / src.name if src.parent.name in ("analysis",) else out / Path(*src.parts[1:])
        dest.parent.mkdir(parents=True, exist_ok=True)
        _copy(src, dest)
        copied.append(dest.as_posix())
        manifest[dest.relative_to(out).as_posix()] = sha256_of(dest)
    if bib.is_file():
        _copy(bib, out / bib.name)
        copied.append((out / bib.name).as_posix())
        manifest[bib.name] = sha256_of(out / bib.name)

    # A SECONDARY review has no dataset and no runs, but it does have registers,
    # and they are the whole of its replication material: the search log is the
    # search, the registry is every include/exclude decision with its reason, the
    # cards are the extraction. Without them the package for a review is a folder
    # of plotting scripts. Copied here rather than by the caller's shell because
    # their basenames are script-owned (Invariant 6) — the deposit copy is a
    # different file, but only the writer can say so.
    for src in review_records():
        rel = src.as_posix()
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        _copy(src, dest)
        copied.append(dest.as_posix())
        manifest[dest.relative_to(out).as_posix()] = sha256_of(dest)

    # The registers travel with the package: they are what makes it checkable.
    write_text_atomic(out / "runs.jsonl",
                      "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in runs))
    write_text_atomic(out / "datasets.jsonl",
                      "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in datasets))
    environments = {r.get("env", {}).get("hash", "?"): r.get("env", {}) for r in runs
                    if r.get("env")}
    write_text_atomic(out / "ENVIRONMENT.json",
                      json.dumps(environments, indent=2, ensure_ascii=False) + "\n")
    # Data checksums recorded even for files that are not shipped: a recipient who
    # downloads the data elsewhere can prove it is the same bytes.
    data_hashes = {f["path"]: f["sha256"] for d in datasets for f in d.get("files", [])}
    write_text_atomic(out / "MANIFEST.json", json.dumps(
        {"files": manifest, "data_files_not_included": data_hashes}, indent=2) + "\n")
    write_text_atomic(out / "README.md",
                      readme_text(project, plan_result, runs, secondary))
    return {"written": out.as_posix(), "files_copied": len(copied),
            "manifest_entries": len(manifest),
            "data_files_referenced": len(data_hashes)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", action="store_true", help="write the package (default: plan only)")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--datasets", default="analysis/datasets.jsonl")
    ap.add_argument("--runs", default="analysis/runs.jsonl")
    ap.add_argument("--analysis", default="analysis")
    ap.add_argument("--bib", default="bib/references.bib")
    ap.add_argument("--project", default="PROJECT.md")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    for flag, value in (("--out", args.out), ("--datasets", args.datasets),
                        ("--runs", args.runs), ("--analysis", args.analysis),
                        ("--bib", args.bib), ("--project", args.project)):
        require_within_cwd(value, flag)

    datasets = read_jsonl(Path(args.datasets)) if Path(args.datasets).is_file() else []
    runs = read_jsonl(Path(args.runs)) if Path(args.runs).is_file() else []
    analysis = Path(args.analysis)
    if not analysis.is_dir() and not datasets:
        die(f"neither {args.analysis}/ nor {args.datasets} exists — there is no "
            f"analysis here to package")

    ptype = paper_type(Path(args.project))
    secondary = ptype in SECONDARY_TYPES
    result = plan(datasets, runs, analysis, Path(args.bib), secondary)
    result["paper_type"] = ptype or "unknown"
    if args.build:
        result["build"] = build(Path(args.out), result, runs, datasets,
                                Path(args.project), Path(args.bib), secondary)
    result["result"] = "COMPLETE" if not result["gaps"] else "INCOMPLETE"
    emit(result, args.json_out)
    sys.exit(0 if result["result"] == "COMPLETE" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read or write a file — {e}")
