#!/usr/bin/env python3
"""experiment_db.py — the run record. The ONLY sanctioned writer of analysis/runs.jsonl.

WHY THIS EXISTS
"The model reached 0.94 ROC-AUC" is the sentence an empirical paper is built on,
and until now nothing in this kit could answer the three questions a reviewer asks
about it: which run produced it, with which seed, and on which data. The analysis
agent wrote scripts and a free-text RUNLOG; the number reaching the manuscript was
whatever the digest said, and by the time the draft was written the terminal that
produced it was gone.

Every other link in this chain is a record on disk with a script that owns it.
This is that record for the experiment: one line per run, carrying the dataset it
read (`DS-####` from `dataset_db.py`), the seed, the configuration and its hash,
the metrics, and a fingerprint of the environment it ran in.

WHAT IT REFUSES
- **A run with no seed.** Not a default of 0, not "unset" — refused. A run nobody
  can repeat is not evidence, and the field that makes it repeatable is the one
  most easily left out.
- **A run pointing at unregistered data.** The dataset id must exist in
  `analysis/datasets.jsonl`. A result whose input is unrecorded is exactly the
  unbound state this pair of registers was built to end.
- **To name a winner.** `summary` reports mean, std, min, max and the seeds behind
  each group, and stops there. Whether one model is better than another is a
  question about uncertainty, not about which mean is larger — `data-scientist`
  computes that with a paired test or bootstrap CI, by default, and this script
  deliberately gives no `--best` flag to short-circuit it.
- **To recompute your metrics.** It records what you report. `verify` re-hashes the
  configuration to catch a record edited after the fact, but a metric it never
  computed is a metric it cannot check.

USAGE
  python scripts/experiment_db.py add --payload '{"experiment":"baselines",
      "model":"lightgbm","dataset":"DS-0001","seed":42,"metrics":{"roc_auc":0.809}}'
  python scripts/experiment_db.py summary [--experiment baselines] [--metric roc_auc]
  python scripts/experiment_db.py trace 0.809 [--metric roc_auc] [--tolerance 0.001]
  python scripts/experiment_db.py verify · list · stats

Exit codes: 0 ok · 1 error · 2 verify found a problem (unregistered dataset,
single-seed group, tampered config, or a missing environment record).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import (die, emit, file_lock, next_id, parse_json_or_jsonl, read_jsonl,
                        read_stdin_text, require_within_cwd, write_jsonl)

DEFAULT_FILE = "analysis/runs.jsonl"
DEFAULT_DATASETS = "analysis/datasets.jsonl"
# Below this many seeds a group's spread is not an estimate of anything. Reported
# as a finding rather than refused at write time: the first run of an experiment
# legitimately exists alone, and refusing it would push people out of the register.
MIN_SEEDS = 3


def config_hash(config: dict) -> str:
    """SHA-256 over canonical JSON — sorted keys, no incidental whitespace.

    Canonical because the same configuration typed twice must hash the same, and
    a hash that changed with key order would report every re-run as a different
    experiment.
    """
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _known_datasets(path: str) -> set[str] | None:
    p = Path(path)
    if not p.is_file():
        return None
    return {r.get("id") for r in read_jsonl(p) if r.get("id")}


def _validate(rec: dict, known: set[str] | None, datasets_path: str):
    for field in ("experiment", "model"):
        if not rec.get(field):
            die(f"run rejected: no {field!r} — a run that cannot be grouped cannot "
                f"be summarised")
    seed = rec.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, int):
        die("run rejected: 'seed' must be an integer. A run nobody can repeat is "
            "not evidence, and this is the field most easily left out — so it is "
            "refused rather than defaulted.")
    metrics = rec.get("metrics")
    if not isinstance(metrics, dict) or not metrics:
        die("run rejected: 'metrics' must be a non-empty object, e.g. "
            '{"roc_auc": 0.809}')
    for name, value in metrics.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            die(f"run rejected: metric {name!r} is {value!r} — metrics are numbers; "
                f"a note belongs in 'notes'")
    dataset = rec.get("dataset")
    if not dataset:
        die("run rejected: no 'dataset' — register the data first (/find-dataset, "
            "or scripts/dataset_db.py add), then reference its DS-#### id. A result "
            "whose input is unrecorded is the state this register exists to end.")
    if known is None:
        die(f"run rejected: {datasets_path} does not exist, so dataset {dataset!r} "
            f"cannot be checked. Register the dataset first.")
    if dataset not in known:
        die(f"run rejected: dataset {dataset!r} is not in {datasets_path} "
            f"(known: {sorted(known) or 'none'})")


def cmd_add(args, path):
    raw = read_stdin_text() if args.stdin else args.payload
    if not raw:
        die("add requires --stdin or --payload '<object>'")
    try:
        payloads = parse_json_or_jsonl(raw)
    except json.JSONDecodeError as e:
        die(f"input is not valid JSON/JSONL — {e.msg}")
    known = _known_datasets(args.datasets)
    for rec in payloads:
        if not isinstance(rec, dict):
            die(f"record rejected: expected a JSON object, got {type(rec).__name__}")
        _validate(rec, known, args.datasets)
    added = []
    with file_lock(path):
        records = read_jsonl(path)
        for rec in payloads:
            rec.setdefault("config", {})
            rec["config_hash"] = config_hash(rec["config"])
            rec.setdefault("recorded_at", datetime.datetime.now().isoformat(timespec="seconds"))
            rec["id"] = next_id(records, "RUN")
            records.append(rec)
            added.append(rec["id"])
        write_jsonl(path, records)
    emit({"added": added, "total": len(records)}, True)


def _group_key(rec: dict) -> tuple[str, str]:
    return rec.get("experiment", "?"), rec.get("model", "?")


def summarise(records: list[dict], metric: str | None = None,
              experiment: str | None = None) -> dict:
    """Mean, std, min, max and the seeds behind each (experiment, model) group.

    No ranking, and no `--best`. Which mean is larger is not the question a paper
    answers; whether the difference survives resampling is, and that is computed
    where the predictions still exist — not here, from summary statistics that
    have already thrown the pairing away.
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for rec in records:
        if experiment and rec.get("experiment") != experiment:
            continue
        groups.setdefault(_group_key(rec), []).append(rec)
    out = []
    for (exp, model), runs in sorted(groups.items()):
        seeds = sorted({r["seed"] for r in runs})
        names = {metric} if metric else {m for r in runs for m in r.get("metrics", {})}
        stats = {}
        for name in sorted(names):
            values = [r["metrics"][name] for r in runs if name in r.get("metrics", {})]
            if not values:
                continue
            stats[name] = {
                "n": len(values), "mean": round(statistics.fmean(values), 6),
                "std": round(statistics.stdev(values), 6) if len(values) > 1 else None,
                "min": min(values), "max": max(values),
            }
        out.append({"experiment": exp, "model": model, "runs": len(runs),
                    "seeds": seeds, "metrics": stats,
                    "single_seed": len(seeds) < 2})
    return {"groups": out,
            "note": ("no ranking is reported: which mean is larger is not the "
                     "question — whether the difference survives resampling is, and "
                     "that is data-scientist's paired test, not a summary statistic")}


