#!/usr/bin/env python3
"""train_runner.py — the training loop as a recorded procedure, not an improvised script.

WHY THIS EXISTS
`/experiment` had a design step, a leakage check and a run register, and between
them a hole: the script that actually produced the numbers was written fresh
every session. That is the one artefact in the empirical half where improvisation
is most expensive. Fitting the imputer before the split, a random_state left at
its default, a fold that shares a patient with its own test set, a losing run
quietly not written down — none of these look like errors. They look like results.

This runs the matrix from a config file instead:

  * preprocessing is fitted **inside** each fold because it is a Pipeline, so the
    manifest's `preprocessing_fitted: "within-fold"` is true by construction
    rather than by declaration — the one leak `leakage_check.py` can only take
    the author's word for;
  * every (model, seed) pair becomes a row in `analysis/runs.jsonl`, including
    the ones that lose, written through `experiment_db.py`;
  * the split manifest and the per-fold predictions are written as the run
    happens, so the leakage check and the paired comparison later run on the
    actual partition rather than a reconstruction of it.

WHAT IT REFUSES
- **To train on unregistered data.** The dataset id must exist in
  `analysis/datasets.jsonl`, and its files must still hash to what the register
  recorded. Training on drifted bytes produces numbers nothing can reconcile.
- **To run seedless.** `seeds` is required and every estimator that accepts a
  `random_state` gets one. A single unseeded run is not a result.
- **To name a winner.** No `--best`, no ranking, no bolding. Which mean is larger
  is not the finding; whether the difference survives resampling is, and that is
  `results_table.py --reference`, computed from the predictions this writes.
- **To hide the floor.** A trivial baseline (majority class / mean) is added to
  every matrix unless `--no-baseline` is passed, and its absence is reported. A
  model compared only against other models has no floor under it.
- **To silently drop rows.** Missing targets, unusable columns and dropped
  features are counted and reported, never handled quietly.

USAGE
  python scripts/train_runner.py --config analysis/experiment.json --dry-run
  python scripts/train_runner.py --config analysis/experiment.json
  python scripts/train_runner.py --config analysis/experiment.json --no-record

Config (analysis/experiment.json):
  {"experiment": "baselines", "dataset": "DS-0001",
   "data": "analysis/data/features.csv", "target": "label",
   "task": "classification", "id_column": "sample_id", "group_column": "patient_id",
   "protocol": {"kind": "kfold", "folds": 5, "stratified": true},
   "seeds": [42, 43, 44, 45, 46],
   "metrics": ["roc_auc", "f1", "accuracy"],
   "preprocessing": {"impute": "median", "scale": true, "one_hot": true},
   "models": {"logreg": {"type": "logreg", "C": 1.0},
              "gbdt": {"type": "gbdt", "max_iter": 200}}}

Exit codes: 0 ran · 1 error · 2 refused (unregistered/drifted data, config problem)
· 3 BLOCKED (scikit-learn/pandas/numpy not installed).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd  # noqa: E402

SCRIPTS = Path(__file__).parent
DEFAULT_CONFIG = "analysis/experiment.json"
DEFAULT_REGISTER = "analysis/datasets.jsonl"
ML_HINT = ("scikit-learn, pandas and numpy are not installed. They are deliberately "
           "not core dependencies of this kit — install them when you train: "
           "pip install -r requirements-ml.txt")


def _ml():
    """Import the ML stack on first use, or exit BLOCKED with the install line.

    Deferred rather than top-level so that `--help`, config validation and every
    other script in the kit keep working on a machine that will never train
    anything — the same contract pandoc and latexmk have in the build scripts.
    """
    try:
        import numpy as np
        import pandas as pd
        import sklearn  # noqa: F401
    except ImportError:
        print(f"BLOCKED: {ML_HINT}", file=sys.stderr)
        sys.exit(3)
    return np, pd


def model_registry(task: str) -> dict:
    """type → (constructor, defaults). Import-time cost paid only when training."""
    from sklearn.dummy import DummyClassifier, DummyRegressor
    from sklearn.ensemble import (ExtraTreesClassifier, ExtraTreesRegressor,
                                  HistGradientBoostingClassifier,
                                  HistGradientBoostingRegressor,
                                  RandomForestClassifier, RandomForestRegressor)
    from sklearn.linear_model import (LinearRegression, LogisticRegression, Ridge)
    from sklearn.naive_bayes import GaussianNB
    from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    from sklearn.svm import SVC, SVR
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
    if task == "classification":
        return {
            "majority": (DummyClassifier, {"strategy": "most_frequent"}),
            "stratified": (DummyClassifier, {"strategy": "stratified"}),
            "logreg": (LogisticRegression, {"max_iter": 1000}),
            "random_forest": (RandomForestClassifier, {"n_estimators": 300}),
            "extra_trees": (ExtraTreesClassifier, {"n_estimators": 300}),
            "gbdt": (HistGradientBoostingClassifier, {}),
            "svm": (SVC, {"probability": True}),
            "knn": (KNeighborsClassifier, {}),
            "decision_tree": (DecisionTreeClassifier, {}),
            "mlp": (MLPClassifier, {"max_iter": 500}),
            "naive_bayes": (GaussianNB, {}),
        }
    return {
        "mean": (DummyRegressor, {"strategy": "mean"}),
        "median": (DummyRegressor, {"strategy": "median"}),
        "linear": (LinearRegression, {}),
        "ridge": (Ridge, {}),
        "random_forest": (RandomForestRegressor, {"n_estimators": 300}),
        "extra_trees": (ExtraTreesRegressor, {"n_estimators": 300}),
        "gbdt": (HistGradientBoostingRegressor, {}),
        "svr": (SVR, {}),
        "knn": (KNeighborsRegressor, {}),
        "decision_tree": (DecisionTreeRegressor, {}),
        "mlp": (MLPRegressor, {"max_iter": 500}),
    }


TRIVIAL = {"classification": ("majority", {"type": "majority"}),
           "regression": ("mean", {"type": "mean"})}

CLASSIFICATION_METRICS = ("accuracy", "balanced_accuracy", "f1", "precision", "recall",
                          "roc_auc", "pr_auc", "mcc")
REGRESSION_METRICS = ("rmse", "mae", "r2", "mape")


def compute_metrics(task, names, y_true, y_pred, y_prob):
    """Every requested metric, or an honest absence.

    A metric that cannot be computed for this data (ROC-AUC on a fold with one
    class present, PR-AUC without probabilities) is left out of the record rather
    than filled with a zero — a zero is a number a reader will average.
    """
    import numpy as np
    from sklearn import metrics as M
    out = {}
    if task == "classification":
        classes = sorted(set(np.asarray(y_true).tolist()))
        binary = len(classes) == 2
        avg = "binary" if binary else "macro"
        for name in names:
            try:
                if name == "accuracy":
                    out[name] = float(M.accuracy_score(y_true, y_pred))
                elif name == "balanced_accuracy":
                    out[name] = float(M.balanced_accuracy_score(y_true, y_pred))
                elif name == "f1":
                    out[name] = float(M.f1_score(y_true, y_pred, average=avg,
                                                 zero_division=0))
                elif name == "precision":
                    out[name] = float(M.precision_score(y_true, y_pred, average=avg,
                                                        zero_division=0))
                elif name == "recall":
                    out[name] = float(M.recall_score(y_true, y_pred, average=avg,
                                                     zero_division=0))
                elif name == "mcc":
                    out[name] = float(M.matthews_corrcoef(y_true, y_pred))
                elif name == "roc_auc" and y_prob is not None and len(classes) > 1:
                    if binary:
                        out[name] = float(M.roc_auc_score(y_true, y_prob[:, 1]))
                    else:
                        out[name] = float(M.roc_auc_score(y_true, y_prob,
                                                          multi_class="ovr",
                                                          average="macro"))
                elif name == "pr_auc" and y_prob is not None and binary:
                    out[name] = float(M.average_precision_score(y_true, y_prob[:, 1]))
            except ValueError:
                continue  # reported by its absence, never by a placeholder
    else:
        for name in names:
            try:
                if name == "rmse":
                    out[name] = float(M.mean_squared_error(y_true, y_pred) ** 0.5)
                elif name == "mae":
                    out[name] = float(M.mean_absolute_error(y_true, y_pred))
                elif name == "r2":
                    out[name] = float(M.r2_score(y_true, y_pred))
                elif name == "mape":
                    out[name] = float(M.mean_absolute_percentage_error(y_true, y_pred))
            except ValueError:
                continue
    return out


def load_config(path: str) -> dict:
    p = Path(path)
    if not p.is_file():
        die(f"{path} does not exist — /experiment scaffolds it, or write it by hand "
            f"(see this script's docstring for the shape)")
    try:
        cfg = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON — {e.msg} (line {e.lineno})")
    for field in ("experiment", "dataset", "data", "target", "models"):
        if not cfg.get(field):
            die(f"config is missing {field!r}")
    task = cfg.setdefault("task", "classification")
    if task not in ("classification", "regression"):
        die(f"task {task!r} must be 'classification' or 'regression'")
    seeds = cfg.get("seeds")
    if not isinstance(seeds, list) or not seeds or not all(
            isinstance(s, int) and not isinstance(s, bool) for s in seeds):
        die("config needs 'seeds': a non-empty list of integers. A run nobody can "
            "repeat is not evidence, so there is no default here.")
    if not isinstance(cfg["models"], dict) or not cfg["models"]:
        die("'models' must be a non-empty object: {name: {\"type\": \"logreg\", …}}")
    protocol = cfg.setdefault("protocol", {"kind": "kfold", "folds": 5,
                                           "stratified": task == "classification"})
    if protocol.get("kind") not in ("kfold", "group-kfold", "holdout", "timeseries"):
        die("protocol.kind must be kfold | group-kfold | holdout | timeseries")
    if protocol["kind"] == "group-kfold" and not cfg.get("group_column"):
        die("protocol.kind 'group-kfold' needs 'group_column' — the column whose "
            "values must never straddle a fold boundary (patient, subject, session)")
    known = set(CLASSIFICATION_METRICS if task == "classification" else REGRESSION_METRICS)
    metrics = cfg.setdefault("metrics", sorted(known))
    unknown = [m for m in metrics if m not in known]
    if unknown:
        die(f"unknown metric(s) {unknown} for task {task!r} — known: {sorted(known)}")
    cfg.setdefault("preprocessing", {"impute": "median", "scale": True, "one_hot": True})
    return cfg


def dataset_state(register: str, ds_id: str) -> dict:
    """The register's own verdict on this dataset, reused rather than re-implemented."""
    import dataset_db
    records = read_jsonl(register)
    if not records:
        return {"status": "UNREGISTERED",
                "problem": f"{register} holds no datasets — register the data before "
                           f"training on it (/find-dataset, or dataset_db.py add)"}
    if not any(r.get("id") == ds_id for r in records):
        return {"status": "UNREGISTERED",
                "problem": f"dataset {ds_id!r} is not in {register}"}
    report = dataset_db.verify(records, ds_id)["datasets"][0]
    return report


