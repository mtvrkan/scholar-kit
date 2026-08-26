"""Regression tests for .claude/hooks/phase_gate.py — CLAUDE.md Invariant 3
(phase gates: no drafting before outline approval, no critique before
verify=PASS, no formatting before Major=0). Before this hook existed, these
gates were markdown instructions inside SKILL.md files only, with no
tool-call-layer enforcement — a direct Write/Edit or a Bash-invoked build
script could bypass them entirely.
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"


def _run_hook(payload, cwd):
    # The hook no-ops outside a Scholar-Kit project (see _project_scope.py):
    # drafts/, build/ and exports/ are ordinary directory names, and as a
    # plugin this hook runs in every session. These tests exercise the GATE
    # logic, so the fixture declares a kit project; the guard itself has its
    # own tests in test_project_scope_hook.py.
    Path(cwd, "PROJECT.md").touch()
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "phase_gate.py")],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return proc.stdout


def _write(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# What scripts/write_verify_status.py actually writes for a PASS it was able to
# corroborate: the counts PLUS the `live_recheck` block recording that doi2bib
# and cite_audit were re-run against the files on disk. The format gate opens
# for either shape, but only this one opens it SILENTLY — see
# verify_provenance_note(). Tests that are about some other part of the gate use
# this so the note does not show up in their output as unrelated noise; the note
# itself is asserted directly in its own section below.
VERIFY_PASS = json.dumps({
    "result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0,
    "missing": 0, "unresolved": 0,
    "live_recheck": {"doi2bib_confirmed": True, "cite_audit_confirmed": True,
                     "bib_checked": "bib/references.bib", "drafts_checked": "drafts"},
})


# ---------- draft gate: outline must be approved ----------

def test_draft_write_blocked_when_no_outline(tmp_path):
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert "deny" in out
    assert "outline" in out.lower()


def test_draft_write_blocked_when_outline_pending(tmp_path):
    _write(tmp_path, "outline/outline.md", "**Status:** pending-approval\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert "deny" in out


def test_draft_write_allowed_when_outline_approved(tmp_path):
    _write(tmp_path, "outline/outline.md", "**Status:** approved\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert out.strip() == ""


def test_draft_write_allowed_when_the_approval_marker_is_in_turkish(tmp_path):
    """/outline tells the session to write user-facing strings in Turkish and
    then shows an English "**Status:** approved" template. A session obeying both
    writes "**Durum:** approved" — and the gate used to reject a genuinely
    approved outline, reporting it as unapproved. What carries the authorisation
    is the word "approved" and the provenance record, never the label's language.
    """
    _write(tmp_path, "outline/outline.md", "**Durum:** approved\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert out.strip() == ""


def test_a_missing_marker_and_a_pending_outline_get_different_messages(tmp_path):
    """The two failures need different actions from the reader: a pending outline
    must be approved, while a missing marker on an already-approved outline must
    be restored — re-running /outline there regenerates a file whose content was
    already right. One shared "not approved" message sends half the readers the
    wrong way."""
    _write(tmp_path, "outline/outline.md", "**Status:** pending-approval\n")
    pending = _run_hook({"tool_name": "Write",
                          "tool_input": {"file_path": str(tmp_path / "drafts" / "a.md")}}, tmp_path)
    _write(tmp_path, "outline/outline.md", "# İskelet\n\nGövde, işaret satırı yok.\n")
    missing = _run_hook({"tool_name": "Write",
                          "tool_input": {"file_path": str(tmp_path / "drafts" / "a.md")}}, tmp_path)
    assert "deny" in pending and "deny" in missing
    assert "pending-approval" in pending
    assert "no approval marker" in missing
    assert "pending-approval" not in missing


def test_draft_write_allowed_when_approved_with_matching_timestamp(tmp_path):
    # outline/SKILL.md's real approval step writes "Approved at" alongside
    # "Status: approved" — must still be allowed, not just the bare-Status form.
    now = datetime.datetime.now(datetime.timezone.utc)
    p = _write(tmp_path, "outline/outline.md",
               f"**Status:** approved\n**Approved at:** {now.isoformat()}\n")
    os.utime(p, (now.timestamp(), now.timestamp()))
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert out.strip() == ""


def test_draft_write_blocked_when_outline_edited_after_approval(tmp_path):
    # Approve, then edit the file again afterward (mtime advances past the
    # recorded "Approved at" timestamp) — the approval must no longer count.
    approved_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    p = _write(tmp_path, "outline/outline.md",
               f"**Status:** approved\n**Approved at:** {approved_at.isoformat()}\n"
               f"## Extra heading added after approval\n")
    later = approved_at + datetime.timedelta(minutes=30)
    os.utime(p, (later.timestamp(), later.timestamp()))
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert "deny" in out
    assert "modified after" in out.lower()


def test_draft_write_blocked_when_outline_edited_after_approval_naive_timestamp(tmp_path):
    # Regression: a hand-edited "Approved at" with no "Z"/offset (naive) made
    # `mtime > approved_at` raise TypeError (tz-aware vs. naive comparison)
    # OUTSIDE this function's own try/except — swallowed by main()'s outer
    # fail-open backstop, which silently disabled the staleness check
    # entirely instead of falling back to "can't check, allow" on purpose.
    approved_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
    naive_str = approved_at.replace(tzinfo=None).isoformat()  # no "Z", no offset
    p = _write(tmp_path, "outline/outline.md",
               f"**Status:** approved\n**Approved at:** {naive_str}\n"
               f"## Extra heading added after approval\n")
    later = approved_at + datetime.timedelta(minutes=30)
    os.utime(p, (later.timestamp(), later.timestamp()))
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert "deny" in out
    assert "modified after" in out.lower()


def test_drafts_status_md_exempt_from_outline_gate(tmp_path):
    # drafts/STATUS.md is written by /critique itself (Major-issue TODOs) —
    # must never be blocked by the outline gate.
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "STATUS.md")}}, tmp_path)
    assert out.strip() == ""


def test_edit_of_existing_draft_also_gated(tmp_path):
    out = _run_hook({"tool_name": "Edit",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert "deny" in out


# ---------- the outline gate, bound to content instead of to a clock ----------
# The approval line and the "Approved at" timestamp are both hand-written into
# the file the gate reads. When the project keeps a provenance ledger, the
# recorded approval carries the SHA-256 of what was approved, so "edited
# afterwards" becomes a question about bytes. Neither closes the forgery — see
# provenance.py's header and test_provenance.py's two by-name limit tests.

def _attest(tmp_path, event, rel):
    """Record an attestation the way the /outline skill does — through the
    sanctioned writer, so these tests exercise the real chain rather than a
    hand-built fixture that could drift from it."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "provenance.py"),
         "--record", event, "--path", rel, "--json"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)["recorded"]


