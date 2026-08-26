"""_project_scope.py — is the current directory a Scholar-Kit project?

The enforcement hooks (phase_gate, protect_data_files, cite_warn) gate on
directory and file names that are entirely ordinary outside this kit:
`drafts/`, `build/`, `exports/`, `reviews/`, and — the sharpest case —
`references.bib`, which exists in essentially every LaTeX repository ever
written.

That was harmless while the kit was installed per-project: `/new-project`
copies the runtime into the project directory, so the hooks only ever ran
where the kit lived. It stops being harmless the moment the kit is installed
as a Claude Code plugin, because a plugin's hooks run in EVERY session the
plugin is enabled for. Without this guard, enabling Scholar-Kit would deny
edits to `references.bib` in an unrelated thesis repo and block writes to
`build/` in an unrelated software project — enforcement leaking out of the
project it was written for, which is a defect, not strictness.

The marker is `PROJECT.md` in the working directory. It is the kit's declared
single source of truth (CLAUDE.md § State files), `/new-project` always writes
it, and every gated command already refuses to run without it — so "no
PROJECT.md" cannot describe a live kit project whose gates are being bypassed.

`PROJECT.md` alone is a WEAK marker, though: the name is not the kit's
property, and an unrelated repository that happens to carry a file by that name
re-arms every gate above in a directory this hook has no jurisdiction over —
the same over-gating defect this module was written to prevent, one step in.
So the marker is now read in two stages:

  1. A POSITIVE kit signal decides it outright: the signature line the template
     carries, enough of the template's own field labels to be it, or any file
     only a kit project holds (its state files, or the runtime `/new-project`
     materialises). A materialised project always carries
     `.claude/hooks/phase_gate.py` — the very file asking the question — so a
     real project can essentially never fail this stage.
  2. Only when NO kit signal is present does a foreign PACKAGE MANIFEST
     (package.json, Cargo.toml, go.mod, …) veto. That is the concrete case the
     module docstring already named: "block writes to `build/` in an unrelated
     software project". A software project has a manifest; a paper does not.

Anything else — a PROJECT.md with no kit signal and no manifest either — stays
a kit project, i.e. stays GATED. That asymmetry is deliberate: over-gating
announces itself in a deny message the author can read and act on, while
under-gating is silent, and a gate that turns itself off quietly is the worse
of the two failures by a wide margin.

Fail-open by design: any error resolving the marker returns False (not a kit
project, do not gate). A guard that crashes must not become a new way for a
hook to block every tool call in a session.

Change record: the two-stage marker is DECISIONS.md D-092 (sixth external
review); the module itself postdates the log's D-084 and CHANGELOG.md carries
its release note. Behaviour is locked by tests/test_project_scope_hook.py; see
`hooks` in tests/README.md.
"""
from __future__ import annotations

from pathlib import Path

MARKER = "PROJECT.md"

# The explicit machine marker the template's first line carries. Checked ahead
# of the field labels because it is the one signal a user restructuring their
# PROJECT.md has no reason to remove — the labels stay as the fallback for every
# project created before this line existed.
KIT_SIGNATURE = "<!-- scholar-kit-project -->"

# Field labels the template's PROJECT.md carries and the wizard keeps ("Do not
# delete fields; write TBD if unknown"). Two of them, not one: a single generic
# label could plausibly appear in somebody else's project brief, a pair of these
# in one file is the kit's template.
KIT_FIELDS = ("**Type:**", "**Target venue:**", "**Citation style:**",
              "**Search languages:**", "**Word budget (total):**", "**Phase:**")
_FIELDS_REQUIRED = 2

# Files only a Scholar-Kit project holds — its script-owned state, or the
# runtime /new-project copies in. Any ONE of these settles the question.
KIT_ARTIFACTS = (
    Path(".claude") / "hooks" / "phase_gate.py",
    Path("scripts") / "registry_db.py",
    Path("sources") / "registry.jsonl",
    Path("evidence") / "cards.jsonl",
    Path("outline") / "outline.md",
    Path("drafts") / "STATUS.md",
    Path("verify-status.json"),
)

# Package manifests. Only consulted when no kit signal was found at all, and
# deliberately limited to unambiguous ecosystem manifests: a Makefile or a
# .gitignore says nothing about whether a directory is a paper.
FOREIGN_MANIFESTS = ("package.json", "pnpm-workspace.yaml", "Cargo.toml", "go.mod",
                     "pyproject.toml", "setup.py", "pom.xml", "build.gradle",
                     "build.gradle.kts", "Gemfile", "composer.json", "deno.json",
                     "pubspec.yaml")

# A PROJECT.md is read only up to this many bytes. The template is ~2 KB; the
# cap keeps a hook that runs before EVERY tool call from ever reading a large
# file that merely shares the name.
_MAX_MARKER_BYTES = 64 * 1024


def _marker_declares_kit(marker: Path) -> bool:
    """The signature line, or enough of the template's field labels to be it."""
    try:
        text = marker.read_text(encoding="utf-8", errors="replace")[:_MAX_MARKER_BYTES]
    except OSError:
        return False
    if KIT_SIGNATURE in text:
        return True
    return sum(1 for label in KIT_FIELDS if label in text) >= _FIELDS_REQUIRED


def is_kit_project(cwd: Path | str | None = None) -> bool:
    """True when `cwd` looks like a Scholar-Kit project directory.

    Checked at the working directory only, never walked upward: a parent
    directory holding an unrelated PROJECT.md must not silently re-arm the
    gates for every subdirectory beneath it.
    """
    try:
        root = Path(cwd) if cwd is not None else Path.cwd()
        marker = root / MARKER
        if not marker.is_file():
            return False
        if _marker_declares_kit(marker):
            return True
        if any((root / rel).is_file() for rel in KIT_ARTIFACTS):
            return True
        # No kit signal: let an unambiguous foreign manifest veto, and default
        # to gating otherwise (see the module docstring on failure direction).
        return not any((root / name).is_file() for name in FOREIGN_MANIFESTS)
    except OSError:
        return False
