#!/usr/bin/env python3
"""meta_analysis.py — fixed- and random-effects pooling, heterogeneity, small-study bias.

Turns an extraction table into a pooled estimate with the numbers a Methods and
Results section actually has to report: per-study effects with CIs, both models,
Q / I² / tau², a prediction interval, Egger's test, and an ASCII forest plot.

WHAT THIS DOES NOT DO — read this before using the output:
  It does not decide whether pooling is APPROPRIATE. That is a judgement about
  whether the studies address the same question with comparable populations,
  interventions and outcomes, and no statistic answers it — I² least of all.
  I² describes how much of the observed variation exceeds sampling error; a
  low I² across studies that should never have been combined is a precise
  measurement of the wrong thing. Take the design question to
  `methodology-advisor` BEFORE running this, not after.
  It also does not extract effect sizes from papers, does not impute missing
  variances, and does not choose a model for you. Both models are always
  reported; picking one is a pre-registered decision, not an outcome.

Effect measures (`--measure`):
  precomputed  yi + (sei | vi)                   generic inverse-variance
  or           e1 n1 e2 e2 -> log odds ratio     analysed on the log scale
  rr           e1 n1 e2 n2 -> log risk ratio     analysed on the log scale
  rd           e1 n1 e2 n2 -> risk difference
  md           m1 sd1 n1 m2 sd2 n2 -> mean difference
  smd          m1 sd1 n1 m2 sd2 n2 -> Hedges' g

Formula provenance, because published variants differ and a silent choice is
not reproducible:
  tau^2       DerSimonian & Laird (1986)
  Hedges' g   J = 1 - 3/(4*df - 1), df = n1+n2-2; var per Borenstein et al.,
              *Introduction to Meta-Analysis* (2009): Vd = (n1+n2)/(n1*n2)
              + d^2/(2*(n1+n2)), Vg = J^2 * Vd. (Some packages use
              2*(n1+n2-2) in the second term; results differ slightly.)
  prediction  Higgins, Thompson & Spiegelhalter (2009): theta_R
              +/- t(k-2) * sqrt(tau^2 + SE_R^2). Needs k >= 3.
  Egger       Egger et al. (1997): OLS of yi/sei on 1/sei, intercept tested on
              t(k-2). NOT run below --egger-min studies (default 10), per
              Sterne et al. (2011) — below that the test has almost no power
              and a null result means nothing.

Input: JSON array, JSONL, or CSV. Column names are matched case-insensitively
with common aliases (`study`/`label`/`id`; `events1`/`e1`; `mean1`/`m1`; ...).

Usage:
  python scripts/meta_analysis.py --input analysis/effects.csv --measure or
  python scripts/meta_analysis.py --input analysis/effects.json --measure smd --alpha 0.10
  python scripts/meta_analysis.py --input data.jsonl --measure precomputed --forest
Output: single JSON object (or the forest plot with --forest).
Exit codes: 0 ok · 1 error (unusable input).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, parse_json_or_jsonl, require_within_cwd
from lib_stats import chi2_sf, norm_ppf, norm_sf, t_ppf, t_sf

LOG_SCALE = {"or": "odds ratio", "rr": "risk ratio"}
MEASURES = ("precomputed", "or", "rr", "rd", "md", "smd")
BINARY_FIELDS = ("e1", "n1", "e2", "n2")
CONTINUOUS_FIELDS = ("m1", "sd1", "n1", "m2", "sd2", "n2")
DEFAULT_EGGER_MIN = 10
CONTINUITY = 0.5

ALIASES = {
    "label": ("label", "study", "study_id", "id", "name", "citation", "source",
              "bib_key", "calisma"),
    "yi": ("yi", "effect", "effect_size", "es", "estimate", "theta", "logor", "log_or"),
    "sei": ("sei", "se", "std_err", "stderr", "standard_error"),
    "vi": ("vi", "var", "variance"),
    "e1": ("e1", "events1", "event1", "ev1", "a", "treat_events", "olay1"),
    "n1": ("n1", "total1", "nt", "treat_n", "toplam1"),
    "e2": ("e2", "events2", "event2", "ev2", "c", "ctrl_events", "olay2"),
    "n2": ("n2", "total2", "nc", "ctrl_n", "toplam2"),
    "m1": ("m1", "mean1", "ort1"),
    "sd1": ("sd1", "std1", "sd_1", "ss1"),
    "m2": ("m2", "mean2", "ort2"),
    "sd2": ("sd2", "std2", "sd_2", "ss2"),
}


def _norm_key(key: str) -> str:
    return "".join(ch for ch in str(key).lower() if ch.isalnum() or ch == "_")


def canonical(row: dict) -> dict:
    """Map a row's columns onto canonical field names, case/alias-insensitively."""
    lookup = {_norm_key(k): v for k, v in row.items() if k is not None}
    out = {}
    for field, names in ALIASES.items():
        for name in names:
            if name in lookup and str(lookup[name]).strip() != "":
                out[field] = lookup[name]
                break
    return out


