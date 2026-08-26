"""Thesis front matter (scripts/frontmatter_check.py).

A thesis is turned back at the institute's formal check far more often than at
the defence, and almost never for its science: a missing ethics declaration, an
approval page in the wrong place, a list of figures that stops at 11 while the
body has 14. The kit knew the required order; nothing checked a document against it.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import frontmatter_check as fc  # noqa: E402,F401  (import smoke: the module must load)

FULL = """# İç Kapak
X Üniversitesi

# Onay Sayfası
Jüri.

# Etik Beyan
Beyan ederim.

# Teşekkür
Sağ olun.

# Özet
Bu tez X hakkındadır.

Anahtar kelimeler: derin öğrenme, rulman, arıza, titreşim

# Abstract
This thesis is about X.

Keywords: deep learning, bearing, fault, vibration

# İçindekiler
1. Giriş
2. Yöntem

# Şekil Listesi
Şekil 1. Akış
"""

BODY = "# Giriş\n\nMetin.\n\n# Yöntem\n\nŞekil 1. Akış\n"


def _run(cwd, *args, expect=0):
    proc = subprocess.run([sys.executable, str(SCRIPTS / "frontmatter_check.py"), *args],
                          cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == expect, f"exit {proc.returncode}: {proc.stdout}{proc.stderr}"
    return proc


def _thesis(tmp_path, front=FULL, body=BODY):
    (tmp_path / "drafts").mkdir(exist_ok=True)
    (tmp_path / "drafts" / "00-front-matter.md").write_text(front, encoding="utf-8")
    (tmp_path / "drafts" / "01-body.md").write_text(body, encoding="utf-8")
    return tmp_path


# ---------- presence and order ----------

def test_a_complete_front_matter_is_clean(tmp_path):
    _thesis(tmp_path)
    out = json.loads(_run(tmp_path).stdout)
    assert out["result"] == "CLEAN", out["problems"]


def test_a_missing_ethics_declaration_is_named(tmp_path):
    front = FULL.replace("# Etik Beyan\nBeyan ederim.\n\n", "")
    _thesis(tmp_path, front=front)
    out = json.loads(_run(tmp_path, expect=2).stdout)
    assert "ethics_declaration" in out["pages_missing"]


def test_pages_out_of_order_are_reported(tmp_path):
    front = FULL.replace("# Onay Sayfası\nJüri.\n\n", "")
    front = front.replace("# Teşekkür", "# Onay Sayfası\nJüri.\n\n# Teşekkür")
    _thesis(tmp_path, front=front)
    out = json.loads(_run(tmp_path, expect=2).stdout)
    assert any(p["check"] == "order" for p in out["problems"])


def test_an_optional_page_that_is_absent_is_not_a_finding(tmp_path):
    # A thesis with no tables needs no list of tables.
    _thesis(tmp_path)
    out = json.loads(_run(tmp_path).stdout)
    assert "abbreviations" not in out["pages_missing"]


def test_english_page_names_are_recognised(tmp_path):
    front = (FULL.replace("# İç Kapak", "# Title Page")
             .replace("# Onay Sayfası", "# Approval Page")
             .replace("# Etik Beyan", "# Declaration of Ethics")
             .replace("# Teşekkür", "# Acknowledgements")
             .replace("# İçindekiler", "# Table of Contents")
             .replace("# Şekil Listesi", "# List of Figures"))
    _thesis(tmp_path, front=front)
    out = json.loads(_run(tmp_path).stdout)
    assert out["result"] == "CLEAN", out["problems"]


def test_an_institute_order_overrides_the_default(tmp_path):
    # The kit does not decide what your institute requires.
    _thesis(tmp_path)
    (tmp_path / "order.json").write_text(json.dumps(
        [["ozet", ["özet"]], ["abstract", ["abstract"]]]), encoding="utf-8")
    out = json.loads(_run(tmp_path, "--order", "order.json").stdout)
    assert out["result"] == "CLEAN" and out["pages_found"] == ["ozet", "abstract"]


# ---------- Özet ↔ Abstract ----------

def test_a_keyword_count_mismatch_is_reported(tmp_path):
    front = FULL.replace("Keywords: deep learning, bearing, fault, vibration",
                         "Keywords: deep learning, bearing")
    _thesis(tmp_path, front=front)
    out = json.loads(_run(tmp_path, expect=2).stdout)
    assert any(p["check"] == "keywords" for p in out["problems"])


def test_a_missing_keyword_line_is_reported(tmp_path):
    front = FULL.replace("Keywords: deep learning, bearing, fault, vibration", "")
    _thesis(tmp_path, front=front)
    out = json.loads(_run(tmp_path, expect=2).stdout)
    assert any(p["check"] == "keywords" for p in out["problems"])


def test_equivalence_of_content_is_not_this_script_s_job(tmp_path):
    # Two entirely different summaries with matching keyword counts pass here;
    # tr_style_check.py is where equivalence lives.
    front = FULL.replace("This thesis is about X.", "Something completely different.")
    _thesis(tmp_path, front=front)
    out = json.loads(_run(tmp_path).stdout)
    assert out["result"] == "CLEAN"
    assert "tr_style_check" in out["note"]


# ---------- contents and lists vs the body ----------

def test_a_contents_entry_with_no_chapter_behind_it_is_reported(tmp_path):
    front = FULL.replace("2. Yöntem", "2. Yöntem\n3. Sonuçlar")
    _thesis(tmp_path, front=front)
    out = json.loads(_run(tmp_path, expect=2).stdout)
    problem = next(p for p in out["problems"] if p["check"] == "contents")
    assert any("Sonuçlar" in e for e in problem["entries"])


def test_a_chapter_missing_from_the_contents_is_reported(tmp_path):
    _thesis(tmp_path, body=BODY + "\n# Tartışma\n\nMetin.\n")
    out = json.loads(_run(tmp_path, expect=2).stdout)
    assert any(p["check"] == "contents" and "not listed" in p["detail"]
               for p in out["problems"])


def test_a_figure_in_the_body_but_not_in_the_list_is_reported(tmp_path):
    _thesis(tmp_path, body=BODY + "\nŞekil 2. Sonuç\n")
    out = json.loads(_run(tmp_path, expect=2).stdout)
    problem = next(p for p in out["problems"] if p["check"] == "list_of_figures")
    assert problem["missing_from_list"] == ["2"]


def test_figures_in_the_body_with_no_list_at_all_are_reported(tmp_path):
    front = FULL.replace("# Şekil Listesi\nŞekil 1. Akış\n", "")
    _thesis(tmp_path, front=front)
    out = json.loads(_run(tmp_path, expect=2).stdout)
    assert any(p["check"] == "list_of_figures" for p in out["problems"])


# ---------- CLI contract ----------

def test_a_missing_front_matter_points_at_the_command_that_writes_it(tmp_path):
    (tmp_path / "drafts").mkdir()
    proc = _run(tmp_path, expect=1)
    assert "/front-matter" in proc.stderr


def test_a_path_outside_the_project_is_refused(tmp_path):
    proc = _run(tmp_path, "--front", "../elsewhere.md", expect=1)
    assert "--front" in proc.stderr
