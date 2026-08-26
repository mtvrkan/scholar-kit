#!/usr/bin/env python3
"""run_evals.py — measure the kit's deterministic checkers against labeled gold sets.

The kit ships checkers that make judgements about a manuscript. This harness
answers the question those checkers cannot answer about themselves: **how often
are they right?** Each gold set is a corpus of hand-labeled cases; the harness
runs the checker over every case, compares the findings it produced against the
findings the case declares, and reports precision / recall / F1 per task.

What these numbers mean — and do not:

  * They measure whether a checker does what its author INTENDED, on cases that
    author chose. They are a regression and calibration instrument, not evidence
    of real-world accuracy: a defect class nobody thought to write a case for is
    invisible here, and scores an undeserved 1.00 by omission.
  * They are honest about direction. A gold set with only positive cases can
    only measure recall; precision needs negatives (clean cases the checker must
    leave alone). Every manifest declares its balance and the harness reports it,
    so a suite that quietly drops its negatives is visible rather than flattering.
  * They say nothing about the LLM-mediated parts of the kit (drafting, review).
    Those are not deterministic and are not measured here.

Gold-set layout — `eval/gold/<task>/manifest.json`:

  {
    "task": "claim_strength",
    "entrypoint": "claim_check",         # module in scripts/ exposing check()
    "description": "...",
    "thresholds": {"precision": 0.90, "recall": 0.85},
    "cases": [
      {"id": "001-...", "drafts": {"discussion.md": "..."},
       "cards": [...], "registry": [...],
       "expect": [{"check": "overclaim", "card": "EV-0001"}]}
    ]
  }

Fixture keys a case may declare: `drafts` and `analysis` (name -> text),
`cards` / `registry` (lists of records), `bib` (BibTeX text), `glossary` (the
tr-terminology object). Per-entrypoint knobs: `type` (failure_scan paper type),
`skip` (claim_check skip pattern), `checks` (tr_style_check subset), `today`
(temporal_check's pinned date — mandatory there, see _findings_temporal).

An `expect` entry is a SUBSET match: the fields it names must equal the
corresponding fields of some actual finding. Naming fewer fields is a weaker
assertion, deliberately — a case that only cares that M1 fired writes
`{"mode": "M1"}` rather than pinning a message that will be reworded.

Usage:
  python scripts/run_evals.py                    # all tasks
  python scripts/run_evals.py --task claim_strength
  python scripts/run_evals.py --strict           # exit 2 if any threshold missed
Exit codes: 0 ok · 1 error · 2 a threshold was missed AND --strict.
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit

ROOT = Path(__file__).parent.parent


def _require_within_kit(path: Path, flag: str) -> Path:
    """Traversal guard for a KIT-owned path.

    Deliberately not lib_common.require_within_cwd: gold sets live in the kit
    (`<kit>/eval/gold`) and are read relative to the kit root, while that helper
    validates against the *current working directory*. Using it here made the
    guard and the actual read target diverge — the same defect
    skill_routing_eval.py documents — so running the harness from anywhere but
    the kit root died on a path it was about to read correctly.
    """
    resolved = path.resolve()
    root = ROOT.resolve()
    if resolved != root and root not in resolved.parents:
        die(f"{flag} must resolve inside the kit directory ({root}), got {resolved}")
    return resolved


def _materialize(case: dict, root: Path) -> None:
    """Write one case's fixture files into a throwaway project directory."""
    drafts = root / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    for name, text in (case.get("drafts") or {}).items():
        (drafts / name).write_text(text, encoding="utf-8")
    for name, text in (case.get("analysis") or {}).items():
        (root / "analysis").mkdir(parents=True, exist_ok=True)
        (root / "analysis" / name).write_text(text, encoding="utf-8")
    if case.get("cards") is not None:
        p = root / "evidence" / "cards.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(json.dumps(c, ensure_ascii=False)
                               for c in case["cards"]) + "\n", encoding="utf-8")
    if case.get("registry") is not None:
        p = root / "sources" / "registry.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False)
                               for r in case["registry"]) + "\n", encoding="utf-8")
    if case.get("bib") is not None:
        p = root / "bib" / "references.bib"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(case["bib"], encoding="utf-8")
    if case.get("prisma_counts") is not None:
        # Akisi defterden turemeyen derleme: sayaclar acikca verilir.
        d = root / "analysis"
        d.mkdir(parents=True, exist_ok=True)
        (d / "prisma-counts.json").write_text(
            json.dumps(case["prisma_counts"], ensure_ascii=False), encoding="utf-8")
    if case.get("project") is not None:
        # PROJECT.md, because several checks read the paper Type and mean
        # different things by the same finding depending on it.
        (root / "PROJECT.md").write_text(case["project"], encoding="utf-8")
    if case.get("extraction") is not None:
        # A review that pools keeps 2x2 cells in a structured table, one JSON
        # per study, not in prose cards. evidence_funnel needs the directory to
        # tell "extracted, just not carded" from "reached no analysis at all".
        d = root / "analysis" / "extraction"
        d.mkdir(parents=True, exist_ok=True)
        for name, rec in case["extraction"].items():
            (d / name).write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    if case.get("glossary") is not None:
        # Written where tr_style_check's own default expects it, so a case's
        # glossary is the same artifact a real project copies from templates/.
        p = root / "templates" / "tr-terminology.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(case["glossary"], ensure_ascii=False),
                     encoding="utf-8")


