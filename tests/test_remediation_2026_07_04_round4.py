"""Regression tests for the 2026-07-04 independent re-review (6 fresh agents,
no access to DECISIONS.md/CHANGELOG.md, each scoped to a different slice:
anti-fabrication hooks, scripts/ security, LaTeX/DOCX build pipeline, test
quality, skill/agent CLI-contract consistency, docs/hygiene). Two of the two
highest-severity claims were independently re-verified live before fixing —
see DECISIONS.md for the corresponding D-0xx entry. Covers:
  - latex_build.sh: the D-070f "Windows absolute OUTDIR" fix never actually
    worked (the bracket expression [A-Za-z]:[/\\]* does not reliably match a
    literal backslash in this shell's case-pattern matching — reproduced
    directly before fixing).
  - xlsx_export.py: header rows in sheet_matrix/sheet_slr bypassed the
    formula-injection escaping every data row already goes through.
  - pdf2md.py: --pdf (unlike --pdf-dir/--out-dir) had no require_within_cwd.
  - write_verify_status.py: a wrong/missing --bib/--drafts path silently
    neutered the live anti-fabrication recheck with zero trace in the
    written file — now recorded via a "live_recheck" field + stderr WARN.
  - _shell_write_sink.py: simple (non-adversarial) variable indirection
    (`p='a'+'b'; open(p,...)` / `p=os.path.join('a','b'); open(p,...)`)
    bypassed the Bash write-sink detection entirely.
  - make_reference_docx.py / docx_style_check.py: Pandoc's docx writer
    references a table style literally named "Table" — never defined, so
    every generated table got no institutional styling; docx-output/SKILL.md
    also documented the wrong style names ("Table Grid", "Block Quote").
"""
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from conftest import kit_project_cwd

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
HOOKS = ROOT / ".claude" / "hooks"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HOOKS))
import write_verify_status  # noqa: E402
from _shell_write_sink import write_targets  # noqa: E402


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


# ---------- latex_build.sh: Windows absolute OUTDIR must not be mangled ----------

