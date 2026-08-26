#!/usr/bin/env python3
"""results_figure.py — the results figure, drawn from the run register.

WHY THIS EXISTS
The numbers in a results table come from `runs.jsonl`; the figure beside it was
drawn by whatever script happened to be open, with whatever default colours
matplotlib ships, and — most often — as a bar chart of five means with no spread
at all. Bars of means are how a 0.002 difference becomes a visual argument.

This draws the seeds. Every run is a point, the mean is a line, ±1 standard
deviation is a bar, and models appear in register order rather than sorted by
score, so the picture makes the same claim as the table: here is the spread, judge
the difference yourself.

WHAT IT REFUSES
- **To sort by score.** Register order, always. A sorted axis is a ranking, and
  ranking without an interval is the overclaim this kit's own first run made.
- **To draw a bar where there is one seed.** A single run is drawn as a single
  point, labelled, because an error bar over n=1 is a drawing of nothing.
- **To invent a caption.** The caption states the experiment, the metric, the
  seed count, what the bar means and what the figure does not say. It is written
  to `analysis/captions.md`, where the drafting step reads it — a figure whose
  caption is written months later is where "±" silently becomes "standard error".
- **To use colour to carry the meaning.** The palette is Okabe–Ito (colourblind
  safe) and every group is also separated by position; the figure survives being
  printed in greyscale, which is still how a thesis is examined.

USAGE
  python scripts/results_figure.py --experiment baselines --metric roc_auc
  python scripts/results_figure.py --experiment baselines --metric rmse --lang en

Exit codes: 0 drawn · 1 error · 2 nothing to draw · 3 BLOCKED (matplotlib absent).
"""
from __future__ import annotations

import argparse
import datetime
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import experiment_db  # noqa: E402
from lib_common import die, emit, read_jsonl, require_within_cwd  # noqa: E402

DEFAULT_RUNS = "analysis/runs.jsonl"
# Okabe–Ito: eight hues distinguishable under the common colour-vision
# deficiencies, and distinguishable from each other in greyscale.
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9",
           "#F0E442", "#000000"]
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
DPI = 300

CAPTIONS = {
    "tr": ("Şekil. {experiment} deneyinde {metric} değerinin modellere göre dağılımı. "
           "Her nokta bir tohumun sonucudur ({seeds} tohum, {runs} koşu); yatay çizgi "
           "ortalamayı, dikey çubuk ±1 standart sapmayı gösterir. Modeller kayıt "
           "sırasındadır — sıralama yapılmamıştır ve şekil hiçbir farkın anlamlı "
           "olduğunu iddia etmez; fark aralıkları sonuç tablosundadır. Veri: {dataset}."),
    "en": ("Figure. Distribution of {metric} by model in experiment {experiment}. "
           "Each point is one seed ({seeds} seeds, {runs} runs); the horizontal line "
           "is the mean and the vertical bar ±1 standard deviation. Models appear in "
           "register order — no ranking is implied, and the figure makes no claim "
           "about significance; the difference intervals are in the results table. "
           "Data: {dataset}."),
}


def _mpl():
    try:
        import matplotlib
    except ImportError:
        print("BLOCKED: matplotlib is not installed. It is deliberately not a core "
              "dependency of this kit — install it when you plot: "
              "pip install -r requirements-ml.txt", file=sys.stderr)
        sys.exit(3)
    matplotlib.use("Agg")  # no display on a build machine, and none needed
    import matplotlib.pyplot as plt
    return plt


def gather(runs_file: str, experiment: str | None, metric: str):
    runs = read_jsonl(runs_file)
    if experiment:
        runs = [r for r in runs if r.get("experiment") == experiment]
    runs = [r for r in runs if metric in (r.get("metrics") or {})]
    if not runs:
        die(f"no runs in {runs_file} carry metric {metric!r}"
            + (f" for experiment {experiment!r}" if experiment else ""), code=2)
    summary = experiment_db.summarise(runs, metric, experiment)
    order, points = [], {}
    for rec in runs:  # register order: first appearance wins
        model = rec.get("model")
        if model not in points:
            points[model] = []
            order.append(model)
        points[model].append((rec.get("seed"), rec["metrics"][metric]))
    return runs, summary, order, points


def draw(plt, order, points, metric, out_stem: Path, lang: str):
    fig, ax = plt.subplots(figsize=(max(4.0, 1.2 * len(order) + 1.6), 3.6))
    single_seed = []
    for i, model in enumerate(order):
        values = [v for _, v in points[model]]
        colour = PALETTE[i % len(PALETTE)]
        marker = MARKERS[i % len(MARKERS)]
        jitter = [i + (k - (len(values) - 1) / 2) * 0.06 for k in range(len(values))]
        ax.plot(jitter, values, marker, color=colour, markersize=5, alpha=0.85,
                linestyle="none", zorder=3)
        mean = statistics.fmean(values)
        ax.plot([i - 0.22, i + 0.22], [mean, mean], color=colour, linewidth=2, zorder=4)
        if len(values) > 1:
            sd = statistics.stdev(values)
            ax.plot([i, i], [mean - sd, mean + sd], color=colour, linewidth=1.2,
                    alpha=0.7, zorder=2)
        else:
            single_seed.append(model)
            ax.annotate("1 seed", (i, mean), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=7, color=colour)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order, rotation=20 if max(len(m) for m in order) > 8 else 0,
                       ha="right" if max(len(m) for m in order) > 8 else "center")
    ax.set_ylabel(metric)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_xlim(-0.6, len(order) - 0.4)
    fig.tight_layout()
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for ext in ("pdf", "png"):
        path = out_stem.with_suffix("." + ext)
        fig.savefig(path, dpi=DPI, bbox_inches="tight")
        written.append(path.as_posix())
    plt.close(fig)
    return written, single_seed


def append_caption(path: Path, text: str, figure_files: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    block = (f"\n<!-- results_figure.py · {stamp} -->\n"
             f"**{Path(figure_files[0]).name}** — {text}\n")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(block)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-file", default=DEFAULT_RUNS)
    ap.add_argument("--experiment")
    ap.add_argument("--metric", required=True)
    ap.add_argument("--lang", default="tr", choices=("tr", "en"),
                    help="caption language (default tr)")
    ap.add_argument("--out", metavar="STEM",
                    help="default analysis/figures/<experiment>-<metric>")
    ap.add_argument("--captions", default="analysis/captions.md")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.runs_file, "--runs-file")
    require_within_cwd(args.captions, "--captions")
    runs, summary, order, points = gather(args.runs_file, args.experiment, args.metric)
    plt = _mpl()
    stem = Path(args.out) if args.out else Path("analysis/figures") / (
        f"{args.experiment or 'runs'}-{args.metric}")
    require_within_cwd(stem.as_posix(), "--out")
    written, single_seed = draw(plt, order, points, args.metric, stem, args.lang)

    seeds = sorted({r.get("seed") for r in runs})
    datasets = sorted({r.get("dataset") for r in runs if r.get("dataset")})
    caption = CAPTIONS[args.lang].format(
        experiment=args.experiment or "—", metric=args.metric, seeds=len(seeds),
        runs=len(runs), dataset=", ".join(datasets) or "—")
    append_caption(Path(args.captions), caption, written)

    emit({"experiment": args.experiment, "metric": args.metric,
          "models": order, "seeds": seeds, "runs": len(runs),
          "files": written, "caption_file": args.captions, "caption": caption,
          "single_seed_models": single_seed,
          "note": ("models are in register order and nothing is sorted; the spread you "
                   "see is the spread across seeds, which is the part a bar chart of "
                   "means deletes")}, args.json_out)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read or write a file — {e}")