def _findings_claim_check(root: Path, case: dict) -> list[dict]:
    import claim_check
    res = claim_check.check(root / "drafts", root / "evidence" / "cards.jsonl",
                            root / "sources" / "registry.jsonl",
                            skip_pattern=case.get("skip", claim_check.DEFAULT_SKIP))
    out = [{**f, "check": "overclaim"} for f in res["overclaim"]]
    out += [{**f, "check": "uncited"} for f in res["uncited_assertions"]]
    return out


def _findings_failure_scan(root: Path, case: dict):
    import failure_scan
    res = failure_scan.check(root / "drafts", root / "analysis", case.get("type"))
    # Two channels. The findings are what precision/recall are computed over;
    # the per-mode STATUS is a separate assertion surface, because some
    # regressions do not add or remove a finding at all — they change what an
    # empty finding list is reported to MEAN. The saturation measure is exactly
    # that: it turns a meaningless CLEAR into INSUFFICIENT EVIDENCE without
    # touching a single finding, so a findings-only gold set cannot see it
    # break.
    return res["findings"], {m: v.get("status") for m, v in res["modes"].items()}


def _findings_tr_style(root: Path, case: dict) -> list[dict]:
    import tr_style_check
    which = tuple(case.get("checks") or tr_style_check.ALL_CHECKS)
    unknown = [c for c in which if c not in tr_style_check.ALL_CHECKS]
    if unknown:
        die(f"case {case.get('id')!r}: unknown tr_style check(s) {unknown} "
            f"(known: {', '.join(tr_style_check.ALL_CHECKS)})")
    res = tr_style_check.check(root / "drafts",
                               root / "templates" / "tr-terminology.json", which)
    return res.get("warnings") or []


def _findings_temporal(root: Path, case: dict) -> list[dict]:
    import temporal_check
    # `today` is mandatory, not defaulted to the real date: half of this
    # checker's findings are relative to it, so a case without one would pass
    # today and fail silently in 2031. A gold set that rots with the calendar
    # measures the calendar, not the checker.
    today = case.get("today")
    if not today:
        die(f"case {case.get('id')!r}: temporal_check cases must declare "
            f"'today' (YYYY-MM-DD) — a date-relative check pinned to the real "
            f"clock would decay into a false pass")
    try:
        pinned = datetime.date.fromisoformat(today)
    except ValueError:
        die(f"case {case.get('id')!r}: 'today' is not an ISO date: {today!r}")
    return (temporal_check.check_bib_temporal(root / "bib" / "references.bib", pinned)
            + temporal_check.check_card_year_anachronism(
                root / "evidence" / "cards.jsonl",
                root / "sources" / "registry.jsonl"))