def build_pipeline(estimator, feature_frame, prep: dict):
    """A Pipeline, so the fit happens inside the fold by construction.

    This is the whole reason the runner exists: the same three lines written by
    hand at the top of an analysis script — impute, scale, encode — fit on the
    whole table and put the test fold's distribution into the training data. Here
    they cannot, because the caller never gets a chance to fit them.
    """
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    numeric = [c for c in feature_frame.columns
               if str(feature_frame[c].dtype).startswith(("int", "float"))]
    categorical = [c for c in feature_frame.columns if c not in numeric]
    steps_num = [("impute", SimpleImputer(strategy=prep.get("impute", "median")))]
    if prep.get("scale", True):
        steps_num.append(("scale", StandardScaler()))
    blocks = [("num", Pipeline(steps_num), numeric)]
    if categorical and prep.get("one_hot", True):
        try:
            encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        except TypeError:  # pragma: no cover - scikit-learn < 1.2
            encoder = OneHotEncoder(handle_unknown="ignore", sparse=False)
        blocks.append(("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", encoder)]), categorical))
    return Pipeline([("prep", ColumnTransformer(blocks, remainder="drop")),
                     ("model", estimator)]), numeric, categorical


def make_estimator(spec: dict, task: str, seed: int):
    registry = model_registry(task)
    kind = spec.get("type")
    if kind not in registry:
        die(f"model type {kind!r} is not known for task {task!r} — available: "
            f"{sorted(registry)}. Pass hyperparameters as sibling keys, e.g. "
            f'{{"type": "gbdt", "max_iter": 200}}')
    cls, defaults = registry[kind]
    params = {**defaults, **{k: v for k, v in spec.items() if k != "type"}}
    try:
        estimator = cls(**params)
    except TypeError as e:
        die(f"{kind} rejected its parameters — {e}")
    if "random_state" in estimator.get_params():
        estimator.set_params(random_state=seed)
    return estimator, params


