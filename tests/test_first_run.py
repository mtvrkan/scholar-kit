"""The plugin first-run path: /plugin install -> /new-project -> a working project.

Everything else in this kit is worthless if this path is broken, and it is the
one path no other test exercises. A plugin install ships only skills and agents;
the deterministic script layer and the enforcement hooks reach the user solely
because `/new-project` copies them out of the kit root. If that copy list drifts
from what the project actually needs — a directory renamed, a script added
outside `scripts/`, a hook that assumes a file the template does not carry — the
failure appears on a new user's very first command and nowhere in CI.

These tests replay the copy list declared in `.claude/skills/new-project/SKILL.md`
and then assert the result stands on its own.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

# The runtime /new-project step 2 copies into a new project.
COPY_DIRS = (".claude", "scripts", "templates")
COPY_FILES = ("CLAUDE.md",)


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    """A project built exactly the way /new-project builds one."""
    dest = tmp_path_factory.mktemp("scholar-firstrun")
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for rel in COPY_DIRS:
        shutil.copytree(ROOT / rel, dest / rel, ignore=ignore)
    for rel in COPY_FILES:
        shutil.copy2(ROOT / rel, dest / rel)
    for item in (ROOT / "project-template").iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)
    return dest


def _run(project, *args):
    proc = subprocess.run([sys.executable, *args], cwd=project,
                          capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout, proc.stderr


# ---------- the copy list still matches reality ----------

def test_every_declared_copy_source_exists():
    # If a source disappears or is renamed, /new-project silently produces a
    # project missing that piece.
    for rel in COPY_DIRS + COPY_FILES + ("project-template",):
        assert (ROOT / rel).exists(), f"/new-project copies {rel}, which does not exist"


def test_new_project_skill_still_declares_this_copy_list():
    # The list above is a transcription of prose. If the skill's step 2 changes,
    # this test is the thing that notices the transcription went stale.
    text = (ROOT / ".claude" / "skills" / "new-project" / "SKILL.md").read_text(
        encoding="utf-8")
    for rel in COPY_DIRS + COPY_FILES:
        assert f"$KIT/{rel}" in text, f"new-project no longer declares copying {rel}"


def test_new_project_patches_the_hook_interpreter():
    # A plugin-installed project never runs INSTALL.sh, so /new-project owns
    # this step. PreToolUse hooks fail OPEN: an unpatched interpreter means
    # enforcement is silently absent, not visibly broken.
    text = (ROOT / ".claude" / "skills" / "new-project" / "SKILL.md").read_text(
        encoding="utf-8")
    assert "patch_hook_interpreter.py" in text


# ---------- the produced project stands on its own ----------

def test_project_carries_the_project_marker(project):
    # Without it every enforcement hook no-ops (see _project_scope.py), so the
    # project would look fine and enforce nothing.
    assert (project / "PROJECT.md").is_file()


def test_the_new_project_is_recognised_by_the_scope_guard(project):
    # The marker is a file NAME plus a signal now (_project_scope.py), and both
    # halves are produced here: the template's signature line and the copied
    # .claude/hooks/. Asserting the produced project passes the guard the hooks
    # actually consult, rather than only that the file exists — a project the
    # guard rejects has every gate switched off and looks perfectly fine.
    sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
    import _project_scope  # the kit's copy; the project's is a verbatim copy of it
    assert _project_scope.is_kit_project(project) is True


def test_kit_integrity_passes_inside_the_new_project(project):
    code, out, err = _run(project, "scripts/validate_kit.py", "--json")
    assert code == 0, out + err
    assert json.loads(out)["problems"] == []


def test_deterministic_scripts_resolve_locally(project):
    # Every skill invokes tools as `python scripts/...`; those must resolve in
    # the project, not in the kit the plugin was installed from.
    for script in ("claim_check.py", "failure_scan.py", "cite_audit.py"):
        code, out, err = _run(project, f"scripts/{script}")
        assert code in (0, 2), f"{script} failed to run in a fresh project: {err}"


def test_enforcement_hooks_fire_in_the_new_project(project):
    payload = json.dumps({"tool_name": "Write",
                          "tool_input": {"file_path": str(project / "drafts" / "intro.md")}})
    proc = subprocess.run(
        [sys.executable, str(project / ".claude" / "hooks" / "phase_gate.py")],
        input=payload, cwd=project, capture_output=True, text=True, encoding="utf-8")
    # A fresh project has no approved outline, so drafting must be denied.
    assert "deny" in proc.stdout
    assert "outline" in proc.stdout.lower()


def test_every_wired_hook_file_was_copied(project):
    settings = json.loads(
        (project / ".claude" / "settings.json").read_text(encoding="utf-8-sig"))
    wired = set()
    for groups in settings.get("hooks", {}).values():
        for g in groups:
            for h in g.get("hooks", []):
                m = re.search(r"\.claude/hooks/(\w+\.py)", h.get("command", ""))
                if m:
                    wired.add(m.group(1))
    assert wired, "settings.json wires no hooks"
    for name in sorted(wired):
        assert (project / ".claude" / "hooks" / name).is_file(), (
            f"settings.json wires {name} but /new-project's copy list does not "
            f"deliver it")


def test_citation_style_assets_were_copied(project):
    # /restyle and the build scripts resolve CSL files from the project.
    assert list((project / "templates" / "csl").glob("*.csl"))


def test_project_skeleton_directories_exist(project):
    for d in ("sources", "evidence", "analysis", "bib", "outline", "drafts",
              "reviews", "exports", "build"):
        assert (project / d).is_dir(), f"project skeleton missing {d}/"
