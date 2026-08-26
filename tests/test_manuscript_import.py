"""Importing a manuscript written outside the kit (scripts/manuscript_import.py).

The whole value of the import is that it does NOT import the document's claims:
the reference list is read as a list of DOIs, the text is not edited, and the
numeric→key mapping is a proposal on disk rather than a rewrite in the prose. The
tests pin those three, plus the conversion refusals.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import manuscript_import as mi  # noqa: E402

PAPER = """# Giriş

Derin öğrenme yaygınlaşmıştır [1]. Doğruluk %92,4 olarak bildirilmiştir [2].
Yılmaz (2020) bunu desteklemektedir.

# Yöntem

Şekil 1 akışı gösterir [1,3].

# Kaynakça

[1] Vaswani, A. Attention is all you need. NeurIPS, 2017. https://doi.org/10.48550/arXiv.1706.03762
[2] Yılmaz, K. Derin öğrenme ile sınıflandırma. Dergi, 2020.
[3] LeCun, Y. Deep learning. Nature 521, 436-444, 2015. doi:10.1038/nature14539
"""


def _paper(tmp_path, text=PAPER, name="paper.md"):
    (tmp_path / name).write_text(text, encoding="utf-8")
    (tmp_path / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
    return name


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "manuscript_import.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


# ---------- the split ----------

def test_sections_come_from_the_headings_the_document_has(tmp_path):
    name = _paper(tmp_path)
    out = json.loads(_run(tmp_path, "--file", name, "--plan").stdout)
    assert [s["title"] for s in out["sections"]] == ["Giriş", "Yöntem"]
    # Turkish headings become ASCII slugs; the reference section is not a draft.
    assert out["sections"][0]["file"] == "drafts/01-giris.md"


def test_a_document_with_no_headings_is_reported_not_invented(tmp_path):
    """The usual outcome of a PDF conversion. One file and a warning beats a
    structure the kit guessed."""
    name = _paper(tmp_path, text="Bir paragraf. Sonra bir paragraf daha.\n")
    out = json.loads(_run(tmp_path, "--file", name, "--plan").stdout)
    assert len(out["sections"]) == 1
    assert any("no markdown headings" in w for w in out["warnings"])


def test_existing_section_files_stop_the_import(tmp_path):
    name = _paper(tmp_path)
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "01-giris.md").write_text("two weeks of edits\n", encoding="utf-8")
    out = json.loads(_run(tmp_path, "--file", name, expect=2).stdout)
    assert out["result"] == "REFUSED" and out["existing_targets"]
    assert (tmp_path / "drafts" / "01-giris.md").read_text(encoding="utf-8") == \
        "two weeks of edits\n"


# ---------- the reference list, read as identifiers ----------

def test_dois_are_extracted_and_entries_without_one_are_reported(tmp_path):
    name = _paper(tmp_path)
    out = json.loads(_run(tmp_path, "--file", name, "--plan").stdout)
    assert out["references"]["entries"] == 3
    assert out["references"]["with_doi"] == 2
    assert out["references"]["without_doi"] == 1


def test_no_field_of_the_reference_list_reaches_the_bibliography(tmp_path):
    """Without --resolve nothing is fetched, and nothing is transcribed either:
    a bib written from the manuscript's own typing is the defect this kit exists
    to prevent."""
    name = _paper(tmp_path)
    _run(tmp_path, "--file", name)
    assert not (tmp_path / "bib" / "references.bib").exists()


def test_reference_entries_are_not_parsed_into_author_title_fields():
    entries = mi.parse_reference_entries(
        "[1] Vaswani, A. Attention is all you need. NeurIPS, 2017. "
        "https://doi.org/10.48550/arXiv.1706.03762\n")
    assert set(entries[0]) == {"index", "raw", "doi", "year"}
    assert entries[0]["doi"] == "10.48550/arXiv.1706.03762"


# ---------- the text is not touched ----------

def test_the_text_is_written_through_unedited(tmp_path):
    name = _paper(tmp_path)
    _run(tmp_path, "--file", name)
    body = (tmp_path / "drafts" / "01-giris.md").read_text(encoding="utf-8")
    assert "[1]" in body and "%92,4" in body
    assert "[@" not in body, "a citation was rewritten without the author seeing it"


def test_the_citation_style_is_detected(tmp_path):
    name = _paper(tmp_path)
    out = json.loads(_run(tmp_path, "--file", name, "--plan").stdout)
    assert out["citations"]["style"] == "numeric"
    assert out["citations"]["numeric"] == [1, 2, 3]


def test_a_narrative_citation_is_counted_once(tmp_path):
    # "Yılmaz (2020)" is one citation, not one author plus one year.
    found = mi.find_citations("Yılmaz (2020) bunu desteklemektedir.")
    assert found["author_year"] == ["Yılmaz"]


def test_an_unsupported_format_is_named(tmp_path):
    (tmp_path / "paper.pages").write_text("x", encoding="utf-8")
    proc = _run(tmp_path, "--file", "paper.pages", "--plan", expect=1)
    assert "unsupported" in (proc.stderr + proc.stdout).lower()