def _num(value, field: str, label: str) -> float:
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        # `from None`: the caller dies on this message, and float()'s own
        # "could not convert string to float" above it names the raw cell
        # without naming the study it came from — which is the only part a
        # user fixing their input file needs.
        raise ValueError(
            f"study {label!r}: {field}={value!r} is not a number") from None


def load_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".csv" or (text.lstrip()[:1] not in "[{"):
        return list(csv.DictReader(io.StringIO(text)))
    return [r for r in parse_json_or_jsonl(text) if isinstance(r, dict)]


# ---------- per-study effect sizes ----------

def effect_precomputed(row: dict, label: str) -> tuple[float, float, list[str]]:
    if "yi" not in row:
        raise ValueError(f"study {label!r}: measure 'precomputed' needs an effect column (yi)")
    yi = _num(row["yi"], "yi", label)
    if "sei" in row:
        sei = _num(row["sei"], "sei", label)
        vi = sei * sei
    elif "vi" in row:
        vi = _num(row["vi"], "vi", label)
    else:
        raise ValueError(f"study {label!r}: needs a standard error (sei) or variance (vi)")
    return yi, vi, []


def _binary_cells(row: dict, label: str) -> tuple[float, float, float, float]:
    for f in BINARY_FIELDS:
        if f not in row:
            raise ValueError(f"study {label!r}: binary measures need {', '.join(BINARY_FIELDS)}"
                             f" — missing {f}")
    e1, n1, e2, n2 = (_num(row[f], f, label) for f in BINARY_FIELDS)
    for name, ev, tot in (("arm 1", e1, n1), ("arm 2", e2, n2)):
        if tot <= 0:
            raise ValueError(f"study {label!r}: {name} total must be > 0")
        if ev < 0 or ev > tot:
            raise ValueError(f"study {label!r}: {name} events ({ev:g}) outside 0..{tot:g}")
    return e1, n1, e2, n2


def effect_binary(row: dict, label: str, measure: str) -> tuple[float, float, list[str]]:
    e1, n1, e2, n2 = _binary_cells(row, label)
    a, b, c, d = e1, n1 - e1, e2, n2 - e2
    notes: list[str] = []
    if measure == "rd":
        yi = a / n1 - c / n2
        vi = (a * b) / (n1 ** 3) + (c * d) / (n2 ** 3)
        if vi == 0:
            raise ValueError(f"study {label!r}: risk difference has zero variance "
                             f"(no events, or events in every participant, in both arms)")
        return yi, vi, notes
    if a == 0 and c == 0:
        raise ValueError(f"study {label!r}: zero events in BOTH arms — a ratio measure is "
                         f"undefined and the study carries no information about it; drop it "
                         f"or switch to --measure rd")
    if 0 in (a, b, c, d):
        # Continuity correction is a choice with consequences (it biases the
        # estimate toward the null and inflates its variance), so it is applied
        # transparently and reported per study rather than done quietly.
        a, b, c, d = a + CONTINUITY, b + CONTINUITY, c + CONTINUITY, d + CONTINUITY
        n1, n2 = n1 + 2 * CONTINUITY, n2 + 2 * CONTINUITY
        notes.append(f"continuity correction +{CONTINUITY} applied to all cells (zero cell)")
    if measure == "or":
        yi = math.log((a * d) / (b * c))
        vi = 1 / a + 1 / b + 1 / c + 1 / d
    else:  # rr
        yi = math.log((a / n1) / (c / n2))
        vi = 1 / a - 1 / n1 + 1 / c - 1 / n2
    return yi, vi, notes


