"""End-to-end pipeline tests over ONE realistic project.

WHY THIS FILE EXISTS
On 2026-08-23 a finished manuscript was taken through the kit's own pipeline for
the first time — twenty review rounds, a real venue's limits, a real submission
check — and twelve defects fell out. Every one of them passed the existing test
suite, because the suite tested functions and this pipeline is made of seams:

  · the typesetting gate counted Major issues with a digit-anchored pattern, so a
    reviewer that BOLDED its item numbers produced zero and the gate opened over
    four unresolved blockers;
  · the PDF builder called pdflatex, so no document that sets a font — i.e. no
    manuscript outside Latin-1 — could be built at all;
  · the word counter split every decimal in two, because a decimal separator is
    not a word character;
  · the submission check read the title with PROJECT.md's trailing decision
    comments attached (118 characters became 788), lost every keyword after a
    line wrap, folded the drafting log and the appendices into the body count,
    and had no concept of a second-language abstract;
  · the AI-disclosure generator printed "No results, data, or findings were
    AI-generated" unconditionally, into a statement whose only purpose is to be
    accurate.

None of them announced itself. Each produced a plausible number or a well-formed
sentence, which is exactly why unit tests did not catch them: the units were
right about the inputs they were given, and wrong about the inputs a real
manuscript has.

So these tests do not exercise functions. They build one project with the file
SHAPES that broke things — Turkish decimals, a bolded review, a wrapped bold
keyword line, a title with a trailing comment, a STATUS log, an appendix, two
abstracts — and run the real scripts and the real hook against it as
subprocesses, asserting the numbers a person would compute by hand.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
HOOKS = ROOT / ".claude" / "hooks"
sys.path.insert(0, str(SCRIPTS))


# ---------- the fixture: a small project shaped like a real one ----------

OZET = """# Özet

<!-- PRISMA-DTA madde 2 karşılığı. Bu yorum sayılmaz. -->

**Amaç.** Bir tarama testinin tanısal doğruluğunu değerlendirmek.

**Bulgular.** Özet duyarlılık ve özgüllük 0,940 ve 0,962 (k = 7); hasta
düzeyinde 0,931 ve 0,911 (k = 22). Güven aralığı 0,859–0,945, öngörü aralığı
0,473–0,992. Tanımlanan 1.572 kayıttan 100 çalışma senteze girmiştir.

**Anahtar sözcükler:** diyabetik retinopati; derin öğrenme; tanısal doğruluk;
tarama; sistematik derleme; gri literatür
"""

ABSTRACT = """# Abstract

**Objective.** To estimate the diagnostic accuracy of a screening test.

**Results.** Summary sensitivity and specificity were 0.940 and 0.962 (k = 7),
and 0.931 and 0.911 at patient level (k = 22). Of 1,572 records, 100 studies
entered the synthesis.

**Keywords:** diabetic retinopathy; deep learning; diagnostic accuracy;
screening; systematic review; grey literature
"""

# The shape that defeated the gate: item numbers inside the bold, so the line
# does not begin with a digit.
REVIEW_TWO_MAJORS = """# Round 1 — Hakem Raporu

## RUBRIC SCORES

| Boyut | Puan |
|---|---|
| Katkı | 4 |

## MAJOR ISSUES

**1. The registration count sums a field's fullness, not its value.**

Prose explaining the finding at some length.

**2. The funding count repeats the same error one paragraph later.**

More prose.

## MINOR ISSUES

1. Typo.

## DECISION

**Major revision.**
"""

REVIEW_ZERO_MAJORS = """# Round 2 — Hakem Raporu

## MAJOR ISSUES

Major issues: 0

**Yok.**

Bu hükme şunları denetleyerek vardım:

1. Havuzlanmış kestirimlerin aritmetiği. Tutuyor.
2. Akış ve payda kimlikleri. Kapanıyor.
3. Sonuçta olup Bulgularda olmayan iddia. Bulunmadı.

## MINOR ISSUES

1. Typo.

## DECISION

