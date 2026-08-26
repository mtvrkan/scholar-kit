#!/usr/bin/env python3
"""syllabus_check.py — the arithmetic and the coverage inside a syllabus, an exam and a rubric.

WHY THIS EXISTS
Teaching documents fail in exactly the ways a script can catch. Assessment
weights that sum to 95. A learning outcome nothing on the exam measures. An exam
question serving an outcome the syllabus does not have. A workload table that
says 240 hours for a 6-ECTS course. A rubric whose four levels differ only by an
adverb — "excellent / good / adequate / poor" — which is not a rubric, it is a
grade with extra steps.

None of that is pedagogy, and all of it gets found by an accreditation visit.

WHAT IT REFUSES
- **To write outcomes.** It reports that "öğrenci konuyu anlar" is not measurable
  and names the verb families that are. Which outcome the course should have is
  the instructor's.
- **To grade a descriptor.** The rubric check reports levels that are not
  observably different; whether the difference it finds is the right one is a
  teaching judgement.
- **To know your institution's ECTS rule.** The Bologna range (25-30 hours per
  credit) is a published standard and is applied as a RANGE; a single institutional
  number goes in the course object.
- **To convert.** A weight stated in points is not turned into a percentage, and
  a workload stated in weeks is not turned into hours.

USAGE
  python scripts/syllabus_check.py                       # teaching/syllabus.json
  python scripts/syllabus_check.py --exam teaching/exam.json
  python scripts/syllabus_check.py --rubric teaching/rubric.json

Exit codes: 0 clean · 1 error · 2 findings.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cite_audit import extract_citations
from lib_common import die, emit, parse_bibtex, require_within_cwd, transliterate

DEFAULT_SYLLABUS = "teaching/syllabus.json"

# Bologna: one ECTS credit is 25-30 hours of student workload. A published
# range, applied as a range — a single number is an institutional choice and
# goes in the course object as `ects_hours_per_credit`.
ECTS_HOURS_MIN, ECTS_HOURS_MAX = 25, 30

# Verbs that name something an examiner can observe, by Bloom level. Both
# languages, because a Turkish syllabus is written in Turkish and a check that
# only knows English verbs reports every outcome as unmeasurable.
BLOOM_VERBS = {
    "remember": {"en": ("define", "list", "recall", "name", "state", "identify"),
                 "tr": ("tanimla", "listele", "sirala", "adlandir", "belirt")},
    "understand": {"en": ("explain", "describe", "summarise", "summarize", "classify",
                          "interpret"),
                   "tr": ("acikla", "ozetle", "siniflandir", "yorumla")},
    "apply": {"en": ("apply", "use", "implement", "solve", "compute", "calculate",
                     "demonstrate"),
              "tr": ("uygula", "kullan", "coz", "hesapla", "gerceklestir")},
    "analyze": {"en": ("analyse", "analyze", "compare", "differentiate", "examine",
                       "distinguish"),
                "tr": ("analiz", "karsilastir", "ayirt", "incele", "cozumle")},
    "evaluate": {"en": ("evaluate", "assess", "justify", "critique", "select", "defend"),
                 "tr": ("degerlendir", "savun", "sec", "elestir", "yargila")},
    "create": {"en": ("design", "develop", "construct", "formulate", "produce", "compose"),
               "tr": ("tasarla", "gelistir", "olustur", "uret", "kur")},
}

# The two languages need different matching and an earlier version used one rule
# for both, with a prefix match that made "useful" read as *apply*, "namely" as
# *remember* and "statement" as *remember*. An unmeasurable outcome passing as
# measurable is a false negative on this file's whole purpose.
#
# English: the verb plus an inflection, and nothing else — `use` must not match
# `useful`. Turkish: agglutinative, so an open suffix is required — one stem
# covers `uygular`, `uygulayabilir`, `uygulamayı`.
_EN_SUFFIX = r"(?:s|es|d|ed|ing)?"


def _en_pattern(verb: str) -> str:
    """`apply` has to match `applies`, which is not `apply` + a suffix. Verbs
    ending in `y` get the y→ie forms explicitly; everything else takes the plain
    inflections. Without this, "Applies the method" read as having no Bloom verb
    at all — the opposite error to the one the bounded match was fixing."""
    if verb.endswith("y"):
        stem = re.escape(verb[:-1])
        return rf"\b{stem}(?:y|ys|ying|ies|ied)\b"
    return rf"\b{re.escape(verb)}{_EN_SUFFIX}\b"

# What a learning outcome says when it has not been written yet. Each is a state
# of mind rather than an observable act, which is why nobody can build an exam
# question from one.
UNMEASURABLE = ("understand", "know", "learn", "appreciate", "be aware", "be familiar",
                "anlar", "bilir", "kavrar", "ogrenir", "farkinda", "asina", "haberdar")

# Adverbs that make a rubric read as differentiated when it is not.
INTENSITY = ("excellent", "very good", "good", "adequate", "fair", "poor", "weak",
             "outstanding", "satisfactory", "unsatisfactory", "partially", "fully",
             "mukemmel", "cok iyi", "iyi", "orta", "yeterli", "yetersiz", "zayif",
             "kismen", "tam", "az", "cok")


def _fold(text: str) -> str:
    return transliterate(str(text)).lower()


def load(path: Path, what: str) -> dict:
    if not path.is_file():
        die(f"{path} does not exist — write the {what} first "
            f"(see the /syllabus skill for its shape)")
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg}")
    if not isinstance(spec, dict):
        die(f"{path} must hold a JSON object")
    return spec


def bloom_of(text: str) -> str | None:
    """The HIGHEST Bloom level expressed in `text`, not the first one matched.

    An outcome names the level of its most demanding verb: "Sınıflandırma
    algoritmalarını **uygular**" is an *apply* outcome, even though the noun
    "sınıflandırma" shares a stem with *classify*. First-match returned
    `understand` for it, because that level is simply earlier in the table —
    which made the answer depend on dictionary order rather than on the outcome.

    This is the same rule `claim_check.rung_of` applies to the claim-strength
    ladder, for the same reason.
    """
    folded = _fold(text)
    best = None
    for i, (level, verbs) in enumerate(BLOOM_VERBS.items()):
        hit = (any(re.search(_en_pattern(v), folded) for v in verbs["en"])
               or any(re.search(rf"\b{re.escape(v)}\w*", folded) for v in verbs["tr"]))
        if hit and (best is None or i > best[0]):
            best = (i, level)
    return best[1] if best else None


def check_outcomes(outcomes: list[dict]) -> dict:
    rows, problems = [], []
    seen = []
    if not outcomes:
        # Every other check here is relative to the outcome list. With none, the
        # assessment, week and exam checks all pass by having nothing to compare
        # against, and the run reports OK for a syllabus that promises nothing.
        return {"outcomes": [], "problems": [
            "no learning outcomes — every other check on this syllabus is relative "
            "to them, so an empty list makes the whole run pass by vacancy"]}
    for oc in outcomes:
        oid = oc.get("id", "?")
        seen.append(oid)
        text = str(oc.get("text", ""))
        folded = _fold(text)
        vague = [w for w in UNMEASURABLE
                 if re.search(rf"\b{re.escape(_fold(w))}\b", folded)]
        detected = bloom_of(text)
        declared = str(oc.get("bloom", "")).lower() or None
        row = {"id": oid, "declared_bloom": declared, "verb_suggests": detected,
               "unmeasurable_verbs": vague}
        if vague and not detected:
            problems.append(f"{oid}: {vague[0]!r} names a state of mind, not an act an "
                            f"examiner can observe — no exam question can be built from "
                            f"it. Measurable families: {', '.join(BLOOM_VERBS)}")
        elif not detected:
            problems.append(f"{oid}: no recognised Bloom verb — an outcome nobody can "
                            f"assess is an outcome nobody can accredit")
        if declared and detected and declared != detected:
            row["mismatch"] = True
            problems.append(f"{oid}: declared as '{declared}' but the verb reads as "
                            f"'{detected}' — one of the two is what the exam will test")
        rows.append(row)
    dupes = sorted({o for o in seen if seen.count(o) > 1})
    if dupes:
        problems.append(f"outcome ids repeated: {dupes}")
    return {"outcomes": rows, "problems": problems}


def check_assessment(assessment: list[dict], outcome_ids: list[str]) -> dict:
    problems = []
    weights = []
    assessed: set[str] = set()
    for item in assessment:
        w = item.get("weight")
        name = item.get("name", "?")
        if not isinstance(w, (int, float)):
            problems.append(f"assessment {name!r} has no numeric weight")
        else:
            weights.append(w)
        mapped = item.get("outcomes") or []
        assessed.update(mapped)
        if not mapped:
            problems.append(f"assessment {name!r} measures no stated outcome — it is "
                            f"marks with no declared purpose")
        unknown = [o for o in mapped if o not in outcome_ids]
        if unknown:
            problems.append(f"assessment {name!r} names unknown outcome(s) {unknown}")
    total = round(sum(weights), 4)
    if weights and total != 100:
        problems.append(f"assessment weights sum to {total}, not 100")
    unassessed = [o for o in outcome_ids if o not in assessed]
    if unassessed:
        problems.append(f"outcome(s) {unassessed} are assessed by nothing")
    return {"total_weight": total, "unassessed_outcomes": unassessed,
            "problems": problems}


def check_weeks(weeks: list[dict], outcome_ids: list[str]) -> dict:
    problems = []
    numbers = [w.get("week") for w in weeks]
    if numbers and numbers != list(range(1, len(numbers) + 1)):
        problems.append(f"week numbering is {numbers}, expected 1..{len(numbers)}")
    taught: set[str] = set()
    for w in weeks:
        mapped = w.get("outcomes") or []
        taught.update(mapped)
        unknown = [o for o in mapped if o not in outcome_ids]
        if unknown:
            problems.append(f"week {w.get('week')} names unknown outcome(s) {unknown}")
    untaught = [o for o in outcome_ids if o not in taught]
    if untaught:
        problems.append(f"outcome(s) {untaught} appear in no week — assessed but "
                        f"never taught is the shape students notice first")
    return {"weeks": len(weeks), "untaught_outcomes": untaught, "problems": problems}


def check_workload(workload: list[dict], ects, per_credit=None) -> dict:
    problems = []
    total = 0.0
    for row in workload:
        count, hours = row.get("count"), row.get("hours")
        if not isinstance(count, (int, float)) or not isinstance(hours, (int, float)):
            problems.append(f"workload row {row.get('activity', '?')!r} needs numeric "
                            f"'count' and 'hours'")
            continue
        total += count * hours
    out = {"total_hours": round(total, 2), "ects": ects}
    if not isinstance(ects, (int, float)) or not workload:
        # Said out loud rather than left as a quiet `checked: false` nobody reads:
        # a workload table with no ECTS beside it was measured against nothing.
        problems.append(
            "workload was not checked — " +
            ("the course object states no numeric 'ects'" if workload else
             "there is no workload table") +
            ", so the hours were measured against nothing")
        return {**out, "problems": problems, "checked": False}
    if per_credit:
        expected = ects * per_credit
        out["expected_hours"] = expected
        if round(total) != round(expected):
            problems.append(f"workload is {round(total)} hours; {ects} ECTS at your "
                            f"institution's {per_credit} h/credit is {round(expected)}")
    else:
        low, high = ects * ECTS_HOURS_MIN, ects * ECTS_HOURS_MAX
        out["bologna_range"] = [low, high]
        if not low <= total <= high:
            problems.append(f"workload is {round(total)} hours; {ects} ECTS is "
                            f"{low}-{high} hours under the Bologna range. Set "
                            f"'ects_hours_per_credit' in the course object if your "
                            f"institution fixes a single figure")
    return {**out, "problems": problems, "checked": True}


def check_readings(weeks: list[dict], bib_path: Path) -> dict:
    keys: set[str] = set()
    for w in weeks:
        keys |= extract_citations(str(w.get("reading", "")))
    if not keys:
        return {"keys": [], "problems": []}
    if not bib_path.is_file():
        return {"keys": sorted(keys), "problems":
                [f"{len(keys)} reading citation(s) but no {bib_path} — run "
                 f"/import-library or /lit-review so the reading list is verified "
                 f"the same way a paper's references are"]}
    known = {e["key"] for e in parse_bibtex(bib_path.read_text(encoding="utf-8",
                                                               errors="replace"))}
    missing = sorted(keys - known)
    return {"keys": sorted(keys), "unresolved": missing,
            "problems": ([f"reading key(s) {missing} are not in {bib_path}"]
                         if missing else [])}


def check_exam(exam: dict, outcome_ids: list[str]) -> dict:
    problems = []
    questions = exam.get("questions") or []
    points = []
    covered: set[str] = set()
    bloom_spread: dict[str, int] = {}
    for q in questions:
        qid = q.get("id", "?")
        p = q.get("points")
        if not isinstance(p, (int, float)):
            problems.append(f"question {qid} has no numeric points")
        else:
            points.append(p)
        mapped = q.get("outcomes") or []
        covered.update(mapped)
        if not mapped:
            problems.append(f"question {qid} measures no outcome")
        orphan = [o for o in mapped if outcome_ids and o not in outcome_ids]
        if orphan:
            problems.append(f"question {qid} names outcome(s) {orphan} the syllabus "
                            f"does not have — an exam wider than the course")
        level = q.get("bloom") or bloom_of(str(q.get("text", "")))
        bloom_spread[level or "unclassified"] = bloom_spread.get(level or "unclassified", 0) + 1
    total_declared = exam.get("total_points")
    computed = round(sum(points), 4)
    if isinstance(total_declared, (int, float)) and computed != total_declared:
        problems.append(f"question points sum to {computed}, the paper declares "
                        f"{total_declared}")
    unmeasured = [o for o in outcome_ids if o not in covered]
    if unmeasured:
        problems.append(f"outcome(s) {unmeasured} are measured by no question")
    return {"questions": len(questions), "computed_points": computed,
            "declared_points": total_declared, "unmeasured_outcomes": unmeasured,
            "bloom_spread": bloom_spread, "problems": problems}


def _descriptor_core(text: str) -> str:
    folded = _fold(text)
    for word in INTENSITY:
        folded = re.sub(rf"\b{re.escape(_fold(word))}\b", " ", folded)
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def check_rubric(rubric: dict) -> dict:
    problems = []
    criteria = rubric.get("criteria") or []
    weights = []
    for c in criteria:
        name = c.get("name", "?")
        w = c.get("weight")
        if not isinstance(w, (int, float)):
            problems.append(f"criterion {name!r} has no numeric weight")
        else:
            weights.append(w)
        levels = c.get("levels") or []
        if len(levels) < 2:
            problems.append(f"criterion {name!r} has fewer than two levels — nothing "
                            f"to distinguish")
            continue
        cores = [_descriptor_core(lv.get("descriptor", "")) for lv in levels]
        empty = [lv.get("label") for lv, core in zip(levels, cores, strict=False)
                 if not core]
        if empty:
            problems.append(f"criterion {name!r}: level(s) {empty} describe nothing "
                            f"observable — strip the adverb and there is no sentence "
                            f"left, which means the level is a grade, not a descriptor")
        elif len(set(cores)) < len(cores):
            problems.append(f"criterion {name!r}: two levels say the same thing once "
                            f"the intensity adverbs are removed — a student cannot tell "
                            f"which one their work is in")
    total = round(sum(weights), 4)
    if weights and total != 100:
        problems.append(f"rubric weights sum to {total}, not 100")
    return {"criteria": len(criteria), "total_weight": total, "problems": problems}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--syllabus", default=DEFAULT_SYLLABUS)
    ap.add_argument("--exam", metavar="FILE")
    ap.add_argument("--rubric", metavar="FILE")
    ap.add_argument("--bib", default="bib/references.bib")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    for flag, value in (("--syllabus", args.syllabus), ("--bib", args.bib)):
        require_within_cwd(value, flag)
    if args.exam:
        require_within_cwd(args.exam, "--exam")
    if args.rubric:
        require_within_cwd(args.rubric, "--rubric")
    if args.exam and args.rubric:
        die("pick one: --exam or --rubric (or neither, to check the syllabus)")

    if args.rubric:
        report = check_rubric(load(Path(args.rubric), "rubric"))
        report["result"] = "OK" if not report["problems"] else "FINDINGS"
        emit(report, args.json_out)
        sys.exit(0 if report["result"] == "OK" else 2)

    syllabus = load(Path(args.syllabus), "syllabus")
    outcomes = syllabus.get("outcomes") or []
    outcome_ids = [o.get("id") for o in outcomes]

    if args.exam:
        report = check_exam(load(Path(args.exam), "exam"), outcome_ids)
        report["result"] = "OK" if not report["problems"] else "FINDINGS"
        emit(report, args.json_out)
        sys.exit(0 if report["result"] == "OK" else 2)

    course = syllabus.get("course") or {}
    report = {
        "course": course.get("code") or course.get("title"),
        "outcomes": check_outcomes(outcomes),
        "assessment": check_assessment(syllabus.get("assessment") or [], outcome_ids),
        "weeks": check_weeks(syllabus.get("weeks") or [], outcome_ids),
        "workload": check_workload(syllabus.get("workload") or [], course.get("ects"),
                                   course.get("ects_hours_per_credit")),
        "readings": check_readings(syllabus.get("weeks") or [], Path(args.bib)),
    }
    problems = []
    for key, section in report.items():
        if isinstance(section, dict):
            problems.extend({key: p} for p in section.get("problems", []))
    report["problems"] = problems
    report["result"] = "OK" if not problems else "FINDINGS"
    report["note"] = ("coverage and arithmetic only. Whether these are the right "
                      "outcomes for this course is a teaching judgement and is not "
                      "checked here")
    emit(report, args.json_out)
    sys.exit(0 if report["result"] == "OK" else 2)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read a file — {e}")
    except UnicodeDecodeError as e:
        die(f"a file is not valid UTF-8 — {e}")
