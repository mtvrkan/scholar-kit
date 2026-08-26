#!/usr/bin/env python3
"""write_verify_status.py — the ONLY sanctioned writer of verify-status.json.

citation-verifier holds no Write tool (CLAUDE.md) — the orchestrator persists
its findings, and this script is the sanctioned path for that: it rejects an
internally inconsistent PASS (fabricated/retracted/missing/unresolved must
all be 0, checked must be > 0) before writing, and writes atomically. This
makes verify-status.json script-owned like registry.jsonl/cards.jsonl
(Invariant 6's pattern) instead of the one file with no sanctioned writer to
point protect_data_files.py at — previously nothing stopped a hand-written
`{"result":"PASS"}` from skipping /verify-citations entirely.

A claim of internal consistency alone doesn't prove the orchestrator actually
ran /verify-citations, though — a consistent-looking PASS can still be
fabricated. Before writing a PASS, this script also independently re-runs
`doi2bib.py --verify` and `cite_audit.py` against the CURRENT bib/drafts on
disk and refuses to write if that live recheck contradicts the claim — a real
DOI resolving to a genuinely different paper (fabricated > 0), an in-text
citation with no matching bib entry, or a literal [CITATION NEEDED] tag still
in the text. Deliberately does NOT hard-block on doi2bib's own "unresolved"
count (entries with no DOI at all) — a thesis with legitimate non-DOI sources
(books, personal communications, TR Dizin papers not in Crossref) marked
verified:false is a normal, accepted state, not a fabrication signal, and
citation-verifier's own judgment about those belongs to the agent, not a
blind recount. This is best-effort, not absolute: it needs network access for
the doi2bib recheck (silently skipped if unreachable — same "can't confirm,
don't pretend otherwise" posture as every other network-optional check in
this kit) and can't verify citation-verifier's retraction/orphan-citation
judgment calls at all. But it closes the cheap version of the bypass:
claiming PASS while the bib file or drafts on disk plainly contradict it.
No `--skip-live-check` escape hatch is offered on purpose — an orchestrator
that could just pass that flag would defeat the entire point; the graceful
"file/network unavailable → can't confirm → don't block" degradation already
covers every legitimate case where the recheck can't run.

Every write — PASS and FAIL alike — is also appended to the provenance chain
(scripts/provenance.py), which records the SHA-256 of the status file it just
wrote and links it to the record before it. That does not make the claim any
truer; it makes the SEQUENCE of claims something a later reader can check, and
makes a verification that was quietly replaced afterwards visible as drift. See
_attest() below and provenance.py's header for what a keyless chain does and
does not prove.

Usage:
  python scripts/write_verify_status.py --result PASS --checked 47 \
    --fabricated 0 --retracted 0 --missing 0 --unresolved 0 [--fixable 0]
    [--bib bib/references.bib] [--drafts drafts]
Exit codes: 0 ok · 1 error (internally inconsistent PASS, contradicted by a
live recheck, or bad args).
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit, require_within_cwd, write_json_atomic

VALID_RESULTS = {"PASS", "FAIL"}
CONSISTENCY_FIELDS = ("fabricated", "retracted", "missing", "unresolved")


DOI2BIB_TIMEOUT_MIN = 120
DOI2BIB_TIMEOUT_MAX = 1800
# Measured 2026-08-16 on the reference manuscript: 20 entries in 1229 s (~61 s
# each) against a doi.org that was rate-limiting after repeated runs. Rounded up
# for margin. This is an observation, not a bound — see _seconds_per_entry().
OBSERVED_SECONDS_PER_ENTRY = 75
# Fallbacks matching doi2bib.py/lib_common.py at the time of writing, used only
# when doi2bib.py can't be imported (it pulls `requests`, which this script
# deliberately does not require).
FALLBACK_RETRIES, FALLBACK_HTTP_TIMEOUT, FALLBACK_BACKOFF = 2, 20, 1.5


def _count_bib_entries(bib: Path) -> int:
    """Number of @type{...} records, for sizing the doi2bib timeout. Any read
    error returns 0, which falls back to the floor timeout."""
    try:
        text = bib.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines() if line.lstrip().startswith("@"))


def _seconds_per_entry() -> float:
    """Per-entry budget for doi2bib --verify, which makes one fetch_csl() call
    per bib entry via http_get_with_retry(retries=RETRIES, backoff=1.5,
    timeout=TIMEOUT).

    NO TRUE UPPER BOUND EXISTS, and it is worth being explicit about why,
    because the obvious arithmetic is wrong: `requests`' `timeout=` bounds each
    socket read, not the total duration of the request, so a server that keeps
    trickling bytes can hold a connection open far past it. Measured on the
    reference manuscript (20 entries, 2026-08-16): 1229 s wall clock, ~61 s per
    entry — comfortably past the RETRIES x TIMEOUT + backoff arithmetic (41.5 s)
    that an earlier version of this function claimed as the worst case.

    So the budget is the larger of two honest-but-partial figures: doi2bib's own
    retry arithmetic (a floor — it tracks retuning of the retry policy, which a
    hard-coded literal does not) and an OBSERVED per-entry cost with margin.
    Neither guarantees completion. That is acceptable only because a budget that
    expires is now recorded as `timeout` rather than as an unexplained failure to
    confirm — the caller is told to re-run the check standalone, not sent hunting
    for a path bug. Imported lazily and defensively: doi2bib.py imports
    `requests` at module level, and this script must stay usable without it."""
    try:
        import doi2bib  # noqa: PLC0415 — see docstring
        retries = getattr(doi2bib, "RETRIES", FALLBACK_RETRIES)
        http_timeout = getattr(doi2bib, "TIMEOUT", FALLBACK_HTTP_TIMEOUT)
    except Exception:
        retries, http_timeout = FALLBACK_RETRIES, FALLBACK_HTTP_TIMEOUT
    arithmetic = retries * http_timeout + max(0, retries - 1) * FALLBACK_BACKOFF
    return max(arithmetic, OBSERVED_SECONDS_PER_ENTRY)


def doi2bib_timeout_for(bib: Path) -> int:
    """A fixed timeout can't fit both a 3-entry pilot and an 80-entry thesis, and
    guessing small is the harmful direction: a recheck that times out is recorded
    as unconfirmed, which reads exactly like a recheck that DISAGREED. Scale with
    the bibliography using doi2bib's own worst case per entry, floor it so a tiny
    bib still gets a fair network window, and cap it so a pathological run cannot
    hang the gate indefinitely. When the cap binds, the budget is knowingly short
    of the worst case — `capped` in live_recheck says so rather than letting the
    resulting timeout look like a full-length attempt."""
    return max(DOI2BIB_TIMEOUT_MIN,
               min(DOI2BIB_TIMEOUT_MAX,
                   int(_seconds_per_entry() * _count_bib_entries(bib))))


def _run_json(cmd: list, timeout: int) -> tuple:
    """Run a kit script expected to emit JSON on stdout. Returns
    (payload|None, reason) where reason names WHY it failed — "timeout",
    "error", "unparseable" — instead of collapsing every cause into None."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except OSError:
        return None, "error"
    try:
        return json.loads(proc.stdout), "confirmed"
    except json.JSONDecodeError:
        return None, "unparseable"


