"""Regression tests for the third 2026-07-04 pass (D-071 in DECISIONS.md):
closing the remaining gaps flagged but not yet fixed in the second pass —
docx_build.sh's LOCALAPPDATA crash (same bug class as D-068a, unfixed here),
the docx_style_check.py auto-wiring, verify-status.json becoming genuinely
script-owned (closing the hand-fabrication gap for real instead of just
raising the bar at read time), word_budget.py's unclosed-code-fence
robustness, and the deduplicated skill/agent frontmatter parser.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import kit_project_cwd

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
HOOKS = ROOT / ".claude" / "hooks"

sys.path.insert(0, str(SCRIPTS))
import word_budget  # noqa: E402
import write_verify_status  # noqa: E402


def _bash_runs(bash: str) -> bool:
    """Whether that bash can execute anything — a partial Git for Windows
    install leaves `bin\\bash.exe` on disk with an empty `usr\\bin\\` behind it,
    and an existence check calls that a working shell."""
    try:
        return subprocess.run([bash, "-c", "exit 0"],
                              capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _find_git_bash() -> str:
    for cand in (r"C:\Program Files\Git\bin\bash.exe",
                 r"C:\Program Files\Git\usr\bin\bash.exe",
                 shutil.which("bash")):
        if cand and Path(cand).exists() and _bash_runs(cand):
            return cand
    pytest.skip("no working bash executable available")


# ---------- docx_build.sh: LOCALAPPDATA unbound-variable crash ----------

def test_docx_build_blocked_message_not_unbound_variable_crash(tmp_path):
    bash = _find_git_bash()
    md = tmp_path / "section.md"
    md.write_text("# Heading\n\nSome text.\n", encoding="utf-8")

    env = dict(os.environ)
    env.pop("LOCALAPPDATA", None)
    env["PATH"] = os.pathsep.join(
        p for p in env.get("PATH", "").split(os.pathsep) if "pandoc" not in p.lower())

    proc = subprocess.run(
        [bash, "scripts/docx_build.sh", str(tmp_path / "out.docx"),
         "templates/csl/apa.csl", "-", str(md)],
        cwd=ROOT, capture_output=True, text=True, env=env)

    assert "unbound variable" not in proc.stderr, proc.stderr
    assert proc.returncode == 3, (proc.returncode, proc.stdout, proc.stderr)
    assert "BLOCKED" in proc.stdout


# ---------- docx_build.sh: auto style-check wiring doesn't break normal builds ----------

def test_docx_build_succeeds_and_runs_style_check_without_crashing(tmp_path):
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc not installed")
    bash = _find_git_bash()

    ref = tmp_path / "ref.docx"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "make_reference_docx.py"), "--out", "ref.docx"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    assert ref.exists()

    md = tmp_path / "section.md"
    md.write_text("# Heading\n\nSome text in the section.\n", encoding="utf-8")
    # docx_build.sh hardcodes "bib/references.bib" as a project-cwd-relative
    # path (pandoc treats a missing --bibliography file as a hard failure,
    # not the soft warning the script's own log-grep assumes) — cwd must be
    # tmp_path (the fictional "project") for that to resolve, so the script
    # itself and the CSL file are passed as absolute paths instead.
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("", encoding="utf-8")

    out = tmp_path / "out.docx"
    # .as_posix() throughout: docx_build.sh's new `$(dirname "$0")` needs a
    # "/"-containing path to resolve correctly in Git Bash — a raw Windows
    # backslash path passed as $0 has no "/" for dirname to split on.
    proc = subprocess.run(
        [bash, (SCRIPTS / "docx_build.sh").as_posix(), out.as_posix(),
         (ROOT / "templates" / "csl" / "apa.csl").as_posix(), ref.as_posix(), md.as_posix()],
        cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "OK:" in proc.stdout
    assert out.exists()
    # Whether or not it happens to flag a mismatch, it must not crash the
    # build or corrupt the "OK:" success signal.
    assert "Traceback" not in proc.stdout and "Traceback" not in proc.stderr


# ---------- phase_gate.py / protect_data_files.py: verify-status.json now script-owned ----------

def test_verify_status_write_via_script_succeeds(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "write_verify_status.py"),
         "--result", "PASS", "--checked", "5", "--fabricated", "0",
         "--retracted", "0", "--missing", "0", "--unresolved", "0"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    data = json.loads((tmp_path / "verify-status.json").read_text(encoding="utf-8"))
    assert data["result"] == "PASS"
    assert data["checked"] == 5


def test_verify_status_write_rejects_internally_inconsistent_pass(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "write_verify_status.py"),
         "--result", "PASS", "--checked", "5", "--fabricated", "1",
         "--retracted", "0", "--missing", "0", "--unresolved", "0"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "fabricated" in proc.stderr.lower()
    assert not (tmp_path / "verify-status.json").exists()


def test_protect_data_files_blocks_direct_write_of_verify_status(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "protect_data_files.py")],
        input=json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": str(tmp_path / "verify-status.json")}}),
        cwd=kit_project_cwd(), capture_output=True, text=True, encoding="utf-8")
    assert "deny" in proc.stdout


def test_protect_data_files_blocks_bash_redirect_into_verify_status():
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "protect_data_files.py")],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": "echo '{\"result\":\"PASS\"}' > verify-status.json"}}),
        cwd=kit_project_cwd(), capture_output=True, text=True, encoding="utf-8")
    assert "deny" in proc.stdout


def test_protect_data_files_allows_sanctioned_script_for_verify_status():
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "protect_data_files.py")],
        input=json.dumps({"tool_name": "Bash",
                          "tool_input": {"command": "python scripts/write_verify_status.py --result PASS"}}),
        cwd=kit_project_cwd(), capture_output=True, text=True, encoding="utf-8")
    assert proc.stdout.strip() == ""


# ---------- write_verify_status.py: live recheck can't be fooled by a consistent-looking lie ----------

def _args(**overrides):
    base = dict(result="PASS", checked=5, fabricated=0, retracted=0, missing=0,
               unresolved=0, fixable=0, bib="bib/references.bib", drafts="drafts")
    base.update(overrides)
    return type("Args", (), base)()


def test_live_recheck_skipped_gracefully_when_bib_and_drafts_absent(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    def fail_if_called(*a, **k):
        raise AssertionError("subprocess.run must not be called when bib/drafts don't exist")

    monkeypatch.setattr(write_verify_status.subprocess, "run", fail_if_called)
    status = write_verify_status.build_status(_args())
    assert status["result"] == "PASS"


def test_live_recheck_blocks_pass_when_doi2bib_finds_fabrication(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@article{a2020x, title={x}}", encoding="utf-8")

    class FakeProc:
        stdout = json.dumps({"result": "FAIL", "fabricated": 1, "unresolved": 0})

    monkeypatch.setattr(write_verify_status.subprocess, "run", lambda *a, **k: FakeProc())
    with pytest.raises(SystemExit):
        write_verify_status.build_status(_args())


def test_live_recheck_does_not_block_on_unresolved_only(monkeypatch, tmp_path):
    # Regression-guard: entries with no DOI at all (legitimate non-DOI
    # sources — books, personal communications, TR Dizin papers not in
    # Crossref) must not block a PASS just because doi2bib.py --verify's own
    # "unresolved" count is nonzero — only real fabrication (fabricated > 0)
    # is unambiguous enough to hard-block on.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@book{b2020y, title={y}}", encoding="utf-8")

    class FakeProc:
        stdout = json.dumps({"result": "FAIL", "fabricated": 0, "unresolved": 1})

    monkeypatch.setattr(write_verify_status.subprocess, "run", lambda *a, **k: FakeProc())
    status = write_verify_status.build_status(_args())
    assert status["result"] == "PASS"


def test_live_recheck_blocks_pass_when_cite_audit_finds_missing_citation(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "intro.md").write_text("Some claim [@ghost2099].\n", encoding="utf-8")

    def fake_run(cmd, **k):
        class FakeProc:
            pass
        proc = FakeProc()
        if "doi2bib.py" in cmd[1]:
            proc.stdout = json.dumps({"result": "PASS", "fabricated": 0, "unresolved": 0})
        else:
            proc.stdout = json.dumps({"missing": ["ghost2099"], "placeholders": []})
        return proc

    monkeypatch.setattr(write_verify_status.subprocess, "run", fake_run)
    with pytest.raises(SystemExit):
        write_verify_status.build_status(_args())


def test_live_recheck_allows_pass_when_everything_checks_out(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@article{a2020x, title={x}}", encoding="utf-8")
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "intro.md").write_text("Some claim [@a2020x].\n", encoding="utf-8")

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
    status = write_verify_status.build_status(_args())
    assert status["result"] == "PASS"


def test_live_recheck_degrades_gracefully_when_subprocess_fails(monkeypatch, tmp_path):
    # Network down / requests not installed / any subprocess failure must be
    # treated as "can't confirm," not as a hard block — otherwise the gate
    # becomes hard-dependent on network availability for every single write.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bib").mkdir()
    (tmp_path / "bib" / "references.bib").write_text("@article{a2020x, title={x}}", encoding="utf-8")

    def raise_oserror(*a, **k):
        raise OSError("network unreachable")

    monkeypatch.setattr(write_verify_status.subprocess, "run", raise_oserror)
    status = write_verify_status.build_status(_args())
    assert status["result"] == "PASS"


# ---------- word_budget.py: unclosed code-fence robustness ----------

def test_count_words_handles_unclosed_code_fence():
    text = "Real prose here.\n```\nfenced code never closes\nmore code\n"
    # Before the fix: an odd number of ``` markers left everything from the
    # unclosed fence to EOF unstripped and counted as prose words.
    assert word_budget.count_words(text) == len(["Real", "prose", "here"])


def test_count_words_still_strips_balanced_fences():
    text = "Real prose.\n```\ncode block\n```\nMore prose after.\n"
    words = word_budget.count_words(text)
    assert words == len(["Real", "prose", "More", "prose", "after"])


def test_count_words_does_not_charge_for_html_comments():
    # /draft REQUIRES an HTML comment per empirical claim (`<!-- EV-0045 -->`),
    # so a compliant draft is full of them. Counted, they inflate the author's
    # figure against a limit the venue enforces on what it publishes.
    text = ("Real prose here.\n"
            "<!-- EV-0045: bir sürü açıklama sözcüğü, çok satırlı\n"
            "     ve içinde sayılar 22,3 taşıyan bir not -->\n"
            "More prose after.\n")
    assert word_budget.count_words(text) == len(
        ["Real", "prose", "here", "More", "prose", "after"])


def test_count_words_does_not_fuse_words_across_an_inline_comment():
    assert word_budget.count_words("alpha<!-- x -->beta\n") == 2
