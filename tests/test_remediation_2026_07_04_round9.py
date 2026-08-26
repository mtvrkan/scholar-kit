"""Regression tests for the twenty-fifth independent review (round 9):

Hook layer
  * _shell_write_sink.py: nested-shell wrappers (bash -c / sh -c / powershell
    -Command / python -c os.system) that put the real command right after a
    quote used to defeat every hook at once; perl -pi / sed -ni in-place edits
    weren't recognized (no literal "-i").
  * phase_gate.py / template_supremacy_gate.py: build-script name matching was
    case-sensitive, so `bash scripts/LATEX_BUILD.SH` / `DOCX_BUILD.SH` skipped
    the gate on a case-insensitive filesystem; a heredoc body mentioning a
    build command was mis-read as an invocation (false-positive deny).
  * agent_write_scope.py: contiguous-subsequence containment let a nested
    lookalike (sources/analysis/, evidence/templates/ingested/) escape scope.

Script layer
  * make_reference_docx.py --size <=2 / directory --out; xlsx_export.py wrong-
    shape records; patch_hook_interpreter.py non-dict/non-UTF8/versioned;
    skill_routing_eval.py non-array; word_budget.py partial-number truncation;
    prisma_flow.py negative counts; cite_audit.py wrong path false-pass;
    doi2bib.py --verify empty bib false-PASS; registry_db.py set-field
    validation; venue_check.py caching a transient network error.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(SCRIPTS))
from _shell_write_sink import write_targets  # noqa: E402
import phase_gate  # noqa: E402
import template_supremacy_gate as tsg  # noqa: E402
import agent_write_scope as aws  # noqa: E402


def _run(script, *args, cwd, stdin=None, flag_S=False):
    cmd = [sys.executable] + (["-S"] if flag_S else []) + [str(SCRIPTS / script), *args]
    p = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout or "", p.stderr or ""


def _clean_err(code, out, err):
    return code == 1 and "ERROR" in (out + err) and "Traceback" not in err


# ---------- _shell_write_sink: nested-shell wrappers ----------

@pytest.mark.parametrize("cmd", [
    'bash -c "cp sources/registry.jsonl /tmp/out.bak"',
    "sh -c 'rm sources/registry.jsonl'",
    'powershell -Command "Remove-Item sources/registry.jsonl"',
    'powershell -Command "Set-Content -Path sources/registry.jsonl -Value data"',
    "python3 -c \"import os; os.system('cp sources/registry.jsonl x')\"",
])
def test_nested_shell_wrapper_detected(cmd):
    assert any("registry.jsonl" in t for t in write_targets(cmd)), cmd


def test_reads_not_falsely_flagged_after_wrapper_fix():
    # broadening the command-position anchor must not make an ordinary read
    # name the protected file as a write target
    for cmd in ("cat sources/registry.jsonl", "wc -l scripts/latex_build.sh"):
        assert not any("registry.jsonl" in t for t in write_targets(cmd)), cmd


# ---------- _shell_write_sink: perl -pi / sed -ni ----------

def test_perl_pi_inplace_detected():
    assert "sources/registry.jsonl" in write_targets('perl -pi -e "s/x/y/" sources/registry.jsonl')


def test_sed_ni_inplace_detected():
    assert "sources/registry.jsonl" in write_targets('sed -ni "1p" sources/registry.jsonl')


def test_sed_non_inplace_not_flagged():
    # -e alone has no 'i' in the flag cluster — not an in-place edit
    assert write_targets('sed -e "s/a/b/" file.txt') == []


# ---------- phase_gate: case-insensitive build script + heredoc ----------

@pytest.mark.parametrize("cmd", [
    "bash scripts/LATEX_BUILD.SH build/thesis.pdf",
    "./scripts/DOCX_BUILD.SH out.docx",
])
def test_phase_gate_build_script_case_insensitive(cmd):
    assert phase_gate._invokes_build_script(cmd) is True


@pytest.mark.parametrize("cmd", [
    "python scripts/xlsx_export.py --out exports/x.xlsx",
    "python3.11 scripts/xlsx_export.py --out exports/x.xlsx",
    "py.exe scripts/make_reference_docx.py --out templates/paper/reference.docx",
])
def test_phase_gate_literature_and_setup_scripts_not_build_gated(cmd):
    # C1 regression: xlsx_export.py (literature/synthesis matrix) and
    # make_reference_docx.py (reference-doc style template, /ingest-template
    # setup) run BEFORE citation verification exists — they must NOT be gated
    # behind verify=PASS + Major=0 like the manuscript builders are.
    assert phase_gate._invokes_build_script(cmd) is False


def test_phase_gate_lowercase_build_script_still_gated():
    assert phase_gate._invokes_build_script("bash scripts/latex_build.sh build/x.pdf") is True


def test_phase_gate_heredoc_body_mention_not_gated():
    heredoc = ("cat <<'EOF' > sources/scratch_note.txt\n"
               "bash scripts/latex_build.sh output.pdf\n"
               "EOF")
    assert phase_gate._invokes_build_script(heredoc) is False


def test_phase_gate_heredoc_redirect_target_still_seen():
    # the OPENING line's redirect target must survive heredoc stripping.
    # strip_heredocs moved to _shell_write_sink.py (shared by protect_data_files.py
    # and agent_write_scope.py too, not just phase_gate.py) — write_targets()
    # applies it internally, so no explicit pre-stripping call is needed here.
    heredoc = "cat <<'EOF' > drafts/intro.md\nsome body text\nEOF"
    assert "drafts/intro.md" in phase_gate.write_targets(heredoc)


# ---------- template_supremacy: case-insensitive ----------

def test_template_supremacy_docx_build_case_insensitive():
    args = tsg._build_script_args(
        "bash scripts/DOCX_BUILD.SH out.docx style.csl ref.docx sec.md", "docx_build.sh")
    assert args == ["out.docx", "style.csl", "ref.docx", "sec.md"]


# ---------- agent_write_scope: containment escape ----------

@pytest.mark.parametrize("agent,path", [
    ("format-engineer", "evidence/templates/ingested/evil.md"),
    ("format-engineer", "sources/build/evil.tex"),
    ("data-scientist", "sources/analysis/evil.md"),
    ("source-analyst", "sources/evidence/extracts/evil.json"),
])
def test_agent_write_scope_nested_lookalike_denied(agent, path):
    assert aws._in_scope(path, aws.AGENT_SCOPES[agent]) is False


@pytest.mark.parametrize("agent,path", [
    ("format-engineer", "build/paper.pdf"),
    ("format-engineer", "templates/ingested/reference.docx"),
    ("data-scientist", "analysis/01_eda.py"),
    ("source-analyst", "evidence/extracts/smith2024.json"),
])
def test_agent_write_scope_genuine_in_scope_allowed(agent, path):
    assert aws._in_scope(path, aws.AGENT_SCOPES[agent]) is True


def test_agent_write_scope_absolute_under_root_relativized():
    # an absolute path under the real project root is anchored via its
    # project-relative form
    abs_escape = str((ROOT / "sources" / "analysis" / "evil.md"))
    assert aws._in_scope(abs_escape, aws.AGENT_SCOPES["data-scientist"]) is False
    abs_ok = str((ROOT / "analysis" / "ok.py"))
    assert aws._in_scope(abs_ok, aws.AGENT_SCOPES["data-scientist"]) is True


# ---------- make_reference_docx.py ----------

@pytest.mark.parametrize("size", ["0", "1", "2", "-3"])
def test_make_reference_docx_bad_size_clean_error(tmp_path, size):
    pytest.importorskip("docx")
    c, o, e = _run("make_reference_docx.py", "--out", "ref.docx", "--size", size, cwd=tmp_path)
    assert _clean_err(c, o, e), (c, e[:200])


def test_make_reference_docx_dir_out_clean_error(tmp_path):
    pytest.importorskip("docx")
    (tmp_path / "adir").mkdir()
    c, o, e = _run("make_reference_docx.py", "--out", "adir", cwd=tmp_path)
    assert _clean_err(c, o, e) and "directory" in (o + e)


def test_make_reference_docx_valid_size_succeeds(tmp_path):
    pytest.importorskip("docx")
    c, o, e = _run("make_reference_docx.py", "--out", "ref.docx", "--size", "12", cwd=tmp_path)
    assert c == 0 and "written" in o


# ---------- xlsx_export.py wrong-shape records ----------

def _reg(tmp_path):
    p = tmp_path / "reg.jsonl"
    p.write_text(json.dumps({"id": "SRC-0001", "title": "t", "status": "included"}) + "\n", encoding="utf-8")
    return p


def test_xlsx_export_tags_non_list_no_crash(tmp_path):
    pytest.importorskip("openpyxl")
    cards = tmp_path / "cards.jsonl"
    cards.write_text(json.dumps({"id": "EV-0001", "source": "src1", "tags": 5}) + "\n", encoding="utf-8")
    c, o, e = _run("xlsx_export.py", "--out", "o.xlsx", "--registry", str(_reg(tmp_path)),
                   "--cards", str(cards), "--sheet", "matrix", cwd=tmp_path)
    assert "Traceback" not in e


def test_xlsx_export_metrics_non_dict_no_crash(tmp_path):
    pytest.importorskip("openpyxl")
    cards = tmp_path / "cards.jsonl"
    cards.write_text(json.dumps({"id": "EV-0001", "source": "SRC-0001", "type": "method",
                                 "claim": "x", "metrics": ["a", "b"]}) + "\n", encoding="utf-8")
    c, o, e = _run("xlsx_export.py", "--out", "o.xlsx", "--registry", str(_reg(tmp_path)),
                   "--cards", str(cards), "--sheet", "extraction", cwd=tmp_path)
    assert "Traceback" not in e


def test_xlsx_export_bare_array_record_clean_error(tmp_path):
    pytest.importorskip("openpyxl")
    reg = tmp_path / "reg.jsonl"
    reg.write_text(json.dumps(["just", "an", "array"]) + "\n"
                   + json.dumps({"id": "SRC-0002", "title": "t2", "status": "included"}) + "\n",
                   encoding="utf-8")
    c, o, e = _run("xlsx_export.py", "--out", "o.xlsx", "--registry", str(reg), cwd=tmp_path)
    assert _clean_err(c, o, e)


# ---------- patch_hook_interpreter.py ----------

def test_patch_hook_interpreter_top_level_array_clean_error(tmp_path):
    st = tmp_path / "settings.json"
    st.write_text("[1,2,3]", encoding="utf-8")
    c, o, e = _run("patch_hook_interpreter.py", "--target", "python", "--settings", str(st), cwd=tmp_path)
    assert _clean_err(c, o, e)


def test_patch_hook_interpreter_non_utf8_clean_error(tmp_path):
    st = tmp_path / "settings.json"
    st.write_bytes(b"\xff\xfe{bad}")
    c, o, e = _run("patch_hook_interpreter.py", "--target", "python", "--settings", str(st), cwd=tmp_path)
    assert _clean_err(c, o, e)


def test_patch_hook_interpreter_versioned_interpreter_rewritten(tmp_path):
    st = tmp_path / "settings.json"
    st.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [
        {"command": "python3.11 .claude/hooks/x.py"}]}]}}), encoding="utf-8")
    c, o, e = _run("patch_hook_interpreter.py", "--target", "python", "--settings", str(st), cwd=tmp_path)
    cmd = json.loads(st.read_text(encoding="utf-8"))["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert c == 0 and cmd == "python .claude/hooks/x.py"


# ---------- skill_routing_eval.py ----------

def test_skill_routing_eval_object_not_array_clean_error(tmp_path):
    p = tmp_path / "prompts.json"
    p.write_text('{"prompt": "x", "expect": "draft"}', encoding="utf-8")
    c, o, e = _run("skill_routing_eval.py", "--prompts", str(p), cwd=tmp_path)
    assert _clean_err(c, o, e)


# ---------- word_budget.py ----------

def _project(tmp_path, budget_line):
    (tmp_path / "drafts").mkdir(exist_ok=True)
    p = tmp_path / "PROJECT.md"
    p.write_text(budget_line + "\n**Type:** imrad\n", encoding="utf-8")
    return p


@pytest.mark.parametrize("line", [
    "Word budget (total): 12x34",   # partial number — was silently truncated to 12
    "Word budget (total): -5000",   # negative — matched nothing, silently fell back to null
    "Word budget (total): abcXYZ",  # pure garbage
])
def test_word_budget_malformed_value_clean_error(tmp_path, line):
    p = _project(tmp_path, line)
    c, o, e = _run("word_budget.py", "--project", str(p), "--drafts", str(tmp_path / "drafts"), cwd=tmp_path)
    assert _clean_err(c, o, e)


def test_word_budget_valid_value_succeeds(tmp_path):
    p = _project(tmp_path, "Word budget (total): 12,000")
    c, o, e = _run("word_budget.py", "--project", str(p), "--drafts", str(tmp_path / "drafts"), cwd=tmp_path)
    assert c == 0 and json.loads(o)["budget_total"] == 12000


def test_word_budget_absent_line_is_null_not_error(tmp_path):
    (tmp_path / "drafts").mkdir()
    p = tmp_path / "PROJECT.md"
    p.write_text("**Type:** imrad\n", encoding="utf-8")
    c, o, e = _run("word_budget.py", "--project", str(p), "--drafts", str(tmp_path / "drafts"), cwd=tmp_path)
    assert c == 0 and json.loads(o)["budget_total"] is None


# ---------- prisma_flow.py ----------

def test_prisma_flow_negative_counts_clean_error(tmp_path):
    counts = json.dumps({"identified": -5, "duplicates": 0, "screened": -5, "excluded_screening": 0,
                         "fulltext": -5, "excluded_fulltext": 0, "included": -5})
    c, o, e = _run("prisma_flow.py", "--counts", counts, "--out-dir", str(tmp_path), cwd=tmp_path)
    assert _clean_err(c, o, e)


# ---------- cite_audit.py wrong-path false-pass ----------

def test_cite_audit_missing_file_clean_error(tmp_path):
    c, o, e = _run("cite_audit.py", "--file", "nope.md", "--bib", "x.bib", cwd=tmp_path)
    assert _clean_err(c, o, e)


def test_cite_audit_drafts_is_a_file_clean_error(tmp_path):
    f = tmp_path / "afile.md"
    f.write_text("x", encoding="utf-8")
    c, o, e = _run("cite_audit.py", "--drafts", str(f), "--bib", "x.bib", cwd=tmp_path)
    assert _clean_err(c, o, e)


# ---------- doi2bib.py --verify empty bib ----------

def test_doi2bib_verify_empty_bib_not_pass(tmp_path):
    pytest.importorskip("requests")
    bib = tmp_path / "empty.bib"
    bib.write_text("", encoding="utf-8")
    c, o, e = _run("doi2bib.py", "--verify", "--bib", str(bib), cwd=tmp_path)
    assert _clean_err(c, o, e) and "PASS" not in o


# ---------- registry_db.py set-field validation ----------

def _registry(tmp_path):
    p = tmp_path / "sources" / "registry.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"id": "SRC-0001", "title": "t", "bib_key": "kaya2023x"}) + "\n"
                 + json.dumps({"id": "SRC-0002", "title": "t2"}) + "\n", encoding="utf-8")
    return p


def test_registry_set_field_bad_year_clean_error(tmp_path):
    p = _registry(tmp_path)
    c, o, e = _run("registry_db.py", "--file", str(p), "set-field", "SRC-0002", "year", "not-a-year", cwd=tmp_path)
    assert _clean_err(c, o, e)


def test_registry_set_field_duplicate_bib_key_clean_error(tmp_path):
    p = _registry(tmp_path)
    c, o, e = _run("registry_db.py", "--file", str(p), "set-field", "SRC-0002", "bib_key", "kaya2023x", cwd=tmp_path)
    assert _clean_err(c, o, e)


def test_registry_set_field_valid_year_succeeds(tmp_path):
    p = _registry(tmp_path)
    c, o, e = _run("registry_db.py", "--file", str(p), "set-field", "SRC-0002", "year", "2022", cwd=tmp_path)
    assert c == 0 and "updated" in o


# ---------- venue_check.py: transient network error must not be cached ----------

def test_venue_check_network_error_not_cached(tmp_path, monkeypatch, capsys):
    import venue_check
    monkeypatch.chdir(tmp_path)
    (tmp_path / "sources").mkdir()
    cache = tmp_path / "sources" / "venues.jsonl"
    # a truthy stand-in so main() doesn't die on `requests is None`
    monkeypatch.setattr(venue_check, "requests", object())
    monkeypatch.setattr(venue_check, "lookup_local", lambda issn, title: {})
    monkeypatch.setattr(venue_check, "lookup_openalex",
                        lambda issn, title: {"openalex_error": "ProxyError: connection refused"})
    monkeypatch.setattr(sys, "argv", ["venue_check.py", "--issn", "0888-3270", "--cache", "sources/venues.jsonl"])
    venue_check.main()
    out = json.loads(capsys.readouterr().out)
    assert "openalex_error" in out
    assert out.get("cache", "").startswith("not-cached")
    # nothing persisted -> a later successful lookup can't be poisoned by it
    assert not cache.exists() or cache.read_text(encoding="utf-8").strip() == ""