def _live_reverify(bib_path: str, drafts_path: str) -> dict:
    """Independently re-run doi2bib.py --verify (bib fabrication/unresolved
    DOIs) and cite_audit.py (missing/placeholder in-text citations) against
    whatever is CURRENTLY on disk. Returns {"doi2bib": dict|None,
    "cite_audit": dict|None} plus a "<check>_reason" for each — None for a
    check means "couldn't run it", which callers must treat as "can't
    independently confirm," never as grounds to skip the check silently.
    Best-effort, same spirit as venue_check.py's local-dataset fallback or
    latex_build.sh's BLOCKED message.

    The reason strings exist because a bare None conflates four different
    situations — "fresh project, no bib yet" (legitimate), "--bib points at
    the wrong path while the real files sit elsewhere" (the failure mode this
    function exists to catch), "network down" and "the recheck simply needed
    more time than it was given". Reporting only the first two, as this
    function once did, sent readers hunting for a path bug when the real
    cause was the clock. build_status() persists whichever applies."""
    here = Path(__file__).parent
    result: dict = {"doi2bib": None, "cite_audit": None,
                    "doi2bib_reason": "absent", "cite_audit_reason": "absent",
                    "doi2bib_timeout_s": None}
    bib = Path(bib_path)
    if bib.exists():
        budget = doi2bib_timeout_for(bib)
        result["doi2bib_timeout_s"] = budget
        result["doi2bib_timeout_capped"] = budget == DOI2BIB_TIMEOUT_MAX
        result["doi2bib"], result["doi2bib_reason"] = _run_json(
            [sys.executable, str(here / "doi2bib.py"), "--verify", "--bib", str(bib), "--json"],
            budget)
    drafts = Path(drafts_path)
    if drafts.exists():
        result["cite_audit"], result["cite_audit_reason"] = _run_json(
            [sys.executable, str(here / "cite_audit.py"), "--drafts", str(drafts),
             "--bib", str(bib), "--json"], 30)
    return result


