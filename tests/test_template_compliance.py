"""Tests for template_compliance.py — the built document vs the ingested
template's extracted rules (Invariant 8, TEMPLATE SUPREMACY).

The behaviour under test is mostly about what the checker REFUSES to claim.
Three states have to stay distinguishable — compliant, contradicted, and never
verified — because collapsing the third into the first is how a compliance
report becomes a false guarantee, which is worse than having no report.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import template_compliance as tc  # noqa: E402

docx = pytest.importorskip("docx", reason="python-docx not installed")


def _profile(tmp_path, rules: dict | None, prose: str = "# Template Profile\n\nBody: 12pt Times.\n"):
    p = tmp_path / "templates" / "ingested" / "template-profile.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    text = prose
    if rules is not None:
        text += "\n```json template-rules\n" + json.dumps(rules, indent=2) + "\n```\n"
    p.write_text(text, encoding="utf-8")
    return p


def _docx(tmp_path, *, font="Times New Roman", size=12, margin_mm=25.4,
          heading1_size=16, name="paper.docx"):
    from docx import Document
    from docx.shared import Mm, Pt
    doc = Document()
    s = doc.sections[0]
    s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Mm(margin_mm)
    s.page_width, s.page_height = Mm(210), Mm(297)
    normal = doc.styles["Normal"]
    normal.font.name = font
    normal.font.size = Pt(size)
    normal.paragraph_format.line_spacing = 1.5
    h1 = doc.styles["Heading 1"]
    h1.font.name = font
    h1.font.size = Pt(heading1_size)
    h1.font.bold = True
    doc.add_paragraph("Giriş", style="Heading 1")
    doc.add_paragraph("Bir cümle.")
    out = tmp_path / name
    doc.save(str(out))
    return out


FULL_RULES = {
    "source_template": "journal-template.docx",
    "target": "docx",
    "page": {"size": "A4", "margins_mm": {"top": 25.4, "bottom": 25.4,
                                          "left": 25.4, "right": 25.4}},
    "body": {"font": "Times New Roman", "size_pt": 12, "line_spacing": 1.5},
    "headings": {"Heading 1": {"font": "Times New Roman", "size_pt": 16, "bold": True}},
    "caption": {"style_name": "Caption"},
}


def _verdicts(report):
    return {r["rule"]: r["verdict"] for r in report["results"]}


# ---------------------------------------------------------------- the states

def test_no_profile_is_not_a_pass_and_not_a_failure(tmp_path):
    """A project with no registered template is outside the invariant, and the
    report must say that rather than reporting zero mismatches, which reads as
    a clean bill of health for a check that never ran."""
    built = _docx(tmp_path)
    r = tc.run(built, tmp_path / "templates" / "ingested" / "template-profile.md")
    assert r["status"] == "no-template"
    assert r["results"] == []
    assert "no template registered" in r["warnings"][0]


def test_prose_only_profile_reports_unbound(tmp_path):
    """The state the whole script exists to expose: a profile whose rules are
    prose cannot be checked, and saying so is the honest output."""
    prof = _profile(tmp_path, None)
    r = tc.run(_docx(tmp_path), prof)
    assert r["status"] == "unbound"
    assert "template-rules" in r["warnings"][0]
    assert r["results"] == []


def test_compliant_build_passes_every_stated_rule(tmp_path):
    prof = _profile(tmp_path, FULL_RULES)
    r = tc.run(_docx(tmp_path), prof)
    assert r["status"] == "checked" and r["format"] == "docx"
    assert r["counts"]["mismatch"] == 0
    v = _verdicts(r)
    for rule in ("page.margins_mm.top", "page.size", "body.font",
                 "body.size_pt", "body.line_spacing",
                 "headings.Heading 1.size_pt"):
        assert v[rule] == "pass", (rule, r["results"])


def test_wrong_margin_and_font_are_reported_separately(tmp_path):
    prof = _profile(tmp_path, FULL_RULES)
    r = tc.run(_docx(tmp_path, font="Arial", margin_mm=20), prof)
    v = _verdicts(r)
    assert v["body.font"] == "mismatch"
    assert v["page.margins_mm.left"] == "mismatch"
    assert v["body.size_pt"] == "pass"
    assert r["counts"]["mismatch"] >= 5


def test_null_rule_is_unchecked_never_pass(tmp_path):
    """A null in the profile means the analyzer could not determine the value.
    Treating it as satisfied would invent a guarantee out of an absence."""
    rules = json.loads(json.dumps(FULL_RULES))
    rules["body"]["font"] = None
    r = tc.run(_docx(tmp_path), _profile(tmp_path, rules))
    assert _verdicts(r)["body.font"] == "unchecked"
    assert any("could not determine" in x["why"] for x in r["results"]
               if x["rule"] == "body.font")


def test_style_absent_from_build_is_unchecked_not_mismatch(tmp_path):
    """The built document defining no such style is a different fact from it
    defining the style differently, and the report keeps them apart."""
    rules = json.loads(json.dumps(FULL_RULES))
    rules["headings"] = {"Heading 9": {"font": "Times New Roman", "size_pt": 9}}
    r = tc.run(_docx(tmp_path), _profile(tmp_path, rules))
    assert _verdicts(r)["headings.Heading 9"] == "unchecked"


def test_unchecked_rules_raise_a_warning_so_they_cannot_read_as_compliant(tmp_path):
    rules = json.loads(json.dumps(FULL_RULES))
    rules["body"]["line_spacing"] = None
    r = tc.run(_docx(tmp_path), _profile(tmp_path, rules))
    assert any("unchecked" in w and "NOT the same as" in w for w in r["warnings"])


def test_malformed_rules_block_is_reported_not_ignored(tmp_path):
    p = tmp_path / "templates" / "ingested" / "template-profile.md"
    p.parent.mkdir(parents=True)
    p.write_text("# Profile\n\n```json template-rules\n{not json,,}\n```\n", encoding="utf-8")
    r = tc.run(_docx(tmp_path), p)
    assert r["status"] == "unbound"
    assert "not valid JSON" in r["warnings"][0]


def test_untagged_json_block_does_not_count_as_the_rules_block(tmp_path):
    """Profiles legitimately contain example JSON. Only the tagged block is the
    contract; a bare ```json fence must not be adopted as one."""
    p = tmp_path / "templates" / "ingested" / "template-profile.md"
    p.parent.mkdir(parents=True)
    p.write_text('# Profile\n\n```json\n{"page": {"size": "A4"}}\n```\n', encoding="utf-8")
    assert tc.run(_docx(tmp_path), p)["status"] == "unbound"


# ------------------------------------------------------------------- LaTeX

TEX_RULES = {
    "target": "latex",
    "page": {"margins_mm": {"top": 25.0, "bottom": 25.0, "left": 30.0, "right": 20.0}},
    "latex": {"documentclass": "IEEEtran", "class_options": ["conference"],
              "required_packages": ["graphicx", "cite"]},
}

TEX_OK = (r"\documentclass[conference]{IEEEtran}" "\n"
          r"\usepackage{graphicx}" "\n"
          r"\usepackage{cite}" "\n"
          r"\usepackage[top=25mm,bottom=25mm,left=3cm,right=2cm]{geometry}" "\n"
          r"\begin{document}x\end{document}" "\n")


def test_latex_compliant_source_passes(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(TEX_OK, encoding="utf-8")
    r = tc.run(tex, _profile(tmp_path, TEX_RULES))
    assert r["format"] == "latex" and r["counts"]["mismatch"] == 0
    v = _verdicts(r)
    assert v["latex.documentclass"] == "pass"
    assert v["latex.required_packages"] == "pass"
    assert v["page.margins_mm.left"] == "pass"  # 3cm stated in cm, rule in mm


def test_latex_missing_package_and_wrong_class_are_mismatches(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(r"\documentclass[conference]{article}" "\n"
                   r"\usepackage{graphicx}" "\n"
                   r"\begin{document}x\end{document}" "\n", encoding="utf-8")
    r = tc.run(tex, _profile(tmp_path, TEX_RULES))
    v = _verdicts(r)
    assert v["latex.documentclass"] == "mismatch"
    assert v["latex.required_packages"] == "mismatch"
    assert any("cite" in x["why"] for x in r["results"]
               if x["rule"] == "latex.required_packages")


def test_commented_out_package_does_not_count_as_present(tmp_path):
    """A LaTeX comment is not source. Reading one as a satisfied rule would
    report compliance for a package the build never loads."""
    tex = tmp_path / "main.tex"
    tex.write_text(r"\documentclass[conference]{IEEEtran}" "\n"
                   r"\usepackage{graphicx}" "\n"
                   r"% \usepackage{cite}" "\n"
                   r"\begin{document}x\end{document}" "\n", encoding="utf-8")
    r = tc.run(tex, _profile(tmp_path, TEX_RULES))
    assert _verdicts(r)["latex.required_packages"] == "mismatch"


def test_latex_margin_absent_from_source_is_unchecked(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(r"\documentclass[conference]{IEEEtran}" "\n"
                   r"\usepackage{graphicx}" "\n\\usepackage{cite}\n"
                   r"\begin{document}x\end{document}" "\n", encoding="utf-8")
    r = tc.run(tex, _profile(tmp_path, TEX_RULES))
    assert _verdicts(r)["page.margins_mm.top"] == "unchecked"


# ---------------------------------------------------------------------- CLI

def _run_cli(cwd, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / "template_compliance.py"), *args],
                          cwd=cwd, capture_output=True, text=True)


def test_cli_exits_2_on_mismatch_and_0_when_clean(tmp_path):
    _profile(tmp_path, FULL_RULES)
    _docx(tmp_path, name="ok.docx")
    _docx(tmp_path, font="Arial", name="bad.docx")
    clean = _run_cli(tmp_path, "--built", "ok.docx")
    assert clean.returncode == 0, clean.stdout + clean.stderr
    bad = _run_cli(tmp_path, "--built", "bad.docx")
    assert bad.returncode == 2
    assert json.loads(bad.stdout)["counts"]["mismatch"] >= 1


def test_cli_output_is_json_without_the_json_flag(tmp_path):
    """Kit invariant: structured output is always JSON, --json or not."""
    _profile(tmp_path, FULL_RULES)
    _docx(tmp_path, name="ok.docx")
    r = _run_cli(tmp_path, "--built", "ok.docx")
    assert json.loads(r.stdout)["status"] == "checked"


def test_cli_rejects_a_path_outside_the_project(tmp_path):
    _profile(tmp_path, FULL_RULES)
    r = _run_cli(tmp_path, "--built", "../outside.docx")
    assert r.returncode == 1
    assert "--built" in r.stderr


# ------------------------------------------------------------------- wiring

@pytest.mark.parametrize("script", ["docx_build.sh", "latex_build.sh"])
def test_both_build_scripts_run_the_check(script):
    """A checker nobody calls is documentation. Asserted textually rather than
    by running the builds, because that needs pandoc/latexmk plus a working
    bash — this test has to fail on a dropped wiring even where those are
    absent, which is where the wiring would silently rot."""
    text = (SCRIPTS / script).read_text(encoding="utf-8")
    assert "template_compliance.py" in text, f"{script} never invokes the checker"
    assert "template-profile.md" in text, f"{script} does not gate on a profile"


@pytest.mark.parametrize("script", ["docx_build.sh", "latex_build.sh"])
def test_the_check_cannot_fail_the_build(script):
    """WARN-only is the contract (D-071c's decision, inherited): drift needs a
    human decision, so the checker's exit code must never become the script's."""
    text = (SCRIPTS / script).read_text(encoding="utf-8")
    block = text[text.index("template_compliance.py"):]
    block = block[:block.index("exit 0")] if "exit 0" in block else block
    assert "exit 2" not in block and "exit 1" not in block, (
        f"{script} exits on the compliance result — it must only WARN")
