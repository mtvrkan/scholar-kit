"""Regression tests for scripts/write_verify_status.py's newest consistency
checks. Older write_verify_status.py coverage (the live doi2bib/cite_audit
recheck's fabricated/missing gate, the "incomplete recheck" WARN) predates
this file and still lives in test_remediation_2026_07_04_round3.py and
test_remediation_2026_07_04_round4.py — out of scope for this pass, left as
is; this file is the canonical home going forward for new write_verify_status
tests instead of another dated round-N file.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import write_verify_status  # noqa: E402


def _vs_args(**overrides):
    base = dict(result="PASS", checked=5, fabricated=0, retracted=0, missing=0,
               unresolved=0, fixable=0, bib="bib/references.bib", drafts="drafts")
    base.update(overrides)
    return type("Args", (), base)()


def test_write_verify_status_rejects_negative_fabricated(run, tmp_path):
    # `if val > 0` (instead of `!= 0`) let a negative value slip past the
    # internal-consistency check entirely.
    code, out, err = run("write_verify_status.py", "--result", "PASS", "--checked", "5",
                         "--fabricated", "-1", "--retracted", "0", "--missing", "0",
                         "--unresolved", "0")
    assert code == 1
    assert "fabricated" in err.lower()
    assert not (tmp_path / "verify-status.json").exists()


def test_checked_mismatch_against_live_doi2bib_recheck_blocks_pass(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@article{a2020x, title={x}}", encoding="utf-8")

    def fake_run(cmd, **k):
        class FakeProc:
            pass
        proc = FakeProc()
        if "doi2bib.py" in cmd[1]:
            # live recheck says only 2 entries were actually examined, but
            # the caller below claims 5 were checked.
            proc.stdout = json.dumps({"result": "PASS", "fabricated": 0, "unresolved": 0, "checked": 2})
        else:
            proc.stdout = json.dumps({"missing": [], "placeholders": []})
        return proc

    monkeypatch.setattr(write_verify_status.subprocess, "run", fake_run)
    with pytest.raises(SystemExit):
        write_verify_status.build_status(_vs_args(checked=5))


def test_checked_matching_live_doi2bib_recheck_allows_pass(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@article{a2020x, title={x}}", encoding="utf-8")

    def fake_run(cmd, **k):
        class FakeProc:
            pass
        proc = FakeProc()
        if "doi2bib.py" in cmd[1]:
            proc.stdout = json.dumps({"result": "PASS", "fabricated": 0, "unresolved": 0, "checked": 5})
        else:
            proc.stdout = json.dumps({"missing": [], "placeholders": []})
        return proc

    monkeypatch.setattr(write_verify_status.subprocess, "run", fake_run)
    status = write_verify_status.build_status(_vs_args(checked=5))
    assert status["result"] == "PASS"


def _cite_audit_project(tmp_path, monkeypatch, payload):
    """Project state that actually reaches the cite_audit branch of the recheck.

    _live_reverify() only shells out to cite_audit.py when the drafts directory
    EXISTS; without it the branch is skipped and `cite_audit` stays None, so a
    test asserting on cite_audit behaviour would pass vacuously no matter what
    the gate does.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@article{a2020x, title={x}}",
                                                     encoding="utf-8")
    (tmp_path / "drafts").mkdir()

    def fake_run(cmd, **k):
        class FakeProc:
            pass
        proc = FakeProc()
        if "doi2bib.py" in cmd[1]:
            proc.stdout = json.dumps({"result": "PASS", "fabricated": 0,
                                      "unresolved": 0, "checked": 5})
        else:
            proc.stdout = json.dumps(payload)
        return proc

    monkeypatch.setattr(write_verify_status.subprocess, "run", fake_run)


def test_material_gap_in_live_recheck_blocks_pass(monkeypatch, tmp_path):
    # The gate and its own recheck must agree: cite_audit.py exits 2 on a
    # [MATERIAL GAP], so a PASS written over one would be a gate contradicting
    # the very tool it re-runs to corroborate itself.
    _cite_audit_project(tmp_path, monkeypatch,
                        {"missing": [], "placeholders": [],
                         "material_gaps": ["drafts/intro.md:4"]})
    with pytest.raises(SystemExit):
        write_verify_status.build_status(_vs_args(checked=5))


def test_llm_supplemented_in_live_recheck_does_not_block_pass(monkeypatch, tmp_path):
    # An author-authorized fill is a disclosure, not a defect.
    _cite_audit_project(tmp_path, monkeypatch,
                        {"missing": [], "placeholders": [], "material_gaps": [],
                         "llm_supplemented": ["drafts/intro.md:7"]})
    status = write_verify_status.build_status(_vs_args(checked=5))
    assert status["result"] == "PASS"
    assert status["live_recheck"]["cite_audit_confirmed"] is True


def test_recheck_without_material_gaps_key_still_passes(monkeypatch, tmp_path):
    # An older cite_audit.py build emits no material_gaps key; absence must read
    # as "none found", not crash the gate.
    _cite_audit_project(tmp_path, monkeypatch, {"missing": [], "placeholders": []})
    status = write_verify_status.build_status(_vs_args(checked=5))
    assert status["result"] == "PASS"
    assert status["live_recheck"]["cite_audit_confirmed"] is True