def test_draft_allowed_when_the_attested_outline_still_matches_byte_for_byte(tmp_path):
    # Deliberately with a STALE-looking timestamp: an outline re-saved after
    # approval (mtime moves, content does not) is not a change, and the ledger is
    # what can tell the difference.
    approved_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
    p = _write(tmp_path, "outline/outline.md",
               f"**Status:** approved\n**Approved at:** {approved_at.isoformat()}\n")
    _attest(tmp_path, "outline-approved", "outline/outline.md")
    later = approved_at + datetime.timedelta(hours=1)
    os.utime(p, (later.timestamp(), later.timestamp()))
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert out.strip() == ""


def test_draft_blocked_when_the_outline_changed_since_it_was_attested(tmp_path):
    p = _write(tmp_path, "outline/outline.md", "**Status:** approved\n")
    _attest(tmp_path, "outline-approved", "outline/outline.md")
    p.write_text("**Status:** approved\n## a whole section added afterwards\n",
                 encoding="utf-8")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert "deny" in out
    assert "no longer matches" in out.lower()


def test_a_hand_edited_ledger_record_is_not_evidence(tmp_path):
    # Rewriting the recorded digest to match an edited outline must not buy an
    # approval: the record's own hash no longer recomputes, so the gate ignores
    # it entirely and falls back to the timestamp check (which denies here,
    # because the file was edited after its recorded approval time).
    approved_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)
    p = _write(tmp_path, "outline/outline.md",
               f"**Status:** approved\n**Approved at:** {approved_at.isoformat()}\n")
    _attest(tmp_path, "outline-approved", "outline/outline.md")
    p.write_text(f"**Status:** approved\n**Approved at:** {approved_at.isoformat()}\n"
                 f"## added afterwards\n", encoding="utf-8")
    ledger = tmp_path / "provenance.jsonl"
    os.chmod(ledger, 0o644)
    record = json.loads(ledger.read_text(encoding="utf-8").strip())
    record["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()   # forged to match
    ledger.write_text(json.dumps(record) + "\n", encoding="utf-8")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert "deny" in out
    assert "modified after" in out.lower()


def test_an_unattested_outline_still_uses_the_timestamp_check(tmp_path):
    # Backwards compatibility, pinned: every project created before the ledger
    # existed, and every author who never runs /outline's record step, keeps
    # exactly the behaviour they had.
    _write(tmp_path, "outline/outline.md", "**Status:** approved\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert out.strip() == ""


# ---------- critique gate: verify-status.json must be PASS ----------

def test_review_write_blocked_when_no_verify_status(tmp_path):
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "reviews" / "round-1.md")}}, tmp_path)
    assert "deny" in out
    assert "verify-citations" in out.lower()


