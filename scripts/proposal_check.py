#!/usr/bin/env python3
"""proposal_check.py — the arithmetic and the graph inside a grant proposal, and the report that follows it.

WHY THIS EXISTS
A proposal is rejected for two different kinds of reason. The first is that the
idea did not convince anyone, and nothing here touches that. The second is that
the objectives do not map onto the work packages, a deliverable falls outside the
project's own duration, the budget lines do not sum to the total, or the
personnel figure and the person-months describe two different projects. Reviewers
find all four, every round, and every one of them is arithmetic or a graph.

The same shape returns at reporting time: planned work packages against what
actually happened, where "what actually happened" is already recorded in this
project's run, dataset and source registers.

WHAT IT REFUSES
- **To know the call.** Section names, character limits and the project's duration
  come from `call-fields.json`, which YOU fill from the call text with the URL you
  read it at. No file ⇒ `UNCHECKED`, not `OK`. "TÜBİTAK 1001 allows N pages" is a
  remembered limit and belongs to the same error class as a remembered DOI.
- **To judge fundability.** Whether the idea is worth funding, whether the budget
  is proportionate, whether the team is right — none of it is here.
- **To invent a number.** A budget line with no amount is reported, never
  estimated. A person-month rate that was not given is not assumed.
- **To explain away slippage.** `--report` shows planned against actual. It writes
  no reason for a gap; the reason is the researcher's to give.

USAGE
  python scripts/proposal_check.py --check
  python scripts/proposal_check.py --gantt markdown
  python scripts/proposal_check.py --report            # progress / final report

Exit codes: 0 clean · 1 error · 2 findings or UNCHECKED.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd, transliterate
from word_budget import count_words

DEFAULT_DIR = "proposal"
PLACEHOLDER_RE = re.compile(r"(<[^>\n]{2,60}>|\bTODO\b|\bTBD\b|X{3,}|_{4,}|\.{4,})")


def _fold(text: str) -> str:
    return transliterate(text).lower()


def _load(path: Path, what: str, required: tuple[str, ...] = (),
          need_source: bool = False, need_list: str | None = None) -> dict | None:
    if not path.is_file():
        return None
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(spec, dict):
        die(f"{path} must hold a JSON object")
    if need_source and not spec.get("source_url"):
        die(f"{path} has no 'source_url' — {what} with no source is a remembered "
            f"{what}, and this file exists so nothing is remembered")
    missing = [k for k in required if k not in spec]
    if missing:
        die(f"{path} is missing {', '.join(missing)}")
    if need_list and (not isinstance(spec.get(need_list), list) or not spec[need_list]):
        # Without this, a call file carrying only a source_url passed validation
        # and then checked ZERO narrative sections while reporting `OK` — the
        # authority file existed, so the run never fell back to UNCHECKED either.
        # Every other authority file in the kit requires its list; this one was
        # the exception.
        die(f"{path} needs a non-empty '{need_list}' array — the sections the call "
            f"actually asks for. A call file with no field list checks nothing and "
            f"would report OK for doing so")
    return spec


def sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"^#{1,6}[ \t]*(.+?)[ \t]*$", text, flags=re.M)
    return [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def check_narrative(text: str, call: dict | None) -> dict:
    """Each section the call asks for: present, answered, and within its limit.

    Limits are applied in the unit the call states them in — `max_chars` or
    `max_words`, never converted from pages, because a page is a typesetting
    fact and this script cannot see the typesetting.
    """
    fields = (call or {}).get("fields") or []
    found = [(_fold(h), b) for h, b in sections(text)]
    rows, problems = [], []
    for field in fields:
        name = field if isinstance(field, str) else field.get("name", "")
        spec = {} if isinstance(field, str) else field
        label = _fold(str(name).replace("_", " ")).strip()
        if not label:
            # An entry with no name would match the FIRST section (every string
            # contains ""), silently reporting a random section as that field's
            # answer. Named as a malformed entry instead.
            problems.append(f"call-fields entry {field!r} has no 'name' — it cannot "
                            f"be matched to a section")
            rows.append({"field": None, "present": False, "malformed": True})
            continue
        body = next((b for h, b in found if label in h), None)
        row = {"field": name, "present": body is not None}
        if body is None:
            rows.append(row)
            problems.append(f"no section for '{name}'")
            continue
        stripped = body.strip()
        row["chars"], row["words"] = len(stripped), count_words(stripped)
        if not stripped:
            problems.append(f"'{name}' has a heading and nothing under it")
        elif PLACEHOLDER_RE.search(stripped):
            row["placeholder"] = True
            problems.append(f"'{name}' still holds a placeholder")
        for key, unit in (("max_chars", "chars"), ("max_words", "words")):
            cap = spec.get(key)
            if cap and row.get(unit, 0) > cap:
                row["over"] = True
                problems.append(f"'{name}' is {row[unit]} {unit}, the call allows {cap}")
        rows.append(row)
    return {"fields": rows, "problems": problems}


def check_workpackages(wp_spec: dict | None, duration: int | None) -> dict:
    """The graph a reviewer walks: objective → work package → deliverable.

    Both directions are checked. An objective no work package serves is a promise
    with no work behind it; a work package serving no objective is work with no
    reason, and reviewers name both.
    """
    if not wp_spec:
        return {"problems": ["proposal/workpackages.json not found"], "workpackages": []}
    wps = wp_spec.get("workpackages") or []
    objectives = wp_spec.get("objectives") or []
    duration = duration or wp_spec.get("duration_months")
    problems, rows = [], []

    obj_ids = [o.get("id") for o in objectives if isinstance(o, dict)]
    dupes = sorted({i for i in obj_ids if obj_ids.count(i) > 1})
    if dupes:
        problems.append(f"objective ids repeated: {dupes}")
    served: set[str] = set()
    all_ids: list[str] = []

    for wp in wps:
        wid = wp.get("id", "?")
        start, end = wp.get("start_month"), wp.get("end_month")
        pm = wp.get("person_months") or {}
        total_pm = sum(v for v in pm.values() if isinstance(v, (int, float)))
        wp_objs = wp.get("objectives") or []
        served.update(wp_objs)
        deliverables = wp.get("deliverables") or []
        milestones = wp.get("milestones") or []
        all_ids += [d.get("id") for d in deliverables] + [m.get("id") for m in milestones]

        row = {"id": wid, "title": wp.get("title"), "start_month": start,
               "end_month": end, "person_months": total_pm,
               "objectives": wp_objs, "deliverables": len(deliverables),
               "milestones": len(milestones)}
        if not isinstance(start, int) or not isinstance(end, int):
            problems.append(f"{wid}: start_month/end_month must be integers")
        else:
            if start > end:
                problems.append(f"{wid}: starts in month {start} and ends in month {end}")
            if start < 1:
                problems.append(f"{wid}: starts in month {start} — months are 1-based")
            if duration and end > duration:
                problems.append(f"{wid}: ends in month {end}, the project lasts "
                                f"{duration} months")
        if not wp_objs:
            problems.append(f"{wid}: serves no objective — work with no stated reason")
        else:
            unknown = [o for o in wp_objs if obj_ids and o not in obj_ids]
            if unknown:
                problems.append(f"{wid}: references unknown objective(s) {unknown}")
        if not deliverables:
            problems.append(f"{wid}: has no deliverable — a work package with no output "
                            f"cannot be reported on")
        if total_pm <= 0:
            problems.append(f"{wid}: zero person-months")
        for item, kind in ([(d, "deliverable") for d in deliverables] +
                           [(m, "milestone") for m in milestones]):
            month = item.get("month")
            if not isinstance(month, int):
                problems.append(f"{wid}/{item.get('id', '?')}: {kind} has no integer month")
                continue
            if duration and month > duration:
                problems.append(f"{item.get('id', '?')}: {kind} due in month {month}, "
                                f"outside the project's {duration} months")
            elif isinstance(start, int) and isinstance(end, int) and not start <= month <= end:
                problems.append(f"{item.get('id', '?')}: {kind} due in month {month}, "
                                f"outside {wid}'s months {start}-{end}")
        rows.append(row)

    orphan_objectives = [o for o in obj_ids if o not in served]
    if orphan_objectives:
        problems.append(f"objective(s) {orphan_objectives} are served by no work package")
    id_dupes = sorted({i for i in all_ids if i and all_ids.count(i) > 1})
    if id_dupes:
        problems.append(f"deliverable/milestone ids repeated: {id_dupes}")

    return {"duration_months": duration, "objectives": obj_ids,
            "workpackages": rows, "orphan_objectives": orphan_objectives,
            "total_person_months": sum(r["person_months"] for r in rows),
            "problems": problems}


def check_budget(budget: dict | None, person_months: float) -> dict:
    """Sums, justifications, and the one inconsistency reviewers reliably find:
    a personnel figure that does not follow from the person-months."""
    if not budget:
        return {"problems": ["proposal/budget.json not found"], "lines": []}
    lines = budget.get("lines") or []
    problems = []
    total_declared = budget.get("total")
    amounts = []
    for line in lines:
        amount = line.get("amount")
        if not isinstance(amount, (int, float)):
            problems.append(f"budget line {line.get('item', '?')!r} has no numeric amount")
            continue
        amounts.append(amount)
        if not str(line.get("justification", "")).strip():
            problems.append(f"budget line {line.get('item', '?')!r} has no justification — "
                            f"an unjustified line is the first one cut")
    computed = sum(amounts)
    if isinstance(total_declared, (int, float)) and round(computed, 2) != round(total_declared, 2):
        problems.append(f"budget lines sum to {computed}, the declared total is "
                        f"{total_declared} (difference {round(total_declared - computed, 2)})")

    # The personnel-vs-person-months comparison lives in personnel_consistency():
    # it needs the work packages, which this function deliberately does not see.
    return {"lines": len(lines), "computed_total": computed,
            "declared_total": total_declared,
            "currency": budget.get("currency"),
            "person_months": person_months,
            "problems": problems}


def personnel_consistency(wp_spec: dict | None, budget: dict | None) -> dict:
    """person-months × rate, per role, against the declared personnel line."""
    if not wp_spec or not budget:
        return {"checked": False}
    rates = budget.get("personnel_rate_per_month") or {}
    if not rates:
        return {"checked": False,
                "why": "budget.json states no personnel_rate_per_month — nothing to "
                       "compare the person-months against, and a rate is not assumed"}
    per_role: dict[str, float] = {}
    for wp in wp_spec.get("workpackages") or []:
        for role, months in (wp.get("person_months") or {}).items():
            if isinstance(months, (int, float)):
                per_role[role] = per_role.get(role, 0) + months
    expected = sum(per_role.get(role, 0) * rate for role, rate in rates.items())
    declared = next((line.get("amount") for line in budget.get("lines") or []
                     if _fold(str(line.get("item", ""))).startswith(("personel", "personnel",
                                                                    "staff", "salary"))), None)
    unpriced = sorted(set(per_role) - set(rates))
    out = {"checked": True, "person_months_by_role": per_role,
           "expected_from_rates": round(expected, 2), "declared_personnel_line": declared,
           "roles_with_no_rate": unpriced, "problems": []}
    if unpriced:
        out["problems"].append(f"role(s) {unpriced} have person-months but no rate — "
                               f"the personnel figure cannot be derived for them")
    if isinstance(declared, (int, float)) and round(declared, 2) != round(expected, 2):
        out["problems"].append(
            f"personnel line is {declared}, but {sum(per_role.values())} person-months "
            f"at the stated rates come to {round(expected, 2)} — one of the two is "
            f"describing a different project")
    return out


def gantt(wp_spec: dict, fmt: str) -> str:
    wps = wp_spec.get("workpackages") or []
    longest = max((wp.get("end_month") or 0) for wp in wps) if wps else 0
    duration = wp_spec.get("duration_months") or longest
    if fmt == "latex":
        rows = []
        for wp in wps:
            start, end = wp.get("start_month", 1), wp.get("end_month", 1)
            rows.append(f"  \\ganttbar{{{wp.get('id')}: {wp.get('title', '')}}}"
                        f"{{{start}}}{{{end}}} \\\\")
        # Built by concatenation, not %-formatting: the LaTeX comment marker is
        # itself a '%', and "% requires" parses as the %r conversion.
        return ("% requires \\usepackage{pgfgantt}\n"
                f"\\begin{{ganttchart}}[vgrid, hgrid, x unit=0.35cm]{{1}}{{{duration}}}\n"
                f"  \\gantttitle{{Months}}{{{duration}}} \\\\\n"
                f"  \\gantttitlelist{{1,...,{duration}}}{{1}} \\\\\n"
                + "\n".join(rows) + "\n\\end{ganttchart}\n")
    lines = [f"| WP | Title | {' | '.join(str(m) for m in range(1, duration + 1))} |",
             f"|---|---|{'---|' * duration}"]
    for wp in wps:
        start, end = wp.get("start_month", 1), wp.get("end_month", 1)
        cells = ["█" if start <= m <= end else "" for m in range(1, duration + 1)]
        lines.append(f"| {wp.get('id')} | {wp.get('title', '')} | {' | '.join(cells)} |")
    return "\n".join(lines)


def progress(wp_spec: dict | None, done: dict | None, runs: list[dict],
             datasets: list[dict], sources: list[dict], drafts: Path) -> dict:
    """Planned against actual. The actual side is derived where a register holds
    it and declared where only you know it — and a deliverable nobody reported on
    is 'not reported', never 'incomplete'. Those are different claims."""
    reported = {k: v for k, v in ((done or {}).get("deliverables") or {}).items()}
    rows, problems = [], []
    if not (wp_spec or {}).get("workpackages"):
        # A progress report with no plan behind it has nothing to be against, and
        # reporting OK for that is the same silence-reads-as-pass shape the rest of
        # this file refuses. The SKILL states the gate; nothing enforced it.
        return {"deliverables": [], "derived_from_registers": {},
                "problems": ["proposal/workpackages.json holds no work packages — a "
                             "progress report is the plan with an outcome attached, "
                             "and there is no plan to report against. Transcribe the "
                             "proposal's work plan into that file first"],
                "note": "nothing was compared"}
    for wp in (wp_spec or {}).get("workpackages") or []:
        for d in wp.get("deliverables") or []:
            did = d.get("id")
            state = reported.get(did)
            row = {"id": did, "workpackage": wp.get("id"), "title": d.get("title"),
                   "planned_month": d.get("month"),
                   "reported": bool(state), "completed_month": (state or {}).get("month"),
                   "evidence": (state or {}).get("evidence")}
            if state and isinstance(state.get("month"), int) and isinstance(d.get("month"), int):
                row["slippage_months"] = state["month"] - d["month"]
            if not state:
                problems.append(f"{did}: not reported — say whether it is done, late or "
                                f"dropped; 'not reported' is not 'complete'")
            rows.append(row)
    derived = {
        "runs_recorded": len(runs),
        "datasets_registered": len(datasets),
        "sources_registered": len(sources),
        "draft_files": len(list(drafts.glob("*.md"))) if drafts.is_dir() else 0,
    }
    return {"deliverables": rows, "derived_from_registers": derived,
            "problems": problems,
            "note": ("planned against actual. No reason is written for a gap — that "
                     "is yours, and a report that explains slippage before stating it "
                     "is the one nobody believes")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--gantt", choices=("markdown", "latex"))
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--runs", default="analysis/runs.jsonl")
    ap.add_argument("--datasets", default="analysis/datasets.jsonl")
    ap.add_argument("--registry", default="sources/registry.jsonl")
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    if sum(map(bool, (args.check, args.gantt, args.report))) != 1:
        die("pick exactly one: --check, --gantt <markdown|latex> or --report")
    for flag, value in (("--dir", args.dir), ("--runs", args.runs),
                        ("--datasets", args.datasets), ("--registry", args.registry),
                        ("--drafts", args.drafts)):
        require_within_cwd(value, flag)

    root = Path(args.dir)
    call = _load(root / "call-fields.json", "a call limit", need_source=True,
                 need_list="fields")
    wp_spec = _load(root / "workpackages.json", "a work-package plan")
    budget = _load(root / "budget.json", "a budget")

    if args.gantt:
        if not wp_spec:
            die(f"{root / 'workpackages.json'} does not exist — there is nothing to chart")
        print(gantt(wp_spec, args.gantt))
        return

    if args.report:
        report = progress(wp_spec, _load(root / "progress.json", "a progress record"),
                          read_jsonl(args.runs), read_jsonl(args.datasets),
                          read_jsonl(args.registry), Path(args.drafts))
        report["result"] = "OK" if not report["problems"] else "FINDINGS"
        emit(report, args.json_out)
        sys.exit(0 if report["result"] == "OK" else 2)

    narrative_path = root / "proposal.md"
    narrative = (narrative_path.read_text(encoding="utf-8", errors="replace")
                 if narrative_path.is_file() else "")
    wps = check_workpackages(wp_spec, (call or {}).get("duration_months"))
    report = {
        "call_source": (call or {}).get("source_url"),
        "narrative": (check_narrative(narrative, call) if narrative else
                      {"problems": [f"{narrative_path} not found"]}),
        "workpackages": wps,
        "budget": check_budget(budget, wps.get("total_person_months", 0)),
        "personnel": personnel_consistency(wp_spec, budget),
    }
    problems = []
    for key, section in report.items():
        if isinstance(section, dict):
            problems.extend({key: p} for p in section.get("problems", []))
    report["problems"] = problems
    report["result"] = "OK" if not problems else "FINDINGS"
    if call is None:
        report["result"] = "UNCHECKED"
        report["note"] = (
            f"no {root / 'call-fields.json'} — the work packages and budget were "
            f"checked against themselves, but no section name, character limit or "
            f"project duration came from the call. Fill it from the call text; this "
            f"kit will not recall a funder's limits.")
    emit(report, args.json_out)
    sys.exit(0 if report["result"] == "OK" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