def build_status(args) -> dict:
    if args.result not in VALID_RESULTS:
        die(f"--result must be one of {sorted(VALID_RESULTS)}")
    # A negative count is nonsensical for either result. The PASS path below
    # separately requires the consistency fields to be exactly 0, but a FAIL
    # (or --fixable/--checked on any result) would otherwise persist a bogus
    # negative into verify-status.json that /critique and /submit-check consume.
    for name in ("checked",) + CONSISTENCY_FIELDS + ("fixable",):
        if getattr(args, name) < 0:
            die(f"--{name} must be >= 0, got {getattr(args, name)}")
    live_recheck = {"doi2bib_confirmed": False, "cite_audit_confirmed": False,
                    "doi2bib_reason": "not-run", "cite_audit_reason": "not-run",
                    "bib_checked": args.bib, "drafts_checked": args.drafts}
    if args.result == "PASS":
        for name in CONSISTENCY_FIELDS:
            val = getattr(args, name)
            if val != 0:
                die(f"--result PASS is inconsistent with --{name} {val} — a PASS "
                    f"requires {', '.join(CONSISTENCY_FIELDS)} to all be 0")
        if args.checked <= 0:
            die("--result PASS requires --checked > 0 — nothing was actually verified")
        live = _live_reverify(args.bib, args.drafts)
        d = live.get("doi2bib")
        live_recheck["doi2bib_confirmed"] = d is not None
        live_recheck["doi2bib_reason"] = live.get("doi2bib_reason", "not-run")
        if live.get("doi2bib_timeout_s") is not None:
            live_recheck["doi2bib_timeout_s"] = live["doi2bib_timeout_s"]
            live_recheck["doi2bib_timeout_capped"] = bool(live.get("doi2bib_timeout_capped"))
        if d is not None and d.get("fabricated", 0) > 0:
            die(f"claimed PASS contradicted by a live `doi2bib.py --verify` recheck of "
                f"{args.bib} — it found {d.get('fabricated', 0)} fabricated entry(ies) just now "
                f"(a real DOI resolving to a different paper). Re-run /verify-citations.")
        if d is not None and d.get("checked") is not None:
            # doi2bib.py --verify's own "checked" count is EVERY bib entry it
            # examined, including ones with no DOI field at all (reported
            # UNRESOLVED, not fabrication). citation-verifier legitimately
            # excludes those accepted non-DOI sources (books, personal
            # communications, TR Dizin papers not in Crossref) from its own
            # --checked figure — Invariant 3's own docstring above calls that
            # a "normal, accepted state, not a fabrication signal." Comparing
            # args.checked against the RAW live total then falsely blocked a
            # legitimate PASS whenever any such source was in the bib. Compare
            # against the count of entries doi2bib actually attempted a DOI
            # lookup for instead — that still catches the real failure mode
            # (wrong --bib path, stale/hand-typed --checked, a smaller/larger
            # bib than claimed), just not the no-DOI-is-normal case.
            live_entries = d.get("entries")
            if live_entries is not None:
                doi_checked = sum(
                    1 for r in live_entries
                    if not (r.get("status") == "UNRESOLVED"
                            and "no DOI field" in (r.get("reason") or "")))
            else:
                # Older/other doi2bib.py build with a "checked" total but no
                # per-entry "entries" breakdown — can't separate out no-DOI
                # entries, so fall back to the raw total (previous behavior).
                doi_checked = d.get("checked")
            if doi_checked != args.checked:
                die(f"claimed --checked {args.checked} does not match the live "
                    f"`doi2bib.py --verify` recheck of {args.bib}, which just found "
                    f"{doi_checked} DOI-bearing entr(y/ies) actually checked (of "
                    f"{d.get('checked')} total bib entries) — re-run /verify-citations "
                    f"against the current bibliography.")
        ca = live.get("cite_audit")
        live_recheck["cite_audit_confirmed"] = ca is not None
        live_recheck["cite_audit_reason"] = live.get("cite_audit_reason", "not-run")
        if ca is not None:
            missing = ca.get("missing") or []
            placeholders = ca.get("placeholders") or []
            # [MATERIAL GAP] blocks on the same footing as [CITATION NEEDED]:
            # both mark a hole in a finished manuscript. Without this, a draft
            # whose gaps the writer honestly refused to fill from model memory
            # could be written PASS even though cite_audit.py itself exits 2 on
            # it — the gate and its own recheck would disagree.
            # [LLM-SUPPLEMENTED] is deliberately absent: an author-authorized
            # fill is a decision to disclose, not a defect to block.
            material_gaps = ca.get("material_gaps") or []
            if missing or placeholders or material_gaps:
                die(f"claimed PASS contradicted by a live `cite_audit.py` recheck of "
                    f"{args.drafts} — {len(missing)} missing citation(s), "
                    f"{len(placeholders)} [CITATION NEEDED] placeholder(s), "
                    f"{len(material_gaps)} [MATERIAL GAP] tag(s) still present. "
                    f"Re-run /verify-citations.")
        if not (live_recheck["doi2bib_confirmed"] and live_recheck["cite_audit_confirmed"]):
            # Visible, not blocking (D-072c's own reasoning: a hard block here
            # would punish legitimate offline/fresh-project cases). But a wrong
            # --bib/--drafts path previously degraded exactly like a legitimate
            # fresh project, with zero trace in the written file — now every
            # PASS honestly records whether it was actually independently
            # corroborated, so a bad path can't pass for a confirmed one.
            hint = {
                "absent": "the file/directory is not there — a fresh project, or the "
                          "wrong path while the real files sit elsewhere",
                "timeout": f"it ran out of time (doi2bib budget "
                           f"{live_recheck.get('doi2bib_timeout_s')}s"
                           + (", CAPPED below this bibliography's worst case"
                              if live_recheck.get("doi2bib_timeout_capped") else "")
                           + "). NOT a disagreement and NOT a path problem: re-run the "
                             "check on its own to see its verdict",
                "error": "the checker could not be launched",
                "unparseable": "the checker ran but its output was not JSON",
                "not-run": "the recheck was not attempted",
            }
            causes = "; ".join(
                f"{name}={live_recheck[name + '_reason']} "
                f"({hint.get(live_recheck[name + '_reason'], 'unknown cause')})"
                for name in ("doi2bib", "cite_audit")
                if not live_recheck[name + "_confirmed"])
            print(f"WARN: PASS written with an incomplete live recheck against "
                  f"--bib {args.bib!r} --drafts {args.drafts!r} — {causes}. "
                  f"This PASS is NOT independently corroborated.",
                  file=sys.stderr)
    return {
        "result": args.result,
        "checked": args.checked,
        "fabricated": args.fabricated,
        "retracted": args.retracted,
        "missing": args.missing,
        "unresolved": args.unresolved,
        "fixable": args.fixable,
        "timestamp": datetime.date.today().isoformat(),
        "live_recheck": live_recheck,
    }