def test_review_write_blocked_when_verify_fail(tmp_path):
    _write(tmp_path, "verify-status.json", json.dumps({"result": "FAIL"}))
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "reviews" / "round-1.md")}}, tmp_path)
    assert "deny" in out


def test_review_write_allowed_when_verify_pass(tmp_path):
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "reviews" / "round-1.md")}}, tmp_path)
    assert out.strip() == ""


def test_review_write_blocked_on_malformed_verify_status_json(tmp_path):
    _write(tmp_path, "verify-status.json", "{not valid json")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "reviews" / "round-1.md")}}, tmp_path)
    assert "deny" in out


# ---------- format gate: verify PASS AND latest review Major=0 ----------

def test_build_write_blocked_without_any_review(tmp_path):
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert "deny" in out
    assert "critique" in out.lower()


def test_export_write_blocked_when_major_issues_remain(tmp_path):
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    _write(tmp_path, "reviews/round-1.md", "## SUMMARY\nMajor issues:    2\nMinor issues:    1\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "exports" / "paper.docx")}}, tmp_path)
    assert "deny" in out
    assert "major" in out.lower()


def test_export_write_allowed_when_major_zero_and_verify_pass(tmp_path):
    _write(tmp_path, "verify-status.json", VERIFY_PASS)
    _write(tmp_path, "reviews/round-2.md", "## SUMMARY\nMajor issues:    0\nMinor issues:    1\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "exports" / "paper.docx")}}, tmp_path)
    assert out.strip() == ""


def test_format_gate_picks_highest_round_not_lexicographically_last(tmp_path):
    # round-2 sorts after round-10 lexicographically ("round-2" > "round-10")
    # but round-10 is the actually-latest round; the gate must compare
    # numerically, not by filename string order.
    _write(tmp_path, "verify-status.json", VERIFY_PASS)
    _write(tmp_path, "reviews/round-2.md", "## SUMMARY\nMajor issues:    3\n")
    _write(tmp_path, "reviews/round-10.md", "## SUMMARY\nMajor issues:    0\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert out.strip() == ""


def test_format_gate_falls_back_to_counting_major_section_items(tmp_path):
    # If a review doesn't include the "Major issues: N" summary line, count
    # numbered items under "## MAJOR ISSUES" instead of failing closed forever.
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    _write(tmp_path, "reviews/round-1.md",
           "## MAJOR ISSUES\n1. Overclaiming in abstract\n2. RQ2 unanswered\n\n## MINOR ISSUES\n1. Typo\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert "deny" in out


def test_format_gate_section_fallback_ignores_indented_sub_items(tmp_path):
    # Regression: `^\s*\d+\.` (any leading whitespace) also matched an INDENTED
    # numbered sub-point under a single top-level Major issue, double-counting
    # it as if it were its own separate issue and blocking a build that
    # actually has just 1 real Major issue, not 2.
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    _write(tmp_path, "reviews/round-1.md",
           "## MAJOR ISSUES\n1. Overclaiming in abstract\n   1. Specifically, the RQ2 claim\n\n"
           "## MINOR ISSUES\n1. Typo\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert "deny" in out
    assert "1 unresolved" in out  # not 2 — the indented sub-item must not be double-counted


# ---------- Bash surface: format-engineer runs build scripts via Bash ----------

sys.path.insert(0, str(HOOKS))
from phase_gate import _invokes_build_script  # noqa: E402


def test_invokes_build_script_detects_bare_relative_execution():
    assert _invokes_build_script("./scripts/latex_build.sh --out build/main.pdf") is True


def test_invokes_build_script_detects_bare_execution_after_chain_operator():
    assert _invokes_build_script("cd /tmp && scripts/docx_build.sh --out exports/x.docx") is True


def test_invokes_build_script_bare_mention_still_not_gated():
    # Must not regress the existing "mention, not invocation" guarantee.
    assert _invokes_build_script("wc -l scripts/latex_build.sh") is False
    assert _invokes_build_script("cat scripts/xlsx_export.py") is False


def test_bash_direct_execution_of_build_script_blocked_without_gates(tmp_path):
    out = _run_hook({"tool_name": "Bash", "tool_input": {"command": "./scripts/latex_build.sh main.tex build"}},
                    tmp_path)
    assert "deny" in out


def test_bash_direct_execution_of_build_script_allowed_when_gates_satisfied(tmp_path):
    _write(tmp_path, "verify-status.json", VERIFY_PASS)
    _write(tmp_path, "reviews/round-1.md", "## SUMMARY\nMajor issues:    0\n")
    out = _run_hook({"tool_name": "Bash", "tool_input": {"command": "./scripts/latex_build.sh main.tex build"}},
                    tmp_path)
    assert out.strip() == ""


def test_invokes_build_script_detects_source_keyword():
    assert _invokes_build_script("source scripts/latex_build.sh") is True


def test_invokes_build_script_detects_dot_sourcing():
    assert _invokes_build_script(". scripts/latex_build.sh") is True


def test_invokes_build_script_dot_alone_is_not_a_build_invocation():
    # A bare "." with no following build-script token must not false-positive.
    assert _invokes_build_script(". some_other_file.sh") is False


def test_bash_latex_build_blocked_without_gates(tmp_path):
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "bash scripts/latex_build.sh main.tex build"}}, tmp_path)
    assert "deny" in out


def test_bash_latex_build_allowed_when_gates_satisfied(tmp_path):
    _write(tmp_path, "verify-status.json", VERIFY_PASS)
    _write(tmp_path, "reviews/round-1.md", "## SUMMARY\nMajor issues:    0\n")
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "bash scripts/latex_build.sh main.tex build"}}, tmp_path)
    assert out.strip() == ""


