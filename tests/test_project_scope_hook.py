"""Tests for the hooks' project-scope guard (.claude/hooks/_project_scope.py).

The enforcement hooks gate on names that are entirely ordinary outside this kit:
`drafts/`, `build/`, `exports/`, `reviews/`, and `references.bib` — which exists
in essentially every LaTeX repository ever written. That was harmless while the
kit was installed per-project. As a Claude Code plugin the hooks run in EVERY
session, so without this guard enabling Scholar-Kit would deny edits to an
unrelated project's bibliography and block writes to an unrelated `build/`.

These tests pin both directions: the guard must silence the hooks outside a kit
project, and must NOT silence them inside one.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))

import _project_scope  # noqa: E402


def _run(hook, payload, cwd):
    return subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        input=json.dumps(payload), cwd=cwd, capture_output=True, text=True,
        encoding="utf-8")


# ---------- is_kit_project ----------

def test_marker_present_is_a_kit_project(tmp_path):
    (tmp_path / "PROJECT.md").touch()
    assert _project_scope.is_kit_project(tmp_path) is True


def test_marker_absent_is_not_a_kit_project(tmp_path):
    assert _project_scope.is_kit_project(tmp_path) is False


def test_marker_directory_does_not_count(tmp_path):
    # A directory named PROJECT.md is not the kit's source of truth.
    (tmp_path / "PROJECT.md").mkdir()
    assert _project_scope.is_kit_project(tmp_path) is False


def test_marker_is_not_searched_upward(tmp_path):
    # A parent directory holding an unrelated PROJECT.md must not silently
    # re-arm the gates for every subdirectory beneath it.
    (tmp_path / "PROJECT.md").touch()
    child = tmp_path / "unrelated-repo"
    child.mkdir()
    assert _project_scope.is_kit_project(child) is False


def test_unreadable_path_fails_open(tmp_path):
    # A guard that raises must not become a new way to block every tool call.
    assert _project_scope.is_kit_project(tmp_path / "does" / "not" / "exist") is False


# ---------- the marker is weak on its own: PROJECT.md is not the kit's name ----------
# An unrelated repository that happens to carry a PROJECT.md re-armed every gate
# in a directory these hooks have no jurisdiction over — the same over-gating
# defect this module exists to prevent, one step in. A positive kit signal now
# settles it; only in the absence of any signal does a package manifest veto.

def test_foreign_repo_with_a_project_md_and_a_manifest_is_not_a_kit_project(tmp_path):
    # The concrete case: a software project whose build/ this hook would
    # otherwise gate, carrying a PROJECT.md for entirely unrelated reasons.
    (tmp_path / "PROJECT.md").write_text("# Project\n\nA note about this app.\n",
                                         encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name":"app"}', encoding="utf-8")
    assert _project_scope.is_kit_project(tmp_path) is False


def test_signature_line_beats_a_manifest(tmp_path):
    # A paper that also ships code (an analysis package, a web demo) is still a
    # paper. The positive signal is checked first for exactly this case.
    (tmp_path / "PROJECT.md").write_text(
        _project_scope.KIT_SIGNATURE + "\n# PROJECT.md\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='analysis'\n", encoding="utf-8")
    assert _project_scope.is_kit_project(tmp_path) is True


def test_template_field_labels_identify_a_project_created_before_the_signature(tmp_path):
    # Every project made from the old template still carries the wizard's field
    # labels; enforcement must not switch off for them.
    (tmp_path / "PROJECT.md").write_text(
        "# PROJECT.md\n- **Target venue:** TBD\n- **Citation style:** ieee\n",
        encoding="utf-8")
    (tmp_path / "go.mod").write_text("module x\n", encoding="utf-8")
    assert _project_scope.is_kit_project(tmp_path) is True


def test_one_generic_field_label_alone_is_not_enough(tmp_path):
    # A single label could plausibly appear in somebody else's project brief.
    (tmp_path / "PROJECT.md").write_text("# Roadmap\n- **Phase:** discovery\n",
                                         encoding="utf-8")
    (tmp_path / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
    assert _project_scope.is_kit_project(tmp_path) is False


def test_the_materialised_runtime_alone_identifies_a_kit_project(tmp_path):
    # The hook asking the question is itself the signal: /new-project copies
    # .claude/hooks/ into the project, so a real project can essentially never
    # fail this check no matter what its PROJECT.md was rewritten to say.
    (tmp_path / "PROJECT.md").write_text("rewritten by the author\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "phase_gate.py").touch()
    assert _project_scope.is_kit_project(tmp_path) is True


def test_kit_state_files_identify_a_kit_project(tmp_path):
    (tmp_path / "PROJECT.md").write_text("rewritten\n", encoding="utf-8")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / "cards.jsonl").touch()
    assert _project_scope.is_kit_project(tmp_path) is True


def test_unknown_directory_still_gates(tmp_path):
    # The failure direction, pinned: no kit signal AND no manifest either means
    # the question is unanswerable, and an unanswerable question must resolve to
    # "gate". Over-gating announces itself in a deny message; under-gating is
    # silent, and a gate that switches itself off quietly is the worse failure.
    (tmp_path / "PROJECT.md").touch()
    assert _project_scope.is_kit_project(tmp_path) is True


def test_the_shipped_template_is_recognised_as_a_kit_project(tmp_path):
    # Bound to the real file: if project-template/PROJECT.md ever loses the
    # signature line AND its field labels, every new project would start with
    # its gates off.
    import shutil
    shutil.copy2(ROOT / "project-template" / "PROJECT.md", tmp_path / "PROJECT.md")
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert _project_scope.is_kit_project(tmp_path) is True


# ---------- phase_gate: build/ and drafts/ outside a kit project ----------

def test_phase_gate_silent_outside_kit_project(tmp_path):
    # No outline, writing into drafts/ — inside a kit project this is denied.
    out = _run("phase_gate.py",
               {"tool_name": "Write",
                "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}},
               tmp_path).stdout
    assert out.strip() == ""


def test_phase_gate_active_inside_kit_project(tmp_path):
    (tmp_path / "PROJECT.md").touch()
    out = _run("phase_gate.py",
               {"tool_name": "Write",
                "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}},
               tmp_path).stdout
    assert "deny" in out


def test_phase_gate_does_not_block_unrelated_build_dir(tmp_path):
    # The concrete regression: a software project's build/ output.
    out = _run("phase_gate.py",
               {"tool_name": "Write",
                "tool_input": {"file_path": str(tmp_path / "build" / "bundle.js")}},
               tmp_path).stdout
    assert out.strip() == ""


# ---------- protect_data_files: references.bib outside a kit project ----------

def test_references_bib_editable_outside_kit_project(tmp_path):
    # The sharpest case: any LaTeX repo has one, and the deny message would
    # tell the author to run a script they do not have.
    out = _run("protect_data_files.py",
               {"tool_name": "Write",
                "tool_input": {"file_path": str(tmp_path / "references.bib")}},
               tmp_path).stdout
    assert out.strip() == ""


def test_references_bib_protected_inside_kit_project(tmp_path):
    (tmp_path / "PROJECT.md").touch()
    out = _run("protect_data_files.py",
               {"tool_name": "Write",
                "tool_input": {"file_path": str(tmp_path / "bib" / "references.bib")}},
               tmp_path).stdout
    assert "deny" in out


def test_cards_jsonl_still_protected_inside_kit_project(tmp_path):
    (tmp_path / "PROJECT.md").touch()
    out = _run("protect_data_files.py",
               {"tool_name": "Write",
                "tool_input": {"file_path": str(tmp_path / "evidence" / "cards.jsonl")}},
               tmp_path).stdout
    assert "deny" in out


# ---------- cite_warn ----------

def test_cite_warn_silent_outside_kit_project(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "cite_audit.py").write_text("import sys; sys.exit(0)", encoding="utf-8")
    proc = _run("cite_warn.py",
                {"tool_name": "Write", "cwd": str(tmp_path),
                 "tool_input": {"file_path": str(tmp_path / "drafts" / "intro.md")}},
                tmp_path)
    assert proc.returncode == 0 and proc.stderr.strip() == ""


# ---------- the guard is actually wired into every hook that needs it ----------

def test_guard_wired_into_every_broad_path_hook():
    # A hook that gates on ordinary directory names but skips the guard is the
    # exact defect this module exists to prevent, and it would only surface
    # after the plugin shipped.
    for hook in ("phase_gate.py", "protect_data_files.py", "cite_warn.py"):
        text = (HOOKS / hook).read_text(encoding="utf-8")
        assert "is_kit_project" in text, f"{hook} does not consult the project scope guard"
