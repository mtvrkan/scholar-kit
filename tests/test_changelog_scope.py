"""The kit's CHANGELOG is a record of the kit, and nothing else.

This kit is used from inside its own repository: a real review runs under
`runs/<project>/`, and defects that run finds are fixed in `scripts/`. That
arrangement is deliberate and it is how most of the entries in CHANGELOG.md
came to exist — but it has one failure mode, and the failure mode fired.

For four days the `[Unreleased]` section carried six sections that were the
*review's* log, not the kit's: a manuscript that got 13% shorter, PRISMA box
counts, and eight scripts (`bivariate_dta.py`, `eligibility_consolidate.py`,
`intl_funnel.py`, `register_included.py`, `pool_run.py`, `quadas_summary.py`,
`strata_build.py`, `extraction_check.py`) that live under
`runs/dr-tarama/analysis/` — a path `.gitignore` excludes. Somebody cloning the
kit read release notes for files their checkout does not contain and never
could. Two entries were also written twice, in two lengths, because a section
re-stated from memory is not recognised as a duplicate by the person restating
it.

The line these tests draw is not "no project may be mentioned". Motivation is
what makes a changelog entry readable, and `consistency_check.py` gained its
table-totals check *because* one manuscript's table summed to 67 while its prose
said 68 — that sentence belongs here. The line is about the SUBJECT: if the
thing that changed is not in this repository, its record is not in this
repository's changelog. The review's own log lives at
`runs/dr-tarama/CHANGELOG.md`.

Four checks, each pinned to one half of what actually happened:
  - no entry may name a FILE under `runs/` (the leak's own signature);
  - no entry may name a `*.py` script that `scripts/` does not contain;
  - no entry may name a PATH the checkout cannot resolve;
  - no two DESCRIPTIVE `###` sections in one release may share a heading.

The third check exists because the second one had a blind spot that fired. Its
pattern matches a bare `foo.py`, and a name written the way a reader actually
reads it — `scripts/foo.py` — contains a slash and never matched. Five entries
went in that way, describing two scripts and a set of `meta.json` fields that
only ever existed under `runs/`, and every gate in the suite stayed green. A
check that covers the unqualified half of a name space is not a check, it is a
sample.

The third check looks only at headings carrying an em-dash summary, which is
this file's convention for a section that says what it did. Bare Keep a
Changelog category words (`### Added`, `### Fixed`, `### Changed`) repeat
throughout the released history by design — they interleave with the
descriptive ones as entries are grouped by date — and a check that failed on
those would be a check somebody deletes rather than a check somebody reads.
The defect this pins is the one that happened: two *named* sections, written
twice at two lengths, four sections apart.
"""
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"

# Scripts a changelog entry may legitimately name. `runs/*/analysis/*.py` is
# deliberately NOT here: those belong to a project, not to the kit.
KIT_SCRIPTS = {p.name for p in (ROOT / "scripts").glob("*.py")}
KIT_SCRIPTS |= {p.name for p in (ROOT / "scripts").glob("*.sh")}
KIT_SCRIPTS |= {p.name for p in (ROOT / ".claude" / "hooks").glob("*.py")}
KIT_SCRIPTS |= {p.name for p in (ROOT / "tests").glob("*.py")}
KIT_SCRIPTS |= {p.name for p in ROOT.glob("*.py")}
KIT_SCRIPTS |= {p.name for p in ROOT.glob("*.sh")}
KIT_SCRIPTS |= {p.name for p in (ROOT / "web").glob("*.py")}
KIT_SCRIPTS |= {p.name for p in (ROOT / "web").glob("*.mjs")}

# Named in prose as software the kit interoperates with or deliberately does not
# depend on, never as a file this repository ships. Kept explicit so the check
# stays a whitelist rather than a heuristic about which names "look external".
EXTERNAL = {
    "setup.py",      # packaging, discussed but not shipped
    "conftest.py",   # pytest's own file name, referenced generically
}


def _text() -> str:
    return CHANGELOG.read_text(encoding="utf-8")


def _releases() -> dict:
    """`## ` heading -> list of `### ` headings under it."""
    out, cur = {}, None
    for line in _text().splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif line.startswith("### ") and cur is not None:
            out[cur].append(line[4:].strip())
    return out


def test_the_changelog_names_no_file_under_runs():
    """`runs/` is gitignored: a clone cannot contain what such an entry describes.

    A *directory* under `runs/` may be named, and so may a project's own
    `CHANGELOG.md`. Stating where the boundary runs requires pointing at it —
    the entry that records this very fix has to say the leaked material now
    lives in `runs/dr-tarama/CHANGELOG.md`, and a check that forbade the
    sentence describing the rule would be a check somebody deletes. What no
    entry may do is name a FILE inside `runs/`, because naming one is how you
    describe having changed it, and that is the leak: eight scripts under
    `runs/dr-tarama/analysis/` were written up here as if the kit shipped them.
    """
    hits = []
    for n, line in enumerate(_text().splitlines(), 1):
        for m in re.finditer(r"runs/[\w.\-/]+", line):
            path = m.group(0)
            tail = path.rsplit("/", 1)[-1]
            if "." not in tail:            # a directory: names the boundary
                continue
            if tail.upper() == "CHANGELOG.MD":   # a project's own log, by design
                continue
            hits.append(f"{n}: {path}")
    assert not hits, (
        "CHANGELOG.md names files under runs/, which .gitignore excludes — so a "
        "clone cannot contain the files these entries describe. A project's own "
        "changes belong in that project's changelog (runs/<project>/CHANGELOG.md), "
        "not here; only the kit-side fix its run produced belongs here:\n  "
        + "\n  ".join(hits)
    )