def test_bash_unrelated_command_not_gated(tmp_path):
    out = _run_hook({"tool_name": "Bash", "tool_input": {"command": "pytest tests/ -x -q"}}, tmp_path)
    assert out.strip() == ""


def test_bash_merely_mentioning_build_script_name_not_gated(tmp_path):
    # Regression: an early version matched any command containing a build
    # script's filename as a substring — `wc -l scripts/make_reference_docx.py`
    # or `cat scripts/latex_build.sh` must NOT trigger the format gate; only
    # an actual interpreter invocation (`bash scripts/latex_build.sh ...`) should.
    for cmd in ("wc -l scripts/make_reference_docx.py",
                "cat scripts/latex_build.sh",
                "grep -n foo scripts/xlsx_export.py"):
        out = _run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, tmp_path)
        assert out.strip() == "", cmd


def test_bash_multiple_py_file_arguments_not_gated(tmp_path):
    # Regression: a \b-boundary regex treating bare "py"/"sh" as interpreter
    # aliases matches the tail of an unrelated ARGUMENT's own .py/.sh
    # extension (e.g. "...kit.py" ends in "py"), then false-triggers on the
    # NEXT whitespace-separated argument as if it were the invoked script —
    # reproduced live: `wc -l scripts/validate_kit.py scripts/skill_routing_eval.py
    # scripts/extract_skill_descriptions.py scripts/make_reference_docx.py` was
    # incorrectly denied even though nothing here invokes make_reference_docx.py.
    cmd = ("wc -l scripts/validate_kit.py scripts/skill_routing_eval.py "
           "scripts/extract_skill_descriptions.py scripts/make_reference_docx.py")
    out = _run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, tmp_path)
    assert out.strip() == ""


# ---------- Bash bypass of drafts/reviews gates (independent review, 2026-07-04) ----------

def test_bash_write_to_drafts_blocked_when_no_outline(tmp_path):
    # Regression: gate_reason_for_bash used to only recognize "build"/"exports"
    # path components, so `echo ... > drafts/intro.md` bypassed the
    # outline-approval gate entirely even though the identical Write call to
    # the same path was correctly blocked.
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "echo 'text [@fake2024]' > drafts/intro.md"}}, tmp_path)
    assert "deny" in out
    assert "outline" in out.lower()


def test_bash_write_to_drafts_allowed_when_outline_approved(tmp_path):
    _write(tmp_path, "outline/outline.md", "**Status:** approved\n")
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "echo 'text' > drafts/intro.md"}}, tmp_path)
    assert out.strip() == ""