**Minor Revision.**
"""

LIMITS = {
    "venue": "Test Venue",
    "source_url": "https://example.org/authors",
    "read_on": "2026-08-23",
    "abstract_max_words": 250,
    "abstract_max_words_by_file": {"ozet.md": 250, "abstract.md": 287},
    "keywords": {"min": 3, "max": 5},
    "required_statements": ["çıkar çatışması"],
}

PASS_STATUS = {"result": "PASS", "checked": 2, "fabricated": 0, "retracted": 0,
               "missing": 0, "unresolved": 0, "fixable": 0, "timestamp": "2026-08-23"}


def _w(base: Path, rel: str, text: str) -> Path:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def project(tmp_path: Path, *, review: str = REVIEW_TWO_MAJORS,
            status: dict | None = None) -> Path:
    """A project with the file shapes that broke the pipeline."""
    _w(tmp_path, "PROJECT.md",
       "# PROJECT\n\n"
       "- **Title (working):** Kısa ve doğru başlık  <!-- 2026-08-21 (round-5): bu\n"
       "  yorum başlığın parçası değildir ve bir portala yapıştırılmamalıdır -->\n"
       "- **Output language:** tr\n")
    _w(tmp_path, "drafts/ozet.md", OZET)
    _w(tmp_path, "drafts/abstract.md", ABSTRACT)
    _w(tmp_path, "drafts/methods.md", "# Yöntem\n\n" + "kelime " * 300)
    _w(tmp_path, "drafts/ek-a-prisma.md", "# Ek A\n\n" + "ek " * 400)
    _w(tmp_path, "drafts/STATUS.md", "# STATUS\n\n" + "gunluk " * 900)
    _w(tmp_path, "bib/references.bib",
       "@article{a2020x,\n  title = {A},\n  doi = {10.1/a},\n  verified = {true},\n}\n\n"
       "@article{b2021y,\n  title = {B},\n  doi = {10.1/b},\n  verified = {true},\n}\n")
    _w(tmp_path, "reviews/round-1.md", review)
    _w(tmp_path, "verify-status.json",
       json.dumps(status if status is not None else PASS_STATUS))
    _w(tmp_path, "limits.json", json.dumps(LIMITS, ensure_ascii=False))
    return tmp_path


def _run(script: str, *args, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=str(cwd), timeout=120)


def _gate(cwd: Path, target: str) -> str:
    proc = subprocess.run([sys.executable, str(HOOKS / "phase_gate.py")],
                          input=json.dumps({"tool_name": "Write",
                                            "tool_input": {"file_path": str(cwd / target)}}),
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=str(cwd), timeout=60)
    return proc.stdout


# ---------- 1. measurement ----------

def test_turkish_decimals_and_thousands_count_as_one_word_each():
    from word_budget import count_words
    # Six numbers, each of which a person, a portal field and Word all count once.
    text = "0,940 ve 0,962 ile 0,931 ve 0,911; 0,859–0,945 ve 1.572 kayıt."
    # Seven numbers (six decimals + one thousands-separated) and five words:
    # ve · ile · ve · ve · kayıt. The en dash joins two numbers that are each
    # counted once. Before the fix this returned 19, because every separator
    # split its number in two.
    assert count_words(text) == 12, count_words(text)


def test_html_comments_do_not_count_against_a_word_limit():
    from word_budget import count_words
    assert count_words("bir iki <!-- üç dört beş -->") == 2


# ---------- 2. the submission check, against a real venue file ----------

def test_submission_check_reads_the_project_the_way_a_person_would(tmp_path):
    p = project(tmp_path)
    proc = _run("submission_pack.py", "--check", "--limits", "limits.json",
                "--json", cwd=p)
    out = json.loads(proc.stdout)

    # The title is what goes in the portal field — not PROJECT.md's decision log.
    assert out["title"]["title"] == "Kısa ve doğru başlık"
    assert "<!--" not in out["title"]["title"]

    # Six keywords across a wrapped, bolded line — in BOTH abstracts, because a
    # Turkish manuscript's list is not only the English one. The venue allows 5.
    kw = out["keywords"]
    assert set(kw["files"]) == {"ozet.md", "abstract.md"}, kw
    tr = kw["files"]["ozet.md"]
    en = kw["files"]["abstract.md"]
    assert tr["count"] == en["count"] == 6
    assert tr["keywords"][0] == "diyabetik retinopati"     # no stray asterisks
    assert tr["keywords"][-1] == "gri literatür"           # the wrap survived
    assert en["keywords"][0] == "diabetic retinopathy"
    assert "ozet.md" in kw["problem"] and "abstract.md" in kw["problem"]
    assert "at most 5" in kw["problem"]

    # Two abstracts, two limits.
    files = out["abstract"]["files"]
    assert set(files) == {"ozet.md", "abstract.md"}
    assert files["ozet.md"]["limit"] == 250
    assert files["abstract.md"]["limit"] == 287

    # The body is the body: no drafting log, appendices reported apart.
    ms = out["manuscript"]
    assert "STATUS.md" not in ms["files"]
    assert ms["excluded_from_count"] == ["STATUS.md"]
    assert ms["appendix_files"] == ["ek-a-prisma.md"]
    assert ms["appendix_words"] > 0
    assert ms["body_words"] == ms["total_words"]
    # methods (300) + the two abstracts, and nothing from the 900-word log.
    assert 300 < ms["body_words"] < 900


# ---------- 3. the gate, on a review shaped like a real one ----------

def test_gate_blocks_a_build_when_the_review_bolds_its_major_numbers(tmp_path):
    # The failure that mattered most: this review has two Major issues and the
    # gate used to read zero, because neither line starts with a digit.
    p = project(tmp_path, review=REVIEW_TWO_MAJORS)
    out = _gate(p, "build/main.pdf")
    assert "deny" in out
    assert "2 unresolved" in out


def test_gate_opens_when_the_review_states_zero_and_justifies_it(tmp_path):
    # A zero-Major review that lists what it looked for. Counting those items
    # would block a clean build; the explicit count line is what prevents it.
    p = project(tmp_path, review=REVIEW_ZERO_MAJORS)
    assert "deny" not in _gate(p, "build/main.pdf")


def test_gate_stays_shut_on_a_failed_citation_verification(tmp_path):
    # Major = 0 is not sufficient on its own: the fabrication gate comes first.
    p = project(tmp_path, review=REVIEW_ZERO_MAJORS,
                status={**PASS_STATUS, "result": "FAIL", "fabricated": 1})
    out = _gate(p, "build/main.pdf")
    assert "deny" in out


# ---------- 4. the disclosure the pipeline ends with ----------

def test_ai_disclosure_will_not_contradict_itself_for_this_project(tmp_path):
    p = project(tmp_path)
    proc = _run("compliance_gen.py", "ai-disclosure", "--tool", "T",
                "--uses", "data analysis; drafting", "--no-ai-results", cwd=p)
    assert proc.returncode == 1
    assert "contradicts" in proc.stdout + proc.stderr

    ok = _run("compliance_gen.py", "--json", "ai-disclosure", "--tool", "T",
              "--uses", "data analysis; drafting", cwd=p)
    result = json.loads(ok.stdout)
    assert "No results, data, or findings were AI-generated" not in result["statement"]
    assert result.get("notes")


# ---------- 5. the build, for a document that is not in Latin-1 ----------

def test_build_picks_a_unicode_engine_for_a_document_that_sets_a_font(tmp_path):
    # pdflatex cannot load fontspec, so before this the kit could not build ANY
    # manuscript that names a main font — which every non-Latin-1 one must.
    import shutil
    import subprocess as sp

    def runs(c):
        # On disk is not the same as runnable: a partial Git for Windows install
        # keeps bin\bash.exe and empties the usr\bin\ it execs into.
        try:
            return sp.run([c, "-c", "exit 0"], capture_output=True,
                          timeout=20).returncode == 0
        except (OSError, sp.SubprocessError):
            return False

    bash = next((c for c in (r"C:\Program Files\Git\bin\bash.exe", shutil.which("bash"))
                 if c and Path(c).exists() and runs(c)), None)
    if not bash:
        import pytest
        pytest.skip("no working bash available")
    bindir = tmp_path / "fakebin"
    bindir.mkdir()
    argv_log = tmp_path / "argv.txt"
    stub = bindir / "latexmk"
    stub.write_text("#!/bin/sh\n"
                    f'printf "%s\\n" "$@" > "{argv_log.as_posix()}"\nexit 12\n',
                    encoding="utf-8")
    stub.chmod(0o755)
    main = tmp_path / "main.tex"
    main.write_text("\\documentclass{article}\n\\usepackage{fontspec}\n"
                    "\\setmainfont{Times New Roman}\n"
                    "\\begin{document}Türkçe\\end{document}\n", encoding="utf-8")
    subprocess.run([bash, str(SCRIPTS / "latex_build.sh"), str(main),
                    str(tmp_path / "out")],
                   capture_output=True, text=True,
                   env={"PATH": f"{bindir.as_posix()}:/usr/bin:/bin",
                        "HOME": str(tmp_path)}, timeout=120)
    if not argv_log.exists():
        import pytest
        pytest.skip("stub latexmk was not reached in this environment")
    argv = argv_log.read_text(encoding="utf-8").split("\n")
    assert "-xelatex" in argv and "-pdf" not in argv


# ---------- 6. the sequence, as a claim ----------

def test_the_gate_sequence_is_verify_then_major_then_build(tmp_path):
    """The kit's headline guarantee, exercised in order on one project.

    Stated as: no formatting before the citation gate passes, and none before
    Major = 0. Both halves were individually tested and the composition was not,
    which is how a review with two Major issues reached an open gate.
    """
    p = project(tmp_path, review=REVIEW_TWO_MAJORS,
                status={**PASS_STATUS, "result": "FAIL", "fabricated": 1})
    assert "deny" in _gate(p, "build/main.pdf"), "FAIL verify must block"

    (p / "verify-status.json").write_text(json.dumps(PASS_STATUS), encoding="utf-8")
    assert "deny" in _gate(p, "build/main.pdf"), "2 Major issues must still block"

    (p / "reviews" / "round-1.md").write_text(REVIEW_ZERO_MAJORS, encoding="utf-8")
    assert "deny" not in _gate(p, "build/main.pdf"), "PASS + 0 Major must open"