def splitter_for(cfg: dict, seed: int, y, groups):
    from sklearn.model_selection import (GroupKFold, KFold, StratifiedGroupKFold,
                                         StratifiedKFold, TimeSeriesSplit,
                                         train_test_split)
    protocol = cfg["protocol"]
    kind, folds = protocol["kind"], int(protocol.get("folds", 5))
    stratify = bool(protocol.get("stratified", cfg["task"] == "classification"))
    if kind == "holdout":
        size = float(protocol.get("test_size", 0.2))
        idx = list(range(len(y)))
        train, test = train_test_split(
            idx, test_size=size, random_state=seed,
            stratify=(y if stratify and cfg["task"] == "classification" else None))
        return [(train, test)], f"holdout({size})"
    if kind == "timeseries":
        # No randomness by design: an ordered split is the same split every time.
        # Seeds then vary only model initialisation, and the record says so.
        return list(TimeSeriesSplit(n_splits=folds).split(range(len(y)))), \
            f"timeseries({folds})"
    if kind == "group-kfold":
        if stratify and cfg["task"] == "classification":
            cv = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
        else:
            try:
                cv = GroupKFold(n_splits=folds, shuffle=True, random_state=seed)
            except TypeError:  # pragma: no cover - scikit-learn < 1.6
                cv = GroupKFold(n_splits=folds)
        return list(cv.split(range(len(y)), y, groups)), f"group-kfold({folds})"
    cv = (StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
          if stratify and cfg["task"] == "classification"
          else KFold(n_splits=folds, shuffle=True, random_state=seed))
    return list(cv.split(range(len(y)), y)), f"{'stratified-' if stratify else ''}kfold({folds})"