def _attest(status_file: str, status: dict) -> dict:
    """Append this write to the provenance chain (scripts/provenance.py).

    Here rather than left to the caller because this script is the ONLY
    sanctioned writer of verify-status.json: an attestation the orchestrator has
    to remember to make is one that is missing exactly when it matters. Both
    results are recorded, not just PASS — a FAIL that later becomes a PASS is the
    sequence a reader most wants to see, and a ledger that only ever holds good
    news is a ledger nobody should trust.

    Never fatal. The status file is already written and correct at this point;
    failing the whole command because an advisory record could not be appended
    would trade a working gate for a bookkeeping error. The failure is reported
    in the JSON instead, under the same "missing data is reported, never zeroed"
    rule as everything else here.
    """
    note = f"result={status['result']} checked={status['checked']}"
    try:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "provenance.py"),
             "--record", "verify-status", "--path", status_file, "--note", note,
             "--json"],
            capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            return {"recorded": False, "reason": (proc.stderr or "").strip()[:200]}
        return {"recorded": True, "record": json.loads(proc.stdout).get("recorded")}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"recorded": False, "reason": type(exc).__name__}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--result", required=True, help="PASS or FAIL")
    ap.add_argument("--checked", type=int, default=0)
    ap.add_argument("--fabricated", type=int, default=0)
    ap.add_argument("--retracted", type=int, default=0)
    ap.add_argument("--missing", type=int, default=0)
    ap.add_argument("--unresolved", type=int, default=0)
    ap.add_argument("--fixable", type=int, default=0)
    ap.add_argument("--bib", default="bib/references.bib",
                    help="cross-checked live via doi2bib.py --verify before a PASS is written")
    ap.add_argument("--drafts", default="drafts",
                    help="cross-checked live via cite_audit.py before a PASS is written")
    ap.add_argument("--file", default="verify-status.json")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()
    require_within_cwd(args.file, "--file")
    require_within_cwd(args.bib, "--bib")
    require_within_cwd(args.drafts, "--drafts")
    status = build_status(args)
    write_json_atomic(args.file, status)
    emit({"written": args.file, "status": status,
          "attested": _attest(args.file, status)}, True)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to write the status file — {e}")