def test_bash_write_to_drafts_via_cp_blocked_when_no_outline(tmp_path):
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "cp scratch/intro.md drafts/intro.md"}}, tmp_path)
    assert "deny" in out
    assert "outline" in out.lower()


def test_bash_write_to_reviews_blocked_when_no_verify_status(tmp_path):
    # Regression: `cat <<'EOF' > reviews/round-1.md` used to bypass the
    # verify=PASS gate the same way the drafts case bypassed outline-approval.
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "echo '## SUMMARY' > reviews/round-1.md"}}, tmp_path)
    assert "deny" in out
    assert "verify-citations" in out.lower()


def test_bash_write_to_reviews_allowed_when_verify_pass(tmp_path):
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "echo '## SUMMARY' > reviews/round-1.md"}}, tmp_path)
    assert out.strip() == ""


def test_bash_write_to_drafts_status_md_still_exempt(tmp_path):
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "echo 'TODO' > drafts/STATUS.md"}}, tmp_path)
    assert out.strip() == ""


# ---------- path traversal (2nd independent review, D-063) ----------

def test_path_traversal_via_drafts_dotdot_reviews_still_gated_as_reviews(tmp_path):
    # Regression: PurePosixPath(...).parts does NOT collapse ".." — a literal
    # "drafts/../reviews/round-1.md" contains "drafts" as a component, so an
    # un-normalized check misroutes it to the (permissive, outline-approved)
    # drafts gate instead of the reviews gate, bypassing verify-PASS entirely.
    _write(tmp_path, "outline/outline.md", "**Status:** approved\n")
    _write(tmp_path, "verify-status.json", json.dumps({"result": "FAIL"}))
    path = str(tmp_path / "drafts" / ".." / "reviews" / "round-1.md")
    out = _run_hook({"tool_name": "Write", "tool_input": {"file_path": path}}, tmp_path)
    assert "deny" in out
    assert "verify-citations" in out.lower()


def test_nested_lookalike_directory_not_gated_as_project_drafts(tmp_path):
    # Regression: a bare "drafts" in parts membership test (the prior
    # gate_reason_for_path) matches "drafts" as a path component ANYWHERE,
    # not just at the project root — so notes/drafts/x.md (a scratch
    # subdirectory that is NOT this project's actual drafts/ state file
    # location) got gated by the outline-approval check it has no business
    # being subject to. No outline exists here at all; the un-anchored check
    # would deny this write, but the anchored check must allow it since the
    # write target's top-level directory is "notes", not "drafts".
    path = str(tmp_path / "notes" / "drafts" / "x.md")
    out = _run_hook({"tool_name": "Write", "tool_input": {"file_path": path}}, tmp_path)
    assert "deny" not in out

    # The real top-level drafts/ directory must still be gated identically.
    real_path = str(tmp_path / "drafts" / "x.md")
    out2 = _run_hook({"tool_name": "Write", "tool_input": {"file_path": real_path}}, tmp_path)
    assert "deny" in out2


# ---------- interpreter-token variants (2nd independent review, D-063) ----------
# These originally asserted that xlsx_export.py / make_reference_docx.py were
# DENIED via each interpreter-token spelling. Post-C1 those two scripts are no
# longer build-gated (they run pre-verification), so the same commands must now
# be ALLOWED — which still exercises the versioned/absolute/py.exe interpreter
# parser, just asserting the corrected outcome. Manuscript-builder gating via
# interpreter tokens is covered by the build/exports integration tests above
# and test_invokes_build_script_* below.

def test_xlsx_export_not_gated_via_versioned_python(tmp_path):
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "python3.11 scripts/xlsx_export.py --out exports/x.xlsx"}}, tmp_path)
    assert out.strip() == ""


def test_xlsx_export_not_gated_via_absolute_interpreter_path(tmp_path):
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "/usr/bin/python3 scripts/xlsx_export.py --out exports/x.xlsx"}}, tmp_path)
    assert out.strip() == ""


def test_make_reference_docx_not_gated_via_py_launcher(tmp_path):
    out = _run_hook({"tool_name": "Bash",
                      "tool_input": {"command": "py.exe scripts/make_reference_docx.py"}}, tmp_path)
    assert out.strip() == ""


def test_export_excel_xlsx_write_allowed_pre_verification(tmp_path):
    # C1 regression at the path-gate surface: a direct Write of the literature
    # matrix to exports/*.xlsx must not be blocked before verification exists.
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "exports" / "matrix.xlsx")}}, tmp_path)
    assert out.strip() == ""