def _findings_consistency(root: Path, case: dict) -> list[dict]:
    import consistency_check
    pc = root / "analysis" / "prisma-counts.json"
    res = consistency_check.check(root / "drafts", root / "analysis" / "counts.json",
                                  root / "sources" / "registry.jsonl",
                                  pc if pc.is_file() else None)
    out = [{**f, "check": "manifest_mismatch"} for f in res["manifest_mismatch"]]
    out += [{**f, "check": "cross_section_drift"} for f in res["cross_section_drift"]]
    # Hangi akisa karsi karsilastirildigi YALNIZCA takasi sinayan vakalarda bir
    # bulgudur. Her vakada uretmek, akisla ilgisi olmayan on iki vakaya sahte
    # pozitif eklemek olur -- yani denetimin kendisine degil, oleceklere gurultu.
    if case.get("prisma_counts") is not None:
        src = res["prisma"]["source"]
        out += [{"check": "prisma_source",
                 "source": "REDDEDILDI" if "REDDEDILDI" in src else Path(src).name}]
    out += [{**m, "check": "prisma_mismatch"} for m in res["prisma"]["mismatches"]]
    return out


def _findings_figure(root: Path, case: dict) -> list[dict]:
    import figure_check
    res = figure_check.check(root / "drafts", root / "analysis" / "captions.md")
    out = []
    # Flattened one finding per defect so a case can name exactly which figure
    # or table it is asserting about, rather than matching a whole grouped dict.
    for kind in ("figures", "tables"):
        group = res[kind]
        for num in group["missing"]:
            out.append({"check": "missing", "kind": kind, "num": num})
        for num in group["orphaned"]:
            out.append({"check": "orphaned", "kind": kind, "num": num})
        for dup in group["duplicate_numbers"]:
            out.append({"check": "duplicate_number", "kind": kind, "num": dup["num"]})
        for gap in group["sequence_gaps"]:
            out.append({"check": "sequence_gap", "kind": kind, "num": gap})
        for ooo in group["out_of_order"]:
            out.append({"check": "out_of_order", "kind": kind, "num": ooo["label"]})
        for dr in group["degenerate_ranges"]:
            out.append({"check": "degenerate_range", "kind": kind, "text": dr["text"]})
    for name in res["uncaptioned_figures"]:
        out.append({"check": "uncaptioned", "kind": "figures", "name": name})
    return out


def _rel_where(where: str, root: Path) -> str:
    """`drafts/x.md:12`, not `C:/Users/.../tmp8sk1/drafts/x.md:12`.

    The checkers report a real path because a real project has one; the harness
    runs them in a throwaway directory whose name changes every invocation. A
    case that wants to assert WHICH line was flagged can only do so against a
    stable path, so the harness — which owns the temp root — is what strips it.
    Left alone, a `where` expectation is unwritable and the field silently
    becomes unassertable, which is how a location bug hides from a gold set.
    """
    prefix = root.as_posix().rstrip("/") + "/"
    return where[len(prefix):] if where.startswith(prefix) else where


def _findings_cite_audit(root: Path, case: dict) -> list[dict]:
    import cite_audit
    res = cite_audit.check(root / "drafts", root / "bib" / "references.bib")
    out = [{"check": "missing", "key": k} for k in res["missing"]]
    out += [{"check": "orphan", "key": k} for k in res["orphans"]]
    out += [{"check": "unverified_cited", "key": k} for k in res["unverified_cited"]]
    # Tag findings carry a location, not a key. The three tags stay SEPARATE
    # checks rather than one "placeholder" bucket: they mean different things
    # ([CITATION NEEDED] = no source attached yet, [MATERIAL GAP] = refused to
    # fill from memory, [LLM-SUPPLEMENTED] = authorized fill), and collapsing
    # them would let a case assert the blocking pair while the non-blocking one
    # silently substituted for it.
    for kind, key in (("placeholder", "placeholders"),
                      ("material_gap", "material_gaps"),
                      ("llm_supplemented", "llm_supplemented")):
        out += [{"check": kind, "where": _rel_where(w, root)} for w in res[key]]
    return out


def _findings_bib_doctor(root: Path, case: dict) -> list[dict]:
    import bib_doctor
    from lib_common import parse_bibtex
    bib = root / "bib" / "references.bib"
    if not bib.exists():
        die(f"case {case.get('id')!r}: bib_doctor cases must declare a 'bib' fixture")
    problems, _ = bib_doctor.audit(parse_bibtex(bib.read_text(encoding="utf-8")))
    # One finding per ISSUE, not per entry: an entry with three defects is three
    # things a case may assert about independently, and a per-entry shape would
    # make "flagged for the wrong reason" score as a true positive.
    return [{"check": issue["kind"], "key": p["key"]}
            for p in problems for issue in p["issues"]]


