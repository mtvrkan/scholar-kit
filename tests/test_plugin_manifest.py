"""Tests for the Claude Code plugin manifests (.claude-plugin/).

The agent list in `plugin.json` is written out file by file — the manifest
schema rejects a bare directory for `agents`, so there is no way to say "all of
them". That makes the list drift-prone in exactly one direction: add an agent,
forget the manifest, and the plugin ships without it. Nothing at runtime
complains; the agent is simply missing for every plugin user while every local
test still passes.

`claude plugin validate` checks the schema. These tests check the thing it
cannot: that the manifest still describes THIS kit.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
PLUGIN_DIR = ROOT / ".claude-plugin"


def _plugin() -> dict:
    return json.loads((PLUGIN_DIR / "plugin.json").read_text(encoding="utf-8"))


def _marketplace() -> dict:
    return json.loads((PLUGIN_DIR / "marketplace.json").read_text(encoding="utf-8"))


# ---------- presence and schema basics ----------

def test_both_manifests_exist():
    assert (PLUGIN_DIR / "plugin.json").is_file()
    assert (PLUGIN_DIR / "marketplace.json").is_file()


def test_plugin_declares_a_name():
    # The only field the schema actually requires.
    assert _plugin().get("name")


def test_marketplace_entry_names_the_plugin():
    entries = _marketplace()["plugins"]
    assert [e["name"] for e in entries] == [_plugin()["name"]]


# ---------- the manifest still describes this kit ----------

def test_every_agent_file_is_listed():
    on_disk = {p.name for p in (ROOT / ".claude" / "agents").glob("*.md")}
    listed = {Path(p).name for p in _plugin()["agents"]}
    assert listed == on_disk, (
        f"plugin.json's agents list is out of sync — missing: "
        f"{sorted(on_disk - listed)}, stale: {sorted(listed - on_disk)}")


def test_every_listed_agent_path_resolves():
    for rel in _plugin()["agents"]:
        assert (ROOT / rel.removeprefix("./")).is_file(), f"{rel} does not exist"


def test_skills_path_resolves_and_holds_skills():
    skills = _plugin()["skills"]
    assert isinstance(skills, str) and skills.startswith("./")
    d = ROOT / skills.removeprefix("./")
    assert d.is_dir()
    assert list(d.glob("*/SKILL.md")), "skills path contains no SKILL.md"


def test_all_paths_are_plugin_relative():
    # The schema requires every custom path to start with "./".
    paths = [_plugin()["skills"], *_plugin()["agents"],
             *_marketplace()["plugins"][0]["skills"]]
    for p in paths:
        assert p.startswith("./"), f"{p} is not plugin-root-relative"


# ---------- consistency with the rest of the repo ----------

def test_plugin_version_matches_the_citation_record():
    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    m = re.search(r"^version:\s*(\S+)\s*$", cff, re.MULTILINE)
    assert m, "CITATION.cff has no version"
    assert _plugin()["version"] == m.group(1)


def test_plugin_and_marketplace_versions_agree():
    assert _plugin()["version"] == _marketplace()["plugins"][0]["version"]


def test_declared_license_matches_the_repo():
    assert _plugin()["license"] == "MIT"
    assert _marketplace()["plugins"][0]["license"] == "MIT"
    assert "MIT License" in (ROOT / "LICENSE").read_text(encoding="utf-8")


def test_marketplace_description_counts_match_the_catalog():
    """The storefront copy is a published number like any other.

    `test_governance_docs.py` binds every count in both READMEs and in site.ts
    to the repository itself. This string was the one that got away: it shipped
    reading "17 workflow commands + 11 knowledge skills + 9 subagents" against a
    real 43 / 11 / 10 — stale by more than half, in the first sentence anyone
    sees before installing. Every other test here checks structure (paths
    resolve, versions agree, agents are listed), and structure was fine.

    The commands/knowledge split lives in web/src/data/site.ts, which
    test_governance_docs.py already re-derives against .claude/skills/; reading
    it here rather than restating it keeps one source of truth for the split.
    """
    desc = _marketplace()["plugins"][0]["description"]
    skills = [p.parent.name for p in (ROOT / ".claude" / "skills").glob("*/SKILL.md")]
    agents = list((ROOT / ".claude" / "agents").glob("*.md"))
    site = (ROOT / "web" / "src" / "data" / "site.ts").read_text(encoding="utf-8")

    def _site(field: str) -> int:
        m = re.search(rf"^\s*{field}:\s*(\d+),", site, re.M)
        assert m, f"site.ts declares no {field}"
        return int(m.group(1))

    commands, knowledge = _site("commands"), _site("knowledge")
    assert commands + knowledge == len(skills), (
        f"site.ts splits {commands}+{knowledge} but .claude/skills/ holds {len(skills)}")
    for n, label, pattern in (
        (commands, "workflow commands", rf"\b{commands} workflow commands\b"),
        (knowledge, "knowledge skills", rf"\b{knowledge} knowledge skills\b"),
        (len(agents), "subagents", rf"\b{len(agents)} subagents\b"),
    ):
        assert re.search(pattern, desc), (
            f"marketplace.json does not claim {n} {label}; description reads: {desc[:120]!r}")


def test_marketplace_description_directs_users_to_new_project():
    # A plugin install ships skills and agents; the deterministic script layer
    # and the enforcement hooks are materialised into the user's project by
    # /new-project. Someone who installs the plugin and never runs it gets the
    # prompts without the guarantees, so the entry has to say so.
    assert "/new-project" in _marketplace()["plugins"][0]["description"]
