"""Regression tests for the fixes applied after the fourteenth review pass
(D-069): xlsx formula injection, patch_hook_interpreter --target validation,
doi2bib DOI format pre-validation, docx_style_check/xlsx_export/pdf2md path
discipline, and the phase_gate.py Bash write-sink bypass (cp/redirect into
build/exports slipping past the interpreter+script-token allowlist).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import kit_project_cwd

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
HOOKS = ROOT / ".claude" / "hooks"

sys.path.insert(0, str(SCRIPTS))
import lib_common  # noqa: E402


# ---------- xlsx_export.py: formula injection (CWE-1236) ----------

def test_escape_formula_prefixes_dangerous_leading_chars():
    import xlsx_export
    for bad in ("=cmd|'/bin/calc'!A1", "+1+1", "-1+1", "@SUM(A1:A9)", "\t=1"):
        assert xlsx_export._escape_formula(bad).startswith("'")


def test_escape_formula_leaves_ordinary_strings_untouched():
    import xlsx_export
    assert xlsx_export._escape_formula("IEEE Transactions") == "IEEE Transactions"
    assert xlsx_export._escape_formula(None) is None
    assert xlsx_export._escape_formula(2023) == 2023


def test_xlsx_export_screening_sheet_neutralizes_formula_in_title(tmp_path):
    reg = tmp_path / "sources" / "registry.jsonl"
    reg.parent.mkdir(parents=True)
    rec = {"id": "SRC-0001", "title": "=cmd|'/c calc'!A1", "year": 2023,
           "status": "included", "reason": "+HYPERLINK(\"http://evil\")"}
    reg.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    out = tmp_path / "out.xlsx"
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "xlsx_export.py"), "--sheet", "screening",
         "--registry", str(reg), "--out", str(out), "--json"],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    from openpyxl import load_workbook
    wb = load_workbook(out)
    ws = wb["screening"]
    title_cell = ws.cell(row=2, column=2)
    assert title_cell.data_type != "f"  # never stored as a live formula
    assert title_cell.value.startswith("'")


# ---------- patch_hook_interpreter.py: --target validation ----------

def test_patch_hook_interpreter_rejects_shell_metacharacters(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "patch_hook_interpreter.py"),
         "--target", "python; rm -rf /", "--settings", str(settings)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "ERROR" in proc.stderr


def test_patch_hook_interpreter_accepts_plain_interpreter_tokens(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [
        {"hooks": [{"type": "command", "command": "python3 x.py"}]}]}}), encoding="utf-8")
    for target in ("python", "python3", "py", "/usr/bin/python3", r"C:\Python311\python.exe"):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "patch_hook_interpreter.py"),
             "--target", target, "--settings", str(settings)],
            cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0, (target, proc.stderr)


# ---------- doi2bib.py: DOI format pre-validation ----------

def test_fetch_bibtex_rejects_malformed_doi_before_network_call(monkeypatch):
    import doi2bib

    def fail_if_called(*a, **k):
        raise AssertionError("network must not be reached for a malformed DOI")

    monkeypatch.setattr(doi2bib.requests, "get", fail_if_called)
    with pytest.raises(SystemExit):
        doi2bib.fetch_bibtex("not-a-doi")


def test_fetch_bibtex_accepts_doi_url_prefix(monkeypatch):
    import doi2bib

    class FakeResp:
        status_code = 200
        text = "@article{x, title={y}}"
        encoding = "utf-8"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(doi2bib.requests, "get", lambda *a, **k: FakeResp())
    bib = doi2bib.fetch_bibtex("https://doi.org/10.1016/j.ymssp.2023.00001")
    assert "@article" in bib


# ---------- docx_style_check.py / xlsx_export.py / pdf2md.py: path discipline ----------

def test_docx_style_check_rejects_reference_outside_cwd(tmp_path):
    built = tmp_path / "built.docx"
    built.write_text("x", encoding="utf-8")
    outside = tmp_path.parent / "outside_ref.docx"
    outside.write_text("x", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "docx_style_check.py"),
         "--built", str(built), "--reference", str(outside)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "--reference" in proc.stderr
    outside.unlink()


def test_xlsx_export_rejects_extracts_dir_outside_cwd(tmp_path):
    reg = tmp_path / "sources" / "registry.jsonl"
    reg.parent.mkdir(parents=True)
    reg.write_text(json.dumps({"id": "SRC-0001", "title": "t", "status": "included"}) + "\n",
                   encoding="utf-8")
    outside = tmp_path.parent / "outside_extracts"
    outside.mkdir(exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "xlsx_export.py"), "--registry", str(reg),
         "--extracts", str(outside), "--out", str(tmp_path / "out.xlsx")],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "--extracts" in proc.stderr


def test_pdf2md_rejects_pdf_dir_outside_cwd(tmp_path):
    outside = tmp_path.parent / "outside_pdfs"
    outside.mkdir(exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "pdf2md.py"), "--all", "--pdf-dir", str(outside)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1
    assert "--pdf-dir" in proc.stderr


# ---------- phase_gate.py: generic write-sink bypass into build/exports ----------

def _write(tmp_path, rel, text):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _run_phase_gate(payload, cwd):
    # phase_gate.py no-ops outside a Scholar-Kit project (build/ and drafts/ are
    # ordinary directory names, and as a plugin the hook runs in every session).
    # These tests exercise the write-sink gate, so the fixture declares one.
    Path(cwd, "PROJECT.md").touch()
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "phase_gate.py")],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    return proc.stdout


def test_bash_cp_into_build_now_gated_without_prior_bypass(tmp_path):
    out = _run_phase_gate({"tool_name": "Bash",
                           "tool_input": {"command": "cp draft.pdf build/final.pdf"}}, tmp_path)
    assert "deny" in out


def test_bash_redirect_into_exports_now_gated(tmp_path):
    out = _run_phase_gate({"tool_name": "Bash",
                           "tool_input": {"command": "cat notes.md > exports/out.md"}}, tmp_path)
    assert "deny" in out


def test_bash_cp_into_build_allowed_once_gates_satisfied(tmp_path):
    # The `live_recheck` block is what scripts/write_verify_status.py actually
    # writes for a corroborated PASS. Without it the gate still OPENS — this
    # test's subject — but attaches the uncorroborated-PASS note (D-092c,
    # asserted in test_phase_gate_hook.py), which would show up here as noise
    # from a mechanism this test is not about.
    _write(tmp_path, "verify-status.json", json.dumps({"result": "PASS", "checked": 1,
                                                        "fabricated": 0, "retracted": 0,
                                                        "missing": 0, "unresolved": 0,
                                                        "live_recheck": {"doi2bib_confirmed": True,
                                                                         "cite_audit_confirmed": True}}))
    _write(tmp_path, "reviews/round-1.md", "## SUMMARY\nMajor issues:    0\n")
    out = _run_phase_gate({"tool_name": "Bash",
                           "tool_input": {"command": "cp draft.pdf build/final.pdf"}}, tmp_path)
    assert out.strip() == ""


def test_bash_cp_into_unrelated_dir_still_not_gated(tmp_path):
    out = _run_phase_gate({"tool_name": "Bash",
                           "tool_input": {"command": "cp report.md docs/report.md"}}, tmp_path)
    assert out.strip() == ""


# ---------- protect_data_files.py: PowerShell / in-place-editor / delete forms ----------

def _run_protect(payload):
    proc = subprocess.run(
        [sys.executable, str(HOOKS / "protect_data_files.py")],
        input=json.dumps(payload), cwd=kit_project_cwd(),
        capture_output=True, text=True, encoding="utf-8")
    return proc.stdout


def test_protect_data_files_blocks_powershell_copy_item():
    out = _run_protect({"tool_name": "Bash", "tool_input": {
        "command": "Copy-Item /tmp/x sources/registry.jsonl"}})
    assert "deny" in out


def test_protect_data_files_blocks_powershell_move_item():
    out = _run_protect({"tool_name": "Bash", "tool_input": {
        "command": "Move-Item sources/registry.jsonl ../out.bak"}})
    assert "deny" in out


def test_protect_data_files_blocks_sed_inplace_edit():
    out = _run_protect({"tool_name": "Bash", "tool_input": {
        "command": "sed -i 's/x/y/' evidence/cards.jsonl"}})
    assert "deny" in out


def test_protect_data_files_blocks_rm_of_protected_file():
    out = _run_protect({"tool_name": "Bash", "tool_input": {
        "command": "rm sources/venues.jsonl"}})
    assert "deny" in out


def test_protect_data_files_blocks_notebookedit_of_protected_file():
    out = _run_protect({"tool_name": "NotebookEdit", "tool_input": {
        "notebook_path": "evidence/cards.jsonl"}})
    assert "deny" in out


# ---------- lib_common.py: dedup'd helpers ----------

def test_parse_json_or_jsonl_handles_single_object():
    assert lib_common.parse_json_or_jsonl('{"a": 1}') == [{"a": 1}]


def test_parse_json_or_jsonl_handles_array():
    assert lib_common.parse_json_or_jsonl('[{"a": 1}, {"a": 2}]') == [{"a": 1}, {"a": 2}]


def test_parse_json_or_jsonl_handles_pretty_printed_single_object():
    raw = json.dumps({"a": 1, "b": 2}, indent=2)
    assert lib_common.parse_json_or_jsonl(raw) == [{"a": 1, "b": 2}]


def test_parse_json_or_jsonl_falls_back_to_jsonl_lines():
    raw = '{"a": 1}\n{"a": 2}\n'
    assert lib_common.parse_json_or_jsonl(raw) == [{"a": 1}, {"a": 2}]


def test_parse_json_or_jsonl_raises_on_garbage():
    with pytest.raises(json.JSONDecodeError):
        lib_common.parse_json_or_jsonl("not json at all {")


def test_http_get_with_retry_retries_transient_errors_then_succeeds(monkeypatch):
    import requests
    calls = []

    def flaky(url, timeout=None, **kwargs):
        calls.append(url)
        if len(calls) < 2:
            raise requests.ConnectionError("transient")
        return "ok"

    monkeypatch.setattr(requests, "get", flaky)
    monkeypatch.setattr(lib_common.time, "sleep", lambda *_: None)
    result = lib_common.http_get_with_retry("https://example.org", retries=3, backoff=0)
    assert result == "ok"
    assert len(calls) == 2


def test_http_get_with_retry_raises_after_exhausting_retries(monkeypatch):
    import requests

    def always_fails(url, timeout=None, **kwargs):
        raise requests.Timeout("still down")

    monkeypatch.setattr(requests, "get", always_fails)
    monkeypatch.setattr(lib_common.time, "sleep", lambda *_: None)
    with pytest.raises(requests.Timeout):
        lib_common.http_get_with_retry("https://example.org", retries=2, backoff=0)
