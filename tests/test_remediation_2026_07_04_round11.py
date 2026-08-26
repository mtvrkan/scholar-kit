"""Regression tests for the twenty-seventh independent review (round 11):

Hook layer — _shell_write_sink.py
  * _unwrap() gained PowerShell's `& {...}` call operator, Invoke-Expression/
    iex (direct and piped forms), and cmd.exe's `/c` flag.
  * shutil.rmtree() is now a recognized delete-sink (whole-directory deletion).
  * _tokens() strips stray backticks left by an unresolved command-substitution
    wrapper (`` rm `echo path` ``) so the basename match isn't defeated by a
    trailing backtick character.
  * strip_heredocs() moved from phase_gate.py into the shared module so
    protect_data_files.py and agent_write_scope.py get the same heredoc-body
    exemption phase_gate.py already had (an asymmetry: a heredoc body merely
    documenting a write-sink pattern was denied by protect_data_files.py even
    though nothing was actually written).
  * protect_data_files.py's _protected_name() now fnmatch-checks a wildcard/
    glob target (`mv sources/*.jsonl dest`) against the protected-filename set.

Script layer
  * evidence_db.py conflicts: a string conflicts_with field (instead of a
    list) no longer iterates character-by-character into bogus pairs.
  * lib_common.parse_json_or_jsonl: a pathologically deep JSON payload no
    longer crashes with a raw RecursionError.
  * word_budget.py: a decimal-looking budget value ("12,000.50", "12000.5")
    is now rejected instead of silently mis-parsed 100x too large.
  * xlsx_export.py: registry authors-as-list-of-dicts, title-as-list, a card
    claim-as-list, and tags-as-list-of-dicts no longer crash the export.
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
import protect_data_files as pdf  # noqa: E402

R = "registry.jsonl"


def _hit(cmd):
    return any(R in t for t in write_targets(cmd))


def _run(script, *args, cwd, stdin=None):
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=cwd, input=stdin,
                       capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout or "", p.stderr or ""


def _clean_err(c, o, e):
    return c == 1 and "ERROR" in (o + e) and "Traceback" not in e


# ---------- _unwrap: new wrapper forms ----------

@pytest.mark.parametrize("cmd", [
    'powershell -Command "& {Remove-Item sources/' + R + '}"',
    "iex 'Remove-Item sources/" + R + "'",
    "Invoke-Expression 'Remove-Item sources/" + R + "'",
    "'Remove-Item sources/" + R + "' | iex",
    'cmd /c "del sources\\' + R + '"',
])
def test_new_wrapper_forms_caught(cmd):
    assert _hit(cmd), cmd


def test_two_level_nesting_still_caught():
    assert _hit("bash -c \"sh -c 'rm sources/" + R + "'\"")


def test_env_and_exec_prefixed_wrappers_still_caught():
    assert _hit("env python3 -c \"import os; os.remove('sources/" + R + "')\"")
    assert _hit("exec bash -c \"rm sources/" + R + "\"")


# ---------- shutil.rmtree ----------

def test_shutil_rmtree_detected():
    targets = write_targets("python3 -c \"import shutil; shutil.rmtree('sources')\"")
    assert "sources" in targets


# ---------- backtick command-substitution token cleanup ----------

def test_backtick_wrapped_target_basename_matches():
    assert _hit("bash -c \"rm \\`echo sources/" + R + "\\`\"")


# ---------- shared heredoc stripping (protect_data_files / agent_write_scope) ----------

def test_protect_data_files_heredoc_body_mention_not_denied():
    heredoc_prose = ("cat <<'EOF' >> notes.py\n"
                     "# example: New-Item sources/" + R + " -Force\n"
                     "EOF")
    assert not _hit(heredoc_prose)


def test_write_targets_heredoc_real_redirect_still_seen():
    heredoc_real = "cat <<'EOF' > drafts/intro.md\nsome body text\nEOF"
    assert any("drafts/intro.md" in t for t in write_targets(heredoc_real))


# ---------- wildcard/glob protected-filename matching ----------

@pytest.mark.parametrize("pattern,want", [
    ("sources/*.jsonl", True),
    ("sources/registry.jsonl", True),
    ("sources/*.txt", False),
])
def test_protect_data_files_wildcard_match(pattern, want):
    assert (pdf._protected_name(pattern) is not None) == want


# ---------- round-10 fixes still hold (no re-regression) ----------

@pytest.mark.parametrize("cmd", [
    'git commit -m "mv ' + R + ' handling refactor"',
    "python3 -c \"print('cp " + R + " backup.jsonl')\"",
])
def test_round10_prose_fix_still_holds(cmd):
    assert write_targets(cmd) == [], cmd


def test_reads_still_not_flagged():
    assert not _hit("cat sources/" + R)
    assert not _hit("wc -l scripts/latex_build.sh")


# ---------- evidence_db.py conflicts: string conflicts_with ----------

def test_evidence_db_conflicts_string_field_no_crash(tmp_path):
    cards = tmp_path / "cards.jsonl"
    cards.write_text(
        json.dumps({"id": "EV-0001", "source": "s", "type": "finding", "claim": "x",
                   "conflicts_with": "EV-0002"}) + "\n"
        + json.dumps({"id": "EV-0002", "source": "s2", "type": "finding", "claim": "y"}) + "\n",
        encoding="utf-8")
    c, o, e = _run("evidence_db.py", "--file", str(cards), "conflicts", cwd=tmp_path)
    assert c == 0 and json.loads(o) == []


def test_evidence_db_conflicts_real_list_still_works(tmp_path):
    cards = tmp_path / "cards.jsonl"
    cards.write_text(
        json.dumps({"id": "EV-0001", "source": "s", "type": "finding", "claim": "x",
                   "conflicts_with": ["EV-0002"]}) + "\n"
        + json.dumps({"id": "EV-0002", "source": "s2", "type": "finding", "claim": "y"}) + "\n",
        encoding="utf-8")
    c, o, e = _run("evidence_db.py", "--file", str(cards), "conflicts", cwd=tmp_path)
    pairs = json.loads(o)
    assert c == 0 and len(pairs) == 1


# ---------- lib_common.parse_json_or_jsonl: RecursionError guard ----------

def _deeply_nested_json():
    return "[" * 5000 + "1" + "]" * 5000


def test_registry_db_add_deeply_nested_json_clean_error(tmp_path):
    reg = tmp_path / "reg.jsonl"
    reg.write_text("", encoding="utf-8")
    c, o, e = _run("registry_db.py", "--file", str(reg), "add", "--stdin",
                   cwd=tmp_path, stdin=_deeply_nested_json())
    assert _clean_err(c, o, e)


def test_evidence_db_add_deeply_nested_json_clean_error(tmp_path):
    cards = tmp_path / "cards.jsonl"
    cards.write_text("", encoding="utf-8")
    c, o, e = _run("evidence_db.py", "--file", str(cards), "add", "--stdin",
                   cwd=tmp_path, stdin=_deeply_nested_json())
    assert _clean_err(c, o, e)


# ---------- word_budget.py: decimal rejection ----------

def _project(tmp_path, budget_line):
    (tmp_path / "drafts").mkdir(exist_ok=True)
    p = tmp_path / "PROJECT.md"
    p.write_text(budget_line + "\n**Type:** imrad\n", encoding="utf-8")
    return p


@pytest.mark.parametrize("line", [
    "Word budget (total): 12,000.50",
    "Word budget (total): 12000.5",
])
def test_word_budget_decimal_value_clean_error(tmp_path, line):
    p = _project(tmp_path, line)
    c, o, e = _run("word_budget.py", "--project", str(p), "--drafts", str(tmp_path / "drafts"), cwd=tmp_path)
    assert _clean_err(c, o, e)


@pytest.mark.parametrize("line,expected", [
    ("Word budget (total): 12,000", 12000),
    ("Word budget (total): 12.000", 12000),  # 3-digit suffix -> European grouping, not a decimal
])
def test_word_budget_grouping_still_accepted(tmp_path, line, expected):
    p = _project(tmp_path, line)
    c, o, e = _run("word_budget.py", "--project", str(p), "--drafts", str(tmp_path / "drafts"), cwd=tmp_path)
    assert c == 0 and json.loads(o)["budget_total"] == expected


# ---------- xlsx_export.py: wrong-shaped title/authors/claim/tags ----------

def test_xlsx_export_wrong_shape_fields_no_crash(tmp_path):
    pytest.importorskip("openpyxl")
    reg = tmp_path / "reg.jsonl"
    reg.write_text(json.dumps({
        "id": "SRC-0001", "title": ["weird", "list", "title"],
        "authors": [{"family": "Kaya"}, {"family": "Demir"}],
        "status": "included", "bib_key": "kaya2023x",
    }) + "\n", encoding="utf-8")
    cards = tmp_path / "cards.jsonl"
    cards.write_text(json.dumps({
        "id": "EV-0001", "source": "kaya2023x", "type": "method",
        "claim": ["weird", "claim", "list"],
        "tags": [{"weird": "tag"}, "normal-tag"],
    }) + "\n", encoding="utf-8")
    c, o, e = _run("xlsx_export.py", "--out", "o.xlsx", "--registry", str(reg),
                   "--cards", str(cards), "--sheet", "all", cwd=tmp_path)
    assert "Traceback" not in e


def test_xlsx_export_normal_shapes_still_work(tmp_path):
    pytest.importorskip("openpyxl")
    reg = tmp_path / "reg.jsonl"
    reg.write_text(json.dumps({
        "id": "SRC-0001", "title": "A Real Title", "authors": ["Kaya, A.", "Demir, C."],
        "status": "included", "bib_key": "kaya2023x",
    }) + "\n", encoding="utf-8")
    cards = tmp_path / "cards.jsonl"
    cards.write_text(json.dumps({
        "id": "EV-0001", "source": "kaya2023x", "type": "method", "claim": "a real claim",
        "tags": ["rq1"],
    }) + "\n", encoding="utf-8")
    c, o, e = _run("xlsx_export.py", "--out", "o.xlsx", "--registry", str(reg),
                   "--cards", str(cards), "--sheet", "all", cwd=tmp_path)
    assert c == 0 and "written" in o