def _findings_evidence_funnel(root: Path, case: dict) -> list[dict]:
    import evidence_funnel
    ext = root / "analysis" / "extraction"
    res = evidence_funnel.build_funnel(
        root / "evidence" / "cards.jsonl", root / "sources" / "registry.jsonl",
        root / "drafts", root / "bib" / "references.bib",
        root / "PROJECT.md", ext if ext.is_dir() else None)
    # `expected_uncited` is reported as a finding even though it is explicitly
    # NOT a defect. That is deliberate: the split between "orphan" (extraction
    # that never reached the paper) and "expected" (own-result cards, cards from
    # an excluded source) is the checker's actual judgement, and a gold set that
    # only scored orphans could not catch a regression that reclassified every
    # own-result card as waste.
    out = [{"check": "orphan_card", "id": o["id"], "source": o["source"]}
           for o in res["orphan_cards"]]
    out += [{"check": "expected_uncited", "id": e["id"], "source": e["source"]}
            for e in res["expected_uncited"]]
    # The stage-2->3 direction: an included study that reached no analysis at
    # all. Reported only when the paper type says every included study owed the
    # synthesis its data, which is the judgement being scored — a regression
    # that raised it for a narrative review would be as wrong as one that
    # dropped it for a systematic one.
    if res.get("coverage_required"):
        out += [{"check": "unextracted_included", "source": k}
                for k in res.get("unextracted_included", [])]
    out += [{"check": "orphan_extraction", "file": f}
            for f in res.get("orphan_extractions", [])]
    return out


def _findings_draft_integrity(root: Path, case: dict) -> list[dict]:
    import draft_integrity
    res = draft_integrity.check(root / "drafts", root)
    out = []
    for x in res["unwritten_generated_blocks"]:
        out.append({"check": "unwritten_generated", "tag": x["tag"]})
    for x in res["undeclared_generated_blocks"]:
        out.append({"check": "undeclared_generated", "tag": x["tag"]})
    for x in res["marker_problems"]:
        out.append({"check": x["kind"], "tag": x["tag"]})
    for x in res["control_characters"]:
        # Satir numarasi degil, DOSYA + KOD adlanir. Satir numarasina baglanmak
        # fixture'a bir satir eklendiginde vakayi kirardi. Kodu adlamak ise
        # gerekli: "bu dosyada bir kontrol karakteri var" iddiasi, ikisinden
        # birinin kaybolmasini goremez — ve bu betigin ilk surumunun gercek
        # hatasi tam olarak buydu (splitlines \f'i satir sonu sayip yutuyordu).
        for code in x.get("control", []):
            out.append({"check": "control_characters",
                        "file": Path(x["file"]).name, "code": code})
        if x.get("replacement_chars"):
            out.append({"check": "control_characters",
                        "file": Path(x["file"]).name, "code": "U+FFFD"})
    return out


ENTRYPOINTS = {
    "claim_check": _findings_claim_check,
    "draft_integrity": _findings_draft_integrity,
    "failure_scan": _findings_failure_scan,
    "tr_style_check": _findings_tr_style,
    "temporal_check": _findings_temporal,
    "consistency_check": _findings_consistency,
    "figure_check": _findings_figure,
    "cite_audit": _findings_cite_audit,
    "bib_doctor": _findings_bib_doctor,
    "evidence_funnel": _findings_evidence_funnel,
}


def matches(expect: dict, finding: dict) -> bool:
    """Subset match — every field `expect` names must equal the finding's."""
    return all(finding.get(k) == v for k, v in expect.items())


