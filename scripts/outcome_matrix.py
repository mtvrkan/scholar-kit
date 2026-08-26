#!/usr/bin/env python3
"""outcome_matrix.py — programme outcome ↔ course outcome ↔ assessment, both directions.

WHY THIS EXISTS
An accreditation visit (MÜDEK, ABET, and every institutional review that copies
them) asks one question in three forms: is every programme outcome measured
somewhere, is every course outcome serving something, and is every claimed
contribution backed by an assessment that actually produces a number.

Departments answer it with a spreadsheet that is filled in once, drifts as
courses change, and is repaired the week before the visit. The failure is always
the same shape — a programme outcome nobody assesses, a course outcome mapped to
nothing, a contribution level declared for an outcome the course never assesses.
All three are graph problems.

WHAT IT REFUSES
- **To know your programme's outcomes.** They come from
  `teaching/program-outcomes.json`, filled from your programme's own document.
  There is no built-in list of MÜDEK or ABET outcomes here: they are revised, they
  differ by discipline, and a remembered outcome text on an accreditation form is
  worse than a blank one. No file ⇒ UNCHECKED.
- **To rate a contribution.** A course declares its own contribution level. This
  reports the levels that are outside the declared scale, and the ones declared
  for an outcome the course does not assess — never whether a 3 should be a 2.
- **To average.** A "programme outcome achievement" number computed by averaging
  contribution levels is a number with no unit, and it is not produced here.

USAGE
  python scripts/outcome_matrix.py --syllabus teaching/syllabus.json
  python scripts/outcome_matrix.py --syllabus teaching/*.json --matrix markdown

Exit codes: 0 clean · 1 error · 2 findings or UNCHECKED.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd

DEFAULT_PROGRAMME = "teaching/program-outcomes.json"


def load_programme(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(spec, dict):
        die(f"{path} must hold a JSON object")
    if not spec.get("source_url") and not spec.get("source_document"):
        die(f"{path} has no 'source_url' or 'source_document' — a programme outcome "
            f"list with no source is a remembered list, and an accreditation form "
            f"built on one is worse than a blank one")
    if not isinstance(spec.get("outcomes"), list) or not spec["outcomes"]:
        die(f"{path} needs a non-empty 'outcomes' array")
    return spec


def load_syllabus(path: Path) -> dict:
    if not path.is_file():
        die(f"{path} does not exist")
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(spec, dict):
        die(f"{path} must hold a JSON object")
    return spec


def build(programme: dict | None, syllabi: list[tuple[str, dict]]) -> dict:
    prog_ids = [o.get("id") for o in (programme or {}).get("outcomes") or []]
    scale = (programme or {}).get("contribution_scale") or [1, 2, 3]
    problems = []
    cells: dict[str, dict[str, dict]] = {}   # course -> programme outcome -> cell
    served: set[str] = set()

    for course_key, syllabus in syllabi:
        course = (syllabus.get("course") or {}).get("code") or course_key
        outcomes = syllabus.get("outcomes") or []
        assessment = syllabus.get("assessment") or []
        assessed = {o for item in assessment for o in (item.get("outcomes") or [])}
        cells[course] = {}
        for oc in outcomes:
            oid = oc.get("id", "?")
            mapped = oc.get("programme_outcomes") or []
            if not mapped:
                problems.append(f"{course}/{oid}: maps to no programme outcome — a "
                                f"course outcome serving nothing is either missing "
                                f"from the map or missing a reason")
            for entry in mapped:
                # Either "PÇ1" or {"id": "PÇ1", "level": 3}
                pid = entry.get("id") if isinstance(entry, dict) else entry
                level = entry.get("level") if isinstance(entry, dict) else None
                if prog_ids and pid not in prog_ids:
                    problems.append(f"{course}/{oid}: names unknown programme outcome "
                                    f"{pid!r}")
                    continue
                if level is not None and level not in scale:
                    problems.append(f"{course}/{oid}→{pid}: contribution level {level} "
                                    f"is outside the declared scale {scale}")
                if oid not in assessed:
                    problems.append(f"{course}/{oid}→{pid}: contributes to a programme "
                                    f"outcome but is assessed by nothing in this course "
                                    f"— a contribution no assessment produces a number "
                                    f"for is a claim, not a measurement")
                served.add(pid)
                cell = cells[course].setdefault(pid, {"course_outcomes": [], "levels": []})
                cell["course_outcomes"].append(oid)
                if level is not None:
                    cell["levels"].append(level)

    uncovered = [p for p in prog_ids if p not in served]
    if uncovered:
        problems.append(f"programme outcome(s) {uncovered} are served by no course "
                        f"outcome in the syllabi given — either a course is missing "
                        f"from this run, or nothing measures them")

    return {
        "programme": (programme or {}).get("programme"),
        "programme_source": ((programme or {}).get("source_url") or
                             (programme or {}).get("source_document")),
        "programme_outcomes": prog_ids,
        "contribution_scale": scale,
        "courses": sorted(cells),
        "matrix": cells,
        "uncovered_programme_outcomes": uncovered,
        "problems": problems,
        "note": ("coverage in both directions, and nothing else. No achievement "
                 "percentage is computed: an average of contribution levels is a "
                 "number with no unit"),
    }


def render_matrix(report: dict, fmt: str) -> str:
    prog = report["programme_outcomes"]
    courses = report["courses"]
    if not prog or not courses:
        return "(nothing to render — no programme outcomes or no syllabi)"
    header = "| Course | " + " | ".join(prog) + " |"
    sep = "|---|" + "---|" * len(prog)
    lines = [header, sep]
    for course in courses:
        row = [course]
        for pid in prog:
            cell = report["matrix"][course].get(pid)
            if not cell:
                row.append("")
            elif cell["levels"]:
                row.append(f"{max(cell['levels'])} ({','.join(cell['course_outcomes'])})")
            else:
                row.append(",".join(cell["course_outcomes"]))
        lines.append("| " + " | ".join(row) + " |")
    if fmt == "latex":
        cols = "l" + "c" * len(prog)
        body = "\n".join(line.strip("|").replace("|", "&").strip() + r" \\"
                         for line in lines if not line.startswith("|---"))
        return (f"\\begin{{tabular}}{{{cols}}}\n\\hline\n{body}\n\\hline\n"
                f"\\end{{tabular}}\n")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--syllabus", nargs="+", default=["teaching/syllabus.json"],
                    help="one or more syllabus JSON files")
    ap.add_argument("--programme", default=DEFAULT_PROGRAMME)
    ap.add_argument("--matrix", choices=("markdown", "latex"),
                    help="render the matrix instead of the report")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.programme, "--programme")
    syllabi = []
    for rel in args.syllabus:
        require_within_cwd(rel, "--syllabus")
        syllabi.append((Path(rel).stem, load_syllabus(Path(rel))))

    programme = load_programme(Path(args.programme))
    report = build(programme, syllabi)

    if args.matrix:
        print(render_matrix(report, args.matrix))
        return

    report["result"] = "OK" if not report["problems"] else "FINDINGS"
    if programme is None:
        report["result"] = "UNCHECKED"
        report["note"] = (
            f"no {args.programme} — the course outcomes were read, but nothing was "
            f"checked against a programme. Fill it from your programme's own outcome "
            f"document; this kit ships no MÜDEK or ABET outcome list.")
    emit(report, args.json_out)
    sys.exit(0 if report["result"] == "OK" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
