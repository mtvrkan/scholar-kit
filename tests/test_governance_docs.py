"""Tests for the kit's governance/provenance documents.

These files make claims *about the kit* to people outside it — a citation
record, a scope boundary, an inventory count. They drift silently: a version
bumps in one place, a boundary gets crossed in code while the recorded boundary
still says it will not be, a README keeps counting tools that were renamed. Each
test here pins one such claim to something checkable.

CITATION.cff is parsed without PyYAML: the kit's runtime dependencies do not
include it, and adding one so a metadata file can be linted would be a poor
trade. The file's shape is flat enough to read with a small parser, and these
tests assert exactly that flatness.
"""
import ast
import json
import os
import re
import sys

import pytest
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _cff() -> dict:
    """Top-level scalar keys of CITATION.cff.

    Deliberately shallow — it reads `key: value` at column 0 and ignores nested
    blocks and comments. If the file ever needs real YAML parsing, that is a
    signal the metadata grew beyond what a citation record should carry.
    """
    out = {}
    for line in (ROOT / "CITATION.cff").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith((" ", "-", "#")):
            continue
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


# ---------- CITATION.cff ----------

def test_citation_file_exists_and_has_required_fields():
    cff = _cff()
    for field in ("cff-version", "title", "message", "type", "license", "version"):
        assert cff.get(field), f"CITATION.cff missing required field {field!r}"


def test_citation_declares_the_repo_license():
    # A citation record advertising a different licence than LICENSE grants is
    # the kind of mismatch nobody notices until someone relies on it.
    assert _cff()["license"] == "MIT"
    assert "MIT License" in (ROOT / "LICENSE").read_text(encoding="utf-8")


def test_citation_has_an_author():
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert "family-names:" in text and "given-names:" in text


def test_citation_version_matches_latest_released_changelog_version():
    # CHANGELOG's released sections are `## <version> — <date>`; Unreleased work
    # sits above them and must not be treated as the citable version.
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    released = re.findall(r"^##\s+(\d+\.\d+\.\d+)\s", changelog, re.MULTILINE)
    assert released, "CHANGELOG has no released version heading"
    assert _cff()["version"] == released[0], (
        f"CITATION.cff version {_cff()['version']!r} != latest released "
        f"CHANGELOG version {released[0]!r}")


