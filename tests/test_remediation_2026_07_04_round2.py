"""Regression tests for the second 2026-07-04 review pass (D-070 in
DECISIONS.md): the zero-fabrication chain's own weak spots (doi2bib author
matching, the verify-status.json hand-fabrication bypass, evidence_db's
missing registry cross-check), plus the PRISMA template-injection gap and a
few smaller consistency fixes found while auditing templates/skills/agents.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
HOOKS = ROOT / ".claude" / "hooks"

sys.path.insert(0, str(SCRIPTS))
import doi2bib  # noqa: E402
import evidence_db  # noqa: E402


# ---------- doi2bib.py: author-family matching false positives ----------

def test_local_family_names_parses_multi_author_field():
    assert doi2bib._local_family_names("Kaya, Ahmet and Yilmaz, Berk") == {"kaya", "yilmaz"}


def test_local_family_names_and_joiner_no_longer_false_matches_an():
    # Regression: raw substring `"an" in "kaya, ahmet and yilmaz, berk"` was
    # True purely because of the " and " joiner — a DOI whose real first
    # author family is "An" would have falsely "matched" ANY multi-author
    # entry regardless of who the real authors are.
    families = doi2bib._local_family_names("Kaya, Ahmet and Yilmaz, Berk")
    assert "an" not in families


def test_local_family_names_short_surname_no_longer_false_matches_substring():
    # Regression: fam="ng" matched inside "Zhang" via raw substring search.
    families = doi2bib._local_family_names("Zhang, Wei")
    assert "ng" not in families
    assert families == {"zhang"}


def test_verify_flags_fabricated_when_author_genuinely_mismatches(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "refs.bib"
    bad.write_text("""@article{fake2023x,
  title = {Deep learning for bearing fault diagnosis},
  author = {Zhang, Wei},
  journal = {MSSP},
  year = {2023},
  doi = {10.1016/j.ymssp.2023.00001},
  verified = {true},
}""", encoding="utf-8")
    csl = {"title": "Deep learning for bearing fault diagnosis",
           "author": [{"family": "Ng", "given": "Andrew"}],
           "issued": {"date-parts": [[2023]]}}
    monkeypatch.setattr(doi2bib, "fetch_csl", lambda doi: csl)
    with pytest.raises(SystemExit) as exc:
        doi2bib.cmd_verify(type("A", (), {"bib": str(bad), "entry": None, "json_out": True})())
    assert exc.value.code == 2
    report = json.loads(capsys.readouterr().out)
    # Before the fix: fam="ng" is a substring of the local author "zhang",
    # so this would have wrongly PASSED as if Ng == Zhang.
    assert report["fabricated"] == 1
    assert "first author mismatch" in report["entries"][0]["reason"]


# ---------- phase_gate.py: verify-status.json hand-fabrication bypass ----------

def _run_phase_gate(payload, cwd):
    # phase_gate.py no-ops outside a Scholar-Kit project; these tests exercise
    # the gate, so the fixture declares one. See .claude/hooks/_project_scope.py.
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


def test_hand_written_minimal_pass_no_longer_satisfies_the_gate(tmp_path):
    # Regression: an agent (or a careless orchestrator) writing just
    # {"result": "PASS"} directly — without ever running doi2bib.py --verify —
    # used to fully satisfy the citation gate. "checked" missing/zero is now
    # treated as internally inconsistent with a PASS claim.
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS"}))
    out = _run_phase_gate({"tool_name": "Write",
                           "tool_input": {"file_path": str(tmp_path / "reviews" / "round-1.md")}}, tmp_path)
    assert "deny" in out
    assert "checked" in out.lower()


def test_pass_with_nonzero_fabricated_count_rejected(tmp_path):
    _write(tmp_path, "verify-status.json",
           json.dumps({"result": "PASS", "checked": 5, "fabricated": 1, "retracted": 0,
                      "missing": 0, "unresolved": 0}))
    out = _run_phase_gate({"tool_name": "Write",
                           "tool_input": {"file_path": str(tmp_path / "reviews" / "round-1.md")}}, tmp_path)
    assert "deny" in out
    assert "fabricated" in out.lower()


def test_internally_consistent_pass_still_satisfies_the_gate(tmp_path):
    _write(tmp_path, "verify-status.json",
           json.dumps({"result": "PASS", "checked": 5, "fabricated": 0, "retracted": 0,
                      "missing": 0, "unresolved": 0}))
    out = _run_phase_gate({"tool_name": "Write",
                           "tool_input": {"file_path": str(tmp_path / "reviews" / "round-1.md")}}, tmp_path)
    assert out.strip() == ""


def test_stale_pass_rejected_when_bib_edited_afterward(tmp_path):
    status = _write(tmp_path, "verify-status.json",
                    json.dumps({"result": "PASS", "checked": 5, "fabricated": 0, "retracted": 0,
                               "missing": 0, "unresolved": 0}))
    bib = _write(tmp_path, "bib/references.bib", "@article{a2020x, title={x}}")
    # Force the bib file's mtime strictly after verify-status.json's.
    os.utime(status, (status.stat().st_mtime - 10, status.stat().st_mtime - 10))
    os.utime(bib, None)
    out = _run_phase_gate({"tool_name": "Write",
                           "tool_input": {"file_path": str(tmp_path / "reviews" / "round-1.md")}}, tmp_path)
    assert "deny" in out
    assert "modified after" in out.lower()


# ---------- evidence_db.py: card source must exist in the registry ----------

def test_known_sources_returns_none_when_registry_missing(tmp_path):
    assert evidence_db.known_sources(tmp_path / "sources" / "registry.jsonl") is None


def test_known_sources_collects_bib_keys_and_ids(tmp_path):
    reg = tmp_path / "sources" / "registry.jsonl"
    reg.parent.mkdir(parents=True)
    reg.write_text(
        json.dumps({"id": "SRC-0001", "bib_key": "kaya2023deep", "title": "x"}) + "\n"
        + json.dumps({"id": "SRC-0002", "title": "y"}) + "\n",
        encoding="utf-8")
    known = evidence_db.known_sources(reg)
    assert known == {"kaya2023deep", "SRC-0001", "SRC-0002"}


def test_validate_rejects_source_not_in_registry():
    known = {"kaya2023deep"}
    errs = evidence_db.validate(
        {"source": "fabricated2099ghost", "type": "finding", "claim": "x"}, known)
    assert any("not found in" in e for e in errs)


def test_validate_accepts_source_when_no_registry_check_requested():
    errs = evidence_db.validate({"source": "anything", "type": "finding", "claim": "x"}, None)
    assert errs == []


def test_evidence_db_add_rejects_unknown_source_when_registry_present(tmp_path):
    reg = tmp_path / "sources" / "registry.jsonl"
    reg.parent.mkdir(parents=True)
    reg.write_text(json.dumps({"id": "SRC-0001", "bib_key": "kaya2023deep", "title": "x"}) + "\n",
                   encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "evidence_db.py"), "add", "--json",
         json.dumps({"source": "not-a-real-source", "type": "finding", "claim": "x"})],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "not found in" in proc.stderr


def test_evidence_db_add_accepts_known_source_when_registry_present(tmp_path):
    reg = tmp_path / "sources" / "registry.jsonl"
    reg.parent.mkdir(parents=True)
    reg.write_text(json.dumps({"id": "SRC-0001", "bib_key": "kaya2023deep", "title": "x"}) + "\n",
                   encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "evidence_db.py"), "add", "--json",
         json.dumps({"source": "kaya2023deep", "type": "finding", "claim": "x"})],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr


# ---------- prisma_flow.py: mermaid/TikZ label escaping ----------

def test_tex_escape_neutralizes_latex_special_chars():
    import prisma_flow
    assert prisma_flow._tex_escape("cost > 30%") == r"cost > 30\%"
    assert prisma_flow._tex_escape("no_full_text") == r"no\_full\_text"


def test_mermaid_escape_neutralizes_quotes_and_angle_brackets():
    import prisma_flow
    out = prisma_flow._mermaid_escape('reason "with quotes" <script>')
    assert '"' not in out.replace("&quot;", "")
    assert "<script>" not in out


def test_prisma_flow_survives_special_chars_in_excluded_reason(tmp_path):
    # The subject here is ESCAPING, not stage attribution. The reason goes in
    # the full-text dict because that is the one the diagram's exclusion box
    # renders — it no longer borrows the all-stage dict, whose stage it cannot
    # know (see tests/test_prisma_flow.py).
    counts = {"identified": 10, "duplicates": 2, "screened": 8, "excluded_screening": 3,
              "fulltext": 5, "excluded_fulltext": 1, "included": 4,
              "excluded_reasons": {"cost > 30%": 1},
              "excluded_reasons_fulltext": {"cost > 30%": 1}}
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "prisma_flow.py"), "--counts", json.dumps(counts),
         "--out-dir", str(tmp_path / "outline")],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    tex = (tmp_path / "outline" / "prisma.tex").read_text(encoding="utf-8")
    assert r"cost > 30\%" in tex
    assert "cost > 30%" not in tex  # never appears unescaped


# ---------- word_budget.py: RQ-trace word-boundary fix ----------

def test_rq_trace_does_not_confuse_rq1_with_rq10(tmp_path):
    project = tmp_path / "PROJECT.md"
    project.write_text("**Type:** imrad\n- RQ1: does X affect Y?\n", encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "introduction.md").write_text("This section only discusses RQ10 in depth.\n",
                                            encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "word_budget.py"), "--rq-trace",
         "--project", str(project), "--drafts", str(drafts),
         "--outline", str(tmp_path / "outline" / "outline.md")],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    report = json.loads(proc.stdout)
    assert report["untraced"] == ["RQ1"]


def test_rq_trace_still_matches_exact_rq(tmp_path):
    project = tmp_path / "PROJECT.md"
    project.write_text("**Type:** imrad\n- RQ1: does X affect Y?\n", encoding="utf-8")
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    (drafts / "introduction.md").write_text("This directly answers RQ1 in the intro.\n",
                                            encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "word_budget.py"), "--rq-trace",
         "--project", str(project), "--drafts", str(drafts),
         "--outline", str(tmp_path / "outline" / "outline.md")],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    report = json.loads(proc.stdout)
    assert report["untraced"] == []


# ---------- word_budget.py / prisma_flow.py: path traversal ----------

def test_word_budget_rejects_project_path_outside_cwd(tmp_path):
    outside = tmp_path.parent / "outside_PROJECT.md"
    outside.write_text("**Type:** imrad\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "word_budget.py"), "--project", str(outside)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "--project" in proc.stderr
    outside.unlink()


def test_prisma_flow_rejects_registry_path_outside_cwd(tmp_path):
    outside = tmp_path.parent / "outside_registry.jsonl"
    outside.write_text(json.dumps({"status": "included"}) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "prisma_flow.py"), "--registry", str(outside),
         "--out-dir", str(tmp_path / "outline")],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "--registry" in proc.stderr
    outside.unlink()


# ---------- latex_build.sh: empty-bibliography surfacing ----------

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


def test_latex_build_warns_on_empty_bibliography(tmp_path):
    if not shutil.which("latexmk"):
        pytest.skip("latexmk not installed on this machine")
    bash = _find_git_bash() if sys.platform == "win32" else "bash"
    main_tex = tmp_path / "main.tex"
    main_tex.write_text(r"""\documentclass{article}
\usepackage[backend=biber]{biblatex}
\addbibresource{refs.bib}
\begin{document}
Hello world.
\printbibliography
\end{document}
""", encoding="utf-8")
    proc = subprocess.run(
        [bash, "scripts/latex_build.sh", str(main_tex), str(tmp_path / "build")],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "WARN" in proc.stdout and "EMPTY" in proc.stdout.upper()
