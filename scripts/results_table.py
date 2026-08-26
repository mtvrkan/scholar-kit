#!/usr/bin/env python3
"""results_table.py — the results table, derived from the run register instead of typed.

WHY THIS EXISTS
`experiment_db.py summary` gives mean, std and the seeds behind every group, as
JSON. Getting that into a manuscript meant a person reading numbers off one
screen and typing them into another — which is transcription, the exact operation
this kit refuses everywhere else (bibliographic data from memory, a metric quoted
from recollection). A digit dropped here is invisible: nothing downstream can
tell 0.809 from 0.089 once it is prose.

So the table is generated. Markdown for a draft, LaTeX booktabs for a thesis, CSV
for a spreadsheet — from the register, with the seed count in a column, and with
the difference against a reference model expressed as a paired bootstrap interval
computed from the per-fold predictions the run wrote.

WHAT IT REFUSES
- **To rank.** No sorting by score, no bold on the largest mean, no "best" column.
  A table that visually nominates a winner has made the claim the interval next to
  it may not support, and readers believe the bold, not the bracket.
- **To report a difference without an interval.** `--reference` produces Δ only
  when the predictions exist for both models on shared ids. When they do not, the
  column says why rather than showing a bare subtraction.
- **To average over a single seed.** A group with one seed is printed with an
  empty std and a marker, because "0.809" and "0.809 ± 0.014" are different
  claims and only one of them can be checked.
- **To compute the interval on pooled probabilities.** Seeds are not an ensemble:
  the metric is computed per seed and averaged, and the bootstrap resamples ids,
  never rows.

USAGE
  python scripts/results_table.py --experiment baselines --metric roc_auc
  python scripts/results_table.py --experiment baselines --metric roc_auc \
      --reference majority --format latex --out analysis/tables/results.tex

Exit codes: 0 written · 1 error · 2 nothing to tabulate (no runs matched).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import experiment_db  # noqa: E402
from lib_common import die, emit, read_jsonl, require_within_cwd  # noqa: E402
from lib_stats import bootstrap_ci  # noqa: E402

DEFAULT_RUNS = "analysis/runs.jsonl"
PROB_METRICS = {"roc_auc"}
LABEL_METRICS = {"accuracy", "f1", "precision", "recall", "balanced_accuracy"}
REGRESSION_METRICS = {"rmse", "mae", "r2", "mape"}
BOOTSTRAPPABLE = PROB_METRICS | LABEL_METRICS | REGRESSION_METRICS


# ---------------------------------------------------------------- metrics
# Deliberately stdlib. A table is produced on the machine that writes the paper,
# which is not always the machine that trained the model, and a results table
# that needs scikit-learn installed to render is a table that does not render.

def _auc(pairs: list[tuple[float, float]]) -> float | None:
    """Rank-based ROC-AUC over (label, score). Ties get their average rank."""
    pos = [s for y, s in pairs if y == 1]
    neg = [s for y, s in pairs if y != 1]
    if not pos or not neg:
        return None
    ordered = sorted(pairs, key=lambda p: p[1])
    ranks, i = {}, 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = average
        i = j + 1
    rank_sum = sum(ranks[k] for k, (y, _) in enumerate(ordered) if y == 1)
    return (rank_sum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def _binary_counts(pairs, positive):
    tp = sum(1 for y, p in pairs if p == positive and y == positive)
    fp = sum(1 for y, p in pairs if p == positive and y != positive)
    fn = sum(1 for y, p in pairs if p != positive and y == positive)
    tn = len(pairs) - tp - fp - fn
    return tp, fp, fn, tn


def label_metric(name, pairs, positive):
    if not pairs:
        return None
    if name == "accuracy":
        return sum(1 for y, p in pairs if y == p) / len(pairs)
    tp, fp, fn, tn = _binary_counts(pairs, positive)
    if name == "precision":
        return tp / (tp + fp) if (tp + fp) else None
    if name == "recall":
        return tp / (tp + fn) if (tp + fn) else None
    if name == "balanced_accuracy":
        if not (tp + fn) or not (tn + fp):
            return None
        return (tp / (tp + fn) + tn / (tn + fp)) / 2
    if name == "f1":
        denom = 2 * tp + fp + fn
        return (2 * tp / denom) if denom else None
    return None


def regression_metric(name, pairs):
    if not pairs:
        return None
    errors = [float(y) - float(p) for y, p in pairs]
    if name == "rmse":
        return math.sqrt(sum(e * e for e in errors) / len(errors))
    if name == "mae":
        return sum(abs(e) for e in errors) / len(errors)
    if name == "mape":
        usable = [(y, p) for y, p in pairs if float(y) != 0]
        if not usable:
            return None
        return sum(abs((float(y) - float(p)) / float(y)) for y, p in usable) / len(usable)
    if name == "r2":
        ys = [float(y) for y, _ in pairs]
        mean = sum(ys) / len(ys)
        ss_tot = sum((y - mean) ** 2 for y in ys)
        if ss_tot == 0:
            return None
        return 1 - sum(e * e for e in errors) / ss_tot
    return None


# ---------------------------------------------------------------- predictions

def load_predictions(runs: list[dict], model: str) -> dict[int, dict[str, dict]]:
    """seed → id → {y, prob, pred} for one model, from the files the runs point at."""
    per_seed: dict[int, dict[str, dict]] = {}
    for rec in runs:
        if rec.get("model") != model or not rec.get("predictions"):
            continue
        path = Path(rec["predictions"])
        if not path.is_file():
            continue
        rows = {}
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                prob = row.get("y_prob", "")
                rows[row["id"]] = {
                    "y": row.get("y_true", ""),
                    "pred": row.get("y_pred", ""),
                    "prob": float(prob) if prob not in ("", None) else None,
                }
        if rows:
            per_seed[int(rec["seed"])] = rows
    return per_seed


def _coerce(value):
    try:
        f = float(value)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return value


def paired_difference(metric: str, a_preds, b_preds, positive, resamples: int) -> dict:
    """Paired bootstrap of (model − reference), resampling ids and never rows.

    The pairing is the whole point: the two models saw the same rows, so the
    difference has far less variance than either score's own interval, and an
    unpaired comparison of two overlapping CIs is the wrong test people reach for
    most often.
    """
    seeds = sorted(set(a_preds) & set(b_preds))
    if not seeds:
        return {"available": False,
                "reason": "no seed has predictions for both models"}
    shared = None
    for seed in seeds:
        ids = set(a_preds[seed]) & set(b_preds[seed])
        shared = ids if shared is None else (shared & ids)
    shared = sorted(shared or [])
    if len(shared) < 20:
        return {"available": False,
                "reason": f"only {len(shared)} id(s) are shared by both models across "
                          f"all seeds — too few for a resampled interval"}

    def score(sample_ids, preds_by_seed):
        values = []
        for seed in seeds:
            table = preds_by_seed[seed]
            if metric in PROB_METRICS:
                pairs = [(1 if _coerce(table[i]["y"]) == positive else 0, table[i]["prob"])
                         for i in sample_ids if table[i]["prob"] is not None]
                value = _auc(pairs) if pairs else None
            elif metric in LABEL_METRICS:
                pairs = [(_coerce(table[i]["y"]), _coerce(table[i]["pred"]))
                         for i in sample_ids]
                value = label_metric(metric, pairs, positive)
            else:
                pairs = [(table[i]["y"], table[i]["pred"]) for i in sample_ids]
                value = regression_metric(metric, pairs)
            if value is not None:
                values.append(value)
        return sum(values) / len(values) if values else None

    def difference(sample_ids):
        a, b = score(sample_ids, a_preds), score(sample_ids, b_preds)
        return None if a is None or b is None else a - b

    point = difference(shared)
    interval = bootstrap_ci(shared, difference, resamples=resamples)
    if point is None or interval is None:
        return {"available": False,
                "reason": "the metric was undefined in too many resamples to make an "
                          "interval mean anything"}
    return {"available": True, "delta": round(point, 6),
            "ci95": list(interval), "n_ids": len(shared), "seeds": seeds,
            "resamples": resamples,
            "crosses_zero": bool(interval[0] <= 0 <= interval[1])}


# ---------------------------------------------------------------- rendering

def _cell(stats: dict | None) -> str:
    if not stats:
        return "—"
    if stats.get("std") is None:
        return f"{stats['mean']:.3f} (1 seed)"
    return f"{stats['mean']:.3f} ± {stats['std']:.3f}"


def _delta_cell(diff: dict | None) -> str:
    if diff is None:
        return "—"
    if not diff.get("available"):
        return f"not computed ({diff['reason']})"
    lo, hi = diff["ci95"]
    verdict = "cannot be distinguished from noise" if diff["crosses_zero"] else \
        "interval excludes zero"
    return f"{diff['delta']:+.3f} [{lo:+.3f}, {hi:+.3f}] — {verdict}"


def _tex(text: str) -> str:
    """Escape a cell for LaTeX, then restore the two symbols a table needs as maths.

    `%` is the one that matters: an unescaped per-cent sign in "95% CI" comments
    out the rest of the row, and the table compiles — missing a column, silently.
    """
    out = (text.replace("\\", r"\textbackslash{}").replace("&", r"\&")
           .replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")
           .replace("$", r"\$"))
    return (out.replace("±", r"$\pm$").replace("Δ", r"$\Delta$")
            .replace("—", "--").replace("–", "--"))


def render(rows, metric, reference, fmt) -> str:
    headers = ["Model", metric, "Seeds", "n"]
    if reference:
        headers.append(f"Δ vs {reference} (95% CI, paired bootstrap)")
    if fmt == "csv":
        out = [",".join(headers)]
        for r in rows:
            cells = [r["model"], _cell(r["stats"]),
                     " ".join(str(s) for s in r["seeds"]), str(r["runs"])]
            if reference:
                cells.append(_delta_cell(r.get("delta")))
            out.append(",".join('"' + c.replace('"', '""') + '"' for c in cells))
        return "\n".join(out) + "\n"
    if fmt == "latex":
        spec = "l" + "r" * (len(headers) - 1)
        lines = [r"\begin{table}[htbp]", r"  \centering",
                 r"  \caption{Results by model. Mean $\pm$ standard deviation over "
                 r"seeds; no ranking is implied.}",
                 rf"  \label{{tab:results-{metric}}}",
                 rf"  \begin{{tabular}}{{{spec}}}", r"    \toprule",
                 "    " + " & ".join(_tex(h) for h in headers) + r" \\",
                 r"    \midrule"]
        for r in rows:
            cells = [_tex(r["model"]), _tex(_cell(r["stats"])),
                     "--".join([str(r["seeds"][0]), str(r["seeds"][-1])])
                     if len(r["seeds"]) > 1 else str(r["seeds"][0]),
                     str(r["runs"])]
            if reference:
                cells.append(_tex(_delta_cell(r.get("delta"))))
            lines.append("    " + " & ".join(cells) + r" \\")
        lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}", ""]
        return "\n".join(lines)
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        cells = [r["model"], _cell(r["stats"]),
                 f"{r['seeds'][0]}–{r['seeds'][-1]}" if len(r["seeds"]) > 1
                 else str(r["seeds"][0]), str(r["runs"])]
        if reference:
            cells.append(_delta_cell(r.get("delta")))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-file", default=DEFAULT_RUNS)
    ap.add_argument("--experiment", help="restrict to one experiment name")
    ap.add_argument("--metric", required=True)
    ap.add_argument("--reference", metavar="MODEL",
                    help="compute Δ against this model, as a paired bootstrap interval")
    ap.add_argument("--positive", default="1",
                    help="positive class label for f1/precision/recall/roc_auc "
                         "(default 1)")
    ap.add_argument("--resamples", type=int, default=2000)
    ap.add_argument("--format", default="markdown", choices=("markdown", "latex", "csv"))
    ap.add_argument("--out", metavar="FILE",
                    help="default analysis/tables/<experiment>-<metric>.<ext>")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.runs_file, "--runs-file")
    runs = read_jsonl(args.runs_file)
    if args.experiment:
        runs = [r for r in runs if r.get("experiment") == args.experiment]
    runs = [r for r in runs if args.metric in (r.get("metrics") or {})]
    if not runs:
        die(f"no runs in {args.runs_file} carry metric {args.metric!r}"
            + (f" for experiment {args.experiment!r}" if args.experiment else "")
            + " — check the name with: python scripts/experiment_db.py summary", code=2)

    summary = experiment_db.summarise(runs, args.metric, args.experiment)
    positive = _coerce(args.positive)
    reference_preds = load_predictions(runs, args.reference) if args.reference else None
    if args.reference and not reference_preds:
        reference_note = (f"reference model {args.reference!r} has no prediction files "
                          f"on disk — Δ cannot be paired")
    else:
        reference_note = None

    # Register order — first appearance in runs.jsonl. `summarise` sorts its
    # groups alphabetically, which is not the register's order and would put a
    # model called "a-net" above the baseline it is being compared against.
    order = {}
    for rec in runs:
        order.setdefault(rec.get("model"), len(order))
    groups = sorted(summary["groups"], key=lambda g: order.get(g["model"], len(order)))

    rows = []
    for group in groups:
        row = {"model": group["model"], "seeds": group["seeds"], "runs": group["runs"],
               "stats": group["metrics"].get(args.metric)}
        if args.reference and group["model"] != args.reference:
            if reference_note:
                row["delta"] = {"available": False, "reason": reference_note}
            elif args.metric not in BOOTSTRAPPABLE:
                row["delta"] = {"available": False,
                                "reason": f"{args.metric} is not one this script can "
                                          f"recompute from predictions"}
            else:
                own = load_predictions(runs, group["model"])
                row["delta"] = (paired_difference(args.metric, own, reference_preds,
                                                  positive, args.resamples) if own
                                else {"available": False,
                                      "reason": "no prediction files for this model"})
        rows.append(row)

    text = render(rows, args.metric, args.reference, args.format)
    suffix = {"markdown": ".md", "latex": ".tex", "csv": ".csv"}[args.format]
    out = Path(args.out) if args.out else Path("analysis/tables") / (
        f"{args.experiment or 'runs'}-{args.metric}{suffix}")
    require_within_cwd(out.as_posix(), "--out")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    emit({"experiment": args.experiment, "metric": args.metric,
          "models": [r["model"] for r in rows], "reference": args.reference,
          "single_seed_groups": [r["model"] for r in rows if len(r["seeds"]) < 2],
          "deltas": {r["model"]: r["delta"] for r in rows if r.get("delta")},
          "written": out.as_posix(), "format": args.format,
          "note": ("rows are in register order, not score order, and nothing is bold: "
                   "a table that nominates a winner has made a claim its interval may "
                   "not support")}, args.json_out)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read or write a file — {e}")
    except json.JSONDecodeError as e:
        die(f"a prediction file is not readable — {e}")
