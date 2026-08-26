#!/usr/bin/env python3
"""failure_scan.py — deterministic half of the AI-research failure-mode checklist.

Seven failure modes are known to survive AI-assisted research and read exactly
like competent work (Lu et al. 2026, Nature 651:914-919, Limitations). Most
checklists implementing them are a list of questions someone must remember to
ask. This script does the part a machine can actually decide, and says plainly
which part it cannot:

  M1 implementation bug passing self-review  -> AUTOMATED (partial): implausibly
     exact metric values, one value standing in for several different metrics,
     zero-variance dispersion.
  M2 hallucinated citation                   -> DELEGATED: /verify-citations is
     already a hard gate; re-checking it here would only weaken that boundary.
  M3 hallucinated experimental result        -> AUTOMATED: a number narrated as
     an own result that appears in no analysis/ artefact.
  M4 shortcut reliance                       -> NOT AUTOMATED: needs an ablation
     judgement. Question list in the reference doc; reviewer-critic's job.
  M5 bug reframed as novel insight           -> AUTOMATED (tell): "surprisingly"
     with nothing cited to be surprised against.
  M6 methodology fabrication                 -> AUTOMATED: a hyperparameter in
     Methods that appears in no analysis/ artefact.
  M7 frame-lock                              -> AUTOMATED (tell): hindsight
     phrasing. Orphaned RQs: word_budget.py --rq-trace.

Paper-type pre-filter. The quantitative modes (M1/M3/M6) assume the manuscript
reports its own measurements. On a theoretical, qualitative, narrative-review or
case-report manuscript they would fire on participant counts and worked examples,
so they are switched OFF for those types — and the skip is REPORTED, never
silent, so a mistyped PROJECT.md cannot quietly disable half the scan.

Every finding is a tell, not a verdict. WARN-only by default: a round number can
be real, a surprise can be genuine. `--strict` exits 2 for callers that want a
gate.

Usage:
  python scripts/failure_scan.py [--drafts drafts] [--analysis analysis]
                                 [--project PROJECT.md] [--type <key>] [--json]
  python scripts/failure_scan.py --strict
Exit codes: 0 ok (or warnings, default) · 1 error · 2 warnings found AND --strict.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
# \n excluded — see cite_audit.py: `[^`]*` spans paragraphs and two stray
# backticks silently hide every failure-mode signal between them.
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s.*$", re.MULTILINE)
CITE_RE = re.compile(r"@[A-Za-z][\w:.#$%&+?<>~/-]*")
SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")

# Types whose manuscripts do not report own measurements — the quantitative
# modes are meaningless there and would fire on legitimate prose.
NON_QUANTITATIVE_TYPES = {"theoretical", "narrative-review", "qualitative", "case-report"}

# Turkish patterns throughout this file are DIACRITIC-INSENSITIVE ([sş], [ıi],
# [oö], [uü], [gğ], [cç]). ASCII-folded Turkish is common in practice, and a
# pattern requiring "şaşırtıcı" silently stopped seeing "sasirtici" — which
# makes a check look CLEAR for the wrong reason. Found by the eval harness.
METRIC_WORDS = (r"accuracy|precision|recall|f1|f-?score|auc|auroc|auprc|r2|r\^2"
                r"|correlation|kappa|dice|iou|mae|mse|rmse|sensitivity|specificity"
                r"|do[gğ]ruluk|kesinlik|duyarl[ıi]l[ıi]k|[oö]zg[uü]ll[uü]k|ba[sş]ar[ıi]m")
# A metric value pinned to a metric name, either order ("accuracy of 0.87",
# "0.87 accuracy", "AUC = 0.81").
METRIC_VALUE_RE = re.compile(
    r"(?:(?P<name1>" + METRIC_WORDS + r")\b[^.\n]{0,24}?(?P<val1>\d+[.,]\d+)"
    r"|(?P<val2>\d+[.,]\d+)\s*(?:puanlık\s+)?(?P<name2>" + METRIC_WORDS + r")\b)",
    re.IGNORECASE)
# Implausibly exact values for an empirical metric — the classic shape of a
# constant leaking through a broken pipeline rather than a measurement. Written
# in ALREADY-NORMALIZED form (_norm strips trailing zeros, so "1.00" arrives
# here as "1"); comparing against unnormalized spellings silently matched
# nothing. Only decimals reach this set — METRIC_VALUE_RE requires a decimal
# point — so the bare "1" / "100" entries cannot fire on ordinary counts.
SUSPICIOUS_EXACT = {"0", "0.5", "1", "2", "100"}
ZERO_VARIANCE_RE = re.compile(
    r"(?:±|\+/-)\s*0[.,]0+\b|\b(?:SD|SS|std|stdev|variance|varyans)\s*[=:]?\s*0[.,]0+\b",
    re.IGNORECASE)

SURPRISE_RE = re.compile(
    r"\bsurprisingly\b|\bunexpectedly\b|\bcounterintuitively\b|\bparadoxically\b"
    r"|\bcontrary to (?:our|the)\s+\w+|\bagainst (?:our )?expectation"
    r"|[sş]a[sş][ıi]rt[ıi]c[ıi]|beklenmedik|beklenenin aksine|hipotez\w*\s+aksine"
    r"|ilgin[cç] bir [sş]ekilde",
    re.IGNORECASE)
HINDSIGHT_RE = re.compile(
    r"\bin hindsight\b|\bin retrospect\b|\bwe (?:later )?realized\b|\bhad we known\b"
    r"|\bwith hindsight\b|sonradan fark|geriye d[oö]n[uü]p bak"
    r"|ba[sş]lang[ıi][cç]ta [oö]ng[oö]r\w*me",
    re.IGNORECASE)

# Hyperparameters a Methods section states and an analysis artefact must
# corroborate. Name is captured so the report can say which one drifted. Both
# orders must be matched: English Methods prose writes the value after the name
# ("a learning rate of 0.003") but before it just as often ("for 50 epochs"),
# and Turkish puts it before by default ("50 devir boyunca").
_HP_NAMES = (r"learning[ _-]?rate|lr|batch[ _-]?size|epochs?|seed|dropout"
             r"|n[_-]?estimators|max[_-]?depth|hidden[ _-]?(?:units|size)"
             r"|weight[ _-]?decay|momentum|[oö][gğ]renme[ _-]?oran[ıi]|y[ıi][gğ][ıi]n[ _-]?boyutu"
             r"|devir|tohum")
_HP_VAL = r"\d+(?:[.,]\d+)?(?:e-?\d+)?"
HYPERPARAM_RE = re.compile(
    r"(?:\b(?P<name1>" + _HP_NAMES + r")\s*(?:=|:|of|is|olarak|değeri)?\s*(?P<val1>" + _HP_VAL + r")"
    r"|\b(?P<val2>" + _HP_VAL + r")\s+(?P<name2>" + _HP_NAMES + r")\b)",
    re.IGNORECASE)

# Files whose prose narrates own results (M3's scope) and own procedure (M6's).
RESULTS_FILES = re.compile(r"(?:results?|bulgular|findings|abstract|[oö]zet|discussion|"
                           r"tart[ıi][şs]ma|conclusion|sonu[cç])", re.IGNORECASE)
METHODS_FILES = re.compile(r"(?:methods?|methodology|y[oö]ntem|materyal)", re.IGNORECASE)
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
ARTEFACT_POINTER_RE = re.compile(
    r"\b(?:Table|Figure|Fig\.?|Section|Eq\.?|Equation|Appendix)\s*\d"
    r"|\b(?:Tablo|[SŞ]ekil|B[oö]l[uü]m|Denklem|Ek)\s*\d", re.IGNORECASE)


# An HTML comment is not prose. The four siblings of this check — claim_check,
# figure_check, tr_style_check, word_budget — all read one as text until it was
# fixed, and this one was never tested either way. It matters more here than it
# sounds: the kit's own evidence binding IS an HTML comment (`<!-- EV-0045 -->`),
# so every draft written the way /draft asks is full of them, and a paragraph
# commented out during revision stays in the file on purpose.
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _clean(text: str) -> str:
    return HEADING_RE.sub("", COMMENT_RE.sub(
        "", INLINE_CODE_RE.sub("", FENCE_RE.sub("", text))))


# Grouped thousands in both conventions — "1,572" (English) and "1.572"
# (Turkish). Without these the separator reads as a decimal point, so a
# narrated record count is (a) mistaken for a MEASUREMENT, slipping past the
# "integers are counts and years" skip below, and (b) unable to match the
# artefact that produced it, which stores the plain integer 1572. On this kit's
# own example review that reported the PRISMA identification count, in three
# sections, as an own result with no artefact behind it — while the artefact
# sat in analysis/data/prisma-counts.json holding exactly that number.
_GROUPED_EN_RE = re.compile(r"^[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?$")
_GROUPED_TR_RE = re.compile(r"^[1-9]\d{0,2}(?:\.\d{3})+(?:,\d+)?$")


def _norm(tok: str) -> str:
    """Canonical numeric string: comma decimals to dot, trailing zeros dropped.

    Grouped thousands are un-grouped first: the separator that repeats in
    three-digit runs is the grouping one, and whatever other separator remains
    is the decimal point.
    """
    if _GROUPED_EN_RE.match(tok):
        tok = tok.replace(",", "")
    elif _GROUPED_TR_RE.match(tok):
        tok = tok.replace(".", "").replace(",", ".")
    t = tok.replace(",", ".")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t or "0"


def read_type(project_path: Path) -> str | None:
    if not project_path.exists():
        return None
    for line in project_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"\s*-\s*\*\*Type:\*\*\s*([\w-]+)", line)
        if m:
            val = m.group(1).strip()
            return None if val.upper() == "TBD" else val
    return None


def analysis_numbers(analysis_dir: Path) -> set[str] | None:
    """Every numeric token the analysis artefacts contain, or None if there are
    no artefacts at all.

    None and empty-set are different answers and the callers rely on it: None
    means "no basis to check against, skip the mode"; an empty set would mean
    "artefacts exist and contain no numbers", which really is suspicious.
    """
    if not analysis_dir.exists():
        return None
    nums: set[str] = set()
    found_any = False
    for p in analysis_dir.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".json", ".csv", ".tsv", ".md",
                                                       ".tex", ".txt", ".yaml", ".yml"):
            continue
        found_any = True
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in NUMBER_RE.finditer(text):
            nums.add(_norm(m.group(0)))
    return nums if found_any else None


def backed(value: str, pool: set[str]) -> bool:
    """Is `value` corroborated by some artefact number?

    Prose rounds: a table holding 0.8712 legitimately becomes "0.87" in the
    text, so an artefact number that STARTS WITH the prose value counts as
    backing it. The reverse (prose more precise than any artefact) does not.
    """
    v = _norm(value)
    if v in pool:
        return True
    return any(a.startswith(v) for a in pool if "." in a and "." in v)



# Probe grid for the saturation measure below: every two-decimal value a
# manuscript's prose realistically prints. Deliberately fixed and deliberately
# small — the measure has to be deterministic and cheap, and its job is to tell
# an author whether backing means anything here, not to model their numbers.
# Starts at 1, not 0: "0.00" normalises to the integer 0, and M3 skips
# integers as counts and years, so including it would cap the measure at 0.99
# for a pool that in fact backs everything the mode looks at.
_SATURATION_PROBE = tuple("0.%02d" % i for i in range(1, 100))
# Above this fraction the artefact pool backs so much of the grid that a
# "backed" verdict carries almost no information. 0.5 is where a coin flip
# would do as well, which is the point at which reporting CLEAR would mislead.
SATURATION_LIMIT = 0.5


def backing_saturation(pool: set[str]) -> float:
    """What fraction of ordinary two-decimal values would this pool 'back'?

    backed() accepts an artefact number that STARTS WITH the prose value,
    because a table holding 0.8712 legitimately becomes "0.87" in the text.
    That rule is sound for a handful of artefacts and vacuous for thousands:
    on this kit's own example review the pool holds ~19,500 numbers and backs
    EVERY two-decimal value, so M3 reported CLEAR over a Discussion paragraph
    whose rho, medians and p-values were produced by no script at all. The
    check was not wrong about any single number; it had simply lost the ability
    to be wrong. Measuring that, and saying so, is the difference between a
    clean report and an honest one.
    """
    if not pool:
        return 0.0
    return sum(1 for v in _SATURATION_PROBE if backed(v, pool)) / len(_SATURATION_PROBE)


def sentences_of(drafts_dir: Path) -> list[tuple[str, str]]:
    out = []
    if not drafts_dir.exists():
        return out
    for f in sorted(drafts_dir.glob("**/*.md")):
        if f.name == "STATUS.md":
            continue
        for s in SENT_SPLIT.split(_clean(f.read_text(encoding="utf-8", errors="replace"))):
            s = s.strip()
            if s:
                out.append((s, f.as_posix()))
    return out


def scan_m1(sentences) -> list[dict]:
    hits, by_value = [], {}
    for sent, where in sentences:
        # A metric value in a sentence that CITES a source is a literature
        # number, not an own result — the same exemption scan_m3 already makes,
        # applied here for the same reason. It matters most in a review, whose
        # job includes REPORTING an implausible 1.0 that someone else published:
        # this kit's own example review names two such studies and diagnoses the
        # leakage in the very next clause, and was flagged for doing so.
        # Own results carry no citation key, so the asymmetry is safe.
        if CITE_RE.search(sent):
            continue
        for m in METRIC_VALUE_RE.finditer(sent):
            name = (m.group("name1") or m.group("name2") or "").lower()
            raw = m.group("val1") or m.group("val2")
            val = _norm(raw)
            by_value.setdefault(val, set()).add(name)
            if val in SUSPICIOUS_EXACT:
                # Report the value AS WRITTEN. The normalized form is the
                # comparison key, not something the author would recognise —
                # telling someone who wrote "1.00" that they wrote "1" makes
                # the finding harder to locate in their own draft.
                hits.append({"mode": "M1", "where": where, "signal": "exact-round-metric",
                             "value": raw, "metric": name, "sentence": sent[:200],
                             "msg": f"{name} reported as exactly {raw} — verify it is a "
                                    f"measurement, not a constant leaking through"})
        if ZERO_VARIANCE_RE.search(sent):
            hits.append({"mode": "M1", "where": where, "signal": "zero-variance",
                         "value": None, "metric": None, "sentence": sent[:200],
                         "msg": "zero dispersion reported — identical results across runs "
                                "usually means the seed or the loop is not varying"})
    for val, names in by_value.items():
        if len(names) >= 3:
            hits.append({"mode": "M1", "where": "(across drafts)", "signal": "one-value-many-metrics",
                         "value": val, "metric": ", ".join(sorted(names)), "sentence": None,
                         "msg": f"{val} reported for {len(names)} different metrics "
                                f"({', '.join(sorted(names))}) — a shared constant is more "
                                f"likely than a coincidence"})
    return hits


def scan_m3(sentences, pool: set[str]) -> list[dict]:
    hits = []
    for sent, where in sentences:
        if not RESULTS_FILES.search(Path(where).stem):
            continue
        if CITE_RE.search(sent) or ARTEFACT_POINTER_RE.search(sent):
            continue  # a literature number, or one the reader is sent to a table for
        for m in NUMBER_RE.finditer(sent):
            tok = m.group(0)
            # Decide on the NORMALISED form, not the raw one: "1.572" carries a
            # dot but is the integer 1572, and a count is not a measurement.
            if "." not in _norm(tok):
                continue  # integers are counts and years, not measurements
            if backed(tok, pool):
                continue
            hits.append({"mode": "M3", "where": where, "value": tok, "sentence": sent[:200],
                         "msg": f"'{tok}' is narrated as an own result but appears in no "
                                f"analysis/ artefact — point to the run that produced it"})
    return hits


def scan_m5(sentences) -> list[dict]:
    hits = []
    for i, (sent, where) in enumerate(sentences):
        m = SURPRISE_RE.search(sent)
        if not m:
            continue
        prev = sentences[i - 1][0] if i and sentences[i - 1][1] == where else ""
        if CITE_RE.search(sent) or CITE_RE.search(prev):
            continue
        hits.append({"mode": "M5", "where": where, "phrase": m.group(0), "sentence": sent[:200],
                     "msg": f"'{m.group(0)}' with nothing cited nearby — a result is only "
                            f"surprising relative to published expectation; unanchored "
                            f"surprise is also the shape of a bug retold as a finding"})
    return hits


def scan_m6(sentences, pool: set[str]) -> list[dict]:
    hits = []
    for sent, where in sentences:
        if not METHODS_FILES.search(Path(where).stem):
            continue
        for m in HYPERPARAM_RE.finditer(sent):
            val = m.group("val1") or m.group("val2")
            name = m.group("name1") or m.group("name2")
            if backed(val, pool):
                continue
            hits.append({"mode": "M6", "where": where, "hyperparameter": name,
                         "value": val, "sentence": sent[:200],
                         "msg": f"Methods states {name}={val} but no analysis/ "
                                f"artefact records it — Methods may describe an intended "
                                f"run rather than the one that produced the results"})
    return hits


def scan_m7(sentences) -> list[dict]:
    return [{"mode": "M7", "where": where, "phrase": m.group(0), "sentence": sent[:200],
             "msg": f"'{m.group(0)}' — hindsight phrasing often marks a framing the "
                    f"pipeline could not back out of; check the RQ still fits the study"}
            for sent, where in sentences
            for m in [HINDSIGHT_RE.search(sent)] if m]


def check(drafts_dir: Path, analysis_dir: Path, paper_type: str | None) -> dict:
    sentences = sentences_of(drafts_dir)
    pool = analysis_numbers(analysis_dir)
    # An unknown or absent type keeps the quantitative modes ON. Failing toward
    # more scanning is the safe direction: a missing PROJECT.md must not be a
    # silent way to switch off half the checklist.
    quantitative = paper_type not in NON_QUANTITATIVE_TYPES

    modes: dict[str, dict] = {}

    def record(mode, findings=None, skipped=None):
        modes[mode] = ({"status": "SKIPPED", "reason": skipped, "findings": []}
                       if skipped else
                       {"status": "FLAGGED" if findings else "CLEAR", "findings": findings or []})

    if not quantitative:
        type_skip = f"paper type '{paper_type}' reports no own measurements"
        record("M1", skipped=type_skip)
        record("M3", skipped=type_skip)
        record("M6", skipped=type_skip)
    else:
        record("M1", scan_m1(sentences))
        if pool is None:
            no_pool = "no analysis/ artefacts to check against"
            record("M3", skipped=no_pool)
            record("M6", skipped=no_pool)
        else:
            # A saturated pool cannot produce a meaningful CLEAR, and saying
            # CLEAR anyway is the failure this mode exists to catch, one level
            # up. INSUFFICIENT EVIDENCE is the reference doc's own third
            # verdict and is explicitly not a pass.
            sat = backing_saturation(pool)
            m3_hits, m6_hits = scan_m3(sentences, pool), scan_m6(sentences, pool)
            record("M3", m3_hits)
            record("M6", m6_hits)
            for mode, hits in (("M3", m3_hits), ("M6", m6_hits)):
                modes[mode]["backing_saturation"] = round(sat, 3)
                if sat > SATURATION_LIMIT and not hits:
                    modes[mode]["status"] = "INSUFFICIENT EVIDENCE"
                    modes[mode]["reason"] = (
                        f"the artefact pool backs {sat:.0%} of ordinary two-decimal "
                        f"values, so 'appears in some artefact' no longer "
                        f"distinguishes a produced number from a coincidence — "
                        f"this is NOT a pass; check the narrated numbers by hand "
                        f"against the script that produced them")

    record("M5", scan_m5(sentences))
    record("M7", scan_m7(sentences))
    modes["M2"] = {"status": "DELEGATED", "reason": "/verify-citations is the gate", "findings": []}
    modes["M4"] = {"status": "NOT_AUTOMATED",
                   "reason": "needs an ablation judgement — see the critique skill's "
                             "reference/failure-modes.md and dispatch reviewer-critic",
                   "findings": []}

    findings = [f for m in modes.values() for f in m["findings"]]
    return {
        "paper_type": paper_type,
        "quantitative_modes_active": quantitative,
        "analysis_artefacts_present": pool is not None,
        "files_scanned": sorted({w for _, w in sentences}),
        "modes": modes,
        "findings": findings,
        "warnings": len(findings),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--drafts", default="drafts")
    ap.add_argument("--analysis", default="analysis")
    ap.add_argument("--project", default="PROJECT.md")
    ap.add_argument("--type", dest="paper_type", default=None,
                    help="override the paper type instead of reading PROJECT.md")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any warning (opt-in blocking; default is WARN-only)")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    for val, flag in ((args.drafts, "--drafts"), (args.analysis, "--analysis"),
                      (args.project, "--project")):
        require_within_cwd(val, flag)
    if Path(args.drafts).exists() and not Path(args.drafts).is_dir():
        die(f"--drafts {args.drafts} is not a directory")
    paper_type = args.paper_type or read_type(Path(args.project))
    result = check(Path(args.drafts), Path(args.analysis), paper_type)
    emit(result, True)
    sys.exit(2 if (args.strict and result["warnings"]) else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read input files — {e}")
    except UnicodeDecodeError as e:
        die(f"an input file is not valid UTF-8 — {e}")