def cmd_summary(args, path):
    records = read_jsonl(path)
    if not records:
        die(f"{path} holds no runs — nothing to summarise")
    emit(summarise(records, args.metric, args.experiment), True)


def cmd_trace(args, path):
    """Which run produced this number?

    The question a reviewer asks about a sentence in the results section, and the
    reason a run record is worth keeping at all. Matching is on a tolerance
    because a manuscript rounds: 0.809 in prose is 0.80912... in the record.
    """
    records = read_jsonl(path)
    hits = []
    for rec in records:
        for name, value in rec.get("metrics", {}).items():
            if args.metric and name != args.metric:
                continue
            if abs(value - args.value) <= args.tolerance:
                hits.append({"id": rec["id"], "experiment": rec.get("experiment"),
                             "model": rec.get("model"), "metric": name, "value": value,
                             "seed": rec.get("seed"), "dataset": rec.get("dataset"),
                             "script": rec.get("script")})
    emit({"value": args.value, "tolerance": args.tolerance, "matches": hits,
          "note": ("no match means the number in the manuscript came from somewhere "
                   "this register cannot see — a run that was never recorded, a "
                   "hand-edit, or a different rounding")}, True)
    sys.exit(0 if hits else 2)


def verify(records: list[dict], known: set[str] | None) -> dict:
    problems, groups = [], {}
    for rec in records:
        rid = rec.get("id")
        if config_hash(rec.get("config", {})) != rec.get("config_hash"):
            problems.append({"id": rid, "problem": "config_hash does not match the "
                                                   "configuration — the record was edited after it was written"})
        if known is not None and rec.get("dataset") not in known:
            problems.append({"id": rid, "problem": f"dataset {rec.get('dataset')!r} "
                                                   f"is not in the dataset register"})
        if not rec.get("env"):
            problems.append({"id": rid, "problem": "no environment recorded — run "
                                                   "scripts/env_capture.py and store its output in 'env'"})
        groups.setdefault(_group_key(rec), set()).add(rec.get("seed"))
    for (exp, model), seeds in sorted(groups.items()):
        if len(seeds) < MIN_SEEDS:
            problems.append({"experiment": exp, "model": model,
                             "problem": f"{len(seeds)} seed(s) — a spread over fewer "
                                        f"than {MIN_SEEDS} is not an estimate of anything, "
                                        f"and a single seed is not a result"})
    return {"result": "PASS" if not problems else "FAIL", "runs": len(records),
            "groups": len(groups), "problems": problems}


