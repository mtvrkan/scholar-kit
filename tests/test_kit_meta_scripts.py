"""Tests for the 4 previously-uncovered kit-meta scripts: validate_kit.py,
extract_skill_descriptions.py, skill_routing_eval.py, make_reference_docx.py.
None of these mutate project data (Invariant 6 doesn't apply); they inspect
the kit's own installed skills/agents or generate a build artifact.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import extract_skill_descriptions  # noqa: E402
import validate_kit  # noqa: E402


# ---------- validate_kit.py ----------

def test_validate_kit_reports_zero_problems_on_real_kit(run):
    code, out, err = run("validate_kit.py", "--json")
    data = json.loads(out)
    assert code == 0, data["problems"]
    assert data["problems"] == []
    assert data["counts"]["skills"] > 0
    assert data["counts"]["agents"] > 0


def test_frontmatter_parses_simple_yaml():
    text = '---\nname: draft\ndescription: "Draft a section"\n---\nbody text\n'
    fm = validate_kit.frontmatter(text)
    assert fm == {"name": "draft", "description": "Draft a section"}


def test_frontmatter_returns_empty_dict_without_delimiters():
    assert validate_kit.frontmatter("just a plain markdown file\nno frontmatter\n") == {}


def test_frontmatter_strips_bom_and_quotes():
    text = '﻿---\nname: x\ndescription: "quoted value"\n---\n'
    fm = validate_kit.frontmatter(text)
    assert fm["name"] == "x"
    assert fm["description"] == "quoted value"


def test_validate_kit_reports_invalid_settings_json_instead_of_crashing(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(validate_kit, "ROOT", tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("{not valid json", encoding="utf-8")
    (tmp_path / ".claude" / "skills").mkdir()
    (tmp_path / ".claude" / "agents").mkdir()
    monkeypatch.setattr(sys, "argv", ["validate_kit.py", "--json"])
    with pytest.raises(SystemExit) as exc:
        validate_kit.main()
    assert exc.value.code == 2
    data = json.loads(capsys.readouterr().out)
    assert any("not valid JSON" in p for p in data["problems"])


def test_validate_kit_reports_non_object_settings_json_instead_of_crashing(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(validate_kit, "ROOT", tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text("[1, 2, 3]", encoding="utf-8")
    (tmp_path / ".claude" / "skills").mkdir()
    (tmp_path / ".claude" / "agents").mkdir()
    monkeypatch.setattr(sys, "argv", ["validate_kit.py", "--json"])
    with pytest.raises(SystemExit) as exc:
        validate_kit.main()
    assert exc.value.code == 2
    data = json.loads(capsys.readouterr().out)
    assert any("must be a JSON object" in p for p in data["problems"])


def _settings_with_required_hooks():
    """Build a minimal settings.json dict wiring every REQUIRED_HOOKS entry to
    its event, grouped by event so a single event holds all its hooks."""
    hooks = {}
    for hook_file, event in validate_kit.REQUIRED_HOOKS.items():
        hooks.setdefault(event, [{"hooks": []}])
        hooks[event][0]["hooks"].append(
            {"type": "command", "command": f'python "$CLAUDE_PROJECT_DIR/.claude/hooks/{hook_file}"'})
    return {"hooks": hooks}


def _run_validate_on(tmp_path, monkeypatch, capsys, cfg):
    monkeypatch.setattr(validate_kit, "ROOT", tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(cfg), encoding="utf-8")
    (tmp_path / ".claude" / "skills").mkdir()
    (tmp_path / ".claude" / "agents").mkdir()
    monkeypatch.setattr(sys, "argv", ["validate_kit.py", "--json"])
    with pytest.raises(SystemExit):
        validate_kit.main()
    return json.loads(capsys.readouterr().out)["problems"]


def test_validate_kit_flags_dropped_required_hook(tmp_path, monkeypatch, capsys):
    # Enforcement evaporates silently if a hook entry is dropped from
    # settings.json; validate_kit must catch that, not just missing files.
    cfg = _settings_with_required_hooks()
    cfg["hooks"]["PreToolUse"][0]["hooks"] = [
        h for h in cfg["hooks"]["PreToolUse"][0]["hooks"]
        if "protect_data_files.py" not in h["command"]]
    problems = _run_validate_on(tmp_path, monkeypatch, capsys, cfg)
    assert any("required hook not wired: protect_data_files.py" in p for p in problems)


def test_validate_kit_flags_misrouted_required_hook(tmp_path, monkeypatch, capsys):
    # A hook wired to the wrong event (e.g. cite_warn moved out of PostToolUse)
    # never fires for its intended trigger — treated the same as not wired.
    cfg = _settings_with_required_hooks()
    cfg["hooks"]["PostToolUse"][0]["hooks"] = [
        h for h in cfg["hooks"]["PostToolUse"][0]["hooks"]
        if "cite_warn.py" not in h["command"]]
    cfg["hooks"].setdefault("PreToolUse", [{"hooks": []}])[0]["hooks"].append(
        {"type": "command", "command": 'python "$CLAUDE_PROJECT_DIR/.claude/hooks/cite_warn.py"'})
    problems = _run_validate_on(tmp_path, monkeypatch, capsys, cfg)
    assert any("required hook not wired: cite_warn.py" in p and "PostToolUse" in p
               for p in problems)


def test_validate_kit_accepts_all_required_hooks_wired(tmp_path, monkeypatch, capsys):
    # Positive control: with every required hook wired to its event, none of the
    # "required hook not wired" problems appear (other tmp-kit problems may).
    problems = _run_validate_on(tmp_path, monkeypatch, capsys, _settings_with_required_hooks())
    assert not any("required hook not wired" in p for p in problems)


# ---------- extract_skill_descriptions.py ----------

def test_extract_skill_descriptions_lists_every_skill_dir(run):
    code, out, err = run("extract_skill_descriptions.py")
    assert code == 0, err
    skills = json.loads(out)
    real_dirs = {p.parent.name for p in (ROOT / ".claude" / "skills").glob("*/SKILL.md")}
    assert {s["skill"] for s in skills} == real_dirs
    assert all(s["description"] for s in skills)


def test_extract_skill_descriptions_flags_workflow_vs_knowledge_skill(run):
    code, out, err = run("extract_skill_descriptions.py")
    by_name = {s["skill"]: s for s in json.loads(out)}
    assert by_name["draft"]["is_command"] is True  # disable-model-invocation: true
    assert by_name["academic-writing"]["is_command"] is False


def test_frontmatter_handles_multiline_folded_description():
    text = (
        "---\n"
        "name: slr\n"
        "description: \"first line of a\n"
        "  folded description that continues\n"
        "  across several lines\"\n"
        "disable-model-invocation: true\n"
        "---\n"
    )
    fm = extract_skill_descriptions.frontmatter(text)
    assert fm["name"] == "slr"
    assert "folded description that continues" in fm["description"]
    assert fm["disable-model-invocation"] == "true"


# ---------- skill_routing_eval.py ----------

def _write_prompts(tmp_path, entries):
    p = tmp_path / "prompts.json"
    p.write_text(json.dumps(entries), encoding="utf-8")
    return p


def test_skill_routing_eval_flags_unknown_expect_skill(run, tmp_path):
    prompts = _write_prompts(tmp_path, [{"prompt": "do a thing", "expect": "not-a-real-skill"}])
    code, out, err = run("skill_routing_eval.py", "--prompts", str(prompts), "--json")
    data = json.loads(out)
    assert code == 2
    assert any("not-a-real-skill" in p for p in data["problems"])


def test_skill_routing_eval_flags_missing_prompt_or_expect_fields(run, tmp_path):
    prompts = _write_prompts(tmp_path, [{"expect": "draft"}, {"prompt": "no expect field"}])
    code, out, err = run("skill_routing_eval.py", "--prompts", str(prompts), "--json")
    data = json.loads(out)
    assert code == 2
    assert any("missing 'prompt'" in p for p in data["problems"])
    assert any("missing 'expect'" in p for p in data["problems"])


def test_skill_routing_eval_passes_for_real_skill_and_reports_uncovered(run, tmp_path):
    prompts = _write_prompts(tmp_path, [{"prompt": "write the introduction section", "expect": "draft"}])
    code, out, err = run("skill_routing_eval.py", "--prompts", str(prompts), "--json")
    data = json.loads(out)
    assert data["problems"] == []
    assert code == 0
    assert data["skills_covered_by_eval"] == 1
    assert "draft" not in data["skills_uncovered"]
    assert data["skills_uncovered"]  # every other skill is legitimately uncovered by this 1-entry file


def _routing_eval(*args) -> tuple[int, dict]:
    """Run skill_routing_eval.py against the SHIPPED golden set.

    Not the `run` fixture: that runs scripts inside tmp_path, and the script's
    traversal guard (require_within_cwd) correctly refuses a --prompts path
    outside the working directory. The shipped set only resolves from the kit
    root, so these two tests run there.
    """
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "skill_routing_eval.py"), *args, "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    assert proc.stdout.strip(), f"no JSON on stdout; stderr: {proc.stderr.strip()}"
    return proc.returncode, json.loads(proc.stdout)


def test_shipped_golden_set_covers_every_skill_in_the_catalog():
    """The gap this closes was live: 26 of 28 skills had a golden prompt
    (disclosures and restyle had none) while ROUTING-EVAL.md read "full
    coverage". Nothing failed, because coverage was reported and not counted —
    so a skill added without a prompt kept its description unrouted and its
    routing accuracy unmeasured. The flag exists for exactly this assertion;
    it stays opt-in so the partial-file fixtures above remain legal callers.
    """
    code, data = _routing_eval("--require-full-coverage")
    assert data["problems"] == [], data["problems"]
    assert code == 0
    assert data["skills_uncovered"] == []
    assert data["skills_covered_by_eval"] == data["skills_in_catalog"]


def test_routing_eval_doc_states_the_real_prompt_and_skill_counts():
    """ROUTING-EVAL.md's headline numbers, derived rather than restated.

    The live-accuracy figure in that document is deliberately NOT asserted
    here: it comes from a model run, and a test that pinned it would only be
    pinning the last time somebody typed it. What a test can hold is the size
    and coverage of the set that figure is about — the part that silently
    drifted when two skills arrived without prompts.
    """
    import re
    _, data = _routing_eval()
    doc = (ROOT / "eval" / "ROUTING-EVAL.md").read_text(encoding="utf-8")
    m = re.search(r"(\d+)\s*prompts?\s*/\s*(\d+)\s*skills", doc)
    assert m, ("ROUTING-EVAL.md no longer states its set size as "
               "'<N> prompts / <M> skills' — the line this test derives")
    assert int(m.group(1)) == data["total_prompts"], (
        f"ROUTING-EVAL.md claims {m.group(1)} prompts; the golden set holds "
        f"{data['total_prompts']}")
    assert int(m.group(2)) == data["skills_in_catalog"], (
        f"ROUTING-EVAL.md claims {m.group(2)} skills; the catalog holds "
        f"{data['skills_in_catalog']}")


def test_skill_routing_eval_missing_prompts_file_dies(run, tmp_path):
    code, out, err = run("skill_routing_eval.py", "--prompts", str(tmp_path / "nope.json"), "--json")
    assert code == 1
    assert "not found" in err.lower()


# ---------- make_reference_docx.py ----------

def test_make_reference_docx_produces_valid_docx_with_expected_styles(run, tmp_path):
    code, out, err = run("make_reference_docx.py", "--out", "ref.docx",
                          "--font", "Georgia", "--size", "11", "--spacing", "1.0")
    assert code == 0, err
    out_path = tmp_path / "ref.docx"
    assert out_path.exists()

    from docx import Document
    doc = Document(str(out_path))
    names = {s.name for s in doc.styles}
    for expected in ("Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4",
                     "First Paragraph", "Body Text", "Block Text", "Caption", "Bibliography"):
        assert expected in names, f"missing style: {expected}"

    normal = doc.styles["Normal"]
    assert normal.font.name == "Georgia"
    assert normal.font.size.pt == 11

    heading1 = doc.styles["Heading 1"]
    assert heading1.font.bold is True
    assert heading1.font.size.pt == 14


def test_make_reference_docx_runs_twice_without_duplicate_style_crash(run, tmp_path):
    # Block Text/Bibliography are created via add_style() only when absent from
    # python-docx's default template — regression guard that re-running into a
    # FRESH file each time never hits a "style already exists" crash either way.
    for _ in range(2):
        code, out, err = run("make_reference_docx.py", "--out", "ref.docx")
        assert code == 0, err


def test_make_reference_docx_pandoc_maps_first_paragraph_correctly(run, tmp_path):
    # Regression: Pandoc's docx writer uses "First Paragraph" (not "Body Text")
    # for the paragraph immediately following a heading. A reference.docx
    # missing that style makes Pandoc fall back to unstyled "Normal" for the
    # opening paragraph of every section, even though "Body Text" IS defined
    # and correctly applied to every paragraph after it — reproduced live
    # against a real pandoc invocation before this style was added.
    import shutil
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc not installed")

    code, out, err = run("make_reference_docx.py", "--out", "ref.docx")
    assert code == 0, err

    md = tmp_path / "section.md"
    md.write_text("# Heading\n\nFirst paragraph after the heading.\n\n"
                   "Second paragraph in the same section.\n", encoding="utf-8")
    import subprocess
    proc = subprocess.run(
        ["pandoc", "--from", "markdown", "--to", "docx",
         "--output", "out.docx", "--reference-doc", "ref.docx", "section.md"],
        cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr

    from docx import Document
    doc = Document(str(tmp_path / "out.docx"))
    styled = [(p.style.name, p.text) for p in doc.paragraphs if p.text.strip()]
    assert styled[0][0] == "Heading 1"
    assert styled[1][0] == "First Paragraph", styled
    assert styled[2][0] == "Body Text", styled


# ---------- docx_style_check.py ----------

def test_docx_style_check_flags_missing_first_paragraph_style(run, tmp_path):
    # Regression: docx_style_check.py's CHECK_STYLES list didn't include
    # "First Paragraph" (added to make_reference_docx.py this session) — a
    # built.docx missing that style would have been reported "compliant: true"
    # even though it's missing the exact style Pandoc needs for every
    # section's opening paragraph.
    from docx import Document
    from docx.enum.style import WD_STYLE_TYPE

    ref = Document()
    ref.styles.add_style("First Paragraph", WD_STYLE_TYPE.PARAGRAPH)
    ref_path = tmp_path / "reference.docx"
    ref.save(ref_path)

    built = Document()  # no "First Paragraph" style defined
    built_path = tmp_path / "built.docx"
    built.save(built_path)

    code, out, err = run("docx_style_check.py", "--built", str(built_path),
                          "--reference", str(ref_path))
    data = json.loads(out)
    assert code == 2, err
    assert any(m["style"] == "First Paragraph" for m in data["mismatches"]), data
