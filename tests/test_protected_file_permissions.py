"""The OS-level half of Invariant 6: script-owned data files are read-only.

`.claude/hooks/protect_data_files.py` decides, from the text of a Bash command,
whether that command writes to registry.jsonl/cards.jsonl/… That layer is real
and tested — and its defect history (every bypass in `_shell_write_sink.py`'s
header) is precisely why it should not be the only one. A detector built on
shell syntax knows the syntax it was taught.

These tests cover the layer that needs no pattern at all: after a sanctioned
write, the file carries no write bit, so the ordinary ways of clobbering it —
`>`, `tee`, `Set-Content`, `open(p, "w")` — are refused by the operating
system whether or not the hook recognised the command.

The boundary is asserted too (`test_protection_does_not_pretend_to_stop_unlink`):
unlink and rename are governed by the DIRECTORY's permission, not the file's,
so this layer does not stop them and the test says so out loud rather than
leaving a reader to assume coverage that is not there.
"""
import json
import os
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lib_common  # noqa: E402

# chmod does not constrain root: a POSIX superuser writes through a cleared
# write bit, so these assertions would fail in a root container while the
# behaviour they describe is perfectly correct. Windows has no equivalent
# bypass (the read-only ATTRIBUTE is honoured for Administrators too).
_IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0
root_skip = pytest.mark.skipif(_IS_ROOT, reason="chmod does not constrain root")


def _writable(p: Path) -> bool:
    return bool(p.stat().st_mode & 0o222)


# ---------- the predicate ----------

