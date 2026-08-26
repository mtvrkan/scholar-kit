"""Regression tests for the '..' path-traversal guard in scripts/latex_build.sh
and scripts/docx_build.sh. Deliberately narrower than lib_common.require_within_cwd
(which every Python script's --file/--out-style argument uses): these two shell
scripts legitimately receive absolute paths in normal use (format-engineer,
and this suite's own round2-4 tests, pass tmp_path-absolute MAIN/OUTDIR/OUT
values), so only a literal '..' path component is rejected, not an absolute
path itself.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"


def _bash_runs(bash: str) -> bool:
    """Whether that bash can actually execute something.

    Existing is not the same as working, and the difference is not exotic: a
    partial Git for Windows install leaves `bin\\bash.exe` in place while
    `usr\\bin\\` — the directory it execs into — is empty, so every invocation
    dies in the launcher with "not found". The check here used to ask only
    whether the file was on disk, so the skip below never fired and the twelve
    tests that shell out reported a broken shell as a failure of the scripts
    they exist to test. A one-line probe is the difference between a suite that
    says "cannot check this here" and one that says "your change broke it".
    """
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


def test_latex_build_rejects_dotdot_in_main():
    bash = _find_git_bash()
    proc = subprocess.run(
        [bash, str(SCRIPTS / "latex_build.sh"), "../outside/main.tex", "build"],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 2
    assert "BLOCKED" in proc.stdout


def test_latex_build_rejects_dotdot_in_outdir(tmp_path):
    bash = _find_git_bash()
    main_tex = tmp_path / "main.tex"
    main_tex.write_text(r"\documentclass{article}\begin{document}x\end{document}", encoding="utf-8")
    proc = subprocess.run(
        [bash, str(SCRIPTS / "latex_build.sh"), str(main_tex), "../../outside_build"],
        cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 2
    assert "BLOCKED" in proc.stdout


def test_docx_build_rejects_dotdot_in_out():
    bash = _find_git_bash()
    proc = subprocess.run(
        [bash, str(SCRIPTS / "docx_build.sh"), "../outside.docx",
         "templates/csl/apa.csl", "-", "README.md"],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 2
    assert "BLOCKED" in proc.stdout


def test_docx_build_rejects_dotdot_in_section_file():
    bash = _find_git_bash()
    proc = subprocess.run(
        [bash, str(SCRIPTS / "docx_build.sh"), "out.docx",
         "templates/csl/apa.csl", "-", "../outside/section.md"],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 2
    assert "BLOCKED" in proc.stdout


def test_docx_build_allows_filename_containing_but_not_composed_of_dotdot():
    # Regression: an early version used a bare `*..*` substring match, which
    # would also reject an ordinary filename that merely contains two
    # consecutive dots as text, not a path-traversal component.
    bash = _find_git_bash()
    proc = subprocess.run(
        [bash, str(SCRIPTS / "docx_build.sh"), "v1..2.docx",
         "templates/csl/apa.csl", "-", "README.md"],
        cwd=ROOT, capture_output=True, text=True)
    assert "BLOCKED: path must not contain" not in proc.stdout


def test_docx_build_handles_section_file_starting_with_dash(tmp_path):
    # Regression: pandoc parses a leading '-' argument as an OPTION, not a
    # filename, unless a '--' end-of-options marker precedes it — a section
    # file named e.g. "-draft.md" would otherwise silently be swallowed as a
    # bogus pandoc flag instead of being read as input.
    bash = _find_git_bash()
    md = tmp_path / "-section.md"
    md.write_text("# Heading\n\nSome text.\n", encoding="utf-8")
    proc = subprocess.run(
        [bash, str(SCRIPTS / "docx_build.sh"), str(tmp_path / "out.docx"),
         "templates/csl/apa.csl", "-", str(md)],
        cwd=ROOT, capture_output=True, text=True)
    assert "Unknown option" not in proc.stdout
    assert proc.returncode != 2  # not blocked by the '..' guard either


def test_docx_build_still_allows_absolute_out_without_dotdot(tmp_path):
    # Not a full build success check (that needs bib/references.bib and a
    # real project layout) — only confirms the new '..' guard doesn't
    # misfire on an ordinary absolute path, which it did briefly need to
    # tolerate since round2-4's own tests always pass tmp_path-absolute
    # MAIN/OUTDIR/OUT values.
    bash = _find_git_bash()
    md = tmp_path / "section.md"
    md.write_text("# Heading\n\nSome text.\n", encoding="utf-8")
    proc = subprocess.run(
        [bash, str(SCRIPTS / "docx_build.sh"), str(tmp_path / "out.docx"),
         "templates/csl/apa.csl", "-", str(md)],
        cwd=ROOT, capture_output=True, text=True)
    assert "BLOCKED: path must not contain" not in proc.stdout
    assert proc.returncode != 2


# ---------- engine selection: pdflatex cannot typeset a fontspec document ----------
# A manuscript that sets `mainfont:` in its pandoc front matter compiles under
# `latexmk -pdf` (pdflatex) to "LaTeX Error: Unicode character X" and produces
# NO pdf. That is the wrong engine, not a broken document, and the script used
# to hardcode -pdf. These tests read the chosen engine off latexmk's own
# command line rather than requiring a TeX installation.

def _fake_latexmk(tmp_path):
    """A stub latexmk that records its argv and exits 3, so the script's own
    'not installed' branch is not taken and no TeX distribution is needed."""
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    argv_log = tmp_path / "argv.txt"
    stub = bindir / "latexmk"
    stub.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{argv_log.as_posix()}"\n'
        "exit 12\n", encoding="utf-8")
    stub.chmod(0o755)
    return bindir, argv_log


def _run_build(tmp_path, tex_body):
    bindir, argv_log = _fake_latexmk(tmp_path)
    main = tmp_path / "main.tex"
    main.write_text(tex_body, encoding="utf-8")
    env = {"PATH": f"{bindir.as_posix()}:/usr/bin:/bin", "HOME": str(tmp_path)}
    subprocess.run(
        [_find_git_bash(), str(SCRIPTS / "latex_build.sh"),
         str(main), str(tmp_path / "out")],
        capture_output=True, text=True, env=env)
    if not argv_log.exists():
        pytest.skip("stub latexmk was not reached in this environment")
    return argv_log.read_text(encoding="utf-8").split("\n")


def test_latex_build_picks_xelatex_for_a_fontspec_document(tmp_path):
    argv = _run_build(tmp_path,
                      "\\documentclass{article}\n\\usepackage{fontspec}\n"
                      "\\setmainfont{Times New Roman}\n"
                      "\\begin{document}x\\end{document}\n")
    assert "-xelatex" in argv
    assert "-pdf" not in argv


def test_latex_build_keeps_pdflatex_for_a_plain_document(tmp_path):
    argv = _run_build(tmp_path,
                      "\\documentclass{article}\n\\begin{document}x\\end{document}\n")
    assert "-pdf" in argv
    assert "-xelatex" not in argv


def test_latex_build_engine_override_is_honoured(tmp_path):
    bindir, argv_log = _fake_latexmk(tmp_path)
    main = tmp_path / "main.tex"
    main.write_text("\\documentclass{article}\n\\begin{document}x\\end{document}\n",
                    encoding="utf-8")
    env = {"PATH": f"{bindir.as_posix()}:/usr/bin:/bin", "HOME": str(tmp_path),
           "LATEX_ENGINE": "lualatex"}
    subprocess.run(
        [_find_git_bash(), str(SCRIPTS / "latex_build.sh"),
         str(main), str(tmp_path / "out")],
        capture_output=True, text=True, env=env)
    if not argv_log.exists():
        pytest.skip("stub latexmk was not reached in this environment")
    assert "-lualatex" in argv_log.read_text(encoding="utf-8").split("\n")


def test_latex_build_rejects_an_unknown_engine(tmp_path):
    main = tmp_path / "main.tex"
    main.write_text("\\documentclass{article}\n\\begin{document}x\\end{document}\n",
                    encoding="utf-8")
    proc = subprocess.run(
        [_find_git_bash(), str(SCRIPTS / "latex_build.sh"),
         str(main), str(tmp_path / "out")],
        capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path),
             "LATEX_ENGINE": "rm -rf /"})
    assert proc.returncode == 2
    assert "BLOCKED" in proc.stdout