def test_no_doi_entries_excluded_from_checked_comparison_allows_pass(monkeypatch, tmp_path):
    # A bib with legitimate non-DOI sources (books, personal communications)
    # makes doi2bib.py's raw "checked" total (5, includes 2 UNRESOLVED
    # no-DOI entries) differ from citation-verifier's own --checked count (3,
    # DOI-bearing entries only) — this must NOT block a legitimate PASS.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@article{a2020x, title={x}}", encoding="utf-8")

    def fake_run(cmd, **k):
        class FakeProc:
            pass
        proc = FakeProc()
        if "doi2bib.py" in cmd[1]:
            proc.stdout = json.dumps({
                "result": "FAIL", "fabricated": 0, "unresolved": 2, "checked": 5,
                "entries": [
                    {"key": "a2020x", "status": "PASS"},
                    {"key": "b2021y", "status": "PASS"},
                    {"key": "c2022z", "status": "FIX", "patch": {}},
                    {"key": "book2019", "status": "UNRESOLVED",
                     "reason": "no DOI field — run doi2bib.py --title-search or mark verified:false"},
                    {"key": "personal2020", "status": "UNRESOLVED",
                     "reason": "no DOI field — run doi2bib.py --title-search or mark verified:false"},
                ],
            })
        else:
            proc.stdout = json.dumps({"missing": [], "placeholders": []})
        return proc

    monkeypatch.setattr(write_verify_status.subprocess, "run", fake_run)
    status = write_verify_status.build_status(_vs_args(checked=3))
    assert status["result"] == "PASS"


def test_missing_checked_key_in_live_recheck_does_not_block(monkeypatch, tmp_path):
    # An older/other doi2bib.py build that omits "checked" entirely must
    # degrade to "can't confirm this dimension," the same posture every other
    # live-recheck field takes here — not a hard block.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@article{a2020x, title={x}}", encoding="utf-8")

    def fake_run(cmd, **k):
        class FakeProc:
            pass
        proc = FakeProc()
        if "doi2bib.py" in cmd[1]:
            proc.stdout = json.dumps({"result": "PASS", "fabricated": 0, "unresolved": 0})
        else:
            proc.stdout = json.dumps({"missing": [], "placeholders": []})
        return proc

    monkeypatch.setattr(write_verify_status.subprocess, "run", fake_run)
    status = write_verify_status.build_status(_vs_args(checked=5))
    assert status["result"] == "PASS"


def test_write_verify_status_rejects_negative_count_on_fail_result(run, tmp_path):
    # The PASS path requires the consistency fields to be exactly 0, but the
    # FAIL path did not validate signs at all — a negative --checked/--missing
    # etc. would persist a nonsensical value into verify-status.json.
    code, out, err = run("write_verify_status.py", "--result", "FAIL", "--checked", "-3",
                         "--fabricated", "0", "--retracted", "0", "--missing", "0",
                         "--unresolved", "0")
    assert code == 1
    assert "checked" in err.lower()
    assert not (tmp_path / "verify-status.json").exists()


def test_write_verify_status_rejects_negative_fixable(run, tmp_path):
    code, out, err = run("write_verify_status.py", "--result", "FAIL", "--checked", "5",
                         "--fabricated", "0", "--retracted", "0", "--missing", "0",
                         "--unresolved", "0", "--fixable", "-2")
    assert code == 1
    assert "fixable" in err.lower()


# --- live-recheck failure causes are distinguished, not collapsed into False ---
#
# Measured on the dr-tarama reference manuscript (2026-08-16): a 20-entry
# bibliography needs >300 s of Crossref content negotiation, so the old fixed
# 120 s budget always expired and verify-status.json recorded
# doi2bib_confirmed=false — indistinguishable from "the recheck DISAGREED",
# while the WARN blamed the --bib path, which was correct all along.

def _bib_project(tmp_path, monkeypatch, entries=1):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text(
        "\n".join("@article{k%d,\n title={x}\n}" % i for i in range(entries)),
        encoding="utf-8")
    # drafts/ must exist too, or cite_audit reports "absent" and the test can no
    # longer show that the two checks are reported independently of each other.
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "intro.md").write_text("x [@k0]\n", encoding="utf-8")


def test_doi2bib_timeout_is_recorded_as_timeout_not_as_a_path_problem(monkeypatch, tmp_path, capsys):
    _bib_project(tmp_path, monkeypatch)

    def fake_run(cmd, **k):
        if "doi2bib.py" in cmd[1]:
            raise write_verify_status.subprocess.TimeoutExpired(cmd, k.get("timeout", 1))
        proc = type("FakeProc", (), {})()
        proc.stdout = json.dumps({"missing": [], "placeholders": []})
        return proc

    monkeypatch.setattr(write_verify_status.subprocess, "run", fake_run)
    status = write_verify_status.build_status(_vs_args(checked=5))

    assert status["result"] == "PASS"
    assert status["live_recheck"]["doi2bib_confirmed"] is False
    assert status["live_recheck"]["doi2bib_reason"] == "timeout"
    assert status["live_recheck"]["cite_audit_reason"] == "confirmed"
    warn = capsys.readouterr().err
    assert "timeout" in warn
    # The old message sent readers hunting for a path bug on every cause.
    assert "ran out of time" in warn