def test_every_surface_that_states_a_version_states_the_citable_one():
    """The version tests covered the machine-readable surfaces and stopped there.

    `CITATION.cff`, `plugin.json`, `marketplace.json`, `site.ts` and the newest
    CHANGELOG heading were each bound to another — and the two places a human
    actually reads a version were bound to nothing. They drifted exactly as far
    as being unchecked allows: both READMEs printed a 1.0.0 badge over a
    sentence saying 1.1.0, and `web/package.json` said 1.1.0 as well. Three
    wrong numbers on the two documents a reader opens first, none of which the
    suite could see.

    The badge is matched by its shields.io URL rather than by the alt text: the
    alt read `v1.0.0` while the image behind it read `1.1.0`, so asserting on
    the label would have passed against the wrong picture.
    """
    version = _cff()["version"]
    surfaces = {
        "web/package.json":
            [json.loads((ROOT / "web" / "package.json").read_text(encoding="utf-8"))["version"]],
    }
    for name in ("README.md", "README.tr.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        badge = re.findall(r"img\.shields\.io/badge/[^/]*?(\d+\.\d+\.\d+)", text)
        prose = re.findall(r"(?:Sürüm|Version)\s+\*\*(\d+\.\d+\.\d+)\*\*", text)
        assert badge, f"{name} shows no version badge"
        assert prose, f"{name} states no version in prose"
        surfaces[name] = badge + prose

    wrong = {k: sorted(set(v) - {version}) for k, v in surfaces.items() if set(v) - {version}}
    assert not wrong, (
        f"CITATION.cff declares {version}, but these state something else: {wrong}")


def _zenodo() -> dict:
    return json.loads((ROOT / ".zenodo.json").read_text(encoding="utf-8"))


def test_zenodo_metadata_agrees_with_the_citation_file():
    """Zenodo's GitHub integration reads `.zenodo.json` when it archives a
    release, and whatever is in it becomes the citation record other people
    copy. Left absent, the archive is credited to a GitHub username and
    described by the repository blurb; left unchecked, it drifts from
    `CITATION.cff` and the project ends up with two different citations for one
    piece of software — the failure this kit exists to prevent, in its own
    metadata."""
    z, cff = _zenodo(), _cff()
    assert z["title"] == cff["title"], "the archive would carry a different title"
    assert z["license"].lower() == cff["license"].lower()
    assert z["upload_type"] == "software"
    names = [c["name"] for c in z["creators"]]
    assert names == ["Türkan, Mehmet"], (
        f"creators {names} — a Zenodo record credited to a username rather than "
        f"a person is a citation nobody can resolve to an author")
    assert set(z["keywords"]) == set(_cff_keywords())


def test_zenodo_metadata_declares_no_version_and_no_doi():
    """Both are minted, not written. Zenodo takes the version from the git tag,
    so a `version` here is a second source of truth that can disagree with the
    tag it ships under; and a DOI written before the archive exists is the
    fabricated identifier `test_citation_declares_no_unearned_doi` refuses one
    file over."""
    z = _zenodo()
    for field in ("version", "doi"):
        assert field not in z, (
            f".zenodo.json declares {field!r} — remove it; Zenodo assigns it")


def _cff_keywords() -> list[str]:
    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    # [ \t] rather than \s: \s matches a newline, which lets the repetition skip
    # over the comment block below the list and adopt it as keywords.
    block = re.search(r"(?m)^keywords:\n((?:[ \t]+-[ \t]+.+\n)+)", text)
    assert block, "CITATION.cff no longer lists keywords"
    return [line.strip().lstrip("-").strip() for line in block.group(1).splitlines()]


def test_citation_declares_no_unearned_doi():
    # A DOI is minted by archiving a release. Writing one before that archive
    # exists is a fabricated identifier — the exact defect class this kit is
    # built to prevent, and it would be indefensible in its own metadata.
    assert "doi" not in _cff(), (
        "CITATION.cff carries a top-level doi — remove it unless an archived "
        "release with that DOI actually exists")


# ---------- POSITIONING.md ----------

def test_positioning_document_exists():
    assert (ROOT / "POSITIONING.md").exists()


def test_positioning_records_the_honest_failure_shape():
    # The load-bearing admission: a consistently reported fabrication passes
    # every gate. If this sentence ever disappears, the document has become
    # marketing.
    text = (ROOT / "POSITIONING.md").read_text(encoding="utf-8")
    assert "uydurma tutarlı biçimde raporlandığı sürece" in text


def test_positioning_lists_rejected_mechanisms():
    text = (ROOT / "POSITIONING.md").read_text(encoding="utf-8")
    assert "## Reddedilen mekanizmalar" in text


def test_rejected_bibliographic_memory_matches_the_enforced_invariant():
    # POSITIONING claims BibTeX comes only from doi2bib.py. That claim is only
    # true while CLAUDE.md's invariant says so too.
    positioning = (ROOT / "POSITIONING.md").read_text(encoding="utf-8")
    claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "doi2bib.py" in positioning
    assert "doi2bib.py" in claude_md and "NO FABRICATION" in claude_md


def test_rejected_plagiarism_scoring_matches_submit_check():
    # POSITIONING says the kit refuses to emit a similarity score and delegates
    # to institutional tooling; submit-check must actually still say that.
    positioning = (ROOT / "POSITIONING.md").read_text(encoding="utf-8")
    submit = (ROOT / ".claude" / "skills" / "submit-check" / "SKILL.md").read_text(
        encoding="utf-8")
    assert "Turnitin" in positioning
    assert "DOES NOT run plagiarism checks" in submit


def _positionings() -> tuple[str, str]:
    return ((ROOT / "POSITIONING.md").read_text(encoding="utf-8"),
            (ROOT / "POSITIONING.en.md").read_text(encoding="utf-8"))


def test_english_positioning_exists_and_both_cross_link():
    tr, en = _positionings()
    assert "POSITIONING.en.md" in tr, "Turkish POSITIONING does not link the English one"
    assert "POSITIONING.md" in en, "English POSITIONING does not link the Turkish one"


def test_english_positioning_records_the_honest_failure_shape():
    # Same load-bearing admission as the Turkish original. A translation that
    # softens this sentence turns the document into marketing for the audience
    # least able to check it against the code.
    _, en = _positionings()
    assert "as long as the fabrication is reported consistently" in en


def test_both_positionings_record_the_same_refused_mechanisms():
    # A boundary that exists in one language and not the other is worse than an
    # untranslated document: it reads as a deliberate, differing scope.
    def refused(text: str) -> int:
        body = text.split("## ")  # section-split; the refusals live in one section
        section = [s for s in body if s.lower().startswith(("reddedilen", "refused"))]
        assert section, "a POSITIONING has no refused-mechanisms section"
        # Refusal headings are `**Sentence.**` at line start. The trailing period
        # inside the asterisks is what distinguishes them from ordinary emphasis
        # that happens to land at the start of a wrapped line.
        return len(re.findall(r"^\*\*[^*]+\.\*\*", section[0], re.MULTILINE))

    tr_n, en_n = (refused(t) for t in _positionings())
    assert tr_n == en_n, (
        f"POSITIONING refusals disagree: TR lists {tr_n}, EN lists {en_n}")
    assert tr_n >= 7, f"expected at least 7 recorded refusals, found {tr_n}"


def test_english_readme_points_at_the_english_positioning():
    # Otherwise an English reader following the scope link lands on a document
    # they cannot read — the one place where that matters most.
    en_readme = _readmes()[1]
    assert "POSITIONING.en.md" in en_readme
    assert not re.search(r"\]\(POSITIONING\.md\)", en_readme), (
        "English README still links the Turkish POSITIONING")


def test_rejected_fabricated_gold_labels_matches_the_calibration_reference():
    positioning = (ROOT / "POSITIONING.md").read_text(encoding="utf-8")
    calib = (ROOT / ".claude" / "skills" / "critique" / "reference"
             / "calibration.md").read_text(encoding="utf-8")
    assert "altın etiketi" in positioning or "altın küme" in positioning
    assert "ships **no** labelled papers" in calib or "no** labelled papers" in calib


# ---------- the two READMEs ----------
# A translation is the first thing to go stale: the Turkish README gets a new
# number and the English one keeps the old one for months, with nobody reading
# both. These pin only the CHECKABLE claims — prose is free to differ.

def _readmes() -> tuple[str, str]:
    """(Turkish, English) — and the English one is `README.md`.

    The default README was Turkish for the whole private development period,
    with English as `README.en.md`. That is the wrong way round for a public
    repository: `README.md` is what GitHub renders to everyone who arrives, and
    the reader who cannot read it is the one least able to find the other file.
    Turkish did not become secondary — it moved to `README.tr.md` and both are
    held to exactly the same assertions below.
    """
    return ((ROOT / "README.tr.md").read_text(encoding="utf-8"),
            (ROOT / "README.md").read_text(encoding="utf-8"))


def test_both_readmes_exist_and_cross_link():
    tr, en = _readmes()
    assert "README.md" in tr, "Turkish README does not link the English one"
    assert "README.tr.md" in en, "English README does not link the Turkish one"


def test_both_readmes_agree_on_the_test_count():
    tr, en = _readmes()
    tr_n = re.search(r"\((\d+) test geçer", tr)
    en_n = re.search(r"\((\d+) pass", en)
    assert tr_n and en_n, "a README no longer states its test count"
    assert tr_n.group(1) == en_n.group(1), (
        f"README test counts disagree: TR {tr_n.group(1)} vs EN {en_n.group(1)}")


def test_both_readmes_agree_on_the_tool_count():
    tr, en = _readmes()
    tr_n = re.search(r"\((\d+) araç\)", tr)
    en_n = re.search(r"\((\d+) tools\)", en)
    assert tr_n and en_n, "a README no longer states its tool count"
    assert tr_n.group(1) == en_n.group(1)


def test_readme_tool_count_matches_the_scripts_directory():
    # The number in both READMEs is a claim about scripts/ that nothing else
    # checks — and it went stale the first time a tool was added without
    # bumping it. Counted against the directory, NOT validate_kit.SCRIPTS:
    # that list is a required-presence manifest, not an inventory, so a new
    # tool is legitimately absent from it.
    tools = [p for p in SCRIPTS.iterdir()
             if p.is_file() and p.suffix in (".py", ".sh")
             and not p.name.startswith("_")
             and not p.name.startswith("lib_")]  # imported by siblings, never invoked
    claimed = int(re.search(r"\((\d+) araç\)", _readmes()[0]).group(1))
    assert claimed == len(tools), (
        f"README claims {claimed} tools; scripts/ holds {len(tools)} invocable "
        f"ones: {sorted(p.name for p in tools)}")


# ---------- CONTRIBUTING.md ----------
# The rule this file enforces everywhere else — "a number in a document is
# checkable" — did not reach CONTRIBUTING.md, and its opening line drifted to
# "35 tools ... ~1370 tests" while the READMEs and the site had all moved on.
# The number a new contributor reads first was the one number nothing checked.

def _contributing() -> str:
    return (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")


def _contributing_inventory() -> dict[str, int]:
    m = re.search(r"The repository is large — (\d+) tools, (\d+) skills, "
                  r"(\d+) agents, (\d+) tests", _contributing())
    assert m, "CONTRIBUTING.md no longer opens with its inventory line"
    tools, skills, agents, tests = (int(g) for g in m.groups())
    return {"tools": tools, "skills": skills, "agents": agents, "tests": tests}


def test_contributing_inventory_matches_the_repository():
    claimed = _contributing_inventory()
    tools = [p for p in SCRIPTS.iterdir()
             if p.is_file() and p.suffix in (".py", ".sh")
             and not p.name.startswith(("_", "lib_"))]
    assert claimed["tools"] == len(tools), (
        f"CONTRIBUTING claims {claimed['tools']} tools; scripts/ holds {len(tools)}")
    skills = list((ROOT / ".claude" / "skills").glob("*/SKILL.md"))
    assert claimed["skills"] == len(skills)
    agents = list((ROOT / ".claude" / "agents").glob("*.md"))
    assert claimed["agents"] == len(agents)


def test_contributing_test_count_agrees_with_the_published_one():
    # Chained rather than re-collected: the READMEs' figure is already pinned to
    # a real collection run by test_published_test_count_matches_the_suite, so
    # agreeing with it is agreeing with the suite — at no extra cost.
    tr = _readmes()[0]
    published = int(re.search(r"\((\d+) test geçer", tr).group(1))
    assert _contributing_inventory()["tests"] == published, (
        f"CONTRIBUTING states {_contributing_inventory()['tests']} tests, the "
        f"READMEs state {published}")


# ---------- the build scripts' interpreter is a declared prerequisite ----------
# Both final-output builders are shell scripts and every skill/agent invokes
# them as `bash scripts/...`. The dependency check listed python, pandoc,
# latexmk and the Claude CLI — never bash — so a Windows machine with pandoc and
# MiKTeX installed still failed at /submit-check's build step, after every check
# had reported [ok]. A prerequisite nothing states and nothing probes is one the
# user meets by luck.

def test_the_builders_are_still_shell_scripts():
    # The premise of the two tests below. If the builders were ever ported to
    # Python, the bash prerequisite would become false and these should go.
    for name in ("docx_build.sh", "latex_build.sh"):
        assert (SCRIPTS / name).is_file(), f"{name} is gone — re-check the bash prerequisite"


def test_both_installers_probe_for_bash():
    ps1 = (ROOT / "INSTALL.ps1").read_text(encoding="utf-8")
    sh = (ROOT / "INSTALL.sh").read_text(encoding="utf-8")
    assert re.search(r"Get-Command bash\b", ps1), (
        "INSTALL.ps1 does not check for bash — the interpreter both build "
        "scripts need, and the one a Windows machine is least likely to have")
    assert re.search(r"command -v bash\b", sh), "INSTALL.sh does not check for bash"


def test_both_readmes_declare_the_bash_prerequisite():
    tr, en = _readmes()
    for text, label in ((tr, "Turkish"), (en, "English")):
        assert "bash" in text and "Git.Git" in text, (
            f"the {label} README does not name bash (and where Windows gets it) "
            f"as a prerequisite of the DOCX/PDF builds")


# ---------- inventory claims, bound to the filesystem ----------
# The tool count was already pinned to scripts/ below; the hook, agent and skill
# counts were not, and the hook count was wrong in three places at once (both
# READMEs and the site) for months. "7 hooks" counted FILES in .claude/hooks/,
# which includes the underscore-prefixed shared libraries — _shell_write_sink,
# _project_scope, _degrade — that no event ever invokes. The registered-entry
# count in settings.json is what "7 hooks" was claiming to describe, and it is 6.
#
# Every one of these derives the true number from the artifact rather than
# restating it, which is the only kind of assertion that cannot go stale
# alongside the thing it checks.

def _site_ts() -> str:
    return (ROOT / "web" / "src" / "data" / "site.ts").read_text(encoding="utf-8")


def _site_number(field: str) -> int:
    m = re.search(rf"^\s*{field}:\s*(\d+),", _site_ts(), re.M)
    assert m, f"web/src/data/site.ts declares no {field}"
    return int(m.group(1))


def _registered_hooks() -> set[str]:
    """Hook scripts settings.json actually wires to an event."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    names = set()
    for entries in settings["hooks"].values():
        for matcher in entries:
            for hook in matcher["hooks"]:
                m = re.search(r"([\w-]+\.py)", hook["command"])
                assert m, f"unparseable hook command: {hook['command']}"
                names.add(m.group(1))
    return names


def test_hook_count_claims_match_the_registered_hooks():
    registered = _registered_hooks()
    assert registered, "settings.json registers no hooks at all"
    n = len(registered)
    tr, en = _readmes()
    assert re.search(rf"\b{n} hook\b", tr), (
        f"Turkish README does not claim {n} hooks; settings.json registers "
        f"{sorted(registered)}")
    assert re.search(rf"\b{n} enforcement\s+\n?hooks\b", en) or f"{n} enforcement" in en, (
        f"English README does not claim {n} enforcement hooks")
    assert _site_number("hooks") == n, (
        f"site.ts says {_site_number('hooks')} hooks, settings.json registers {n}")


def test_every_registered_hook_file_exists_and_is_not_a_library():
    # A settings.json entry pointing at a file that is gone fails open in the
    # worst way: the hook never runs and nothing says so.
    for name in _registered_hooks():
        assert (ROOT / ".claude" / "hooks" / name).is_file(), (
            f"settings.json registers {name}, which does not exist")
        assert not name.startswith("_"), (
            f"{name} is underscore-prefixed — that prefix marks a shared library, "
            f"not an entry point")


def test_agent_count_claims_match_the_agents_directory():
    agents = sorted(p.name for p in (ROOT / ".claude" / "agents").glob("*.md"))
    n = len(agents)
    tr, en = _readmes()
    assert re.search(rf"\b{n} uzman subagent\b", tr), (
        f"Turkish README does not claim {n} subagents; found {agents}")
    assert re.search(rf"\b{n} specialist subagents\b", en), (
        f"English README does not claim {n} subagents; found {agents}")
    assert _site_number("agents") == n
    # Not just the headline claim — EVERY agent count a README states. The
    # assertions above pin one sentence each ("10 uzman subagent" / "10
    # specialist subagents"), and the Turkish README's directory-structure
    # paragraph quietly said "(9 subagent)" for a release while both of them
    # passed: the same file contradicting itself, two hundred lines apart, in
    # the section a reader consults to find out what is installed.
    for label, text, pattern in (
        ("Turkish", tr, r"(\d+)\s+(?:uzman\s+)?subagent\b"),
        ("English", en, r"(\d+)\s+(?:specialist\s+)?subagents?\b"),
    ):
        stated = {int(x) for x in re.findall(pattern, text)}
        assert stated <= {n}, (
            f"{label} README states agent counts {sorted(stated)}; "
            f".claude/agents/ holds {n}")
    # The plugin manifest lists them one by one, so it drifts independently.
    manifest = json.loads(
        (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    listed = sorted(Path(p).name for p in manifest["agents"])
    assert listed == agents, (
        f"plugin.json lists {listed}, .claude/agents/ holds {agents}")


def test_every_agent_frontmatter_survives_a_yaml_parse():
    """An agent whose frontmatter will not parse is not a broken agent — it is an
    ABSENT one, and nothing says so.

    `methodology-advisor` shipped with an unquoted multi-line `description:` whose
    continuation line read `...before a meta-analysis: may these studies be`. A
    plain YAML scalar cannot contain `: ` — the parser reads that line as a new
    mapping key, the frontmatter fails, and the harness silently drops the agent.
    It was missing from the session's agent list for a release while
    `validate_kit.py` reported "agents: 10, problems: 0", because that check
    counts FILES and never parses what it counts.

    Found the way these things are found: by dispatching to the agent and being
    told it does not exist — during the one task it exists for, ruling on whether
    a set of studies may be pooled.

    Parsed as TEXT rather than with PyYAML, for the reason test_lint_and_ci_config
    already gives: PyYAML is not a dependency of this kit and adding one so a
    meta-test can read frontmatter would be a poor trade.
    """
    key = re.compile(r"^([A-Za-z_][\w-]*):(.*)$")
    for path in sorted((ROOT / ".claude" / "agents").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{path.name} has no frontmatter"
        block = text.split("---\n", 2)[1]

        quoted = False
        for line in block.splitlines():
            if not line.strip():
                continue
            m = key.match(line)
            if m:
                value = m.group(2).strip()
                # A quoted scalar may contain anything, including ": ".
                quoted = value.startswith(('"', "'")) and not (
                    len(value) > 1 and value.endswith(value[0]))
                continue
            # Continuation of the previous key's value.
            assert quoted or ": " not in line, (
                f"{path.name}: frontmatter continuation line contains an unquoted "
                f"': ', which ends the YAML scalar and drops the agent silently —\n"
                f"    {line.strip()}\n"
                f"  Fix by quoting that key's value.")


def test_skill_count_claims_match_the_skills_directory():
    skills = sorted(p.parent.name for p in (ROOT / ".claude" / "skills").glob("*/SKILL.md"))
    n = len(skills)
    tr, _ = _readmes()
    assert re.search(rf"\b{n} skill:", tr), (
        f"Turkish README does not claim {n} skills; found {len(skills)}")
    # The README splits that total into commands + knowledge skills, and site.ts
    # states both halves. The split is a claim too: it must add back up.
    commands, knowledge = _site_number("commands"), _site_number("knowledge")
    assert commands + knowledge == n, (
        f"site.ts splits skills as {commands} commands + {knowledge} knowledge "
        f"= {commands + knowledge}, but .claude/skills/ holds {n}")


def test_both_readmes_state_the_same_install_commands():
    tr, en = _readmes()
    for cmd in ("/plugin marketplace add mtvrkan/scholar-kit",
                "/plugin install scholar-kit"):
        assert cmd in tr and cmd in en, f"{cmd!r} missing from a README"


def test_both_readmes_carry_the_plugin_caveat():
    # Installing the plugin without running /new-project gives guidance without
    # guarantees. If either README loses that, users get a false impression of
    # what enforcement they have.
    tr, en = _readmes()
    assert "/new-project" in tr and "/new-project" in en
    assert "garantileri almazsınız" in tr
    assert "without the guarantees" in en


# ---------- docs/PERFORMANCE.md ----------
# The one page most likely to acquire an invented table over time: a per-command
# cost figure is the single most requested number and the hardest to justify.

def _performance() -> str:
    return (ROOT / "docs" / "PERFORMANCE.md").read_text(encoding="utf-8")


def test_performance_doc_exists_and_is_linked_from_both_readmes():
    assert (ROOT / "docs" / "PERFORMANCE.md").exists()
    for readme in _readmes():
        assert "docs/PERFORMANCE.md" in readme


def test_performance_doc_publishes_no_per_command_cost_table():
    # Guard against the exact regression: someone adds "| /draft | 25k | $0.40 |"
    # because it looks helpful. Nobody measured it, and it would be believed.
    text = _performance()
    rows = [ln for ln in text.splitlines()
            if ln.strip().startswith("|") and re.search(r"/[a-z-]+\s*\|", ln)
            and re.search(r"\d+\s*(?:k|K|tokens?|\$)", ln)]
    assert not rows, f"PERFORMANCE.md grew a per-command cost table: {rows}"


def test_performance_doc_hardcodes_no_prices():
    # A dollar figure in prose is a price claim. Code spans are excluded on
    # purpose: in THIS document a fenced block is the example rates file, and an
    # inline span is a quoted specimen of the kind of figure the kit refuses to
    # publish. The guard is aimed at assertions, not at quoted specimens — and
    # the per-command-table test above still catches the regression that matters.
    prose = re.sub(r"```.*?```", "", _performance(), flags=re.DOTALL)
    prose = re.sub(r"`[^`\n]*`", "", prose)
    assert not re.search(r"\$\s*\d", prose), "PERFORMANCE.md states a price in prose"


def test_performance_doc_points_at_the_measuring_tool():
    assert "token_report.py" in _performance()
    assert (ROOT / "scripts" / "token_report.py").exists()


def test_token_report_ships_no_price_table():
    # The script must not acquire a default rates dict either — that is the same
    # staleness problem one file over.
    src = (ROOT / "scripts" / "token_report.py").read_text(encoding="utf-8")
    body = re.sub(r'"""(?:.|\n)*?"""', "", src, count=1)  # drop the module docstring
    assert not re.search(r'"(?:input|output|cache_read|cache_write)"\s*:\s*\d', body), \
        "token_report.py hardcodes prices; rates must come from --rates"


# ---------- SECURITY.md ----------
# The document makes a falsifiable promise about what leaves the machine. That
# promise is worth exactly as much as the test that re-derives it from the code.

# Detecting network access by searching the source TEXT cannot tell a function
# being NAMED from a function being CALLED, and it is silenced by anything that
# spells the call differently. `getattr(requests, "get")(url)` reaches the
# network and matches none of the strings a text scan looks for; a docstring
# that politely names `http_get_with_retry` matches all of them and reaches
# nothing. Both errors point the same way for the reader of SECURITY.md: one
# adds a file that does not belong, the other drops one that does — silently,
# with the suite still green. So the detection is done over the parsed syntax.

# Importing any of these means the module can open a socket. `urllib.parse` is
# deliberately absent: it manipulates strings and touches nothing.
NET_MODULES = {"requests", "urllib.request", "urllib.robotparser", "urllib3",
               "httpx", "http.client", "aiohttp", "socket", "ftplib", "smtplib"}
# Calling one of these reaches the network even where the import is elsewhere.
NET_CALLS = {"urlopen", "http_get_with_retry"}


def _module_roots(tree: ast.AST) -> set:
    """Every module name this file imports, dotted form kept."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module)
    return names


def _called_names(tree: ast.AST) -> set:
    """Every name appearing in CALL position — `f()` and `x.f()` alike."""
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                called.add(func.id)
            elif isinstance(func, ast.Attribute):
                called.add(func.attr)
    return called


def _subprocess_scripts(tree: ast.AST) -> set:
    """Kit scripts this file may run as a subprocess.

    A script that opens no socket of its own still puts requests on the wire
    when it shells out to one that does, and the reader asking "what happens if
    I run this?" is owed that.

    The test is not "a `.py` literal sits inside a `subprocess.run(...)` call",
    because it usually does not: the argument list is built a line earlier and
    handed to a local helper, and `write_verify_status.py` — the one file this
    branch exists for — spells it exactly that way. So the condition is the
    weaker pair: the module imports `subprocess` AND names a script. That is
    coarse in the safe direction. A name that is mentioned but never executed
    costs one over-listing in a security document, which a reader can check
    against the source; a name that is executed but never listed is the silence
    this whole detector exists to prevent.
    """
    if "subprocess" not in _module_roots(tree):
        return set()
    return {Path(n.value).name for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value.endswith(".py")}


def _networked_scripts() -> dict:
    """{script name: why it is networked}, closed over indirection.

    Running another kit script that makes requests is still making them, so the
    set is grown to a fixed point rather than read off one pass. IMPORTING one
    is deliberately not the same thing: almost every script here imports
    `lib_common`, which holds the shared retry helper alongside a dozen offline
    utilities, and counting the import would name the whole `scripts/` directory
    as networked. What matters is the CALL, and a call to the helper is caught
    by name wherever the import happened.
    """
    parsed, why = {}, {}
    for path in sorted(SCRIPTS.glob("*.py")):
        try:
            parsed[path.name] = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:  # a file that will not parse is its own failure
            raise AssertionError(f"{path.name} does not parse: {exc}") from exc

    for name, tree in parsed.items():
        imported = _module_roots(tree)
        direct = sorted(imported & NET_MODULES)
        calls = sorted(_called_names(tree) & NET_CALLS)
        if direct:
            why[name] = f"imports {', '.join(direct)}"
        elif calls:
            why[name] = f"calls {', '.join(calls)}"

    changed = True
    while changed:
        changed = False
        for name, tree in parsed.items():
            if name in why:
                continue
            reached = _subprocess_scripts(tree)
            via = sorted(r for r in reached if r in why and r != name)
            if via:
                why[name] = f"runs {', '.join(via)}"
                changed = True
    return why
# Every host the kit's scripts are permitted to contact. Adding one without
# adding it here — and to SECURITY.md — fails the build.
DECLARED_HOSTS = {"doi.org", "api.crossref.org", "api.openalex.org",
                  "www.scimagojr.com", "scimagojr.com", "doaj.org",
                  "www.elsevier.com", "elsevier.com"}


def _security() -> str:
    return (ROOT / "SECURITY.md").read_text(encoding="utf-8")


def test_security_policy_exists():
    assert (ROOT / "SECURITY.md").exists()
    assert (ROOT / "CONTRIBUTING.md").exists()


def test_every_networked_script_is_named_in_the_security_policy():
    # SECURITY.md tells the reader to run a grep and expect a specific list. If
    # a new script starts making requests, that instruction becomes a lie —
    # silently, in the one document a cautious user relies on.
    text = _security()
    why = _networked_scripts()
    undocumented = sorted(n for n in why if n not in text)
    assert not undocumented, (
        f"these scripts touch the network but SECURITY.md does not name them: "
        f"{ {n: why[n] for n in undocumented} }")


def test_the_security_policy_grep_never_names_a_file_the_syntax_clears():
    """The document hands the reader a `grep`; the suite reads the syntax.

    The two are allowed to differ, but only one way. A text scan cannot follow a
    subprocess, so it will legitimately MISS a file — three of the eleven here
    reach the network only by running `doi2bib.py`, and the document says so in
    prose rather than pretending the grep finds them. What it must never do is
    the opposite: answer with a file that opens nothing. That happens the moment
    a docstring politely names `http_get_with_retry`, and it teaches a careful
    reader to distrust a list that was right.

    So: grep ⊆ syntax. Under-reporting is a documented limit of the instrument;
    over-reporting is the instrument lying.
    """
    import subprocess
    # The pattern is READ OUT of SECURITY.md rather than copied into this file.
    # A copy drifts, and a drifted copy would test a command no reader runs.
    printed = re.search(r'grep -ln "([^"]+)" scripts/\*\.py', _security())
    assert printed, "SECURITY.md no longer prints the grep it tells the reader to run"
    # The files are passed explicitly: `scripts/*.py` is expanded by the reader's
    # shell, and this test must not depend on which shell that is.
    files = [str(f) for f in sorted(SCRIPTS.glob("*.py"))]
    try:
        proc = subprocess.run(["grep", "-l", printed.group(1), *files],
                              capture_output=True, text=True, cwd=str(ROOT))
    except (FileNotFoundError, OSError):
        pytest.skip("no grep on this machine")
    assert proc.returncode in (0, 1), (
        f"the grep SECURITY.md prints does not run: rc={proc.returncode} "
        f"{proc.stderr[:200]!r}")
    greped = {Path(line).name for line in proc.stdout.split() if line.endswith(".py")}
    assert greped, "the grep SECURITY.md prints matches nothing at all"
    invented = sorted(greped - set(_networked_scripts()))
    assert not invented, (
        f"SECURITY.md's grep answers with {invented}, which the parsed syntax "
        f"says opens nothing — the marker is being NAMED there, not called. "
        f"Rename the mention or drop the file from the document's list.")


def test_the_security_policy_counts_its_networked_files_the_same_in_both_languages():
    """Both halves of SECURITY.md state the count, and they disagreed.

    The English half said nine, the Turkish half said eight, and neither was
    right: eleven scripts reach the network, two of them through `doi2bib.py`
    and named in no version of the list. A count written in prose has no gate on
    it — nothing recomputes it when a script starts making requests, and the two
    halves drift apart one edit at a time. It is small enough to spell in words
    in both languages, which is exactly why nothing caught it.

    Both numbers the document prints are checked: the total, and the smaller one
    the grep can actually answer with. Only the words are checked, not the
    sentences around them — a count can be right in a claim that is wrong.
    """
    why = _networked_scripts()
    total = len(why)
    # The grep the document prints can only see a call spelled in the source; the
    # rest reach the network through a child process. Both numbers are printed,
    # so both are re-derived here rather than trusted.
    direct = sum(1 for r in why.values() if not r.startswith("runs"))
    words = {3: ("three", "üç"), 8: ("eight", "sekiz"), 9: ("nine", "dokuz"),
             10: ("ten", "on"), 11: ("eleven", "on bir"), 12: ("twelve", "on iki"),
             13: ("thirteen", "on üç"), 14: ("fourteen", "on dört")}
    for n, label in ((total, "networked scripts"), (direct, "the grep finds")):
        assert n in words, f"{n} ({label}) — extend the words table"
        for word in words[n]:
            assert word in _security().lower(), (
                f"{n} — {label} — but SECURITY.md does not say '{word}' anywhere. "
                f"One language half is still stating an old count; both halves "
                f"state it, so both have to be right.")


def test_no_script_contacts_an_undeclared_host():
    found = set()
    for path in SCRIPTS.glob("*.py"):
        for host in re.findall(r"https?://([A-Za-z0-9._-]+)",
                               path.read_text(encoding="utf-8", errors="replace")):
            found.add(host)
    undeclared = sorted(h for h in found if h not in DECLARED_HOSTS)
    assert not undeclared, (
        f"undeclared outbound host(s): {undeclared} — add them to SECURITY.md's "
        f"table and to DECLARED_HOSTS, or remove the call")


def test_the_user_agent_carries_no_real_address():
    # The kit identifies itself with a fixed placeholder. If someone ever
    # "improves" this by interpolating the user's git email — the polite thing to
    # do for Crossref — it would start transmitting an identifier the policy
    # promises never leaves.
    for name in ("doi2bib.py", "venue_check.py", "citation_triangulate.py"):
        src = (SCRIPTS / name).read_text(encoding="utf-8")
        agents = re.findall(r'"User-Agent":\s*"([^"]*)"', src)
        assert agents, f"{name} sends no User-Agent"
        for agent in agents:
            assert "example.org" in agent, (
                f"{name}'s User-Agent is {agent!r} — SECURITY.md promises a "
                f"placeholder, not a real address")


def test_security_policy_states_there_is_no_telemetry():
    assert "no telemetry" in _security().lower()


def test_security_policy_admits_the_hooks_fail_open():
    # The most tempting sentence to soften, and the one a reader most needs.
    text = _security()
    assert "fail OPEN" in text or "fail open" in text.lower()
    assert "not a security boundary" in text


# ---------- the site: security headers, share card, landmarks ----------

# The postbuild step's own regex. Kept identical on purpose: if the two ever
# disagree about what counts as an inline script, the hash set and the script
# set disagree and the page silently stops running its own JavaScript.
_INLINE_SCRIPT = re.compile(r"<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)</script>")


def _csp(html: str) -> dict[str, list[str]]:
    m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)"', html)
    assert m, "the page carries no Content-Security-Policy"
    out = {}
    for directive in m.group(1).split(";"):
        parts = directive.split()
        if parts:
            out[parts[0]] = parts[1:]
    return out


def test_the_share_card_exists_and_is_the_size_it_claims():
    # og:image dimensions are advertised in meta tags; an unfurler that trusts
    # them and gets something else crops the card. The PNG header is read
    # directly rather than through Pillow, which is not a runtime dependency.
    png = ROOT / "docs" / "og.png"
    assert png.exists(), "docs/og.png is missing — run `python web/make_og.py` and rebuild"
    head = png.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n", "og.png is not a PNG"
    width = int.from_bytes(head[16:20], "big")
    height = int.from_bytes(head[20:24], "big")
    assert (width, height) == (1200, 630), f"og.png is {width}x{height}, not 1200x630"


def test_the_structured_faq_matches_the_visible_one():
    # Marking up questions the page does not actually answer is cloaking, and
    # search engines treat it as such. This asserts the JSON-LD is derived from
    # the same array the page renders.
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    blocks = [b for b in _INLINE_SCRIPT.findall(html) if '"FAQPage"' in b]
    assert len(blocks) == 1, "index.html should carry exactly one FAQPage graph"
    graph = json.loads(blocks[0])
    faq = next(n for n in graph["@graph"] if n["@type"] == "FAQPage")
    assert len(faq["mainEntity"]) >= 4, "an FAQ of three answers is not worth marking up"
    for entry in faq["mainEntity"]:
        assert entry["name"] in html, (
            f"the structured FAQ asks {entry['name']!r}, which is not on the page")
        assert "<" not in entry["acceptedAnswer"]["text"], (
            "answer text still carries markup — it should be stripped for JSON-LD")


# ---------- the published test count ----------
# Every other number the READMEs and site.ts state is re-derived from the
# repository above. The test count was the exception: it was written by hand,
# nothing checked it, and it sat at 1213 while the suite had moved on — the exact
# staleness this file exists to prevent, in the one number that describes this
# file's own suite. Deriving it needs a real collection run, which is cheap
# (~3s) because collection does not execute anything.

def _collect(*extra_args: str) -> int:
    """Number of test ITEMS pytest collects, optionally under a marker filter.

    A subprocess, not an in-process pytest call: re-entering pytest from inside a
    running session corrupts the outer run's state. `-p no:cacheprovider` keeps
    it from writing a .pytest_cache into the checkout.

    Counting collected ITEMS rather than `@pytest.mark.live` occurrences in the
    source is the whole point. One marker on a parametrized test produces many
    items, so the source-grep answer (4) and the truth (8) differ by a factor of
    two — the first version of this section grepped, and was wrong in exactly the
    direction that would have let a stale published number pass.
    """
    import subprocess
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider", *extra_args],
        capture_output=True, text=True, cwd=ROOT, encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert proc.returncode == 0, f"collection failed:\n{proc.stdout[-2000:]}"
    total = sum(int(m.group(1))
                for m in re.finditer(r"^tests[/\\].*?: (\d+)$", proc.stdout, re.M))
    assert total > 0, f"parsed no per-file counts from collection output:\n{proc.stdout[-2000:]}"
    return total


def test_published_test_count_matches_the_suite():
    """README.md, README.tr.md and site.ts all state how many tests pass. The
    number is the collected total minus the live-network tests that skip by
    default — the figure a reader reproduces by running `python -m pytest`."""
    total = _collect()
    skipped = _published_skip_count()
    expected = total - skipped
    tr, en = _readmes()
    assert f"{expected} test geçer" in tr, (
        f"Turkish README states a stale test count; the suite collects {total} "
        f"and skips {skipped} by default, so it should say {expected}")
    assert f"{expected} pass" in en, (
        f"English README states a stale test count; expected {expected}")
    assert _site_number("tests") == expected, (
        f"site.ts says {_site_number('tests')} tests, the suite passes {expected}")


def _published_skip_count() -> int:
    """The skip count the READMEs publish, taken from the Turkish one and
    required to agree with the English one — asserted rather than assumed,
    because the two drift independently."""
    tr, en = _readmes()
    m_tr = re.search(r"(\d+)'i canlı ağ testi", tr)
    m_en = re.search(r"(\d+) live-network tests are skipped", en)
    assert m_tr and m_en, "a README no longer states how many tests skip by default"
    assert m_tr.group(1) == m_en.group(1), (
        f"READMEs disagree on the skip count: TR {m_tr.group(1)}, EN {m_en.group(1)}")
    return int(m_tr.group(1))


def test_published_skip_count_matches_the_live_tests():
    """`8 live-network tests are skipped` is a claim about how many ITEMS carry
    the live marker, which is not the number of markers in the source."""
    declared = _published_skip_count()
    actual = _collect("-m", "live")
    assert declared == actual, (
        f"the READMEs publish {declared} skipped live tests, but the suite "
        f"collects {actual} under `-m live`")


# ---------- files the repo needs but .gitignore can silently swallow ----------
#
# This whole section exists because a bare `data/` in .gitignore matched at any
# depth and quietly untracked `web/src/data/site.ts`, and a bare `build/` did
# the same to `project-template/build/`. Neither showed up in any run here: the
# maintainer's working copy had both files, so every test that reads them passed
# locally while a fresh clone failed six of them outright and shipped a
# `/new-project` skeleton with no build directory.
#
# The lesson is that "the file is on disk" and "the file is in the repository"
# are different claims, and every test above only ever checked the first. These
# two check the second, which is the one a user's clone depends on.

def _tracked() -> set[str] | None:
    """Every path git actually tracks, or None outside a git checkout.

    None rather than a failure: the suite is also run from exported trees (the
    release archive, `git checkout-index`), where there is no index to consult
    and the question is unanswerable rather than answered badly.
    """
    import subprocess
    try:
        proc = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                              capture_output=True, text=True, encoding="utf-8")
    except (OSError, FileNotFoundError):  # pragma: no cover - git absent
        return None
    if proc.returncode != 0:
        return None
    return {p.replace("\\", "/") for p in proc.stdout.split("\0") if p}


