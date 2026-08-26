"""Regression tests for the twenty-fourth independent review (D-080):
PowerShell built-in short-alias bypass of every hook built on
_shell_write_sink.py, plain shell variable indirection in a redirect target,
five scripts crashing with a raw ModuleNotFoundError instead of a clean
die() on a missing optional dependency, and skill_routing_eval.py's missing
JSON-error handling + require_within_cwd guard on --prompts.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(HOOKS))
from _shell_write_sink import write_targets  # noqa: E402


# ---------- PowerShell built-in short aliases ----------

def test_write_targets_detects_set_content_alias_sc():
    targets = write_targets("sc sources/registry.jsonl '{\"fake\":1}'")
    assert "sources/registry.jsonl" in targets


def test_write_targets_detects_new_item_alias_ni():
    targets = write_targets('ni drafts/hack.md -Value "unapproved" -Force')
    assert "drafts/hack.md" in targets


def test_write_targets_detects_add_content_alias_ac():
    targets = write_targets('ac reviews/round-1.md "Major issues: 0"')
    assert "reviews/round-1.md" in targets


def test_write_targets_detects_copy_item_alias_cpi():
    targets = write_targets("cpi build/x.tex exports/x.tex")
    assert "exports/x.tex" in targets


def test_write_targets_detects_move_item_alias_mi():
    targets = write_targets("mi drafts/a.md drafts/b.md")
    assert "drafts/b.md" in targets


def test_write_targets_detects_rename_item_alias_rni():
    targets = write_targets("rni drafts/a.md drafts/b.md")
    assert "drafts/b.md" in targets


def test_write_targets_detects_rename_item_alias_ren():
    targets = write_targets("ren drafts/a.md drafts/b.md")
    assert "drafts/b.md" in targets


def test_write_targets_detects_remove_item_alias_ri():
    targets = write_targets("ri drafts/a.md")
    assert "drafts/a.md" in targets


def test_write_targets_detects_remove_item_alias_rd():
    targets = write_targets("rd drafts/a.md")
    assert "drafts/a.md" in targets


def test_write_targets_detects_remove_item_alias_rmdir():
    targets = write_targets("rmdir drafts/a.md")
    assert "drafts/a.md" in targets


def test_write_targets_detects_remove_item_alias_erase():
    targets = write_targets("erase drafts/a.md")
    assert "drafts/a.md" in targets


def test_write_targets_alias_still_ignores_option_flag_and_substring():
    # Command-position anchoring must still exclude an option flag (-ni) and
    # a short alias appearing mid-argument of an unrelated command.
    assert write_targets("some-tool -ni registry.jsonl") == []


# ---------- shell variable indirection in a redirect target ----------

def test_write_targets_resolves_shell_var_in_redirect():
    targets = write_targets('F=drafts/intro.md; echo "unapproved text" > $F')
    assert "drafts/intro.md" in targets


def test_write_targets_resolves_shell_var_braced_form():
    targets = write_targets('F=drafts/intro.md; echo x > ${F}')
    assert "drafts/intro.md" in targets


def test_write_targets_resolves_quoted_shell_var_assignment():
    targets = write_targets('F="sources/registry.jsonl"; sc $F \'{"fake":1}\'')
    assert "sources/registry.jsonl" in targets


def test_write_targets_unassigned_var_left_alone():
    # No assignment for $HOME in-command — must not crash or fabricate a target.
    assert write_targets("echo $HOME") == []


# ---------- optional-dependency ModuleNotFoundError guards ----------

def _run(args):
    return subprocess.run(
        [sys.executable, "-S", *args], cwd=ROOT, capture_output=True, text=True, timeout=30)


def test_make_reference_docx_missing_docx_dies_cleanly():
    r = _run(["scripts/make_reference_docx.py", "--out", "/tmp/ref.docx"])
    assert r.returncode == 1
    assert "ERROR" in r.stdout + r.stderr
    assert "Traceback" not in r.stderr


def test_docx_style_check_missing_docx_dies_cleanly():
    r = _run(["scripts/docx_style_check.py", "--built", "a.docx", "--reference", "b.docx"])
    assert r.returncode == 1
    assert "ERROR" in r.stdout + r.stderr
    assert "Traceback" not in r.stderr


def test_xlsx_export_missing_openpyxl_dies_cleanly():
    r = _run(["scripts/xlsx_export.py", "--out", "/tmp/x.xlsx"])
    assert r.returncode == 1
    assert "ERROR" in r.stdout + r.stderr
    assert "Traceback" not in r.stderr


def test_venue_check_missing_requests_dies_cleanly(tmp_path):
    # Run in an isolated cwd (not ROOT): with the default --cache resolving to
    # tmp_path/sources/venues.jsonl (nonexistent), there is no cache hit to
    # short-circuit on, so execution actually reaches the `requests is None`
    # guard this test exists to check. Running in ROOT let a same-day cached
    # 0888-3270 record in the real sources/venues.jsonl return before the guard.
    r = subprocess.run(
        [sys.executable, "-S", str(SCRIPTS / "venue_check.py"), "--issn", "0888-3270"],
        cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert r.returncode == 1
    assert "ERROR" in r.stdout + r.stderr
    assert "Traceback" not in r.stderr


def test_doi2bib_missing_requests_dies_cleanly():
    r = _run(["scripts/doi2bib.py", "--doi", "10.1000/xyz"])
    assert r.returncode == 1
    assert "ERROR" in r.stdout + r.stderr
    assert "Traceback" not in r.stderr


# ---------- skill_routing_eval.py: JSON error handling + path guard ----------

def test_skill_routing_eval_malformed_json_dies_cleanly(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "skill_routing_eval.py"), "--prompts", str(bad)],
        cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert r.returncode == 1
    assert "ERROR" in r.stdout + r.stderr
    assert "Traceback" not in r.stderr


def test_skill_routing_eval_rejects_path_outside_cwd(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps([{"prompt": "x", "expect": "nonexistent-skill"}]),
                        encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "skill_routing_eval.py"), "--prompts", str(outside)],
        cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert r.returncode == 1
    assert "ERROR" in r.stdout + r.stderr