def test_bash_bare_py_still_not_confused_with_py_file_argument(tmp_path):
    # The old \b-boundary bug is gone, but re-adding "py" as a recognized
    # interpreter must not reintroduce it: a command with several .py FILE
    # arguments and no real interpreter token must still pass clean.
    cmd = "wc -l scripts/validate_kit.py scripts/make_reference_docx.py"
    out = _run_hook({"tool_name": "Bash", "tool_input": {"command": cmd}}, tmp_path)
    assert out.strip() == ""


# ---------- malformed / unparseable review files (2nd independent review, D-063) ----------

def test_format_gate_blocked_when_only_review_file_has_no_round_number(tmp_path):
    # "round-abc.md" matches the glob "round-*.md" but has no numeric round —
    # it must not be treated as a valid "latest round" with 0 Major issues.
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    _write(tmp_path, "reviews/round-abc.md", "## SUMMARY\nMajor issues:    0\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert "deny" in out
    assert "critique" in out.lower()


def test_format_gate_blocked_when_major_count_unparseable(tmp_path):
    # A validly-numbered round file that has neither "Major issues: N" nor a
    # "## MAJOR ISSUES" section must block as "unknown", never silently pass
    # as if it were zero.
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    _write(tmp_path, "reviews/round-1.md", "Just some free-form notes, no structured summary.\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert "deny" in out
    assert "could not determine" in out.lower()


# ---------- unreadable/undecodable state files never crash the hook (D-063) ----------

def test_hook_does_not_crash_on_undecodable_review_file(tmp_path):
    # Calls the hook directly rather than via _run_hook, so it declares the kit
    # project itself.
    (tmp_path / "PROJECT.md").touch()
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    p = tmp_path / "reviews" / "round-1.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xfe\x00\x01not valid utf-8")
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "phase_gate.py")],
        input=json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}),
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert proc.stderr == ""
    # Undecodable review content is treated the same as "couldn't determine" —
    # denied with a clear reason, never a raw traceback.
    assert "deny" in proc.stdout


# ---------- uncorroborated PASS: visible at the format gate, never blocking ----------
# verify_passed() can only ask whether verify-status.json is self-consistent,
# which a hand-authored file satisfies trivially. scripts/write_verify_status.py
# is what actually re-checks the bib and drafts on disk, and it records the
# outcome in `live_recheck`. These pin that the gate says so when that record is
# missing or incomplete — and that saying so never turns into a fourth block.

def _allowed_build(out: str) -> bool:
    return "permissionDecision" not in out


