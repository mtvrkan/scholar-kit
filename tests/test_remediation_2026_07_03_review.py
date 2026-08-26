"""Regression tests for the independent 4-dimension re-review on 2026-07-03
(fresh agents, no access to prior DECISIONS.md entries, verified against
current code only — see DECISIONS.md D-061): a silent-data-loss swallow in
xlsx_export.py, and two writers (pdf2md.py's meta.json, patch_hook_interpreter.py's
settings.json rewrite) that broke the codebase's own LF-only / atomic-write
conventions.
"""
import json

import pytest


# ---------- xlsx_export.py: malformed extract must be visible, not silent ----------

def test_xlsx_export_reports_malformed_extract(run, tmp_path, sample_registry, sample_cards):
    ex_dir = tmp_path / "evidence" / "extracts"
    ex_dir.mkdir(parents=True)
    (ex_dir / "broken.json").write_text("{not valid json", encoding="utf-8")

    code, out, err = run("xlsx_export.py")
    assert code == 0, err
    assert "WARNING" in err and "broken.json" in err
    rep = json.loads(out)
    assert rep["malformed_extracts"] == ["broken.json"]


# ---------- pdf2md.py: meta.json must be LF-only like every other write in the repo ----------

def test_pdf2md_meta_json_is_lf_only(run, tmp_path):
    pymupdf = pytest.importorskip("pymupdf")
    pdf_dir = tmp_path / "sources" / "pdf"
    pdf_dir.mkdir(parents=True)
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf_dir / "x.pdf")
    doc.close()

    code, out, err = run("pdf2md.py", "--pdf", "sources/pdf/x.pdf", "--key", "x")
    assert code == 0, err
    raw = (tmp_path / "sources" / "md" / "x" / "meta.json").read_bytes()
    assert b"\r\n" not in raw


# ---------- patch_hook_interpreter.py: settings.json rewrite must be atomic + LF-only ----------

def test_patch_hook_interpreter_writes_lf_only_no_leftover_tmp(run, tmp_path):
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()
    settings_path = settings_dir / "settings.json"
    settings_path.write_text(json.dumps({
        "hooks": {"PreToolUse": [{"hooks": [{"command": "python3 hooks/foo.py"}]}]}
    }, indent=2) + "\n", encoding="utf-8")

    code, out, err = run("patch_hook_interpreter.py", "--target", "python",
                          "--settings", ".claude/settings.json")
    assert code == 0, err
    rep = json.loads(out)
    assert rep["changed"] is True

    raw = settings_path.read_bytes()
    assert b"\r\n" not in raw
    cfg = json.loads(raw.decode("utf-8"))
    assert cfg["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "python hooks/foo.py"

    leftovers = list(settings_dir.glob("settings.json.tmp*"))
    assert leftovers == []
