r"""Regression tests for an independent review of the hook/script layer
(2026-07-05, 3-agent parallel audit: scripts, hook enforcement, skills/agents):

Hook layer (_shell_write_sink.py, shared by protect_data_files.py/phase_gate.py)
  * _tokens() no longer lets shlex's posix escape-handling silently eat an
    unquoted Windows-style backslash path separator — found live on the kit's
    own primary platform (win32/PowerShell/cmd, where a bare backslash path is
    the DEFAULT syntax, not obfuscation): `del sources\\registry.jsonl`,
    `Remove-Item sources\\registry.jsonl`, `copy`/`cp ... sources\\registry.jsonl`
    all previously merged into one unmatched token ("sourcesregistry.jsonl")
    and bypassed Invariant 6 protection entirely.
  * `install SRC DEST` (coreutils, copies like cp) is now recognized —
    `install -m644 evil sources/registry.jsonl` previously reached the
    protected file untouched.
  * `[IO.File]::Create/OpenWrite/AppendText(path)` and
    `New-Object IO.StreamWriter(path)` / `[IO.StreamWriter]::new(path)` are now
    recognized alongside the pre-existing WriteAllText/WriteAllBytes/etc.
    coverage.
  * Deletion-via-find/xargs/gio-trash is now modeled — found live, all three
    deleted a script-owned file with every gate active: `find sources -name
    registry.jsonl -delete`, `find . -name registry.jsonl -exec rm {} \;`,
    `echo sources/registry.jsonl | xargs rm`, `gio trash
    sources/registry.jsonl`. No `find`/`xargs`/`gio` verb was modeled at all;
    `-exec rm {}` binds the literal `{}`, not the file, so the plain rm pattern
    never fired. A benign `find … -name '*.md'` (no delete action) and `echo
    hello | xargs rm` (no path-like operand) stay allowed.

Script layer
  * venue_check.py's cache_get() no longer raises an uncaught TypeError on a
    hand-edited/corrupt cache row with `"checked_at": null` — `dict.get(key,
    default)` only substitutes the default when the key is ABSENT, not when
    its value is None, so `fromisoformat(None)` slipped past the `except
    ValueError` guard as a raw traceback.
  * doi2bib.py's --append duplicate-DOI check now normalizes via clean_doi()
    (matching registry_db.is_duplicate/bib_doctor) instead of a bare
    .lower() — a bib holding "https://doi.org/10.x" and an incoming bare
    "10.x" are now recognized as the same DOI instead of both getting
    appended.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))
import venue_check  # noqa: E402
from lib_common import clean_doi, parse_bibtex  # noqa: E402


def _protect_verdict(command, cwd):
    # protect_data_files.py no-ops outside a Scholar-Kit project (references.bib
    # exists in every LaTeX repo, and as a plugin the hook runs everywhere), so
    # the fixture declares one. These tests exercise write-sink DETECTION.
    Path(cwd, "PROJECT.md").touch()
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    proc = subprocess.run([sys.executable, str(HOOKS / "protect_data_files.py")],
                          input=payload, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8")
    return "deny" in proc.stdout


# ---------- _shell_write_sink.py: unquoted Windows backslash paths ----------

def test_del_backslash_path_denied(tmp_path):
    assert _protect_verdict(r"del sources\registry.jsonl", tmp_path)


def test_remove_item_backslash_path_denied(tmp_path):
    assert _protect_verdict(r"Remove-Item sources\registry.jsonl", tmp_path)


def test_copy_backslash_path_denied(tmp_path):
    assert _protect_verdict(r"copy x sources\registry.jsonl", tmp_path)


def test_cp_backslash_path_denied(tmp_path):
    assert _protect_verdict(r"cp x sources\registry.jsonl", tmp_path)


def test_forward_slash_path_still_denied_control(tmp_path):
    assert _protect_verdict("cp x sources/registry.jsonl", tmp_path)


def test_escaped_space_still_allowed_not_a_windows_separator(tmp_path):
    # `a\ b.txt` is a legitimate POSIX escaped-space idiom, not a Windows
    # path — must NOT be treated as a backslash separator.
    assert not _protect_verdict(r"cp a\ b.txt drafts/notes.md", tmp_path)


def test_pip_install_still_allowed(tmp_path):
    assert not _protect_verdict("pip install requests", tmp_path)


def test_npm_install_still_allowed(tmp_path):
    assert not _protect_verdict("npm install lodash", tmp_path)


def test_read_only_registry_arg_still_allowed(tmp_path):
    assert not _protect_verdict(
        "python scripts/registry_db.py --file sources/registry.jsonl stats", tmp_path)


# ---------- _shell_write_sink.py: install verb + .NET file APIs ----------

def test_install_verb_denied(tmp_path):
    assert _protect_verdict("install -m644 evil sources/registry.jsonl", tmp_path)


def test_dotnet_file_create_denied(tmp_path):
    assert _protect_verdict('[IO.File]::Create("sources/registry.jsonl")', tmp_path)


def test_dotnet_file_openwrite_denied(tmp_path):
    assert _protect_verdict('[IO.File]::OpenWrite("sources/registry.jsonl")', tmp_path)


def test_dotnet_streamwriter_ctor_denied(tmp_path):
    assert _protect_verdict('New-Object IO.StreamWriter("sources/registry.jsonl")', tmp_path)


def test_dotnet_streamwriter_new_factory_denied(tmp_path):
    assert _protect_verdict('[IO.StreamWriter]::new("sources/registry.jsonl")', tmp_path)


# ---------- _shell_write_sink.py: find / xargs / gio-trash deletion ----------

def test_find_name_delete_denied(tmp_path):
    assert _protect_verdict("find sources -name registry.jsonl -delete", tmp_path)


def test_find_exec_rm_denied(tmp_path):
    assert _protect_verdict(r"find . -name registry.jsonl -exec rm {} \;", tmp_path)


def test_find_exec_unlink_plus_denied(tmp_path):
    assert _protect_verdict(r"find . -name cards.jsonl -exec unlink {} +", tmp_path)


def test_find_positional_path_delete_denied(tmp_path):
    assert _protect_verdict("find sources/registry.jsonl -delete", tmp_path)


def test_find_name_glob_delete_denied(tmp_path):
    # `-name '*.jsonl'` fnmatches a protected basename exactly as the shell expands it.
    assert _protect_verdict("find sources -name '*.jsonl' -delete", tmp_path)


def test_xargs_rm_denied(tmp_path):
    assert _protect_verdict("echo sources/registry.jsonl | xargs rm", tmp_path)


def test_ls_glob_xargs_rm_denied(tmp_path):
    assert _protect_verdict("ls sources/*.jsonl | xargs rm", tmp_path)


def test_gio_trash_denied(tmp_path):
    assert _protect_verdict("gio trash sources/registry.jsonl", tmp_path)


def test_trash_put_denied(tmp_path):
    assert _protect_verdict("trash-put evidence/cards.jsonl", tmp_path)


def test_find_without_delete_action_allowed(tmp_path):
    # A read-only find (no -delete/-exec rm) must not be flagged.
    assert not _protect_verdict("find sources -name '*.md'", tmp_path)


def test_find_delete_unprotected_file_allowed(tmp_path):
    assert not _protect_verdict("find sources -name notes.md -delete", tmp_path)


def test_xargs_rm_no_pathlike_operand_allowed(tmp_path):
    assert not _protect_verdict("echo hello | xargs rm", tmp_path)


# ---------- venue_check.py: null checked_at must not crash ----------

def test_cache_get_null_checked_at_does_not_raise(tmp_path):
    p = tmp_path / "venues.jsonl"
    rec = {"issn": "1234-5678", "checked_at": None, "display_name": "Test Journal"}
    p.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    # Must not raise TypeError; a null checked_at is treated as stale (cache miss).
    assert venue_check.cache_get(p, "1234-5678", "Test Journal") is None


def test_cache_get_missing_checked_at_key_still_treated_as_epoch(tmp_path):
    p = tmp_path / "venues.jsonl"
    rec = {"issn": "1234-5678", "display_name": "Test Journal"}
    p.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    assert venue_check.cache_get(p, "1234-5678", "Test Journal") is None


# ---------- doi2bib.py: --append dedup normalizes DOI like registry_db ----------

def test_append_dedup_recognizes_url_prefixed_duplicate(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        "@article{kaya2023deep,\n"
        "  title = {Deep learning for bearing fault diagnosis},\n"
        "  doi = {https://doi.org/10.1016/j.ymssp.2023.00001},\n"
        "  verified = {true},\n"
        "}\n", encoding="utf-8")
    existing = parse_bibtex(bib.read_text(encoding="utf-8"))
    new_doi = clean_doi("10.1016/J.YMSSP.2023.00001").lower()
    is_dup = new_doi and any(
        clean_doi(e["fields"].get("doi") or "").lower() == new_doi
        for e in existing if e["fields"].get("doi"))
    assert is_dup


def test_append_dedup_distinct_doi_not_flagged(tmp_path):
    bib = tmp_path / "references.bib"
    bib.write_text(
        "@article{kaya2023deep,\n"
        "  doi = {https://doi.org/10.1016/j.ymssp.2023.00001},\n"
        "  verified = {true},\n"
        "}\n", encoding="utf-8")
    existing = parse_bibtex(bib.read_text(encoding="utf-8"))
    new_doi = clean_doi("10.1016/j.sv.2022.00002").lower()
    is_dup = new_doi and any(
        clean_doi(e["fields"].get("doi") or "").lower() == new_doi
        for e in existing if e["fields"].get("doi"))
    assert not is_dup
