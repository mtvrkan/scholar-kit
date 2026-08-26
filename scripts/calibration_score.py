#!/usr/bin/env python3
"""calibration_score.py — score reviewer-critic's verdicts against a user's gold set.

An absolute rubric score is weakly interpretable without knowing the reviewer's
error profile. Two drafts can both be scored "Major Revision" by a reviewer that
is systematically harsh on cross-disciplinary work and systematically lenient on
weak methodology — the score alone never reveals which. This script measures
that profile against papers whose real outcome the user already knows.

GOLD-LABEL ISOLATION is the point of splitting this out of the review itself.
The labels live in a file the reviewer never receives; the verdicts are frozen
to disk by the orchestrator; this script is the ONLY place the two meet, and it
runs afterwards. The property is architectural, not a promise — and it is
additionally checked: a verdict record carrying a label-shaped field means the
answer was in scope while the verdict was formed, so the run is refused rather
than scored (see `--verdicts` validation below).

Positive-class convention (fixed, and stated in every report because reversing
it reverses the prose reading of the same numbers):

    positive = accept + minor_revision        negative = major_revision + reject

    FNR = FN / (FN + TP)  -> the OVER-HARSH rate: a publishable paper sent back
    FPR = FP / (FP + TN)  -> the LENIENT  rate: a flawed paper waved through

Never describe FNR as "missed rejects" or FPR as "over-rejection"; under this
convention those readings are exactly inverted.

Tiers:
  full         5-20 papers, several runs each, majority vote. Reports the
               confusion matrix, balanced accuracy, FNR/FPR with bootstrap CIs.
  directional  exactly 3 papers, one run each. Reports raw direction counts and
               REFUSES to emit FNR/FPR — three draws cannot estimate a rate, and
               printing one would be the whole failure this script exists to fix.

Inputs:
  --gold      JSONL: {"id","label","venue"?,"note"?}
              label in accept|minor_revision|major_revision|reject
  --verdicts  JSONL: {"id","run","decision","major_issues"?}
              decision in Accept|Minor Revision|Major Revision|Reject

Usage:
  python scripts/calibration_score.py --gold eval/calibration/gold.jsonl \\
      --verdicts reviews/calibration/verdicts.jsonl [--tier full] [--json]
Exit codes: 0 scored · 1 error (refused; message says why).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd
from lib_stats import bootstrap_ci

GOLD_LABELS = ("accept", "minor_revision", "major_revision", "reject")
DECISIONS = ("Accept", "Minor Revision", "Major Revision", "Reject")
POSITIVE_GOLD = {"accept", "minor_revision"}
POSITIVE_DECISION = {"Accept", "Minor Revision"}
# Fields whose presence in a verdict record means the gold answer was reachable
# while the verdict was produced. Compared in NORMALIZED form (lowercased,
# non-alphanumerics stripped) so `gold_label`, `GoldLabel`, `gold-label` and
# `Gold Label` are one field rather than four ways past the check — a safety net
# a plausible emitter spelling can walk through is not a safety net.
CONTAMINATION_FIELDS = {"label", "gold", "goldlabel", "expected", "groundtruth",
                        "truth", "answer"}


def _norm_key(key: str) -> str:
    return "".join(ch for ch in str(key).lower() if ch.isalnum())
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 20260812  # fixed so a reported CI is reproducible, not redrawn


def load_gold(path: Path) -> dict[str, dict]:
    rows = read_jsonl(path)
    if not rows:
        die(f"{path} is empty — calibration needs labelled papers")
    gold = {}
    for i, r in enumerate(rows, 1):
        pid, label = r.get("id"), r.get("label")
        if not pid:
            die(f"{path}:{i}: gold entry has no 'id'")
        if pid in gold:
            die(f"{path}:{i}: duplicate gold id {pid!r}")
        if label not in GOLD_LABELS:
            die(f"{path}:{i}: label {label!r} not in {list(GOLD_LABELS)}")
        gold[pid] = r
    return gold


def load_verdicts(path: Path, gold_ids: set[str]) -> dict[str, list[dict]]:
    rows = read_jsonl(path)
    if not rows:
        die(f"{path} is empty — run the calibration panels first")
    by_paper: dict[str, list[dict]] = {}
    for i, r in enumerate(rows, 1):
        leaked = sorted(k for k in r if _norm_key(k) in CONTAMINATION_FIELDS)
        if leaked:
            die(f"{path}:{i}: verdict record carries gold-label field(s) {leaked} — "
                f"the reviewer's context was not isolated from the answer, so this "
                f"run cannot be scored. Re-run the panels without the gold set in "
                f"scope and write verdicts carrying only id/run/decision.")
        pid, decision = r.get("id"), r.get("decision")
        if not pid:
            die(f"{path}:{i}: verdict record has no 'id'")
        if pid not in gold_ids:
            die(f"{path}:{i}: verdict for {pid!r} has no gold entry")
        if decision not in DECISIONS:
            die(f"{path}:{i}: decision {decision!r} not in {list(DECISIONS)}")
        by_paper.setdefault(pid, []).append(r)
    return by_paper


def majority_decision(runs: list[dict]) -> tuple[str, bool]:
    """Most frequent decision, and whether the runs agreed unanimously.

    Ties break toward the MORE conservative decision (later in DECISIONS): a
    reviewer split between Minor and Major has not established the friendlier
    verdict, and resolving ties optimistically would flatter the very error
    profile being measured.
    """
    counts = {d: sum(1 for r in runs if r["decision"] == d) for d in DECISIONS}
    top = max(counts.values())
    winners = [d for d in DECISIONS if counts[d] == top]
    return winners[-1], len(set(r["decision"] for r in runs)) == 1


def _bootstrap(pairs: list[tuple[bool, bool]], metric, resamples: int) -> tuple | None:
    """Percentile CI for `metric` over (gold_positive, predicted_positive) pairs.

    The implementation moved to `lib_stats.bootstrap_ci` when
    `screening_score.py` started reporting intervals too; this stays as the
    named call site, with the seed and resample count still declared here so a
    report can say which draw produced it."""
    return bootstrap_ci(pairs, metric, resamples, BOOTSTRAP_SEED)


def _rates(pairs: list[tuple[bool, bool]]) -> dict:
    tp = sum(1 for g, p in pairs if g and p)
    fn = sum(1 for g, p in pairs if g and not p)
    fp = sum(1 for g, p in pairs if not g and p)
    tn = sum(1 for g, p in pairs if not g and not p)
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn}


def _fnr(pairs):
    c = _rates(pairs)
    return c["fn"] / (c["fn"] + c["tp"]) if (c["fn"] + c["tp"]) else None


def _fpr(pairs):
    c = _rates(pairs)
    return c["fp"] / (c["fp"] + c["tn"]) if (c["fp"] + c["tn"]) else None


def _balanced_accuracy(pairs):
    c = _rates(pairs)
    if not (c["tp"] + c["fn"]) or not (c["fp"] + c["tn"]):
        return None
    tpr = c["tp"] / (c["tp"] + c["fn"])
    tnr = c["tn"] / (c["tn"] + c["fp"])
    return (tpr + tnr) / 2


def boundary_submatrix(gold: dict, predicted: dict[str, str]) -> dict | None:
    """Minor/Major crossings — the boundary the binary matrix collapses.

    This is the highest-traffic decision in practice and the one a binary
    positive/negative split hides entirely, so it is reported separately
    whenever the gold set contains both labels.
    """
    rows = {g: {"stayed": 0, "crossed": 0} for g in ("minor_revision", "major_revision")}
    present = {g["label"] for g in gold.values()}
    if not {"minor_revision", "major_revision"} <= present:
        return None
    for pid, entry in gold.items():
        label = entry["label"]
        if label not in rows or pid not in predicted:
            continue
        pred_positive = predicted[pid] in POSITIVE_DECISION
        gold_positive = label in POSITIVE_GOLD
        rows[label]["stayed" if pred_positive == gold_positive else "crossed"] += 1
    return rows


def score(gold: dict, by_paper: dict[str, list[dict]], tier: str) -> dict:
    scored_ids = sorted(by_paper)
    per_paper, predicted = [], {}
    for pid in scored_ids:
        runs = by_paper[pid]
        decision, unanimous = majority_decision(runs)
        predicted[pid] = decision
        counts = [r.get("major_issues") for r in runs if isinstance(r.get("major_issues"), int)]
        per_paper.append({
            "id": pid,
            "gold_label": gold[pid]["label"],
            "runs": len(runs),
            "decisions": [r["decision"] for r in runs],
            "predicted": decision,
            "unanimous": unanimous,
            "major_issue_range": [min(counts), max(counts)] if counts else None,
        })

    pairs = [(gold[pid]["label"] in POSITIVE_GOLD, predicted[pid] in POSITIVE_DECISION)
             for pid in scored_ids]
    matrix = _rates(pairs)
    unstable = [p["id"] for p in per_paper if p["runs"] > 1 and not p["unanimous"]]

    report = {
        "tier": tier,
        "papers": len(scored_ids),
        "runs_per_paper": sorted({len(by_paper[p]) for p in scored_ids}),
        "positive_class": "accept + minor_revision",
        "per_paper": per_paper,
        "unstable_papers": unstable,
        "boundary_submatrix": boundary_submatrix(gold, predicted),
        "caveats": [],
    }

    if tier == "directional":
        # Three single draws. Direction counts only; a rate here would be the
        # exact overclaim this tool exists to make visible.
        report["confusion_matrix"] = matrix
        report["rates"] = None
        report["caveats"].append(
            "Directional tier: n=3, one run per paper, not ensembled. These are raw "
            "direction counts, NOT an error-rate estimate. Do not quote FNR/FPR from "
            "this tier — run the full tier for a measured profile.")
        return report

    labels_present = {gold[pid]["label"] for pid in scored_ids}
    if not (labels_present & POSITIVE_GOLD) or not (labels_present - POSITIVE_GOLD):
        die("gold set has only one side of the positive/negative split "
            f"(labels present: {sorted(labels_present)}) — FNR or FPR would be "
            "undefined. Add at least one accept/minor_revision AND one "
            "major_revision/reject paper.")

    fnr, fpr = _fnr(pairs), _fpr(pairs)
    bal = _balanced_accuracy(pairs)
    report["confusion_matrix"] = matrix
    report["rates"] = {
        "fnr_over_harsh": round(fnr, 4) if fnr is not None else None,
        "fnr_ci95": _bootstrap(pairs, _fnr, BOOTSTRAP_RESAMPLES),
        "fpr_lenient": round(fpr, 4) if fpr is not None else None,
        "fpr_ci95": _bootstrap(pairs, _fpr, BOOTSTRAP_RESAMPLES),
        "balanced_accuracy": round(bal, 4) if bal is not None else None,
        "balanced_accuracy_ci95": _bootstrap(pairs, _balanced_accuracy, BOOTSTRAP_RESAMPLES),
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED},
    }
    report["caveats"].append(
        "FNR is the OVER-HARSH rate (a publishable paper sent back); FPR is the "
        "LENIENT rate (a flawed paper waved through). The reading inverts if the "
        "positive class is redefined.")
    if len(scored_ids) < 10:
        report["caveats"].append(
            f"n={len(scored_ids)} (<10): confidence intervals are wide. Treat this "
            f"profile as directional, not conclusive.")
    if unstable:
        report["caveats"].append(
            f"{len(unstable)} paper(s) did not get a unanimous decision across runs "
            f"({', '.join(unstable)}) — the profile rests partly on majority votes "
            f"over a reviewer that read those papers inconsistently.")
    report["caveats"].append(
        "Domain-specific: a profile measured on one field does not transfer to "
        "another. Session-scoped: nothing is cached across sessions.")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gold", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--tier", choices=("full", "directional"), default="full")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.gold, "--gold")
    require_within_cwd(args.verdicts, "--verdicts")
    gold_path, verdict_path = Path(args.gold), Path(args.verdicts)
    for p, flag in ((gold_path, "--gold"), (verdict_path, "--verdicts")):
        if not p.exists():
            die(f"{flag} {p} does not exist")

    gold = load_gold(gold_path)
    by_paper = load_verdicts(verdict_path, set(gold))

    if args.tier == "directional":
        if len(by_paper) != 3:
            die(f"directional tier requires exactly 3 papers, got {len(by_paper)}")
        if any(len(v) != 1 for v in by_paper.values()):
            die("directional tier expects exactly one run per paper — do not "
                "ensemble or majority-vote a single draw")
    elif not 5 <= len(by_paper) <= 20:
        die(f"full tier requires 5-20 papers, got {len(by_paper)}. Fewer cannot "
            f"support a rate; more is usually a sign the gold set drifted into a "
            f"benchmark. Use --tier directional for a 3-paper spot check.")

    emit(score(gold, by_paper, args.tier), True)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read input files — {e}")
    except UnicodeDecodeError as e:
        die(f"an input file is not valid UTF-8 — {e}")