def test_build_allowed_but_noted_when_verify_status_was_hand_authored(tmp_path):
    # No live_recheck block at all: the file did not come from the sanctioned
    # writer, so nothing independently corroborated the PASS the final artifact
    # is about to rest on.
    _write(tmp_path, "verify-status.json", json.dumps(
        {"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    _write(tmp_path, "reviews/round-1.md", "## SUMMARY\nMajor issues:    0\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert _allowed_build(out), "the note must not become a fourth blocking gate"
    assert "live_recheck" in out and "write_verify_status.py" in out


def test_build_allowed_but_noted_when_the_live_recheck_was_incomplete(tmp_path):
    # The offline/wrong-path case: write_verify_status.py wrote the PASS but
    # could not corroborate it, and warned once — hundreds of turns ago.
    _write(tmp_path, "verify-status.json", json.dumps({
        "result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0,
        "missing": 0, "unresolved": 0,
        "live_recheck": {"doi2bib_confirmed": False, "cite_audit_confirmed": True}}))
    _write(tmp_path, "reviews/round-1.md", "## SUMMARY\nMajor issues:    0\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert _allowed_build(out)
    assert "not independently corroborated" in out.lower()


def test_no_note_when_the_pass_was_corroborated(tmp_path):
    # The whole value of the note is that it is rare. A notice that also fired
    # on every properly-verified build would be trained away in a week.
    _write(tmp_path, "verify-status.json", VERIFY_PASS)
    _write(tmp_path, "reviews/round-1.md", "## SUMMARY\nMajor issues:    0\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert out.strip() == ""


def test_no_note_outside_the_format_gate(tmp_path):
    # A drafts write with an approved outline never consults verify-status.json,
    # so it must stay silent even when that file is hand-authored.
    _write(tmp_path, "outline/outline.md", "**Status:** approved\n")
    _write(tmp_path, "verify-status.json", json.dumps(
        {"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}}, tmp_path)
    assert out.strip() == ""


def test_no_note_when_the_format_gate_is_denying(tmp_path):
    # A deny already tells the author to re-run /verify-citations; adding the
    # note there would be two messages about the same file in one response.
    _write(tmp_path, "verify-status.json", json.dumps(
        {"result": "PASS", "checked": 1, "fabricated": 0, "retracted": 0, "missing": 0, "unresolved": 0}))
    _write(tmp_path, "reviews/round-1.md", "## SUMMARY\nMajor issues:    2\n")
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}}, tmp_path)
    assert "deny" in out
    assert "live_recheck" not in out


# ---------- fail-open ----------

def test_hook_fails_open_on_garbage_stdin(tmp_path):
    # Fail-OPEN is the contract and is unchanged: exit 0, no permissionDecision,
    # the call proceeds. What changed is that it is no longer SILENT — a
    # degradation notice that the gate did not run is emitted, because exit-0
    # with no output is byte-identical to "checked, nothing to gate" and made a
    # broken gate indistinguishable from a passing one.
    proc = subprocess.run([sys.executable, str(HOOKS / "phase_gate.py")],
                          input="not json", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert "permissionDecision" not in proc.stdout, "a degraded gate must not deny"
    assert payload["systemMessage"].startswith("⚠ Scholar-Kit gate degraded")
    assert "phase_gate" in payload["systemMessage"]
    assert "ALLOWED" in payload["systemMessage"]


def test_hook_is_silent_on_empty_stdin(tmp_path):
    # The asymmetry is deliberate. A harness probing the hook with no payload
    # is not a broken gate, and warning on every such call would train the
    # author to ignore the warning that matters.
    proc = subprocess.run([sys.executable, str(HOOKS / "phase_gate.py")],
                          input="", cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
    assert proc.stderr.strip() == ""


def test_degradation_notice_carries_no_payload_content(tmp_path):
    # A hook sees draft prose, paths and shell commands. The notice reports the
    # exception TYPE and origin only — never str(exc) — so manuscript content
    # cannot ride out into a session-visible warning and the transcript.
    secret = "PATIENT-COHORT-ENROLMENT-1998"
    proc = subprocess.run([sys.executable, str(HOOKS / "phase_gate.py")],
                          input="{not json " + secret, cwd=tmp_path,
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0
    assert secret not in proc.stdout
    assert secret not in proc.stderr


def test_unrelated_write_not_gated(tmp_path):
    out = _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "PROJECT.md")}}, tmp_path)
    assert out.strip() == ""


# ---------- NotebookEdit surface: build/exports aren't restricted to *.md ----------

def test_phase_gate_blocks_notebook_edit_into_build_dir(tmp_path):
    out = _run_hook({"tool_name": "NotebookEdit",
                      "tool_input": {"notebook_path": str(tmp_path / "build" / "analysis.ipynb")}}, tmp_path)
    assert "deny" in out


def test_phase_gate_allows_notebook_edit_outside_gated_dirs(tmp_path):
    out = _run_hook({"tool_name": "NotebookEdit",
                      "tool_input": {"notebook_path": str(tmp_path / "analysis" / "explore.ipynb")}}, tmp_path)
    assert out.strip() == ""


# ---------- Major-count fallback: measured miscounts, both directions ----------
# Nine consecutive review rounds of one manuscript were replayed through the
# pre-2026-08-23 fallback (`^\d+\.` only). It was wrong on eight of them.
# These four tests pin the two failure directions and the two safe outcomes.

def _pass_status():
    return json.dumps({"result": "PASS", "checked": 1, "fabricated": 0,
                       "retracted": 0, "missing": 0, "unresolved": 0})


def _build_attempt(tmp_path):
    return _run_hook({"tool_name": "Write",
                      "tool_input": {"file_path": str(tmp_path / "build" / "main.pdf")}},
                     tmp_path)


def test_format_gate_counts_bold_numbered_major_items(tmp_path):
    # THE DANGEROUS DIRECTION. A reviewer that bolds its item numbers
    # ("**1. ...") writes lines that do not start with a digit, so a
    # digit-anchored count returned 0 and the gate OPENED over real blockers.
    # Measured on four separate rounds carrying 2-4 real Major issues each.
    _write(tmp_path, "verify-status.json", _pass_status())
    _write(tmp_path, "reviews/round-1.md",
           "## MAJOR ISSUES\n\n"
           "**1. The registration count sums a field's fullness, not its value.**\n\n"
           "Some explanatory prose that runs on for a while.\n\n"
           "**2. The funding count repeats the same error one paragraph later.**\n\n"
           "More prose.\n\n## MINOR ISSUES\n1. Typo\n")
    out = _build_attempt(tmp_path)
    assert "deny" in out
    assert "2 unresolved" in out


def test_format_gate_counts_heading_numbered_major_items(tmp_path):
    # Same failure, different reviewer habit: "### 1. Title" headings.
    _write(tmp_path, "verify-status.json", _pass_status())
    _write(tmp_path, "reviews/round-1.md",
           "## MAJOR ISSUES\n\n"
           "### 1. Fourth pool is not reported by the run that produced it\n\n"
           "Prose.\n\n## MINOR ISSUES\n1. Typo\n")
    out = _build_attempt(tmp_path)
    assert "deny" in out
    assert "1 unresolved" in out


def test_format_gate_blocks_when_major_section_has_prose_but_no_items(tmp_path):
    # Substantial prose under the heading that yields no parseable item is
    # UNKNOWN, not zero. Guessing zero here is the same silent pass the
    # digit-anchored count used to produce.
    _write(tmp_path, "verify-status.json", _pass_status())
    _write(tmp_path, "reviews/round-1.md",
           "## MAJOR ISSUES\n\n"
           "There are serious problems throughout the results section, described\n"
           "at length below without any numbering whatsoever, because this\n"
           "reviewer writes in continuous prose rather than in a list.\n\n"
           "## MINOR ISSUES\n1. Typo\n")
    out = _build_attempt(tmp_path)
    assert "deny" in out
    assert "could not determine" in out.lower()


def test_format_gate_treats_bare_none_major_section_as_zero(tmp_path):
    # The one short-section case that IS zero: the agent contract says write
    # "None." under an empty section rather than omitting the heading.
    _write(tmp_path, "verify-status.json", _pass_status())
    _write(tmp_path, "reviews/round-1.md",
           "## MAJOR ISSUES\n\nNone.\n\n## MINOR ISSUES\n1. Typo\n")
    out = _build_attempt(tmp_path)
    assert "deny" not in out


def test_format_gate_explicit_count_line_beats_a_narrated_no_findings_list(tmp_path):
    # A zero-Major review that JUSTIFIES its verdict by numbering what it
    # looked for and did not find. The fallback counts those eight negative
    # findings as eight findings; the explicit line is what stops it. This is
    # why critique/SKILL.md requires the line rather than relying on counting.
    section = "\n".join("%d. Checked this and found nothing." % i for i in range(1, 9))
    _write(tmp_path, "verify-status.json", _pass_status())
    _write(tmp_path, "reviews/round-1.md",
           "## MAJOR ISSUES\n\nMajor issues: 0\n\nNone.\n\n"
           "I reached that verdict by checking the following:\n\n"
           + section + "\n\n## MINOR ISSUES\n1. Typo\n")
    out = _build_attempt(tmp_path)
    assert "deny" not in out


def test_format_gate_overcounts_a_column_zero_fix_list_and_that_is_accepted(tmp_path):
    # KNOWN, DELIBERATE over-count. A single Major issue whose "what would fix
    # it" list is numbered at column 0 is indistinguishable BY SHAPE from five
    # more issues: nothing in the markup says "problem" vs "remedy". Measured on
    # a real review that carried 1 Major and counts as 6.
    #
    # Left uncorrected on purpose. Over-counting blocks a clean build, which is
    # visible and recoverable; under-counting opens the gate over real blockers,
    # which is silent. This test exists to record that the trade was chosen, so
    # a later reader does not "fix" it into the dangerous direction.
    #
    # The real fix is not a better pattern — no pattern can separate a problem
    # from its remedy — it is the explicit "Major issues: N" line that
    # critique/SKILL.md now requires.
    _write(tmp_path, "verify-status.json", _pass_status())
    _write(tmp_path, "reviews/round-1.md",
           "## MAJOR ISSUES\n\n"
           "**1. The audit that closed the class does not cover the class.**\n\n"
           "Long diagnosis prose.\n\n"
           "**What would fix it:**\n\n"
           "1. Replace the count at synthesis.md:326.\n"
           "2. Rewrite discussion.md:469.\n"
           "3. Make the audit walk the schema.\n"
           "4. Add the real vocabulary to the pattern.\n"
           "5. Correct the docstring's claim.\n\n"
           "## MINOR ISSUES\n1. Typo\n")
    out = _build_attempt(tmp_path)
    assert "deny" in out
    assert "6 unresolved" in out  # 1 real; the over-count is the safe direction
