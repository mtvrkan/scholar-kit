"""Regression tests for the twenty-eighth independent review (round 12):

Hook layer
  * patch_hook_interpreter.py's --target now also requires the basename to
    look like a python/python3/py interpreter (in addition to the pre-existing
    shell-metacharacter check) — closes a critical gap where the already-
    allowed "Bash(python scripts/*)" permission let --target repoint every
    hook's interpreter to an arbitrary binary (e.g. C:\\temp\\evil.exe), since
    the old check only validated character safety, not that the target was
    plausibly Python.
  * agent_write_scope.py's PROJECT_ROOT is now Path.cwd() instead of a path
    derived from the hook file's own on-disk location, matching the cwd
    convention phase_gate.py already relies on. This closes the anchored=False
    fallback's subsequence-match bypass: an absolute, genuinely out-of-project
    path (e.g. C:\\Users\\Public\\build\\evil.dll) is now denied outright
    instead of matching "build/" scope just because that component name
    appears somewhere in the path.

Script layer
  * evidence_db.py: a named-but-nonexistent --registry now dies loudly
    instead of silently skipping the Invariant 1 source cross-check (matches
    the die()-on-named-but-absent-file pattern already used elsewhere).
  * doi2bib.py: the DOI is now percent-encoded before being spliced into the
    doi.org request URL, so a DOI containing #/?/& (legal in some real-world
    suffixes) can't get silently truncated/misrouted by the HTTP client.
  * registry_db.py: DOI dedup now normalizes via clean_doi() before
    comparing, so a bare DOI and a doi.org-URL-prefixed DOI for the same
    paper are recognized as duplicates.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))
import registry_db  # noqa: E402


def _run_script(script, *args, cwd):
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=cwd,
                       capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout or "", p.stderr or ""


def _run_hook(hook, payload, cwd):
    proc = subprocess.run([sys.executable, str(HOOKS / hook)],
                          input=json.dumps(payload), cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8")
    return proc


# ---------- patch_hook_interpreter.py: --target must look like a python interpreter ----------

def test_patch_hook_interpreter_rejects_arbitrary_binary_name(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    c, o, e = _run_script("patch_hook_interpreter.py", "--target", r"C:\temp\evil.exe",
                          "--settings", "settings.json", cwd=tmp_path)
    assert c == 1 and "ERROR" in e


def test_patch_hook_interpreter_rejects_arbitrary_bare_name(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    c, o, e = _run_script("patch_hook_interpreter.py", "--target", "evil",
                          "--settings", "settings.json", cwd=tmp_path)
    assert c == 1 and "ERROR" in e


@pytest.mark.parametrize("target", [
    "python", "python3", "py", "python3.11", "/usr/bin/python3", r"C:\Python311\python.exe",
])
def test_patch_hook_interpreter_still_accepts_real_interpreter_tokens(tmp_path, target):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [
        {"hooks": [{"type": "command", "command": "python3 x.py"}]}]}}), encoding="utf-8")
    c, o, e = _run_script("patch_hook_interpreter.py", "--target", target,
                          "--settings", "settings.json", cwd=tmp_path)
    assert c == 0, (target, e)


# ---------- agent_write_scope.py: out-of-project absolute path must be denied, not subsequence-matched ----------

def test_out_of_project_absolute_path_denied_not_subsequence_matched(tmp_path):
    # A path with "build" as a component, but nowhere under this hook
    # invocation's project root (tmp_path) -- must be denied, not matched
    # via the old subsequence fallback.
    outside = tmp_path.parent / "elsewhere" / "build" / "evil.dll"
    payload = {"agent_type": "format-engineer", "tool_name": "Write",
               "tool_input": {"file_path": str(outside)}}
    proc = _run_hook("agent_write_scope.py", payload, tmp_path)
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_in_project_absolute_path_still_allowed(tmp_path):
    payload = {"agent_type": "format-engineer", "tool_name": "Write",
               "tool_input": {"file_path": str(tmp_path / "build" / "paper.pdf")}}
    proc = _run_hook("agent_write_scope.py", payload, tmp_path)
    assert proc.stdout.strip() == ""


# ---------- evidence_db.py: named-but-absent --registry must die loudly ----------

def test_evidence_db_add_named_missing_registry_dies(tmp_path):
    cards = tmp_path / "cards.jsonl"
    cards.write_text("", encoding="utf-8")
    c, o, e = _run_script("evidence_db.py", "--file", str(cards), "--registry", "nope.jsonl",
                          "add", "--json",
                          json.dumps({"source": "kaya2023x", "type": "finding", "claim": "x"}),
                          cwd=tmp_path)
    assert c == 1 and "ERROR" in e and "registry" in e.lower()


def test_evidence_db_add_default_missing_registry_still_skips_gracefully(tmp_path):
    # No --registry passed at all, and the default sources/registry.jsonl
    # doesn't exist in this tmp project -- must still work (unit-testing in
    # isolation / a project not yet using the registry pipeline), unlike the
    # explicitly-named case above.
    cards = tmp_path / "cards.jsonl"
    cards.write_text("", encoding="utf-8")
    c, o, e = _run_script("evidence_db.py", "--file", str(cards), "add", "--json",
                          json.dumps({"source": "kaya2023x", "type": "finding", "claim": "x"}),
                          cwd=tmp_path)
    assert c == 0, e


# ---------- doi2bib.py: DOI URL-encoding ----------

def test_doi_url_percent_encodes_structural_characters():
    sys.path.insert(0, str(SCRIPTS))
    import doi2bib
    url = doi2bib._doi_url("10.1234/x#y")
    assert url == "https://doi.org/10.1234/x%23y"


def test_doi_url_preserves_slash():
    sys.path.insert(0, str(SCRIPTS))
    import doi2bib
    assert doi2bib._doi_url("10.1234/y") == "https://doi.org/10.1234/y"


# ---------- registry_db.py: DOI dedup normalization ----------

def test_registry_dedup_recognizes_doi_url_prefixed_duplicate():
    existing = [{"id": "SRC-0001", "doi": "10.1234/abc"}]
    rec = {"doi": "https://doi.org/10.1234/ABC"}
    assert registry_db.is_duplicate(rec, existing) == "SRC-0001"


def test_registry_dedup_distinct_dois_not_flagged():
    existing = [{"id": "SRC-0001", "doi": "10.1234/abc"}]
    rec = {"doi": "10.1234/xyz"}
    assert registry_db.is_duplicate(rec, existing) is None