def test_every_hook_protected_name_is_also_protected_at_the_os_layer():
    """The two layers must agree on WHICH files they are protecting.

    They are declared in two places by necessity — the hook cannot import from
    scripts/ — so nothing but this test stops one list from growing a seventh
    file that the other has never heard of.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "hooks"))
    import protect_data_files

    assert set(protect_data_files.PROTECTED) == set(lib_common.PROTECTED_BASENAMES)


@pytest.mark.parametrize("name", sorted(lib_common.PROTECTED_BASENAMES))
def test_protected_names_are_matched_on_basename_alone(name, tmp_path):
    assert lib_common.is_protected_data_file(tmp_path / "sources" / name)
    assert lib_common.is_protected_data_file(name.upper())


def test_ordinary_project_files_are_not_protected(tmp_path):
    for ordinary in ("intro.md", "outline.md", "counts.json", "extracts.jsonl",
                     "my-references.bib.bak", "registry.jsonl.lock"):
        assert not lib_common.is_protected_data_file(tmp_path / ordinary), ordinary


# ---------- the marking, through the real writers ----------

@root_skip
def test_registry_db_leaves_the_registry_read_only(run, tmp_path):
    code, out, err = run("registry_db.py", "add", "--payload",
                         json.dumps({"title": "A", "year": 2024}))
    assert code == 0, err
    reg = tmp_path / "sources" / "registry.jsonl"
    assert reg.is_file()
    assert not _writable(reg), "a sanctioned write left the registry writable"


@root_skip
def test_evidence_db_leaves_the_cards_file_read_only(run, tmp_path):
    code, out, err = run("evidence_db.py", "add", "--payload", json.dumps(
        {"source": "kaya2023deep", "type": "finding", "claim": "X beats Y", "strength": 3}))
    assert code == 0, err
    cards = tmp_path / "evidence" / "cards.jsonl"
    assert cards.is_file()
    assert not _writable(cards)


@root_skip
def test_a_second_sanctioned_write_still_succeeds_and_re_arms(run, tmp_path):
    """The whole design fails if protection breaks the sanctioned path itself.

    On Windows os.replace() onto a read-only file raises PermissionError, so
    without the unprotect-before-replace step the SECOND `add` would die on
    every kit project on that platform — a self-inflicted outage, not a gate.
    """
    for i in range(3):
        code, _, err = run("registry_db.py", "add", "--payload",
                           json.dumps({"title": f"paper {i}", "year": 2024}))
        assert code == 0, f"write {i} failed: {err}"
    reg = tmp_path / "sources" / "registry.jsonl"
    assert len(reg.read_text(encoding="utf-8").strip().splitlines()) == 3
    assert not _writable(reg), "the file was left writable after a later write"


@root_skip
def test_a_plain_python_write_is_refused_while_protected(run, tmp_path):
    """The claim this layer actually makes, exercised the way a bypass would.

    No hook is involved: this is `open(p, "w")` against the filesystem, the
    same call every redirect, `tee` and `Set-Content` bottoms out in.
    """
    code, _, err = run("registry_db.py", "add", "--payload", json.dumps({"title": "A"}))
    assert code == 0, err
    reg = tmp_path / "sources" / "registry.jsonl"

    with pytest.raises(PermissionError):
        with reg.open("w", encoding="utf-8") as f:
            f.write("{}\n")

    assert json.loads(reg.read_text(encoding="utf-8").strip())["title"] == "A"


@root_skip
def test_drafts_are_not_marked_read_only(tmp_path):
    """Protection is scoped to the six data files. Marking a draft read-only
    would break the one thing the author is supposed to edit by hand."""
    draft = tmp_path / "intro.md"
    lib_common.write_text_atomic(draft, "# Intro\n")
    assert _writable(draft)


@root_skip
def test_bib_and_verify_status_go_through_the_same_chokepoint(tmp_path):
    bib = tmp_path / "bib" / "references.bib"
    lib_common.write_text_atomic(bib, "@article{a2024x,\n  title = {A},\n}\n")
    assert not _writable(bib)

    status = tmp_path / "verify-status.json"
    lib_common.write_json_atomic(status, {"status": "PASS"})
    assert not _writable(status)


# ---------- the escape hatch ----------

@root_skip
def test_unprotect_restores_writability_and_protect_clears_it(tmp_path):
    """A user abandoning a project must be able to delete their own files
    without this module, and a contributor debugging one must be able to open
    it in an editor. That is a supported operation, not a bypass."""
    p = tmp_path / "sources" / "registry.jsonl"
    p.parent.mkdir(parents=True)
    lib_common.write_jsonl(p, [{"id": "SRC-0001"}])
    assert not _writable(p)

    lib_common.unprotect(p)
    assert _writable(p)
    p.write_text('{"id": "SRC-0002"}\n', encoding="utf-8")  # must not raise

    lib_common.protect(p)
    assert not _writable(p)


def test_the_escape_hatch_is_silent_on_a_missing_file(tmp_path):
    # Called on the failure path of _replace_with_retry, where the destination
    # may legitimately not exist yet. A raise there would turn a failed write
    # into a traceback about permissions.
    lib_common.unprotect(tmp_path / "nope.jsonl")
    lib_common.protect(tmp_path / "nope.jsonl")


# ---------- the stated boundary ----------

@root_skip
def test_protection_does_not_pretend_to_stop_deletion(tmp_path):
    """The stated boundary, asserted on both platforms rather than skipped.

    A read-only file is still DELETABLE — on POSIX outright (unlink is governed
    by the directory's permission), on Windows after clearing the attribute,
    which is exactly what `del /F` and `Remove-Item -Force` do. So deletion
    remains protect_data_files.py's job on every platform, and this test fails
    if a future change makes lib_common's header over-claim.

    Deliberately no platform skip: a conditional skip would make the published
    "N tests pass" figure platform-dependent, and that number is bound to a
    real collection run in test_governance_docs.py.
    """
    p = tmp_path / "sources" / "registry.jsonl"
    p.parent.mkdir(parents=True)
    lib_common.write_jsonl(p, [{"id": "SRC-0001"}])
    assert not _writable(p)

    if os.name == "nt":
        with pytest.raises(PermissionError):
            p.unlink()
        lib_common.unprotect(p)   # what -Force does
    p.unlink()
    assert not p.exists()