def effect_continuous(row: dict, label: str, measure: str) -> tuple[float, float, list[str]]:
    for f in CONTINUOUS_FIELDS:
        if f not in row:
            raise ValueError(f"study {label!r}: continuous measures need "
                             f"{', '.join(CONTINUOUS_FIELDS)} — missing {f}")
    m1, sd1, n1, m2, sd2, n2 = (_num(row[f], f, label) for f in CONTINUOUS_FIELDS)
    if n1 < 2 or n2 < 2:
        raise ValueError(f"study {label!r}: each arm needs n >= 2")
    if sd1 < 0 or sd2 < 0:
        raise ValueError(f"study {label!r}: standard deviations cannot be negative")
    if measure == "md":
        vi = sd1 * sd1 / n1 + sd2 * sd2 / n2
        if vi == 0:
            raise ValueError(f"study {label!r}: both SDs are zero — variance is undefined")
        return m1 - m2, vi, []
    df = n1 + n2 - 2
    s_pooled = math.sqrt(((n1 - 1) * sd1 * sd1 + (n2 - 1) * sd2 * sd2) / df)
    if s_pooled == 0:
        raise ValueError(f"study {label!r}: pooled SD is zero — a standardized effect "
                         f"is undefined")
    d = (m1 - m2) / s_pooled
    j = 1.0 - 3.0 / (4.0 * df - 1.0)
    g = j * d
    vd = (n1 + n2) / (n1 * n2) + d * d / (2.0 * (n1 + n2))
    return g, j * j * vd, []


def study_effect(row: dict, label: str, measure: str) -> tuple[float, float, list[str]]:
    if measure == "precomputed":
        return effect_precomputed(row, label)
    if measure in ("or", "rr", "rd"):
        return effect_binary(row, label, measure)
    return effect_continuous(row, label, measure)


# ---------- pooling ----------

def _pool(ys: list[float], ws: list[float]) -> tuple[float, float]:
    sw = sum(ws)
    return sum(w * y for w, y in zip(ws, ys, strict=True)) / sw, 1.0 / sw


def _ci(est: float, se: float, z: float) -> tuple[float, float]:
    return est - z * se, est + z * se


def _model_block(est: float, se: float, z_crit: float) -> dict:
    z = est / se if se > 0 else float("inf")
    lo, hi = _ci(est, se, z_crit)
    return {"estimate": est, "se": se, "ci_low": lo, "ci_high": hi,
            "z": z, "p": 2.0 * norm_sf(abs(z))}


def heterogeneity(ys: list[float], vis: list[float], theta_fixed: float) -> dict:
    ws = [1.0 / v for v in vis]
    k = len(ys)
    q = sum(w * (y - theta_fixed) ** 2 for w, y in zip(ws, ys, strict=True))
    df = k - 1
    sw, sw2 = sum(ws), sum(w * w for w in ws)
    c = sw - sw2 / sw
    tau2 = max(0.0, (q - df) / c) if c > 0 and df > 0 else 0.0
    i2 = max(0.0, (q - df) / q) * 100.0 if q > 0 and df > 0 else 0.0
    return {"Q": q, "df": df, "p": chi2_sf(q, df) if df > 0 else None,
            "I2_percent": i2, "H2": (q / df) if df > 0 else None,
            "tau2": tau2, "tau": math.sqrt(tau2)}


def egger_test(ys: list[float], seis: list[float], min_studies: int) -> dict:
    k = len(ys)
    if k < min_studies:
        return {"status": "not_run",
                "reason": f"{k} studies < --egger-min {min_studies}: below this the test "
                          f"has almost no power, so a non-significant result would say "
                          f"nothing about small-study effects (Sterne et al. 2011)"}
    xs = [1.0 / s for s in seis]           # precision
    zs = [y / s for y, s in zip(ys, seis, strict=True)]  # standard normal deviate
    n = float(k)
    mx, my = sum(xs) / n, sum(zs) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return {"status": "not_run",
                "reason": "all studies have identical precision — the regression is undefined"}
    slope = sum((x - mx) * (z - my) for x, z in zip(xs, zs, strict=True)) / sxx
    intercept = my - slope * mx
    resid = [z - (intercept + slope * x) for x, z in zip(xs, zs, strict=True)]
    df = k - 2
    s2 = sum(r * r for r in resid) / df
    se_int = math.sqrt(s2 * (1.0 / n + mx * mx / sxx))
    t = intercept / se_int if se_int > 0 else float("inf")
    return {"status": "run", "intercept": intercept, "se": se_int, "t": t, "df": df,
            "p": 2.0 * t_sf(abs(t), df), "slope": slope,
            "interpretation": "a non-zero intercept indicates funnel asymmetry, which has "
                              "several possible causes (publication bias, true heterogeneity, "
                              "poorer methodology in smaller studies, chance) — it is not by "
                              "itself evidence of publication bias"}


# ---------- forest plot ----------

