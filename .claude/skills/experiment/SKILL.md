---
name: experiment
description: "Run the experiment behind an empirical paper and record it: design with methodology-advisor (baselines, splits, metrics, seeds, ablations), build the run matrix, execute through data-scientist, and write one record per run to analysis/runs.jsonl — dataset id, seed, config hash, metrics, environment fingerprint. Every number that later appears in the results section can then be traced back to the run that produced it. Gate: PROJECT.md complete and a registered dataset. Use /analyze-data for one-off analysis; use this when models are trained and compared."
disable-model-invocation: true
argument-hint: "[<what to compare>] [--seeds N] [--dry-run]"
---

# /experiment — Train, Compare, and Leave a Record

## Gate: Abort if Failed

1. **Check:** `PROJECT.md` complete (topic, RQs, type, output language not TBD).
2. **Check:** `analysis/datasets.jsonl` exists and holds at least one record.
   - If not: abort with "Önce veri: `/find-dataset` (varsa `/collect-data`).
     Kayıtlı olmayan veriyle koşu kaydı açılmıyor — sonucun girdisi kayıtsızsa
     sonuç da bağsızdır."
3. **Check:** `python scripts/dataset_db.py verify --id <DS-id>` — report DRIFT or
   MISSING before anything is trained. Training on data that no longer matches its
   record produces numbers nothing can reconcile afterwards.

## Procedure

### Step 1: Design before running — dispatch methodology-advisor

Never skip this to "just get a baseline". The decisions that cannot be repaired
afterwards are all made here.

Dispatch `methodology-advisor` with: the RQs, the task type, the dataset record
(`DS-####`, size, class balance, predefined splits), and what the author intends
to compare. Ask it for:

- the **split protocol** (holdout / k-fold / grouped / time-series — grouped and
  time-series are the two whose absence silently inflates every metric);
- the **baselines** that make the comparison meaningful, including the trivial one
  (majority class, last value, linear model) — a result with no floor under it
  is not a result;
- the **primary metric** and why, plus what it hides (accuracy under imbalance,
  ROC-AUC under heavy skew, RMSE with outliers);
- the **ablations** that would isolate each contribution;
- the **seed count** — 3 is the floor this kit's register warns below, 5–10 is
  the norm for a claim about a difference.

Present its answer to the author before running anything.

### Step 2: Build the run matrix and show the cost

```
Deney: baselines
Model:  majority · logreg · random-forest · lightgbm · <proposed>
Tohum:  42, 43, 44, 45, 46            (5)
Bölme:  5-fold stratified CV, grup=hasta_id
Metrik: ROC-AUC (birincil) · F1 · PR-AUC
→ 25 koşu × ~2 dk ≈ 50 dk
```

Ask before starting. With `--dry-run`, stop here: print the matrix and write
nothing. A matrix printed and rejected costs a minute; a matrix run and rejected
costs an evening and leaves a register full of runs nobody wanted.

### Step 3: Capture the environment once, before the first run

```bash
python scripts/env_capture.py --json > analysis/env.json
```

Python, platform, and the version of every scientific package installed, plus a
short hash. Every run in this batch carries it. Written down now rather than
recalled in the methods section three months later, which is where "scikit-learn
1.5" comes from and why it is so often wrong.

### Step 4: Run the matrix — the runner first, the agent when it cannot

Write the design from Step 1 into `analysis/experiment.json` and run it:

```bash
python scripts/train_runner.py --config analysis/experiment.json --dry-run
python scripts/train_runner.py --config analysis/experiment.json
```

This is the default path, and the reason is the one thing it does that a
hand-written script keeps not doing: preprocessing is a `Pipeline` step, so it is
fitted **inside** each fold by construction — the single leak `leakage_check.py`
can otherwise only take the author's word for. It also writes the split manifest
as it splits, saves the per-fold predictions, and records every run — including
the ones that lose — through `experiment_db.py`.

It refuses what it should: an unregistered or drifted dataset, a config with no
seeds, and a matrix with no trivial baseline (it adds one and says so).

**Dispatch `data-scientist` instead when the runner cannot express the experiment**
— a deep-learning training loop, a custom loss, a domain-specific preprocessing
chain, a model that is not in the registry (`majority · logreg · random_forest ·
extra_trees · gbdt · svm · knn · decision_tree · mlp · naive_bayes`, and their
regression counterparts). Then pass: the matrix, the dataset path AND its
`DS-####` id, the split protocol, the metrics, `analysis/env.json`, and this
instruction verbatim:

> Record every run — including the ones that lose — with
> `python scripts/experiment_db.py add --stdin`, one JSON object per run:
> `{"experiment", "model", "dataset": "DS-####", "seed", "config", "metrics",
> "env": <contents of analysis/env.json's env object>, "script", "duration_s"}`.
> A run that is not recorded did not happen, as far as the manuscript is
> concerned.

**Losing runs are recorded too.** A register holding only the configurations that
worked is how a search over 40 hyperparameter settings becomes "we used lr=0.01"
in the methods section, and the reader cannot tell the difference between a tuned
model and a lucky one.

### Step 4b: Check the split before you believe the metric

`train_runner.py` runs this check itself and reports it with the run; the step
below is what to do when `data-scientist` did the training instead.

