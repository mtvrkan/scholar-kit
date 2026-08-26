"""The attestation chain: what it detects, and what it honestly does not.

`scripts/provenance.py` exists because all three of the kit's gates are
file-based — the session that must pass a gate can write the file the gate
reads. Prevention is out of reach without a secret the orchestrator cannot
reach, and there is no such secret. So the chain does the reachable thing: it
makes the SEQUENCE of attestations checkable, and any rewriting of it visible.

These tests pin both halves. Most of them assert that tampering is caught; the
last group asserts, deliberately and by name, the two things the chain cannot
do — because a reader who believes it signs something would trust it further
than it deserves, and a test suite that only demonstrated strengths would be
where that belief comes from.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import provenance  # noqa: E402

_IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "provenance.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _json(proc) -> dict:
    return json.loads(proc.stdout)


def _artifact(tmp_path, name="outline/outline.md", text="**Status:** approved\n"):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _ledger(tmp_path) -> list[dict]:
    return [json.loads(line) for line in
            (tmp_path / "provenance.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def _rewrite_ledger(tmp_path, records):
    """Write the ledger back, clearing the read-only bit the sanctioned write
    left behind. This is the tamperer's job, done explicitly — which is the
    point: the OS layer makes it deliberate, and the chain makes it visible."""
    p = tmp_path / "provenance.jsonl"
    os.chmod(p, 0o644)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
                 encoding="utf-8")


# ---------- recording ----------

def test_first_record_starts_from_genesis(tmp_path):
    _artifact(tmp_path)
    rec = _json(_run(tmp_path, "--record", "outline-approved",
                     "--path", "outline/outline.md", "--json"))["recorded"]
    assert rec["seq"] == 1
    assert rec["prev"] == provenance.GENESIS
    assert rec["event"] == "outline-approved"
    assert rec["hash"] == provenance.record_hash(rec)


def test_each_record_links_to_the_one_before_it(tmp_path):
    _artifact(tmp_path)
    _artifact(tmp_path, "verify-status.json", '{"result": "PASS"}')
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    _run(tmp_path, "--record", "verify-status", "--path", "verify-status.json")
    first, second = _ledger(tmp_path)
    assert second["prev"] == first["hash"]
    assert second["seq"] == 2


def test_recording_a_missing_file_is_refused(tmp_path):
    # A record with no artifact behind it still reads as an attestation — the
    # same reasoning the removed showcase-index tests applied: a listed thing
    # that does not exist is worse than an absent one.
    _run(tmp_path, "--record", "build", "--path", "build/paper.pdf", expect=1)


def test_event_must_be_a_slug(tmp_path):
    _artifact(tmp_path)
    _run(tmp_path, "--record", "Outline Approved!", "--path", "outline/outline.md", expect=1)


def test_the_ledger_is_read_only_after_a_sanctioned_append(tmp_path):
    if _IS_ROOT:
        pytest.skip("chmod does not constrain root")
    _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    mode = (tmp_path / "provenance.jsonl").stat().st_mode
    assert not mode & 0o222, (
        "provenance.jsonl is writable — a chain whose file anyone can replace "
        "wholesale proves nothing, so it belongs to the same OS layer as the "
        "other six script-owned files")


def test_the_script_can_still_append_to_its_own_read_only_ledger(tmp_path):
    # The protection must not lock out the sanctioned writer — that would make
    # the ledger single-use and the whole mechanism unusable after one record.
    _artifact(tmp_path)
    _artifact(tmp_path, "verify-status.json", "{}")
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    _run(tmp_path, "--record", "verify-status", "--path", "verify-status.json")
    assert len(_ledger(tmp_path)) == 2


# ---------- verification ----------

def test_verify_reports_an_intact_chain(tmp_path):
    _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    result = _json(_run(tmp_path, "--verify", "--json"))
    assert result["status"] == "ok" and result["chain"] == "intact"
    assert result["records"] == 1 and result["drift"] == [] and result["missing"] == []


def test_editing_a_record_in_place_breaks_the_chain(tmp_path):
    _artifact(tmp_path)
    _artifact(tmp_path, "verify-status.json", "{}")
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    _run(tmp_path, "--record", "verify-status", "--path", "verify-status.json")
    records = _ledger(tmp_path)
    records[0]["note"] = "approved by the committee"   # a plausible-looking edit
    _rewrite_ledger(tmp_path, records)
    result = _json(_run(tmp_path, "--verify", "--json"))
    assert result["chain"] == "broken" and result["broken_at"] == 1


def test_deleting_a_record_breaks_the_chain(tmp_path):
    # Tidying the history is the likelier move than forging one record: drop the
    # inconvenient line and the file still parses.
    for name, text in (("outline/outline.md", "x"), ("verify-status.json", "{}"),
                       ("drafts/STATUS.md", "y")):
        _artifact(tmp_path, name, text)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    _run(tmp_path, "--record", "verify-status", "--path", "verify-status.json")
    _run(tmp_path, "--record", "review-round", "--path", "drafts/STATUS.md")
    records = _ledger(tmp_path)
    _rewrite_ledger(tmp_path, [records[0], records[2]])
    result = _json(_run(tmp_path, "--verify", "--json"))
    assert result["chain"] == "broken" and result["broken_at"] == 2


def test_an_edited_artifact_is_drift_not_a_broken_chain(tmp_path):
    # The common, innocent case — a draft revised after it was attested. It must
    # not be reported in the same breath as tampering.
    p = _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    p.write_text("**Status:** approved\n## a section added later\n", encoding="utf-8")
    result = _json(_run(tmp_path, "--verify", "--json"))
    assert result["chain"] == "intact"
    assert [d["path"] for d in result["drift"]] == ["outline/outline.md"]


def test_a_deleted_artifact_is_reported_as_missing_not_as_drift(tmp_path):
    p = _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    p.unlink()
    result = _json(_run(tmp_path, "--verify", "--json"))
    assert result["missing"] and not result["drift"]


def test_an_absent_ledger_is_reported_as_absent_never_as_clean(tmp_path):
    # CONTRIBUTING.md's rule, in the place it matters most: "I found nothing" and
    # "I did not look" must not print the same word.
    result = _json(_run(tmp_path, "--verify", "--json"))
    assert result["status"] == "absent"
    assert result["chain"] == "unknown"


def test_strict_exits_two_on_a_broken_chain(tmp_path):
    _artifact(tmp_path)
    _artifact(tmp_path, "verify-status.json", "{}")
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    _run(tmp_path, "--record", "verify-status", "--path", "verify-status.json")
    records = _ledger(tmp_path)
    records[0]["sha256"] = "0" * 64
    _rewrite_ledger(tmp_path, records)
    _run(tmp_path, "--verify", "--strict", "--json", expect=2)


def test_strict_does_not_exit_two_when_nothing_was_ever_attested(tmp_path):
    # A project that has not run the check has not failed it.
    _run(tmp_path, "--verify", "--strict", "--json", expect=0)


# ---------- querying ----------

def test_attests_reports_a_current_match(tmp_path):
    _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    result = _json(_run(tmp_path, "--attests", "outline/outline.md", "--json"))
    assert result["attested"] and result["matches_current"]


def test_attests_reports_a_stale_match(tmp_path):
    p = _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    p.write_text("edited\n", encoding="utf-8")
    result = _json(_run(tmp_path, "--attests", "outline/outline.md", "--json"))
    assert result["attested"] and not result["matches_current"]


def test_attests_returns_the_latest_record_for_a_path(tmp_path):
    # An outline revised and re-approved: the gate always asks about now.
    p = _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    p.write_text("**Status:** approved\nv2\n", encoding="utf-8")
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    result = _json(_run(tmp_path, "--attests", "outline/outline.md", "--json"))
    assert result["seq"] == 2 and result["matches_current"]


def test_attests_on_an_unrecorded_path(tmp_path):
    _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    result = _json(_run(tmp_path, "--attests", "drafts/intro.md", "--json"))
    assert not result["attested"] and not result["matches_current"]


# ---------- the two limits, asserted by name ----------

def test_the_chain_cannot_detect_a_freshly_forged_record(tmp_path):
    """The limit the header states, pinned so nobody can quietly claim otherwise.

    An orchestrator that never showed the outline to anyone can run the
    sanctioned writer right now and produce a perfectly valid record. Nothing
    here signs anything, so this MUST verify clean — and the value of the
    mechanism is that the forgery is now a dated, hashed line in a file, not an
    absence of one.
    """
    _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md",
         "--note", "nobody actually approved this")
    assert _json(_run(tmp_path, "--verify", "--json"))["status"] == "ok"


def test_a_wholesale_rechained_history_verifies_clean(tmp_path):
    """The other limit: a keyless chain can be recomputed end to end.

    Deleting the ledger and re-attesting from scratch produces an intact chain
    with a shorter history. The chain detects EDITING, not REPLACEMENT — and the
    only thing standing against replacement is the OS-level read-only bit plus
    the hook, i.e. exactly the layers SECURITY.md already says are not a security
    boundary.
    """
    _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    os.chmod(tmp_path / "provenance.jsonl", 0o644)
    (tmp_path / "provenance.jsonl").unlink()
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    result = _json(_run(tmp_path, "--verify", "--json"))
    assert result["status"] == "ok" and result["records"] == 1


# ---------- the hook reads the same chain the script writes ----------

def test_hook_and_script_hash_a_record_identically():
    """`phase_gate.py` re-implements record_hash because hooks import nothing
    from scripts/. That duplication is only safe while it stays exact."""
    sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
    import phase_gate

    record = {"seq": 3, "ts": "2026-08-14T10:00:00Z", "event": "outline-approved",
              "path": "outline/outline.md", "sha256": "ab" * 32, "prev": "cd" * 32,
              "note": "unicode: ölçüm"}
    assert phase_gate._record_hash(record) == provenance.record_hash(record)
    assert phase_gate.HASHED_FIELDS == provenance.HASHED_FIELDS
    assert phase_gate.GENESIS == provenance.GENESIS


# ---------- output contract ----------

@pytest.mark.parametrize("args", [("--verify",), ("--attests", "outline/outline.md")])
def test_output_is_exactly_one_json_object(tmp_path, args):
    _artifact(tmp_path)
    _run(tmp_path, "--record", "outline-approved", "--path", "outline/outline.md")
    json.loads(_run(tmp_path, *args).stdout)   # raises if anything else was printed
