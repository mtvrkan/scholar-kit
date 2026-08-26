"""Every hook module's docstring must anchor its own change history.

The hook layer carries long "an earlier version of this hook…" narratives, and
keeping them at the point of use is deliberate: each one names a bypass that
actually shipped, and a reader widening a pattern needs it in view. The defect
was that the narrative was *unanchored* — the same history also lives in
DECISIONS.md and CHANGELOG.md, with nothing tying the copies together, so a
reader could not tell which was authoritative and drift between them would be
invisible.

This binds them. Every hook module must say where the full record lives and
which tests lock the behaviour, so the duplication is a cross-reference rather
than a fork.
"""
import ast
import re
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).parent.parent / ".claude" / "hooks"
ROOT = Path(__file__).parent.parent
HOOK_FILES = sorted(p.name for p in HOOKS_DIR.glob("*.py"))


def _docstring(name: str) -> str:
    src = (HOOKS_DIR / name).read_text(encoding="utf-8")
    return ast.get_docstring(ast.parse(src)) or ""


def test_hook_files_were_found():
    """A glob that silently matches nothing turns every parametrized test below
    into a vacuous pass."""
    assert len(HOOK_FILES) >= 6, HOOK_FILES


@pytest.mark.parametrize("name", HOOK_FILES)
def test_hook_has_module_docstring(name):
    assert _docstring(name).strip(), f"{name}: no module docstring"


@pytest.mark.parametrize("name", HOOK_FILES)
def test_hook_docstring_carries_a_change_record(name):
    doc = _docstring(name)
    assert "Change record:" in doc, (
        f"{name}: module docstring has no \"Change record:\" section. Add one "
        "naming the authoritative record (DECISIONS.md D-0xx, or CHANGELOG.md "
        "for modules that postdate the log) and the test file that locks the "
        "behaviour — see tests/test_hook_change_records.py for why.")


@pytest.mark.parametrize("name", HOOK_FILES)
def test_change_record_points_at_a_real_authority(name):
    """Either DECISIONS.md D-numbers, or an explicit statement that the module
    postdates the log. "See the git history" is not an anchor."""
    doc = _docstring(name)
    tail = doc.split("Change record:", 1)[1]
    assert re.search(r"D-\d{3}", tail) or "CHANGELOG.md" in tail, (
        f"{name}: change record names no DECISIONS.md D-entry and no CHANGELOG.md")


@pytest.mark.parametrize("name", HOOK_FILES)
def test_change_record_names_an_existing_test_file(name):
    """The clause that says "behaviour is locked by X" must point at a file that
    exists — the exact drift this whole binding is meant to prevent."""
    tail = _docstring(name).split("Change record:", 1)[1]
    referenced = re.findall(r"tests/(test_[\w]+\.py)", tail)
    assert referenced, f"{name}: change record names no test file"
    missing = [t for t in referenced if not (ROOT / "tests" / t).is_file()]
    assert not missing, f"{name}: change record points at missing test file(s): {missing}"


@pytest.mark.parametrize("name", HOOK_FILES)
def test_cited_decision_entries_exist(name):
    """A D-number that was never written is worse than no citation: it reads as
    a record that can be looked up."""
    decisions = (ROOT / "DECISIONS.md").read_text(encoding="utf-8")
    tail = _docstring(name).split("Change record:", 1)[1]
    # Ranges are written "D-074..D-081"; only the endpoints are cited literally.
    cited = set(re.findall(r"D-(\d{3})", tail))
    known = set(re.findall(r"D-(\d{3})", decisions))
    unknown = sorted(cited - known)
    assert not unknown, f"{name}: cites DECISIONS entries that do not exist: {unknown}"