def test_every_script_the_changelog_names_exists_in_the_kit():
    """A `foo.py` in the notes must be a `foo.py` in the checkout."""
    named = {m.group(1) for m in re.finditer(r"`([\w.\-]+\.(?:py|sh|mjs))`", _text())}
    missing = sorted(named - KIT_SCRIPTS - EXTERNAL)
    assert not missing, (
        "CHANGELOG.md names scripts this repository does not ship: "
        f"{missing}. Either the file was renamed and the entry was not updated, "
        "or the entry belongs to a project under runs/ and should be moved to "
        "that project's own changelog. If a name is genuinely external software "
        "being discussed rather than a file, add it to EXTERNAL with the reason."
    )


def _unknown_to_git(paths: list) -> list:
    """Of these paths, the ones git has never tracked. Empty if git cannot run.

    A missing or unusable git is not evidence that a path is fabricated, so the
    check declines rather than accuses: the same posture the kit's own scripts
    take when they cannot confirm something.
    """
    if not paths:
        return []
    import subprocess
    unknown = []
    for path in paths:
        try:
            proc = subprocess.run(
                ["git", "log", "--oneline", "-1", "--all", "--", path],
                capture_output=True, text=True, cwd=str(ROOT), timeout=20)
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            return []
        if proc.returncode != 0:
            return []
        if not proc.stdout.strip():
            unknown.append(path)
    return unknown


def test_every_path_the_changelog_names_resolves_in_the_checkout():
    """A `dir/foo.py` in the notes must be a `dir/foo.py` on disk.

    The sibling check above matches a bare filename, so it never saw the form
    an entry is actually written in. `scripts/supp_fetch.py` and
    `scripts/fetch_oa.py` were both released here while living only under
    `runs/<project>/scripts/`, together with a `pdf2md.py` described as
    reporting three counters when the shipped file reports one — five entries,
    every one of them naming a path, none of them matched.

    Only the location is checkable, and only that is claimed. Whether the file
    at that path does what the entry says it does is not something a test can
    read; that half stays a matter of writing the entry after the diff rather
    than after the intention.

    "Resolves" means on disk OR anywhere in this repository's history. The first
    version of this check asked only about the working tree, and that premise is
    wrong for the document it guards: a changelog is a record of what happened,
    so an entry that correctly describes work on a file which was later renamed
    or deleted is still correct, and failing it would push an author to falsify
    the record to make a test pass. The defect actually being hunted is a path
    that never existed HERE at all — the `runs/` leak — and git answers that
    without asking the entry to describe the present.
    """
    named = {m.group(1) for m in
             re.finditer(r"`((?:[\w.\-]+/)+[\w.\-]+\.(?:py|sh|mjs|ts|astro|json|toml|yml|yaml))`",
                         _text())}
    # Paths under runs/ are the other check's subject; failing here too would
    # report one defect twice and send the reader to the wrong explanation.
    named = {n for n in named if not n.startswith("runs/")}
    # A first segment this repository does not have is a path inside a USER's
    # paper project, not inside the kit: entries legitimately name
    # `analysis/experiment.json` and `drafts/citation-map.json` when describing
    # what a script writes into the project it runs on. The kit's own top-level
    # directories are the ones that exist here, so existence is the test.
    named = {n for n in named if (ROOT / n.split("/", 1)[0]).is_dir()}
    on_disk = {n for n in named if (ROOT / n).exists()}
    missing = sorted(_unknown_to_git(sorted(named - on_disk)))
    assert not missing, (
        "CHANGELOG.md names paths this repository has never had: "
        f"{missing}. An entry written from the intention rather than from the "
        "diff describes work that stayed in a branch, in a project under runs/, "
        "or in a plan. Move it to that project's own changelog, or delete it — "
        "a changelog the repository cannot corroborate is the same defect this "
        "kit's citation gate exists to catch, pointed at the kit itself."
    )


@pytest.mark.parametrize("release", sorted(_releases()))
def test_no_release_records_the_same_section_twice(release):
    """A section re-stated from memory reads as new to the person restating it."""
    descriptive = [h for h in _releases()[release] if "—" in h]
    dupes = [h for h, c in Counter(descriptive).items() if c > 1]
    assert not dupes, (
        f"CHANGELOG.md's `## {release}` carries the same descriptive `###` "
        f"heading more than once: {dupes}. The two that started this were the replication_pack.py fix and the "
        "secondary-review deposit addition, each written twice at different "
        "lengths. Merge them into the fuller one."
    )