def test_absent_bib_is_recorded_as_absent(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no bib/, no drafts/

    monkeypatch.setattr(write_verify_status.subprocess, "run",
                        lambda *a, **k: pytest.fail("no checker should be launched"))
    status = write_verify_status.build_status(_vs_args(checked=5))

    assert status["live_recheck"]["doi2bib_reason"] == "absent"
    assert status["live_recheck"]["cite_audit_reason"] == "absent"


def test_doi2bib_timeout_scales_with_bibliography_size(tmp_path):
    tiny = tmp_path / "tiny.bib"
    tiny.write_text("@article{a,\n title={x}\n}\n", encoding="utf-8")
    assert write_verify_status.doi2bib_timeout_for(tiny) == write_verify_status.DOI2BIB_TIMEOUT_MIN

    real = tmp_path / "real.bib"
    real.write_text("\n".join("@article{k%d,\n title={x}\n}" % i for i in range(20)),
                    encoding="utf-8")
    # 20 entries is the reference manuscript's size; it must clear the old 120 s.
    per_entry = write_verify_status._seconds_per_entry()
    assert write_verify_status.doi2bib_timeout_for(real) == int(20 * per_entry)
    assert write_verify_status.doi2bib_timeout_for(real) > 120

    huge = tmp_path / "huge.bib"
    huge.write_text("\n".join("@article{k%d,\n title={x}\n}" % i for i in range(500)),
                    encoding="utf-8")
    assert write_verify_status.doi2bib_timeout_for(huge) == write_verify_status.DOI2BIB_TIMEOUT_MAX


def test_per_entry_budget_follows_doi2bibs_own_retry_policy(monkeypatch):
    # The whole defect was a budget constant chosen once and left to go stale.
    # Tracking doi2bib's own RETRIES/TIMEOUT means retuning those retunes the
    # gate too, instead of silently invalidating it.
    import doi2bib
    monkeypatch.setattr(doi2bib, "RETRIES", 8, raising=False)
    monkeypatch.setattr(doi2bib, "TIMEOUT", 30, raising=False)
    assert write_verify_status._seconds_per_entry() == 8 * 30 + 7 * write_verify_status.FALLBACK_BACKOFF


def test_per_entry_budget_never_falls_below_the_observed_cost(monkeypatch):
    # requests' `timeout=` bounds each socket READ, not the request's total
    # duration, so the retry arithmetic is a floor and not a bound: the
    # reference manuscript measured ~61 s/entry against an arithmetic 41.5 s.
    # A retry policy tuned down must not drag the budget under what the network
    # was actually observed to cost.
    import doi2bib
    monkeypatch.setattr(doi2bib, "RETRIES", 1, raising=False)
    monkeypatch.setattr(doi2bib, "TIMEOUT", 5, raising=False)
    assert (write_verify_status._seconds_per_entry()
            == write_verify_status.OBSERVED_SECONDS_PER_ENTRY)


def test_budget_covers_the_measured_reference_run(tmp_path):
    # 20 entries took 1229 s wall clock on 2026-08-16. A budget under that would
    # reproduce the original defect on the very manuscript that exposed it.
    bib = tmp_path / "ref.bib"
    bib.write_text("\n".join("@article{k%d,\n title={x}\n}" % i for i in range(20)),
                   encoding="utf-8")
    assert write_verify_status.doi2bib_timeout_for(bib) > 1229


def test_capped_timeout_is_flagged_as_capped(monkeypatch, tmp_path):
    # A budget that hit the ceiling is knowingly SHORT of the worst case; a
    # timeout under it must not read like a full-length attempt that failed.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text(
        "\n".join("@article{k%d,\n title={x}\n}" % i for i in range(500)), encoding="utf-8")

    def fake_run(cmd, **k):
        raise write_verify_status.subprocess.TimeoutExpired(cmd, k.get("timeout", 1))

    monkeypatch.setattr(write_verify_status.subprocess, "run", fake_run)
    status = write_verify_status.build_status(_vs_args(checked=5))
    assert status["live_recheck"]["doi2bib_timeout_s"] == write_verify_status.DOI2BIB_TIMEOUT_MAX
    assert status["live_recheck"]["doi2bib_timeout_capped"] is True


def test_unparseable_checker_output_is_not_reported_as_a_timeout(monkeypatch, tmp_path):
    _bib_project(tmp_path, monkeypatch)

    def fake_run(cmd, **k):
        proc = type("FakeProc", (), {})()
        proc.stdout = "Traceback (most recent call last): ..."
        return proc

    monkeypatch.setattr(write_verify_status.subprocess, "run", fake_run)
    status = write_verify_status.build_status(_vs_args(checked=5))
    assert status["live_recheck"]["doi2bib_reason"] == "unparseable"
