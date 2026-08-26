"""Regression tests for the twenty-sixth independent review (round 10):

Hook layer — _shell_write_sink.py
  * The prior round's broadened command-position anchor (accepting a command
    token right after a quote/paren) over-blocked ordinary prose (git commit
    -m "...mv...", echo "move ...", a Python string literal containing "cp ...").
    Reverted to the narrow anchor + _unwrap(): nested-shell wrappers (bash -c,
    sh -c, powershell -Command, python -c "...os.system('...')") are now handled
    by extracting and re-scanning the inner command, not by widening the anchor.
  * New write/delete APIs the module previously missed are now covered:
    os.open (write flags), Path.replace/.rename, open('r+'), Clear-Content,
    .NET WriteAll*/AppendAll*, `>|` noclobber redirect, dd of=, truncate,
    fileinput.input(inplace=True).

Script layer
  * read_jsonl() validated JSON syntax but not object SHAPE, so a bare
    array/scalar line crashed the first consumer (.get() AttributeError) —
    evidence_db, registry_db, prisma_flow. Now rejected at the source.
  * skill_routing_eval per-element object check; xlsx_export non-object extract
    treated as malformed (skip+warn); registry_db log-query negative --hits.
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

R = "registry.jsonl"


def _hit(cmd):
    return any(R in t for t in write_targets(cmd))


def _run(script, *args, cwd):
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=cwd,
                       capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout or "", p.stderr or ""


def _clean_err(c, o, e):
    return c == 1 and "ERROR" in (o + e) and "Traceback" not in e


# ---------- nested-shell wrappers STILL caught (via _unwrap, narrow anchor) ----------

@pytest.mark.parametrize("cmd", [
    'bash -c "cp sources/' + R + ' /tmp/out.bak"',
    "sh -c 'rm sources/" + R + "'",
    'powershell -Command "Remove-Item sources/' + R + '"',
    'powershell -Command "Set-Content -Path sources/' + R + ' -Value data"',
    "python3 -c \"import os; os.system('cp sources/" + R + " x')\"",
    "python3 -c \"import subprocess; subprocess.run('rm sources/" + R + "')\"",
])
def test_nested_wrapper_still_caught(cmd):
    assert _hit(cmd), cmd


# ---------- over-block regressions from the prior round are FIXED ----------

@pytest.mark.parametrize("cmd", [
    'git commit -m "mv ' + R + ' handling refactor"',
    'echo "move sources/' + R + ' to backup"',
    "python3 -c \"print('cp " + R + " backup.jsonl')\"",
    'python3 -c "x=\'cp draft.pdf build/out.pdf\'"',
])
def test_prose_no_longer_over_blocked(cmd):
    # a command word sitting immediately after a quote is NOT command position
    # anymore — ordinary prose/string-literal mentions must not be flagged
    assert write_targets(cmd) == [], cmd


# ---------- new write/delete APIs now caught ----------

@pytest.mark.parametrize("cmd", [
    "python3 -c \"import os; fd=os.open('sources/" + R + "', os.O_WRONLY|os.O_CREAT|os.O_TRUNC); os.write(fd,b'{}')\"",
    "python3 -c \"import pathlib; pathlib.Path('s.txt').replace('sources/" + R + "')\"",
    "python3 -c \"import pathlib; pathlib.Path('s.txt').rename('sources/" + R + "')\"",
    "python3 -c \"f=open('sources/" + R + "','r+'); f.truncate(0)\"",
    "Clear-Content sources/" + R,
    "pwsh -c \"[System.IO.File]::WriteAllText('sources/" + R + "','{}')\"",
    "echo '{}' >| sources/" + R,
    "dd if=/dev/null of=sources/" + R,
    "truncate -s 0 sources/" + R,
    "python3 -c \"import fileinput,sys;[sys.stdout.write('') for _ in fileinput.input('sources/" + R + "',inplace=True)]\"",
])
def test_new_write_apis_caught(cmd):
    assert _hit(cmd), cmd


def test_os_open_readonly_not_flagged():
    # os.open for reading (no write flag) must not be treated as a write
    assert not _hit("python3 -c \"import os; os.open('sources/" + R + "', os.O_RDONLY)\"")


def test_open_read_mode_not_flagged():
    assert not _hit("python3 -c \"open('sources/" + R + "', 'rb').read()\"")


# ---------- reads still not flagged ----------

@pytest.mark.parametrize("cmd", ["cat sources/" + R, "wc -l scripts/latex_build.sh", "grep -r mv drafts/"])
def test_reads_not_flagged(cmd):
    assert not _hit(cmd)


# ---------- read_jsonl object-shape validation (root cause) ----------

def _jsonl(tmp_path, name, *lines):
    p = tmp_path / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_evidence_db_stats_non_object_line_clean_error(tmp_path):
    f = _jsonl(tmp_path, "cards.jsonl", json.dumps(["a", "b"]), json.dumps({"id": "EV-0001"}))
    assert _clean_err(*_run("evidence_db.py", "--file", str(f), "stats", cwd=tmp_path))


def test_evidence_db_conflicts_non_object_line_clean_error(tmp_path):
    f = _jsonl(tmp_path, "cards.jsonl", json.dumps(["a", "b"]))
    assert _clean_err(*_run("evidence_db.py", "--file", str(f), "conflicts", cwd=tmp_path))


def test_registry_db_stats_non_object_line_clean_error(tmp_path):
    f = _jsonl(tmp_path, "reg.jsonl", '"just a string"')
    assert _clean_err(*_run("registry_db.py", "--file", str(f), "stats", cwd=tmp_path))


def test_registry_db_list_non_object_line_clean_error(tmp_path):
    f = _jsonl(tmp_path, "reg.jsonl", '"just a string"')
    assert _clean_err(*_run("registry_db.py", "--file", str(f), "list", "--status", "included", cwd=tmp_path))


def test_prisma_flow_non_object_registry_clean_error(tmp_path):
    f = _jsonl(tmp_path, "reg.jsonl", '42')
    assert _clean_err(*_run("prisma_flow.py", "--registry", str(f), "--out-dir", str(tmp_path), cwd=tmp_path))


def test_read_jsonl_valid_objects_still_work(tmp_path):
    f = _jsonl(tmp_path, "reg.jsonl", json.dumps({"id": "SRC-0001", "status": "included", "lang": "en"}))
    c, o, e = _run("registry_db.py", "--file", str(f), "stats", cwd=tmp_path)
    assert c == 0 and json.loads(o)["total"] == 1


# ---------- skill_routing_eval per-element object check ----------

def test_skill_routing_eval_non_object_element_clean_error(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps([123, "foo"]), encoding="utf-8")
    assert _clean_err(*_run("skill_routing_eval.py", "--prompts", str(p), cwd=tmp_path))


# ---------- xlsx_export non-object extract -> skip+warn, no crash ----------

def test_xlsx_export_non_object_extract_no_crash(tmp_path):
    pytest.importorskip("openpyxl")
    reg = _jsonl(tmp_path, "reg.jsonl",
                 json.dumps({"id": "SRC-0001", "title": "t", "status": "included", "bib_key": "k"}))
    ext = tmp_path / "extracts"
    ext.mkdir()
    (ext / "k.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    c, o, e = _run("xlsx_export.py", "--out", "o.xlsx", "--registry", str(reg),
                   "--cards", str(tmp_path / "none.jsonl"), "--extracts", str(ext),
                   "--sheet", "slr", cwd=tmp_path)
    assert "Traceback" not in e and c in (0, 1)


# ---------- registry_db log-query negative hits ----------

def test_registry_log_query_negative_hits_clean_error(tmp_path):
    reg = _jsonl(tmp_path, "reg.jsonl", json.dumps({"id": "SRC-0001", "title": "t"}))
    c, o, e = _run("registry_db.py", "--file", str(reg), "log-query", "--db", "scopus",
                   "--query", "x", "--hits", "-5", cwd=tmp_path)
    assert _clean_err(c, o, e)


def test_registry_log_query_valid_hits_still_works(tmp_path):
    reg = _jsonl(tmp_path, "reg.jsonl", json.dumps({"id": "SRC-0001", "title": "t"}))
    c, o, e = _run("registry_db.py", "--file", str(reg), "log-query", "--db", "scopus",
                   "--query", "x", "--hits", "42", cwd=tmp_path)
    assert c == 0 and "logged" in o