`data-scientist` writes `analysis/splits.json` while it splits — the ids per fold,
the id column, the target, the group column if there is one, and how preprocessing
was fitted. Then:

```bash
python scripts/leakage_check.py --splits analysis/splits.json --data analysis/data/<features>.csv
```

Four leaks are arithmetic and it checks all four: the same id in train and test,
the same subject/patient/session on both sides, byte-identical rows under
different ids, and a column that maps one-to-one onto the target. Run it **before**
presenting any metric — a leak does not look like an error, it looks like a good
result, and the number is already in the author's head by the time it is checked.

What it cannot see is in its own output and belongs in the report verbatim:
preprocessing fitted outside the fold is taken from the manifest's declaration,
never detected.

### Step 5: The table comes from the register, the comparison does not

```bash
python scripts/experiment_db.py summary --experiment baselines --metric roc_auc
```

That gives mean, std, min, max and the seeds behind every group. It deliberately
declares no winner.

The table and the figure the manuscript actually carries are generated from the
same register, not typed from that JSON:

```bash
python scripts/results_table.py --experiment baselines --metric roc_auc \
    --reference majority --format latex     # or markdown / csv
python scripts/results_figure.py --experiment baselines --metric roc_auc --lang tr
```

`--reference` computes the difference as a **paired bootstrap interval** over the
per-fold predictions — the pairing is why it is far tighter than comparing two
overlapping confidence intervals, which is the wrong test people reach for most
often. When the predictions are not on disk (a `data-scientist` run that did not
save them), the column says why instead of showing a bare subtraction.

The figure draws one point per seed, not a bar of means, and both artefacts keep
register order rather than sorting by score.

Report the ranking only alongside that interval, and state a non-significant
difference as plainly as a significant one: "the top two models differ by 0.001
[-0.031, +0.033], which this experiment cannot distinguish from noise" is a
finding, not a failure.

### Step 6: Verify, then bind the numbers to the paper

```bash
python scripts/experiment_db.py verify
```

Reports: a run whose config hash no longer matches its configuration (edited after
the fact), a run pointing at a dataset that is not registered, a run with no
environment, and any group with fewer than 3 seeds — because a single seed is not
a result.

Then register the headline numbers as own-result evidence cards (`evidence_db.py`,
type `own-result`), so the drafting stage can cite them like any other evidence,
and update `analysis/counts.json` for `consistency_check.py`.

Later, from any sentence in the draft:

```bash
python scripts/experiment_db.py trace 0.809 --metric roc_auc
```

If nothing matches, the number in the manuscript came from somewhere the register
cannot see. That is exactly the question a reviewer asks and the one this whole
record exists to answer.

## Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 Deney tamamlandı — baselines
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Veri:    DS-0001 (SHA-256 doğrulandı) · 5-fold, grup=hasta_id
Koşu:    25 kayıt (5 model × 5 tohum) · ortam: py3.13.5/sk1.9.0 (a1b2c3…)

Model         ROC-AUC (ort ± ss)   Tohum
majority      0.500 ± 0.000        42–46
logreg        0.771 ± 0.021        42–46
lightgbm      0.809 ± 0.014        42–46

Karşılaştırma: lightgbm − logreg = +0.038, %95 GA [+0.012, +0.061] (eşli bootstrap)
Kayıt doğrulaması: PASS
Kartlar: EV-0091, EV-0092
```

Never present the table without the seeds column and never without the interval
next to the difference. Both are what separates a results section from a leaderboard.

## Notes

- **`/analyze-data` vs `/experiment`.** One-off EDA, a statistical test, a figure →
  `/analyze-data`. Models trained, seeds varied, configurations compared →
  here, because those produce numbers that must be traceable months later.
- **The register is not a leaderboard.** No `--best`, by design. Ranking without
  an uncertainty estimate is the single most common overclaim in applied ML
  papers, and this kit's first end-to-end run made exactly that mistake before
  a bootstrap analysis showed the ranking was not distinguishable from noise.
- **Hyperparameter search** belongs in the register too, as its own experiment
  name (`tuning`), so the reported model's selection is visible rather than
  implied.

## Reference

- **Subagents:** methodology-advisor (design; read-only) · data-scientist (executes
  inside `analysis/`, hook-scoped — for experiments the runner cannot express)
- **Scripts:** `python scripts/train_runner.py` (runs the matrix; needs
  `requirements-ml.txt`) · `python scripts/experiment_db.py` (the run record's only
  writer) · `python scripts/results_table.py` · `python scripts/results_figure.py` ·
  `python scripts/env_capture.py` · `python scripts/dataset_db.py verify` ·
  `python scripts/leakage_check.py` · `python scripts/evidence_db.py` (own-result cards)
- **Writes:** `analysis/runs.jsonl` (through experiment_db.py), `analysis/env.json`,
  `analysis/experiment.json`, `analysis/splits.json` + `analysis/splits/seed-*.json`,
  `analysis/predictions/*.csv`, `analysis/tables/`, `analysis/figures/`, plus
  whatever `data-scientist` produces under `analysis/`
- **Related:** `/find-dataset` (before), `/analyze-data` (one-off analysis),
  `/draft` (where the recorded numbers become prose), ml-research skill
  (experiment-design.md, metrics.md, reproducibility.md)

---
*A number in a results table is a claim about a run. If the run is not recorded, the claim is not checkable — by a reviewer, or by you in six months.*
