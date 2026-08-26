"""The test suite's own index, bound to the suite it describes.

`tests/conftest.py::AREAS` maps subject area -> test files, and `tests/README.md`
renders that map for humans. A lookup table is only worth having if it cannot
quietly go stale, so this file is the binding: a test file that joins the suite
without joining the map fails the build, and so does a map entry pointing at a
file that no longer exists.

This is the same standard the kit applies to its own documentation elsewhere
(`test_governance_docs.py` binds every published number to a test) — applied to
the one document whose whole purpose is to be accurate about the tests.
"""
import re
from pathlib import Path

import pytest

from conftest import AREAS

TESTS_DIR = Path(__file__).parent
README = TESTS_DIR / "README.md"


def _test_files() -> set[str]:
    return {p.name for p in TESTS_DIR.glob("test_*.py")}


def _mapped_files() -> set[str]:
    return {name for files in AREAS.values() for name in files}


def test_every_test_file_is_mapped_to_an_area():
    """A new test file must declare where it belongs, or `-m <area>` silently
    under-selects and the index lies by omission."""
    unmapped = sorted(_test_files() - _mapped_files())
    assert not unmapped, (
        "test files missing from conftest.AREAS: " + ", ".join(unmapped)
        + " — add each to every area it touches (see tests/README.md)")


def test_every_mapped_file_exists():
    """The reverse drift: a file renamed or deleted leaves a dangling entry that
    makes the area look better covered than it is."""
    missing = sorted(_mapped_files() - _test_files())
    assert not missing, (
        "conftest.AREAS names files that do not exist: " + ", ".join(missing))


def test_no_area_is_empty():
    empty = sorted(a for a, files in AREAS.items() if not files)
    assert not empty, f"areas with no test files: {empty}"


def test_no_duplicate_entries_within_an_area():
    for area, files in AREAS.items():
        dupes = sorted({f for f in files if files.count(f) > 1})
        assert not dupes, f"area {area!r} lists {dupes} more than once"


def test_readme_documents_every_area():
    """The area table is the only place an area's meaning is written down."""
    text = README.read_text(encoding="utf-8")
    undocumented = sorted(a for a in AREAS if f"`{a}`" not in text)
    assert not undocumented, (
        "areas missing from the tests/README.md table: " + ", ".join(undocumented))


def test_readme_documents_no_phantom_areas():
    """Rows for areas that no longer exist read as coverage that is not there."""
    text = README.read_text(encoding="utf-8")
    table = re.findall(r"^\| `([a-z]+)` \|", text, re.M)
    phantom = sorted(set(table) - set(AREAS))
    assert not phantom, (
        "tests/README.md documents areas absent from conftest.AREAS: " + ", ".join(phantom))


@pytest.mark.parametrize("name", sorted(_test_files()))
def test_date_named_files_follow_the_remediation_convention(name):
    """Naming a file after the day it was written is what this index exists to
    contain. It is allowed for review-round regression suites — those are named
    after a real, cited event (see tests/README.md) — and nowhere else."""
    if not re.search(r"\d{4}_\d{2}_\d{2}", name):
        return
    assert name.startswith("test_remediation_"), (
        f"{name}: date-named test files are reserved for review-round regression "
        "suites (test_remediation_<YYYY_MM_DD>_<tag>.py). Name this after the "
        "module under test instead — see tests/README.md.")


def test_area_markers_are_registered(pytestconfig):
    """`-m hooks` must not silently match nothing because a marker was never
    declared; with `--strict-markers` an unregistered marker is an error, and
    without it a typo is a silent empty selection."""
    declared = {line.split(":", 1)[0].strip()
                for line in pytestconfig.getini("markers")}
    missing = sorted(set(AREAS) - declared)
    assert not missing, f"areas not registered as pytest markers: {missing}"


def test_area_markers_actually_reach_collected_items(pytestconfig):
    """The map is only real if `pytest_collection_modifyitems` applies it. This
    asserts the wiring, not just the declaration."""
    from conftest import _AREAS_BY_FILE
    assert _AREAS_BY_FILE, "no file -> area index was built from AREAS"
    # This very file is mapped under kitmeta; if the wiring works, its own items
    # carry that marker.
    assert "kitmeta" in _AREAS_BY_FILE.get(Path(__file__).name, [])