def _make_fake_latexmk(bin_dir: Path):
    """A stand-in latexmk that proves which -outdir it was invoked with by
    touching a pdf/log there, without needing a real LaTeX install — lets
    this test run in CI environments without MiKTeX/TeX Live."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    fake = bin_dir / "latexmk"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "outdir=\"\"\n"
        "for arg in \"$@\"; do\n"
        "  case \"$arg\" in\n"
        "    -outdir=*) outdir=\"${arg#-outdir=}\" ;;\n"
        "  esac\n"
        "done\n"
        "mkdir -p \"$outdir\"\n"
        "touch \"$outdir/main.pdf\" \"$outdir/main.log\"\n"
        "exit 0\n",
        encoding="utf-8", newline="\n")
    fake.chmod(0o755)


def _run_latex_build(tmp_path, outdir_arg, env_extra=None):
    bash = _find_git_bash()
    fakebin = tmp_path / "fakebin"
    _make_fake_latexmk(fakebin)
    main_tex = tmp_path / "main.tex"
    main_tex.write_text(r"\documentclass{article}\begin{document}x\end{document}",
                        encoding="utf-8")
    env = dict(os.environ)
    env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
    if env_extra:
        env.update(env_extra)
    # cwd=tmp_path (not ROOT): OUTDIR's relative branch resolves against the
    # caller's original cwd, and the script/main.tex paths are already
    # absolute — running from tmp_path keeps every test hermetic and avoids
    # ever writing scratch output into the real repo root.
    return subprocess.run(
        [bash, str(SCRIPTS / "latex_build.sh"), str(main_tex), outdir_arg],
        cwd=tmp_path, capture_output=True, text=True, env=env)


@pytest.mark.skipif(
    os.name != "nt",
    reason="a native backslash-separator absolute path (C:\\Users\\...) is a Windows-only "
           "filesystem concept: on a real Windows host, tmp_path is already a WindowsPath "
           "so this derivation naturally produces a genuine drive-absolute string. On POSIX, "
           "tmp_path starts with '/' and has no drive letter, so replacing '/' with '\\' "
           "yields a bare-backslash string ('\\tmp\\...') that isn't drive-absolute at all — "
           "correctly falls through to the relative branch, which is what the script's own "
           "case-pattern logic is SUPPOSED to do for it. The forward-slash variant below "
           "already covers the cross-platform-safe form of a Windows-style absolute path.")
def test_latex_build_windows_backslash_outdir_not_mangled(tmp_path):
    # Regression: [A-Za-z]:[/\\]* looks correct but never actually matches a
    # literal backslash in this shell's case-pattern matching (verified via
    # a standalone probe: `case "\\" in [/\\]) ... esac` does not match).
    # A native Windows absolute OUTDIR fell through to the relative branch
    # and got mangled into "$(pwd)/C:\Users\...\build" — reproduced live as
    # the actual cause of a stray "C:" directory this exact bug left behind
    # in the repo root.
    outdir = tmp_path / "winbuild"
    win_outdir = str(outdir).replace("/", "\\")
    proc = _run_latex_build(tmp_path, win_outdir)
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert (outdir / "main.pdf").exists(), (proc.stdout, proc.stderr, list(tmp_path.iterdir()))


def test_latex_build_windows_forwardslash_outdir_not_mangled(tmp_path):
    outdir = tmp_path / "winbuild2"
    win_outdir = str(outdir).replace("\\", "/")
    proc = _run_latex_build(tmp_path, win_outdir)
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert (outdir / "main.pdf").exists(), (proc.stdout, proc.stderr)


def test_latex_build_relative_outdir_still_resolved_against_caller_cwd(tmp_path):
    # Non-regression: the plain relative-path branch must still work exactly
    # as before (resolved against the caller's original cwd == tmp_path here).
    proc = _run_latex_build(tmp_path, "relbuild")
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    assert (tmp_path / "relbuild" / "main.pdf").exists()


# ---------- xlsx_export.py: header rows must be formula-escaped too ----------

def test_xlsx_matrix_header_row_neutralizes_formula_in_card_source(run, tmp_path):
    from openpyxl import load_workbook

    cards_path = tmp_path / "evidence" / "cards.jsonl"
    cards_path.parent.mkdir(parents=True)
    poisoned = {"id": "EV-0001", "source": "=HYPERLINK(\"http://evil.example\",\"click\")",
                "type": "finding", "claim": "x", "tags": ["rq1"]}
    cards_path.write_text(json.dumps(poisoned) + "\n", encoding="utf-8")

    code, out, err = run("xlsx_export.py", "--sheet", "matrix",
                         "--cards", "evidence/cards.jsonl", "--out", "out.xlsx")
    assert code == 0, err

    wb = load_workbook(tmp_path / "out.xlsx")
    ws = wb["matrix"]
    header = [c.value for c in ws[1]]
    assert any(isinstance(v, str) and v.startswith("'=HYPERLINK") for v in header), header
    for cell in ws[1]:
        assert cell.data_type != "f", (cell.value, cell.data_type)


def test_xlsx_slr_header_row_neutralizes_formula_in_extract_field_name(run, tmp_path):
    from openpyxl import load_workbook

    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "registry.jsonl").write_text(
        json.dumps({"id": "SRC-0001", "bib_key": "a2020x", "db": "scopus",
                    "status": "included", "title": "T", "year": 2020}) + "\n",
        encoding="utf-8")
    extracts_dir = tmp_path / "evidence" / "extracts"
    extracts_dir.mkdir(parents=True)
    (extracts_dir / "a2020x.json").write_text(json.dumps({
        "key": "a2020x",
        "fields": {"=cmd|'/c calc'!A1": "poisoned field name"},
    }), encoding="utf-8")

    code, out, err = run("xlsx_export.py", "--sheet", "slr",
                         "--registry", "sources/registry.jsonl",
                         "--extracts", "evidence/extracts", "--out", "out.xlsx")
    assert code == 0, err

    wb = load_workbook(tmp_path / "out.xlsx")
    ws = wb["slr"]
    header = [c.value for c in ws[1]]
    assert any(isinstance(v, str) and v.startswith("'=cmd") for v in header), header
    for cell in ws[1]:
        assert cell.data_type != "f", (cell.value, cell.data_type)


# ---------- pdf2md.py: --pdf must not escape the project directory ----------

def test_pdf2md_rejects_pdf_arg_escaping_project_dir(run, tmp_path):
    outside = tmp_path.parent / "outside_secret.pdf"
    outside.write_bytes(b"%PDF-1.4 fake")
    try:
        code, out, err = run("pdf2md.py", "--pdf", str(outside))
        assert code == 1
        assert "--pdf" in err
        assert not (tmp_path / "sources" / "md").exists()
    finally:
        outside.unlink(missing_ok=True)


def test_pdf2md_allows_pdf_arg_within_project_dir(run, tmp_path):
    pdf_path = tmp_path / "sources" / "pdf" / "in.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    code, out, err = run("pdf2md.py", "--pdf", "sources/pdf/in.pdf")
    assert "--pdf" not in err
    # Fails downstream (not a real PDF for pymupdf4llm) — the point is only
    # that path validation itself didn't reject it.
    assert code != 1 or "--pdf" not in err


# ---------- write_verify_status.py: incomplete live recheck must be visible ----------

def _args(**overrides):
    base = dict(result="PASS", checked=5, fabricated=0, retracted=0, missing=0,
               unresolved=0, fixable=0, bib="bib/references.bib", drafts="drafts")
    base.update(overrides)
    return type("Args", (), base)()


def test_live_recheck_field_false_and_warns_when_bib_and_drafts_absent(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    status = write_verify_status.build_status(_args())
    assert status["result"] == "PASS"
    assert status["live_recheck"]["doi2bib_confirmed"] is False
    assert status["live_recheck"]["cite_audit_confirmed"] is False
    assert status["live_recheck"]["bib_checked"] == "bib/references.bib"
    err = capsys.readouterr().err
    assert "WARN" in err
    assert "incomplete live recheck" in err


def test_live_recheck_field_true_when_both_confirmed(monkeypatch, tmp_path, capsys):
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
    assert status["live_recheck"]["doi2bib_confirmed"] is True
    assert status["live_recheck"]["cite_audit_confirmed"] is True
    err = capsys.readouterr().err
    assert "WARN" not in err


# ---------- _shell_write_sink.py: simple variable indirection must resolve ----------

def test_write_targets_resolves_string_concat_variable():
    cmd = "python -c \"p='sources/reg'+'istry.jsonl'; open(p,'a').write('x')\""
    assert "sources/registry.jsonl" in write_targets(cmd)


def test_write_targets_resolves_os_path_join_variable():
    cmd = "python -c \"import os; p=os.path.join('sources','registry.jsonl'); open(p,'a').write('x')\""
    assert "sources/registry.jsonl" in write_targets(cmd)


def test_write_targets_still_ignores_unrelated_assignments():
    cmd = "python -c \"name='hello'+'world'; print(name)\""
    assert write_targets(cmd) == []


def test_protect_data_files_blocks_variable_indirection_bypass():
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "protect_data_files.py")],
        input=json.dumps({"tool_name": "Bash", "tool_input": {
            "command": "python -c \"p='sources/reg'+'istry.jsonl'; open(p,'a').write('x')\""}}),
        cwd=kit_project_cwd(), capture_output=True, text=True, encoding="utf-8")
    assert "deny" in proc.stdout


# ---------- make_reference_docx.py / docx_style_check.py: "Table" style ----------

def test_make_reference_docx_defines_table_style_with_borders(tmp_path):
    out = tmp_path / "ref.docx"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "make_reference_docx.py"), "--out", str(out)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    with zipfile.ZipFile(out) as z:
        styles_xml = z.read("word/styles.xml").decode("utf-8")
    assert 'w:type="table" w:styleId="Table"' in styles_xml
    assert "tblBorders" in styles_xml


def test_docx_style_check_includes_table_in_check_list():
    sys.path.insert(0, str(SCRIPTS))
    import docx_style_check
    assert "Table" in docx_style_check.CHECK_STYLES


def test_docx_style_check_reports_table_missing_in_built_doc(tmp_path):
    ref = tmp_path / "ref.docx"
    subprocess.run([sys.executable, str(SCRIPTS / "make_reference_docx.py"), "--out", str(ref)],
                  cwd=tmp_path, capture_output=True, text=True, check=True)
    # A "built" doc that never went through our reference doc (bare python-docx
    # Document()) has no "Table" style at all — must be flagged, not silently
    # treated as compliant.
    from docx import Document
    bare = tmp_path / "built.docx"
    Document().save(bare)

    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "docx_style_check.py"),
         "--built", str(bare), "--reference", str(ref), "--json"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 2, (proc.returncode, proc.stdout, proc.stderr)
    report = json.loads(proc.stdout)
    assert any(m["style"] == "Table" for m in report["mismatches"]), report