def run_case(case: dict, runner) -> dict:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _materialize(case, root)
        actual = runner(root, case)
    # Back-compatible: a runner may return findings alone, or (findings, meta).
    status = {}
    if isinstance(actual, tuple):
        actual, status = actual

    expected = case.get("expect") or []
    unmatched_actual = list(actual)
    tp, fn = 0, []
    for exp in expected:
        for i, act in enumerate(unmatched_actual):
            if matches(exp, act):
                tp += 1
                unmatched_actual.pop(i)
                break
        else:
            fn.append(exp)
    # `expect_status` asserts what an EMPTY finding list means, which no
    # finding matcher can express. A mismatch counts as a false negative: the
    # suite was told what the mode should report and it reported something else.
    status_missed = []
    for mode, want in (case.get("expect_status") or {}).items():
        if status.get(mode) != want:
            status_missed.append({"mode": mode, "expected_status": want,
                                  "actual_status": status.get(mode)})
    tp += len((case.get("expect_status") or {})) - len(status_missed)
    fn = fn + status_missed
    return {
        "id": case.get("id"),
        "tp": tp,
        "fp": len(unmatched_actual),
        "fn": len(fn),
        "missed": fn,
        "spurious": [{k: a.get(k) for k in ("check", "mode", "signal", "where", "msg")}
                     for a in unmatched_actual],
    }


def run_task(manifest_path: Path) -> dict:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{manifest_path} is not valid JSON — {e.msg}")
    entry = manifest.get("entrypoint")
    if entry not in ENTRYPOINTS:
        die(f"{manifest_path}: unknown entrypoint {entry!r} "
            f"(known: {', '.join(sorted(ENTRYPOINTS))})")
    runner = ENTRYPOINTS[entry]

    cases = manifest.get("cases") or []
    if not cases:
        die(f"{manifest_path}: no cases — an empty gold set would report a "
            f"vacuous 1.00 and pass every threshold")
    seen = set()
    for c in cases:
        cid = c.get("id")
        if not cid:
            die(f"{manifest_path}: every case needs an 'id'")
        if cid in seen:
            die(f"{manifest_path}: duplicate case id {cid!r}")
        seen.add(cid)

    results = [run_case(c, runner) for c in cases]
    tp = sum(r["tp"] for r in results)
    fp = sum(r["fp"] for r in results)
    fn = sum(r["fn"] for r in results)
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)
          if precision and recall else None)

    # A suite with no negative cases cannot measure precision honestly; say so
    # in the report rather than letting a 1.00 stand unqualified.
    negatives = sum(1 for c in cases
                    if not (c.get("expect") or []) and not (c.get("expect_status") or {}))
    thresholds = manifest.get("thresholds") or {}
    computed = {"precision": precision, "recall": recall, "f1": f1}
    # An unknown metric name reads as None and therefore counts as MISSED. That
    # is the safe direction: a typo'd threshold key must fail loudly rather than
    # silently gate on nothing.
    missed = sorted(k for k, v in thresholds.items()
                    if computed.get(k) is None or computed[k] < v)

    return {
        "task": manifest.get("task") or manifest_path.parent.name,
        "entrypoint": entry,
        "cases": len(cases),
        "positive_cases": len(cases) - negatives,
        "negative_cases": negatives,
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "thresholds": thresholds,
        "thresholds_missed": missed,
        "failing_cases": [r for r in results if r["fp"] or r["fn"]],
    }


# ---------- mutation checking ----------
# A gold set that scores 1.00 has proved its checker does what its author meant.
# It has NOT proved the cases would notice if the checker stopped doing it — a
# negative case that stays silent however the code is broken measures nothing
# while looking exactly like a case that measures something. That is the same
# "undeserved 1.00 by omission" the module docstring warns about, one level
# down, and it is invisible to precision and recall alike.
#
# So each manifest declares MUTATIONS: small, named breakages of its own
# checker's source. The set is credible to the extent that breaking the checker
# makes it fail. A mutation that SURVIVES (the set still passes its thresholds)
# names a real hole in the cases, not a bug in the code.
#
# Source-level substitution, not monkeypatching, on purpose: it mutates the code
# the checker actually ships, and a mutation whose anchor no longer appears dies
# loudly instead of silently testing nothing.

