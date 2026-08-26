#!/usr/bin/env python3
"""screening_score.py — score the kit's title/abstract SCREENING decisions
against the user's own include/exclude labels.

Why this exists
---------------
`eval/MEASUREMENT.md` opens by saying which layers are measured (the
deterministic checkers) and which are not (everything the model decides).
Screening is the LLM-mediated step whose errors are the most consequential and
the least visible: a study wrongly EXCLUDED at title/abstract never reaches
full text, never becomes an evidence card, and therefore leaves no trace
anywhere downstream. Nothing in the kit can notice it. Only a human who reads
the same records can.

So this script does not invent a gold set — it cannot, and one written by the
same model whose decisions it scores would measure agreement with itself. It
takes the labels YOU produced (screening a sample of your own candidates
against your own inclusion criteria) and reports the error profile of the
kit's decisions on those same records. Without that file it refuses to run,
which is the honest state, not a failure.

What it reports, and why not "accuracy"
---------------------------------------
Positive class is INCLUDE. At a realistic 5-10% inclusion rate, a screener that
excluded every record would score 90-95% "accuracy" while finding nothing, so
accuracy is not reported at all. What is reported:

  recall     — of the studies you would include, the share the kit kept. The
               load-bearing number: its complement is the unrecoverable error.
  precision  — of the records the kit kept, the share you would keep. Its
               complement costs you full-text reading time and nothing else.
  Cohen's κ  — chance-corrected agreement, the statistic a systematic review is
               expected to report for its screening step. Undefined when either
               side used a single class; reported as null rather than as 0.

The two error classes are named in the payload (`missed_includes`,
`false_includes`) rather than left as FN/FP, because the whole point is that
they are not interchangeable and the abbreviations invite treating them as if
they were.

Stage, and the one assumption made visible
------------------------------------------
`registry.jsonl` keeps only a record's FINAL status, so a source excluded at
full text looks excluded — although the screening layer had included it, which
is how it reached full text at all. Those are scored as screening-INCLUDE, and
counted in `stage.fulltext_exclusions_scored_as_include` so the reading is
visible. An excluded record with no `stage` field is assumed to be a screening
exclusion (that is what `literature-scout` produces) and counted in
`stage.assumed_screening`; if that assumption is wrong for your project, set the
stage when you exclude, or pass a frozen `--decisions` file instead.

Inputs:
  --gold        JSONL: {"id","label"} · label in include|exclude · optional
                "reason"/"note". `id` matches registry `id` (SRC-####), or a
                `doi`, or a `bib_key` — resolved in that order.
  --decisions   registry.jsonl (default) or a frozen JSONL of
                {"id","decision"} with decision in include|exclude.

Producing the labels (the part that used to be a shell one-liner in the README):
  python scripts/screening_score.py --sample 50      # blinded worksheet, CSV
  ... label the 'label' column yourself, include/exclude ...
  python scripts/screening_score.py --from-worksheet eval/screening/worksheet.csv

The worksheet carries id, title, year and venue — and not the kit's decision.
The README could ask a labeller not to look at the answer first; a sheet the
answer is not on is the version that survives being in a hurry.

Usage:
  python scripts/screening_score.py --gold eval/screening/gold.jsonl
  python scripts/screening_score.py --gold eval/screening/gold.jsonl \\
      --decisions sources/registry.jsonl --json
Exit codes: 0 scored · 1 error (refused; the message says why).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, read_jsonl, require_within_cwd, write_text_atomic  # noqa: E402
from lib_stats import bootstrap_ci, cohen_kappa  # noqa: E402

GOLD_LABELS = ("include", "exclude")
DEFAULT_DECISIONS = "sources/registry.jsonl"
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 20260814  # fixed: a CI that moves when nothing changed is noise

# Below this many scored records, rates and κ are reported as null and only the
# counts stand. Cochrane-style pilot screening runs on ~50 records; 20 is the
# floor at which a recall figure stops being one or two studies wearing a
# percentage sign. The refusal is deliberate: an unreliable rate that LOOKS like
# a measurement is worse than a stated absence, which is the same call
# calibration_score.py makes for its `directional` tier.
MIN_N_FOR_RATES = 20

# Same normalized-field contamination check as calibration_score.py: a decision
# record carrying the answer means the labels were in scope while the decision
# was made, and agreement measured that way is agreement with the answer key.
CONTAMINATION_FIELDS = {"label", "gold", "goldlabel", "expected", "groundtruth",
                        "truth", "answer"}


DEFAULT_WORKSHEET = "eval/screening/worksheet.csv"
DEFAULT_GOLD = "eval/screening/gold.jsonl"
# The columns a blinded worksheet carries — and, by their absence, the ones it
# must not. `status`, `reason` as the register wrote it, `stage`: every field
# that would tell the labeller what the kit decided.
WORKSHEET_COLUMNS = ("id", "title", "year", "venue", "label", "reason")


def _norm_key(key: str) -> str:
    return "".join(ch for ch in str(key).lower() if ch.isalnum())


def load_gold(path: Path) -> list[dict]:
    rows = read_jsonl(path)
    if not rows:
        die(f"{path} is empty — screening cannot be scored against no labels")
    seen, gold = set(), []
    for i, r in enumerate(rows, 1):
        key = r.get("id") or r.get("doi") or r.get("bib_key")
        label = r.get("label")
        if not key:
            die(f"{path}:{i}: gold entry has no 'id', 'doi' or 'bib_key'")
        if label not in GOLD_LABELS:
            die(f"{path}:{i}: label {label!r} not in {list(GOLD_LABELS)}")
        norm = str(key).strip().lower()
        if norm in seen:
            die(f"{path}:{i}: duplicate gold key {key!r}")
        seen.add(norm)
        gold.append({"key": str(key).strip(), "norm": norm, "label": label,
                     "note": r.get("note") or r.get("reason")})
    return gold


def _index_records(records: list[dict]) -> dict[str, dict]:
    """Every handle a gold entry may name -> the record. Later duplicates do not
    overwrite earlier ones: an ambiguous handle should resolve to nothing
    surprising, and a genuine duplicate registry entry is `status:duplicate`
    anyway, which is not scored."""
    index: dict[str, dict] = {}
    for rec in records:
        for field in ("id", "doi", "bib_key"):
            val = rec.get(field)
            if isinstance(val, str) and val.strip():
                index.setdefault(val.strip().lower(), rec)
    return index


def screening_decision(rec: dict) -> tuple[str | None, str]:
    """(decision, why) for one record. `decision` is None when the record
    carries no screening judgement to score."""
    status = rec.get("status")
    stage = rec.get("stage")
    if "decision" in rec and status is None:  # frozen --decisions file
        d = rec["decision"]
        if d not in GOLD_LABELS:
            die(f"decision {d!r} not in {list(GOLD_LABELS)}")
        return d, "frozen"
    if status == "included":
        return "include", "included"
    if status == "excluded":
        if stage == "fulltext":
            return "include", "fulltext_exclusion"
        return "exclude", "screening" if stage == "screening" else "assumed_screening"
    if status == "unretrieved":
        # Sought for retrieval => it passed title/abstract screening. Scoring it as
        # "undecided" would drop it from the denominator and silently inflate
        # precision, since the records you fail to obtain are the ones you screened IN.
        return "include", "unretrieved"
    if status == "duplicate":
        return None, "duplicate"
    return None, "undecided"


def score(gold: list[dict], index: dict[str, dict]) -> dict:
    pairs: list[tuple[bool, bool]] = []
    per_record, unresolved = [], []
    skipped = {"duplicate": 0, "undecided": 0}
    stage = {"fulltext_exclusions_scored_as_include": 0, "assumed_screening": 0,
             "explicit_screening": 0, "unretrieved_scored_as_include": 0,
             "frozen": 0}
    for g in gold:
        rec = index.get(g["norm"])
        if rec is None:
            unresolved.append(g["key"])
            continue
        decision, why = screening_decision(rec)
        if decision is None:
            skipped[why] += 1
            continue
        if why == "fulltext_exclusion":
            stage["fulltext_exclusions_scored_as_include"] += 1
        elif why == "assumed_screening":
            stage["assumed_screening"] += 1
        elif why == "screening":
            stage["explicit_screening"] += 1
        elif why == "unretrieved":
            stage["unretrieved_scored_as_include"] += 1
        elif why == "frozen":
            stage["frozen"] += 1
        gold_pos = g["label"] == "include"
        pred_pos = decision == "include"
        pairs.append((gold_pos, pred_pos))
        per_record.append({"key": g["key"], "gold": g["label"],
                           "decision": decision, "basis": why,
                           "agreed": gold_pos == pred_pos,
                           "note": g["note"]})

    counts = _counts(pairs)
    n = len(pairs)
    enough = n >= MIN_N_FOR_RATES
    report = {
        "scored": n,
        "gold_records": len(gold),
        "unresolved": unresolved,
        "skipped": skipped,
        "stage": stage,
        "counts": counts,
        "missed_includes": [r for r in per_record
                            if r["gold"] == "include" and r["decision"] == "exclude"],
        "false_includes": [r for r in per_record
                           if r["gold"] == "exclude" and r["decision"] == "include"],
        "inclusion_rate_gold": round(counts["kept_by_you"] / n, 4) if n else None,
        "recall": _recall(pairs) if enough else None,
        "precision": _precision(pairs) if enough else None,
        "f1": _f1(pairs) if enough else None,
        "cohen_kappa": (round(k, 4) if (k := cohen_kappa(pairs)) is not None else None)
                       if enough else None,
        "recall_ci95": bootstrap_ci(pairs, _recall, BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED)
                       if enough else None,
        "precision_ci95": bootstrap_ci(pairs, _precision, BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED)
                          if enough else None,
        "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED},
        "per_record": per_record,
        "notes": [],
    }
    if not enough:
        report["notes"].append(
            f"{n} scored record(s) is below the {MIN_N_FOR_RATES}-record floor: "
            f"counts are reported, rates and κ are not. A recall figure over a "
            f"handful of records is one or two studies wearing a percentage sign.")
    if report["cohen_kappa"] is None and enough:
        report["notes"].append(
            "κ is undefined here: one side used a single class, so chance "
            "agreement is 1. Reported as null rather than 0, which would be "
            "indistinguishable from measured total disagreement.")
    if unresolved:
        report["notes"].append(
            f"{len(unresolved)} gold record(s) matched nothing in the decisions "
            f"file and were NOT scored — check the id/doi/bib_key spelling. "
            f"Silently dropping them would flatter whatever remained.")
    if skipped["undecided"]:
        report["notes"].append(
            f"{skipped['undecided']} record(s) carry no screening decision yet "
            f"(status candidate/screened) — screen them before scoring.")
    if stage["assumed_screening"]:
        report["notes"].append(
            f"{stage['assumed_screening']} exclusion(s) had no `stage` field and "
            f"were read as screening-stage. If any was a full-text exclusion, "
            f"this understates recall — set --stage when excluding.")
    if report["missed_includes"]:
        report["notes"].append(
            f"{len(report['missed_includes'])} missed include(s): the error class "
            f"nothing downstream can detect. Read them before trusting the search.")
    return report


def _counts(pairs) -> dict:
    return {
        "both_include": sum(1 for g, p in pairs if g and p),
        "both_exclude": sum(1 for g, p in pairs if not g and not p),
        "kept_by_you": sum(1 for g, _ in pairs if g),
        "kept_by_kit": sum(1 for _, p in pairs if p),
        "missed_includes": sum(1 for g, p in pairs if g and not p),
        "false_includes": sum(1 for g, p in pairs if not g and p),
    }


def _recall(pairs):
    tp = sum(1 for g, p in pairs if g and p)
    fn = sum(1 for g, p in pairs if g and not p)
    return tp / (tp + fn) if (tp + fn) else None


def _precision(pairs):
    tp = sum(1 for g, p in pairs if g and p)
    fp = sum(1 for g, p in pairs if not g and p)
    return tp / (tp + fp) if (tp + fp) else None


def _f1(pairs):
    r, p = _recall(pairs), _precision(pairs)
    return 2 * r * p / (r + p) if (r and p) else None


def sample_worksheet(records: list[dict], n: int, seed: int) -> list[dict]:
    """A random, BLINDED sample of the register, for the author to label.

    Blinded is the whole design. eval/screening/README.md asks the labeller not
    to look at the kit's decision first, because labelling next to an answer
    measures agreement with a suggestion rather than judgement — a large and
    well-documented effect in dual screening. Asking is all the README could do;
    this hands over a sheet the decision is simply not on, which is the version
    that survives being in a hurry.

    Random, not "the interesting ones": a sample chosen by what the author
    remembers is a sample of memorable cases, and recall measured on it is not
    recall. The seed is explicit so the same sample can be regenerated after a
    lost file without silently becoming a different sample.
    """
    eligible = [r for r in records if r.get("id") and r.get("title")]
    if not eligible:
        die("no registered record has both an id and a title — nothing to sample")
    rng = random.Random(seed)
    chosen = rng.sample(eligible, min(n, len(eligible)))
    return [{"id": r["id"], "title": r.get("title", ""), "year": r.get("year", ""),
             "venue": r.get("venue", ""), "label": "", "reason": ""}
            for r in sorted(chosen, key=lambda r: r["id"])]


def write_worksheet(rows: list[dict], path: Path) -> None:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(WORKSHEET_COLUMNS),
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    # utf-8-sig: this file is opened in Excel by a Turkish-speaking author, and
    # without the BOM Excel reads it as the system codepage and mangles every
    # title it is supposed to help them judge.
    path.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(path, "﻿" + buffer.getvalue())


def read_worksheet(path: Path) -> tuple[list[dict], list[dict]]:
    """Filled rows → gold entries, plus the rows that were left blank.

    Blank is not an error and not an exclusion: a labeller who skipped a record
    made no judgement about it, and turning silence into "exclude" would invent
    the exact labels this whole layer refuses to invent.
    """
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in ("id", "label") if c not in (reader.fieldnames or [])]
    if missing:
        die(f"{path} has no {missing} column — is this the worksheet "
            f"--sample wrote? (columns found: {reader.fieldnames})")
    gold, skipped = [], []
    for i, row in enumerate(reader, 2):  # 2: line 1 is the header
        rec_id = (row.get("id") or "").strip()
        label = (row.get("label") or "").strip().lower()
        if not rec_id:
            continue
        if not label:
            skipped.append({"id": rec_id, "line": i})
            continue
        if label not in GOLD_LABELS:
            die(f"{path}:{i}: label {label!r} is neither 'include' nor 'exclude'")
        entry = {"id": rec_id, "label": label}
        if (row.get("reason") or "").strip():
            entry["reason"] = row["reason"].strip()
        gold.append(entry)
    return gold, skipped


def cmd_sample(args):
    out = Path(require_within_cwd(args.out or DEFAULT_WORKSHEET, "--out"))
    if out.exists() and not args.force:
        die(f"{out} already exists — it may hold labels you typed. Move it aside, "
            f"or pass --force to overwrite.")
    dec_path = Path(require_within_cwd(args.decisions, "--decisions"))
    if not dec_path.exists():
        die(f"{dec_path} does not exist — there is nothing to sample")
    if args.sample < 1:
        die(f"--sample must be at least 1, got {args.sample}")
    rows = sample_worksheet(read_jsonl(dec_path), args.sample, args.seed)
    write_worksheet(rows, out)
    emit({"worksheet": out.as_posix(), "records": len(rows), "seed": args.seed,
          "columns": list(WORKSHEET_COLUMNS),
          "note": ("blinded on purpose — the kit's own decision is not on this "
                   "sheet. Label from title and venue alone, then run "
                   "--from-worksheet."),
          "next": f"python scripts/screening_score.py --from-worksheet {out.as_posix()}"},
         args.json_out)


def cmd_from_worksheet(args):
    src = Path(require_within_cwd(args.from_worksheet, "--from-worksheet"))
    if not src.exists():
        die(f"{src} does not exist")
    out = Path(require_within_cwd(args.out or DEFAULT_GOLD, "--out"))
    if out.exists() and not args.force:
        die(f"{out} already exists — pass --force to replace it")
    gold, skipped = read_worksheet(src)
    if not gold:
        die(f"{src} has no labelled rows — fill the 'label' column with "
            f"include/exclude first")
    out.parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(out, "\n".join(json.dumps(g, ensure_ascii=False) for g in gold) + "\n")
    emit({"gold": out.as_posix(), "labelled": len(gold),
          "include": sum(1 for g in gold if g["label"] == "include"),
          "exclude": sum(1 for g in gold if g["label"] == "exclude"),
          "unlabelled_rows": skipped,
          "note": ("blank rows were skipped, not read as exclusions — no "
                   "judgement was made about them"),
          "next": f"python scripts/screening_score.py --gold {out.as_posix()}"},
         args.json_out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gold", help="JSONL of YOUR include/exclude labels")
    ap.add_argument("--sample", type=int, metavar="N",
                    help="write a blinded worksheet of N random registered records "
                         "for you to label (the kit's decision is not on it)")
    ap.add_argument("--from-worksheet", dest="from_worksheet", metavar="CSV",
                    help="convert a filled worksheet into the gold JSONL")
    ap.add_argument("--out", help="destination for --sample / --from-worksheet")
    ap.add_argument("--seed", type=int, default=1,
                    help="sampling seed (default 1) — stated so the same sample "
                         "can be regenerated rather than quietly redrawn")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing worksheet or gold file")
    ap.add_argument("--decisions", default=DEFAULT_DECISIONS,
                    help=f"registry or frozen decisions JSONL (default: {DEFAULT_DECISIONS})")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    modes = [bool(args.sample), bool(args.from_worksheet), bool(args.gold)]
    if sum(modes) > 1:
        die("pick one: --sample (draw a worksheet), --from-worksheet (convert a "
            "filled one) or --gold (score against labels)")
    if args.sample:
        return cmd_sample(args)
    if args.from_worksheet:
        return cmd_from_worksheet(args)
    if not args.gold:
        die("nothing to do — start with --sample N to draw a blinded worksheet, "
            "or pass --gold once you have labels (see eval/screening/README.md)")

    gold_path = Path(require_within_cwd(args.gold, "--gold"))
    dec_path = Path(require_within_cwd(args.decisions, "--decisions"))
    if not gold_path.exists():
        die(f"{gold_path} does not exist. This layer is unmeasured until you "
            f"label a sample yourself: one JSON object per line, "
            f'{{"id": "SRC-0001", "label": "include"}}. See '
            f"eval/screening/README.md. No gold set ships with the kit — one "
            f"written by the model whose decisions it scores would measure "
            f"agreement with itself.")
    if not dec_path.exists():
        die(f"{dec_path} does not exist — nothing to score")

    records = read_jsonl(dec_path)
    if not records:
        die(f"{dec_path} is empty — nothing to score")
    for i, r in enumerate(records, 1):
        leaked = sorted(k for k in r if _norm_key(k) in CONTAMINATION_FIELDS)
        if leaked:
            die(f"{dec_path}:{i}: decision record carries gold-label field(s) "
                f"{leaked} — the answer was in scope while the decision was made, "
                f"so this run cannot be scored. Keep your labels in the gold file "
                f"and out of the register.")
    report = score(load_gold(gold_path), _index_records(records))
    report["gold_file"] = str(gold_path)
    report["decisions_file"] = str(dec_path)
    emit(report, args.json_out)
    sys.exit(0)


if __name__ == "__main__":
    main()