def cmd_verify(args, path):
    records = read_jsonl(path)
    if not records:
        die(f"{path} holds no runs — nothing to verify")
    result = verify(records, _known_datasets(args.datasets))
    emit(result, True)
    sys.exit(0 if result["result"] == "PASS" else 2)


def cmd_list(args, path):
    records = read_jsonl(path)
    if args.experiment:
        records = [r for r in records if r.get("experiment") == args.experiment]
    if args.model:
        records = [r for r in records if r.get("model") == args.model]
    emit(records, True)


def cmd_stats(args, path):
    records = read_jsonl(path)
    by_exp, by_dataset = {}, {}
    for r in records:
        by_exp[r.get("experiment", "?")] = by_exp.get(r.get("experiment", "?"), 0) + 1
        by_dataset[r.get("dataset", "?")] = by_dataset.get(r.get("dataset", "?"), 0) + 1
    emit({"total": len(records), "by_experiment": by_exp, "by_dataset": by_dataset,
          "with_env": sum(1 for r in records if r.get("env"))}, True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", default=DEFAULT_FILE)
    ap.add_argument("--datasets", default=DEFAULT_DATASETS)
    ap.add_argument("--json", dest="json_out", action="store_true",
                    help="accepted for CLI consistency — output is always JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add")
    p_add.add_argument("--stdin", action="store_true")
    p_add.add_argument("--payload", "--json", dest="payload")
    p_s = sub.add_parser("summary")
    p_s.add_argument("--metric")
    p_s.add_argument("--experiment")
    p_t = sub.add_parser("trace")
    p_t.add_argument("value", type=float)
    p_t.add_argument("--metric")
    p_t.add_argument("--tolerance", type=float, default=0.001)
    sub.add_parser("verify")
    p_l = sub.add_parser("list")
    p_l.add_argument("--experiment")
    p_l.add_argument("--model")
    sub.add_parser("stats")
    args = ap.parse_args()
    require_within_cwd(args.file, "--file")
    require_within_cwd(args.datasets, "--datasets")
    {"add": cmd_add, "summary": cmd_summary, "trace": cmd_trace, "verify": cmd_verify,
     "list": cmd_list, "stats": cmd_stats}[args.cmd](args, args.file)


if __name__ == "__main__":
    try:
        main()
    except TimeoutError as e:
        die(f"timed out waiting for another process to release the data-file lock — {e}")
    except OSError as e:
        die(f"failed to read or write the run record — {e}")