def _mutated_module(name: str, replacements: list, mutation_id: str):
    """Load `scripts/<name>.py` with substitutions applied, as a fresh module."""
    path = ROOT / "scripts" / f"{name}.py"
    src = path.read_text(encoding="utf-8")
    for pair in replacements:
        if not (isinstance(pair, list) and len(pair) == 2):
            die(f"mutation {mutation_id!r}: every 'replace' entry must be "
                f"[old, new], got {pair!r}")
        old, new = pair
        if old not in src:
            die(f"mutation {mutation_id!r}: anchor not found in {name}.py: "
                f"{old!r} — the code moved and this mutation now tests nothing")
        if old == new:
            die(f"mutation {mutation_id!r}: replacement is identical to the "
                f"anchor, so nothing is mutated")
        src = src.replace(old, new)
    spec = importlib.util.spec_from_loader(name, loader=None)
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)  # the scripts add their own dir to sys.path
    # exec IS the mechanism here, not an incidental use of it (hence the
    # suppression on the line itself, which is what bandit reads): the
    # mutation harness loads a deliberately-broken copy of a checker that ships
    # in this repo, mutated by string substitution against its own source.
    # `src` never contains anything outside scripts/<name>.py plus the
    # replacements declared in eval/gold/*/manifest.json, both of which are
    # repository content under version control — there is no external or user
    # input on this path. Importing the mutant instead would require writing it
    # to disk, which is strictly worse: a crashed run would leave a sabotaged
    # checker sitting in scripts/.
    exec(compile(src, f"{path} [mutant:{mutation_id}]", "exec"), module.__dict__)  # nosec B102
    return module


def run_mutations(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = manifest.get("entrypoint")
    task = manifest.get("task") or manifest_path.parent.name
    mutations = manifest.get("mutations") or []
    results = []
    for mutation in mutations:
        mid = mutation.get("id")
        if not mid:
            die(f"{manifest_path}: every mutation needs an 'id'")
        # Swap the mutant in under the real module name so the entrypoint's own
        # `import <name>` picks it up, then put the real one back.
        original = sys.modules.get(entry)
        sys.modules[entry] = _mutated_module(entry, mutation.get("replace") or [], mid)
        try:
            scored = run_task(manifest_path)
        finally:
            if original is not None:
                sys.modules[entry] = original
            else:
                sys.modules.pop(entry, None)
        results.append({
            "id": mid,
            "breaks": mutation.get("breaks"),
            "caught": bool(scored["thresholds_missed"]),
            "precision": scored["precision"],
            "recall": scored["recall"],
        })
    survivors = [r["id"] for r in results if not r["caught"]]
    return {
        "task": task,
        "mutations": len(results),
        "caught": len(results) - len(survivors),
        "survivors": survivors,
        "results": results,
    }


def discover(gold_dir: Path) -> list[Path]:
    return sorted(gold_dir.glob("*/manifest.json")) if gold_dir.exists() else []


def run_all(gold_dir: Path, only: str | None = None, mutate: bool = False) -> dict:
    manifests = discover(gold_dir)
    if only:
        manifests = [m for m in manifests if m.parent.name == only]
        if not manifests:
            die(f"no gold set named {only!r} under {gold_dir}")
    tasks = [run_task(m) for m in manifests]
    out = {
        "gold_sets": len(tasks),
        "tasks": tasks,
        "any_threshold_missed": any(t["thresholds_missed"] for t in tasks),
    }
    if mutate:
        mutations = [run_mutations(m) for m in manifests]
        out["mutation_check"] = {
            "tasks": mutations,
            "total": sum(m["mutations"] for m in mutations),
            "caught": sum(m["caught"] for m in mutations),
            "survivors": [f"{m['task']}:{s}" for m in mutations for s in m["survivors"]],
        }
        out["any_mutation_survived"] = bool(out["mutation_check"]["survivors"])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gold", default="eval/gold")
    ap.add_argument("--task", default=None, help="run one gold set by directory name")
    ap.add_argument("--strict", action="store_true",
                    help="exit 2 if any declared threshold is missed, or (with "
                         "--mutate) if any declared mutation survives")
    ap.add_argument("--mutate", action="store_true",
                    help="also break each checker in the ways its manifest "
                         "declares and confirm the gold set notices")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    gold = _require_within_kit(ROOT / args.gold, "--gold")
    result = run_all(gold, args.task, mutate=args.mutate)
    emit(result, True)
    failed = result["any_threshold_missed"] or result.get("any_mutation_survived", False)
    sys.exit(2 if (args.strict and failed) else 0)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read gold sets — {e}")
    except UnicodeDecodeError as e:
        die(f"a gold-set file is not valid UTF-8 — {e}")