def forest_ascii(studies: list[dict], pooled: list[tuple[str, dict]], measure: str,
                 width: int = 41) -> str:
    log = measure in LOG_SCALE
    def disp(v): return math.exp(v) if log else v

    lows = [s["ci_low"] for s in studies] + [p["ci_low"] for _, p in pooled]
    highs = [s["ci_high"] for s in studies] + [p["ci_high"] for _, p in pooled]
    lo, hi = min(lows), max(highs)
    if hi - lo < 1e-12:
        lo, hi = lo - 1.0, hi + 1.0
    pad = (hi - lo) * 0.05
    lo, hi = lo - pad, hi + pad

    def col(v: float) -> int:
        return max(0, min(width - 1, round((v - lo) / (hi - lo) * (width - 1))))

    null = 0.0  # log(1) for ratios, 0 for differences — the no-effect line either way
    null_col = col(null) if lo <= null <= hi else None

    def bar(entry: dict, marker: str) -> str:
        cells = [" "] * width
        if null_col is not None:
            cells[null_col] = "|"
        for i in range(col(entry["ci_low"]), col(entry["ci_high"]) + 1):
            cells[i] = "-"
        cells[col(entry["ci_low"])] = "["
        cells[col(entry["ci_high"])] = "]"
        cells[col(entry["estimate"])] = marker
        return "".join(cells)

    name_w = max([len(s["label"]) for s in studies] + [len(n) for n, _ in pooled] + [5])
    unit = "ratio" if log else "difference"
    out = [f"{'Study'.ljust(name_w)}  {'Effect [95% CI]'.ljust(24)} {'Wt%':>5}  plot ({unit})",
           "-" * (name_w + 34 + width)]
    for s in studies:
        est = f"{disp(s['estimate']):.3f} [{disp(s['ci_low']):.3f}, {disp(s['ci_high']):.3f}]"
        wt = f"{s['weight_random_percent']:.1f}"
        out.append(f"{s['label'].ljust(name_w)}  {est.ljust(24)} {wt:>5}  {bar(s, 'o')}")
    out.append("-" * (name_w + 34 + width))
    for name, p in pooled:
        est = f"{disp(p['estimate']):.3f} [{disp(p['ci_low']):.3f}, {disp(p['ci_high']):.3f}]"
        out.append(f"{name.ljust(name_w)}  {est.ljust(24)} {'':>5}  {bar(p, '#')}")
    out.append(f"scale: {disp(lo):.3f} .. {disp(hi):.3f}"
               + (f"   | = no effect ({'1' if log else '0'})" if null_col is not None else ""))
    return "\n".join(out)


# ---------- orchestration ----------