def test_the_sites_data_module_is_actually_in_the_repository():
    tracked = _tracked()
    if tracked is None:
        pytest.skip("not a git checkout — nothing to ask about tracking")
    # `tools.ts` was on this list and has been deleted with the four reference
    # chapters it fed. One module is left, and it is the one every count in this
    # suite is read from.
    for rel in ("web/src/data/site.ts",):
        assert rel in tracked, (
            f"{rel} exists on disk but git does not track it — check .gitignore "
            f"for an unanchored rule matching one of its parent directories. "
            f"Every count this suite verifies is read from that file, so a clone "
            f"without it fails here with FileNotFoundError rather than a diagnosis.")


def test_every_project_skeleton_directory_ships_in_the_repository():
    """`/new-project` copies `project-template/` verbatim, so a skeleton
    directory that is not tracked simply does not reach a new project — and
    `test_first_run.py` cannot see it locally, because the untracked directory
    is sitting right there in the working copy."""
    tracked = _tracked()
    if tracked is None:
        pytest.skip("not a git checkout — nothing to ask about tracking")
    required = ("sources", "evidence", "analysis", "bib", "outline", "drafts",
                "reviews", "exports", "build")
    for d in required:
        prefix = f"project-template/{d}/"
        assert any(p.startswith(prefix) for p in tracked), (
            f"project-template/{d}/ ships no tracked file, so a clone's "
            f"/new-project produces a project without {d}/. Git cannot store an "
            f"empty directory — add a .gitkeep, and a .gitignore negation if a "
            f"rule matches the directory name.")