def write_splits(path: Path, cfg: dict, ids, fold_pairs, protocol_label: str):
    folds = [{"fold": i, "train": [str(ids[j]) for j in train],
              "test": [str(ids[j]) for j in test]}
             for i, (train, test) in enumerate(fold_pairs)]
    manifest = {
        "dataset": cfg["dataset"], "protocol": protocol_label,
        "id_column": cfg.get("id_column") or "_row_index",
        "target": cfg["target"], "group_column": cfg.get("group_column"),
        # True by construction: the preprocessing is a Pipeline step, so it is
        # fitted on the training half of each fold and nowhere else.
        "preprocessing_fitted": "within-fold",
        "folds": folds,
        "note": ("written by train_runner.py as the split happened. Seeds vary the "
                 "partition; this manifest holds the first seed's, which is the one "
                 "leakage_check.py reads."),
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def record_runs(records: list[dict], runs_file: str, register: str) -> dict:
    """experiment_db.py stays the register's only writer; this hands it the batch."""
    stream = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "experiment_db.py"), "--file", runs_file,
         "--datasets", register, "add", "--stdin"],
        input=stream, capture_output=True, text=True, encoding="utf-8", timeout=300)
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout or "").strip()}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"error": f"experiment_db.py returned unreadable output: {proc.stdout[:200]}"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--register", default=DEFAULT_REGISTER)
    ap.add_argument("--runs-file", default="analysis/runs.jsonl")
    ap.add_argument("--out-dir", default="analysis")
    ap.add_argument("--no-baseline", action="store_true",
                    help="do not add the trivial baseline (and say so in the report)")
    ap.add_argument("--no-record", action="store_true",
                    help="train and write predictions, but do not touch runs.jsonl")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the matrix and its cost; train nothing, write nothing")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    require_within_cwd(args.config, "--config")
    require_within_cwd(args.out_dir, "--out-dir")
    cfg = load_config(args.config)
    require_within_cwd(cfg["data"], "config.data")
    task, seeds = cfg["task"], cfg["seeds"]

    models = dict(cfg["models"])
    baseline_added = None
    trivial_name, trivial_spec = TRIVIAL[task]
    has_trivial = any((m.get("type") in ("majority", "stratified", "mean", "median"))
                      for m in models.values())
    if not has_trivial and not args.no_baseline:
        models[trivial_name] = trivial_spec
        baseline_added = trivial_name

    matrix = [(name, seed) for name in models for seed in seeds]
    state = dataset_state(args.register, cfg["dataset"])
    blocking = state.get("status") in ("UNREGISTERED", "MISSING", "DRIFT")

    if args.dry_run or blocking:
        emit({"experiment": cfg["experiment"], "task": task,
              "dataset": {"id": cfg["dataset"], **state},
              "models": sorted(models), "seeds": seeds,
              "protocol": cfg["protocol"], "metrics": cfg["metrics"],
              "runs": len(matrix), "baseline_added": baseline_added,
              "result": "REFUSED" if blocking else "DRY-RUN",
              "note": ("nothing was trained. " + (
                  "The data must be registered and its bytes must still match before a "
                  "run can be recorded against it." if blocking else
                  "A matrix printed and rejected costs a minute; a matrix run and "
                  "rejected costs an evening."))}, args.json_out)
        sys.exit(2 if blocking else 0)

    np, pd = _ml()
    import env_capture
    env, _ = env_capture.capture()

    data_path = Path(cfg["data"])
    if not data_path.is_file():
        die(f"{cfg['data']} does not exist")
    frame = (pd.read_csv(data_path) if data_path.suffix.lower() in (".csv", ".txt")
             else pd.read_parquet(data_path) if data_path.suffix.lower() == ".parquet"
             else pd.read_csv(data_path, sep="\t"))
    if cfg["target"] not in frame.columns:
        die(f"target column {cfg['target']!r} is not in {cfg['data']} "
            f"(columns: {list(frame.columns)[:20]})")
    before = len(frame)
    frame = frame.dropna(subset=[cfg["target"]])
    dropped_rows = before - len(frame)

    reserved = {cfg["target"], cfg.get("id_column"), cfg.get("group_column"),
                cfg.get("time_column")} - {None}
    features = cfg.get("features") or [c for c in frame.columns if c not in reserved]
    missing_features = [c for c in features if c not in frame.columns]
    if missing_features:
        die(f"features not in the data: {missing_features}")
    X = frame[features]
    y = frame[cfg["target"]]
    groups = frame[cfg["group_column"]] if cfg.get("group_column") else None
    ids = (frame[cfg["id_column"]].astype(str).tolist() if cfg.get("id_column")
           else [str(i) for i in range(len(frame))])
    if cfg.get("id_column") and len(set(ids)) != len(ids):
        die(f"id column {cfg['id_column']!r} has duplicate values — the split manifest "
            f"and the leakage check both key on it")

    out_dir = Path(args.out_dir)
    pred_dir = out_dir / "predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)
    splits_dir = out_dir / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)

    records, per_model_notes = [], {}
    first_manifest = None
    started_all = time.monotonic()
    for seed in seeds:
        fold_pairs, protocol_label = splitter_for(cfg, seed, y, groups)
        manifest = write_splits(splits_dir / f"seed-{seed}.json", cfg, ids, fold_pairs,
                                protocol_label)
        if first_manifest is None:
            first_manifest = manifest
            (out_dir / "splits.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        for name, spec in models.items():
            estimator, params = make_estimator(spec, task, seed)
            pipeline, numeric, categorical = build_pipeline(estimator, X,
                                                            cfg["preprocessing"])
            per_model_notes[name] = {"numeric_features": len(numeric),
                                     "categorical_features": len(categorical)}
            fold_metrics, rows = [], []
            started = time.monotonic()
            for fold, (train_idx, test_idx) in enumerate(fold_pairs):
                pipeline.fit(X.iloc[train_idx], y.iloc[train_idx])
                y_pred = pipeline.predict(X.iloc[test_idx])
                y_prob = None
                if task == "classification" and hasattr(pipeline, "predict_proba"):
                    try:
                        y_prob = pipeline.predict_proba(X.iloc[test_idx])
                    except (AttributeError, ValueError):
                        y_prob = None
                fold_metrics.append(compute_metrics(task, cfg["metrics"],
                                                    y.iloc[test_idx].to_numpy(),
                                                    y_pred, y_prob))
                for k, row_i in enumerate(test_idx):
                    rows.append({"fold": fold, "id": ids[row_i],
                                 "y_true": y.iloc[row_i],
                                 "y_pred": y_pred[k],
                                 "y_prob": (float(y_prob[k][1]) if y_prob is not None
                                            and y_prob.shape[1] == 2 else "")})
            duration = round(time.monotonic() - started, 2)
            names = sorted({m for fm in fold_metrics for m in fm})
            aggregated = {m: round(float(np.mean([fm[m] for fm in fold_metrics
                                                  if m in fm])), 6)
                          for m in names}
            if not aggregated:
                die(f"no metric could be computed for {name!r} — check that the "
                    f"requested metrics fit the task and the label distribution")
            pred_file = pred_dir / f"{cfg['experiment']}__{name}__seed{seed}.csv"
            pd.DataFrame(rows).to_csv(pred_file, index=False)
            records.append({
                "experiment": cfg["experiment"], "model": name, "dataset": cfg["dataset"],
                "seed": seed, "metrics": aggregated,
                "config": {"type": spec.get("type"), "params": params,
                           "protocol": protocol_label, "features": len(features),
                           "preprocessing": cfg["preprocessing"]},
                "per_fold": fold_metrics, "env": env,
                "script": "scripts/train_runner.py", "predictions": pred_file.as_posix(),
                "duration_s": duration,
                "notes": f"config {Path(args.config).as_posix()}",
            })

    leakage = subprocess.run(
        [sys.executable, str(SCRIPTS / "leakage_check.py"),
         "--splits", (out_dir / "splits.json").as_posix(), "--data", cfg["data"]],
        capture_output=True, text=True, encoding="utf-8", timeout=300)
    try:
        leakage_report = json.loads(leakage.stdout)
    except json.JSONDecodeError:
        leakage_report = {"error": (leakage.stderr or leakage.stdout or "")[:300]}

    recorded = {"skipped": "--no-record"} if args.no_record else record_runs(
        records, args.runs_file, args.register)

    emit({"experiment": cfg["experiment"], "task": task, "dataset": cfg["dataset"],
          "runs": len(records), "models": sorted(models), "seeds": seeds,
          "protocol": first_manifest["protocol"] if first_manifest else None,
          "rows_used": len(frame), "rows_dropped_missing_target": dropped_rows,
          "features": {"count": len(features), **(per_model_notes.get(
              next(iter(models)), {}) if per_model_notes else {})},
          "baseline_added": baseline_added,
          "environment": env["hash"], "elapsed_s": round(time.monotonic() - started_all, 1),
          "splits": (out_dir / "splits.json").as_posix(),
          "predictions_dir": pred_dir.as_posix(),
          "leakage_check": {"result": leakage_report.get("result"),
                            "findings": leakage_report.get("findings",
                                                           leakage_report.get("error"))},
          "recorded": recorded,
          "next": ["python scripts/results_table.py --experiment " + cfg["experiment"] +
                   " --metric " + cfg["metrics"][0] + " --reference " +
                   (baseline_added or sorted(models)[0]),
                   "python scripts/results_figure.py --experiment " + cfg["experiment"] +
                   " --metric " + cfg["metrics"][0]],
          "note": ("no winner is declared here. The per-fold predictions are on disk so "
                   "the comparison can be made where the pairing still exists — "
                   "results_table.py --reference")}, args.json_out)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("interrupted — runs already recorded stay recorded; re-running appends "
            "rather than replacing, which is what a register is for", code=1)
    except OSError as e:
        die(f"failed to read or write a file — {e}")