def analyze(rows: list[dict], measure: str, alpha: float, egger_min: int) -> dict:
    if measure not in MEASURES:
        raise ValueError(f"unknown --measure {measure!r} (pick one of {', '.join(MEASURES)})")
    studies, excluded = [], []
    for i, raw in enumerate(rows, 1):
        row = canonical(raw)
        label = str(row.get("label") or f"study-{i}").strip()
        try:
            yi, vi, notes = study_effect(row, label, measure)
        except ValueError as e:
            excluded.append({"label": label, "reason": str(e)})
            continue
        if vi <= 0 or not math.isfinite(yi) or not math.isfinite(vi):
            excluded.append({"label": label,
                             "reason": "non-finite or non-positive variance"})
            continue
        studies.append({"label": label, "estimate": yi, "variance": vi,
                        "se": math.sqrt(vi), "notes": notes})

    k = len(studies)
    if k == 0:
        return {"status": "error", "k": 0, "excluded": excluded,
                "message": "no usable studies — every row failed effect-size computation"}
    if k == 1:
        z_crit = norm_ppf(1 - alpha / 2)
        s = studies[0]
        s["ci_low"], s["ci_high"] = _ci(s["estimate"], s["se"], z_crit)
        return {"status": "insufficient", "k": 1, "measure": measure,
                "studies": studies, "excluded": excluded,
                "message": "a single study is not a meta-analysis — reported as-is, with "
                           "no pooling, no heterogeneity and no bias test"}

    z_crit = norm_ppf(1 - alpha / 2)
    ys = [s["estimate"] for s in studies]
    vis = [s["variance"] for s in studies]
    seis = [s["se"] for s in studies]

    w_fixed = [1.0 / v for v in vis]
    theta_f, var_f = _pool(ys, w_fixed)
    het = heterogeneity(ys, vis, theta_f)
    w_rand = [1.0 / (v + het["tau2"]) for v in vis]
    theta_r, var_r = _pool(ys, w_rand)

    sw_f, sw_r = sum(w_fixed), sum(w_rand)
    for s, wf, wr in zip(studies, w_fixed, w_rand, strict=True):
        s["ci_low"], s["ci_high"] = _ci(s["estimate"], s["se"], z_crit)
        s["weight_fixed_percent"] = 100.0 * wf / sw_f
        s["weight_random_percent"] = 100.0 * wr / sw_r

    fixed = _model_block(theta_f, math.sqrt(var_f), z_crit)
    random = _model_block(theta_r, math.sqrt(var_r), z_crit)
    random["tau2"] = het["tau2"]
    if k >= 3:
        t_crit = t_ppf(1 - alpha / 2, k - 2)
        spread = math.sqrt(het["tau2"] + var_r)
        random["prediction_low"] = theta_r - t_crit * spread
        random["prediction_high"] = theta_r + t_crit * spread
        random["prediction_note"] = ("the interval a NEW study's true effect is expected to "
                                     "fall in — always wider than the CI, and the honest "
                                     "summary when tau2 > 0")
    else:
        random["prediction_note"] = "not computed: a prediction interval needs k >= 3"

    out = {
        "status": "ok",
        "measure": measure,
        "scale": "log" if measure in LOG_SCALE else "raw",
        "k": k,
        "alpha": alpha,
        "studies": studies,
        "fixed_effect": fixed,
        "random_effects": random,
        "heterogeneity": het,
        "publication_bias": {"egger": egger_test(ys, seis, egger_min)},
        "excluded": excluded,
        "caveats": [
            "Both models are reported. Choosing between them is a design decision made "
            "BEFORE seeing these numbers; picking the one with the smaller p-value after "
            "the fact is a result of the analysis, not an input to it.",
            "I2 measures how much variation exceeds sampling error. It does NOT test "
            "whether combining these studies is appropriate, and a low I2 across "
            "incomparable studies is a precise measurement of the wrong quantity.",
            "Every number here inherits the extraction table's errors. Nothing in this "
            "script can detect a transcribed SD that belonged to another arm.",
        ],
    }
    if measure in LOG_SCALE:
        name = LOG_SCALE[measure]
        for block in (out["fixed_effect"], out["random_effects"]):
            block["exp_estimate"] = math.exp(block["estimate"])
            block["exp_ci_low"] = math.exp(block["ci_low"])
            block["exp_ci_high"] = math.exp(block["ci_high"])
        if "prediction_low" in out["random_effects"]:
            out["random_effects"]["exp_prediction_low"] = math.exp(
                out["random_effects"]["prediction_low"])
            out["random_effects"]["exp_prediction_high"] = math.exp(
                out["random_effects"]["prediction_high"])
        out["caveats"].insert(0, f"Pooling is on the log scale; `exp_*` fields are the "
                                 f"{name} a write-up should report.")
    if het["tau2"] > 0 and het["I2_percent"] >= 50:
        out["caveats"].append(
            f"I2 = {het['I2_percent']:.1f}%: report the prediction interval alongside the "
            f"pooled estimate. A random-effects CI alone understates what the next study "
            f"might find.")
    if excluded:
        out["caveats"].append(f"{len(excluded)} row(s) excluded — see `excluded`. An "
                              f"exclusion changes the estimate and belongs in the write-up.")
    out["forest_ascii"] = forest_ascii(
        studies, [("Fixed effect", fixed), ("Random effects", random)], measure)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True, help="CSV / JSON / JSONL extraction table")
    ap.add_argument("--measure", default="precomputed", choices=MEASURES)
    ap.add_argument("--alpha", type=float, default=0.05, help="1 - confidence level")
    ap.add_argument("--egger-min", type=int, default=DEFAULT_EGGER_MIN,
                    help=f"minimum studies for Egger's test (default {DEFAULT_EGGER_MIN})")
    ap.add_argument("--forest", action="store_true", help="print the forest plot, not JSON")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.input, "--input")
    if not 0.0 < args.alpha < 1.0:
        die("--alpha must be strictly between 0 and 1")
    path = Path(args.input)
    if not path.exists():
        die(f"{path} not found")
    try:
        rows = load_rows(path)
    except (ValueError, json.JSONDecodeError) as e:
        die(f"could not parse {path} — {e}")
    if not rows:
        die(f"{path} holds no rows")
    try:
        result = analyze(rows, args.measure, args.alpha, args.egger_min)
    except ValueError as e:
        die(str(e))
    if args.forest:
        print(result.get("forest_ascii") or result.get("message", "no plot"))
        return
    emit(result, True)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read the input file — {e}")
