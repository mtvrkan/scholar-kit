"""Tests for scripts/codex_sync.py and the Codex packaging it produces.

The kit is authored once, in Claude Code's formats, and its Codex half is
generated. That only holds if the generated files are regenerated every time a
source changes — and nothing at runtime notices when they are not: a new agent
simply does not exist under Codex, a newly gated hook simply does not run
there. `--check` in the first test is what turns that into a failing build.

The rest check what the generator's output must mean to Codex, against the
shapes Codex 0.172 documents and embeds in its own binary (hooks schema,
agent TOML keys, `agents/openai.yaml` policy, execpolicy `prefix_rule`).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "codex_sync.py"
CODEX = ROOT / "codex"

sys.path.insert(0, str(ROOT / "scripts"))
import codex_sync  # noqa: E402
from lib_common import parse_frontmatter  # noqa: E402


def _run(*args, cwd=ROOT):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                          text=True, cwd=cwd, encoding="utf-8")


def _settings() -> dict:
    return json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))


def _hooks() -> dict:
    return json.loads((CODEX / "hooks" / "hooks.json").read_text(encoding="utf-8"))


# ---------- the generated half is current ----------

def test_generated_files_are_up_to_date():
    proc = _run("--check")
    report = json.loads(proc.stdout)
    assert proc.returncode == 0 and not report["changed"] and not report["removed"], (
        "Codex files are stale — run: python scripts/codex_sync.py\n" + proc.stdout)


def test_check_detects_a_stale_file_and_writes_nothing(tmp_path):
    kit = _copy_kit(tmp_path)
    target = kit / "codex" / "agents" / "qa-auditor.toml"
    target.write_text("stale\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(kit / "scripts" / "codex_sync.py"), "--check"],
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 2
    assert "codex/agents/qa-auditor.toml" in json.loads(proc.stdout)["changed"]
    assert target.read_text(encoding="utf-8") == "stale\n"


def test_sync_is_idempotent(tmp_path):
    kit = _copy_kit(tmp_path)
    script = str(kit / "scripts" / "codex_sync.py")
    subprocess.run([sys.executable, script], capture_output=True, check=True)
    second = subprocess.run([sys.executable, script], capture_output=True, text=True,
                            encoding="utf-8")
    assert json.loads(second.stdout)["changed"] == []


def test_a_removed_agent_takes_its_codex_file_with_it(tmp_path):
    kit = _copy_kit(tmp_path)
    (kit / ".claude" / "agents" / "style-auditor.md").unlink()
    proc = subprocess.run([sys.executable, str(kit / "scripts" / "codex_sync.py")],
                          capture_output=True, text=True, encoding="utf-8")
    assert "codex/agents/style-auditor.toml" in json.loads(proc.stdout)["removed"]
    assert not (kit / "codex" / "agents" / "style-auditor.toml").exists()


def _copy_kit(tmp_path: Path) -> Path:
    import shutil
    kit = tmp_path / "kit"
    kit.mkdir()
    for name in (".claude", "codex", "scripts", "templates"):
        shutil.copytree(ROOT / name, kit / name,
                        ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "CLAUDE.md", kit / "CLAUDE.md")
    return kit


# ---------- agents ----------

AGENT_FILES = sorted((ROOT / ".claude" / "agents").glob("*.md"))


def test_every_agent_has_a_codex_definition_and_no_other_exists():
    assert {p.stem for p in (CODEX / "agents").glob("*.toml")} == \
           {p.stem for p in AGENT_FILES}


@pytest.mark.parametrize("md", AGENT_FILES, ids=lambda p: p.stem)
def test_agent_toml_parses_and_carries_the_whole_role(md):
    tomllib = pytest.importorskip("tomllib")
    data = tomllib.loads((CODEX / "agents" / f"{md.stem}.toml").read_text(encoding="utf-8"))
    # The keys Codex accepts in a custom agent file that this kit uses. No
    # `model`, `sandbox_mode` or `mcp_servers`: the first goes stale, the other
    # two are ignored by Codex in an agent file.
    assert set(data) == {"name", "description", "model_reasoning_effort",
                         "developer_instructions"}
    fm = parse_frontmatter(md.read_text(encoding="utf-8"))
    assert data["name"] == fm["name"] == md.stem
    assert data["description"] == fm["description"]
    assert data["model_reasoning_effort"] == codex_sync.EFFORT[fm["model"]]
    body = md.read_text(encoding="utf-8").split("\n---\n", 1)[1].strip()
    assert data["developer_instructions"].strip().endswith(body), (
        "the agent's role text did not survive the TOML round trip")
    for block in ("# ROLE", "# INPUT CONTRACT", "# PROCEDURE", "# OUTPUT CONTRACT"):
        assert block in data["developer_instructions"]


@pytest.mark.parametrize("md", AGENT_FILES, ids=lambda p: p.stem)
def test_agent_instructions_state_the_tool_contract(md):
    tomllib = pytest.importorskip("tomllib")
    text = tomllib.loads((CODEX / "agents" / f"{md.stem}.toml")
                         .read_text(encoding="utf-8"))["developer_instructions"]
    tools = {t.strip() for t in
             parse_frontmatter(md.read_text(encoding="utf-8"))["tools"].split(",")}
    assert text.startswith("# CODEX TOOL CONTRACT")
    assert ("READ-ONLY" in text.split("# ROLE")[0]) == (not tools & {"Write", "Edit"})


def test_toml_multiline_escaping_round_trips():
    tomllib = pytest.importorskip("tomllib")
    nasty = 'a \\d+ regex, a """triple""" quote, C:\\path\\n, ends with "'
    parsed = tomllib.loads("v = " + codex_sync._toml_multiline(nasty))
    assert parsed["v"].strip("\n") == nasty


def test_unknown_model_is_refused_not_guessed():
    with pytest.raises(SystemExit):
        codex_sync.agent_toml(_fake_agent("model: gpt-something"))


def _fake_agent(model_line: str) -> Path:
    import tempfile
    d = Path(tempfile.mkdtemp())
    p = d / "x.md"
    p.write_text(f"---\nname: x\ndescription: d\ntools: Read\n{model_line}\n---\n# ROLE\n",
                 encoding="utf-8")
    return p


# ---------- skills ----------

CLAUDE_SKILLS = ROOT / ".claude" / "skills"
SKILL_DIRS = sorted(p.parent for p in CLAUDE_SKILLS.glob("*/SKILL.md"))


def test_codex_skills_are_the_claude_skills_byte_for_byte():
    """One text, read by two harnesses. Everything under codex/skills/ is either
    an exact copy of the file at the same path under .claude/skills/ or a
    generated sidecar — nothing there has a life of its own."""
    assert SKILL_DIRS, "precondition"
    for f in (CODEX / "skills").rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(CODEX / "skills")
        if rel.parts[1:] == ("agents", "openai.yaml"):
            continue
        assert f.read_bytes() == (CLAUDE_SKILLS / rel).read_bytes(), rel
    for f in CLAUDE_SKILLS.rglob("*"):
        if f.is_file() and "__pycache__" not in f.parts:
            assert (CODEX / "skills" / f.relative_to(CLAUDE_SKILLS)).is_file(), f


def test_sidecars_exist_exactly_for_user_invoked_skills():
    """`disable-model-invocation: true` and `allow_implicit_invocation: false`
    are the same promise in two harnesses: the command runs when named."""
    for skill in SKILL_DIRS:
        fm = parse_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
        sidecar = CODEX / "skills" / skill.name / "agents" / "openai.yaml"
        if fm.get("disable-model-invocation") == "true":
            assert sidecar.is_file(), f"{skill.name}: no Codex sidecar"
            assert re.search(r"^policy:\n  allow_implicit_invocation: false$",
                             sidecar.read_text(encoding="utf-8"), re.M)
        else:
            assert not sidecar.exists(), (
                f"{skill.name} is a knowledge skill; a sidecar would hide it")


def test_the_claude_half_carries_no_codex_file():
    """The layout's whole point: what Codex reads is under codex/, and a reader
    of .claude/ finds nothing no Claude tool reads."""
    assert not list(CLAUDE_SKILLS.glob("*/agents/openai.yaml"))
    for stray in ("AGENTS.md", ".codex"):
        assert not (ROOT / stray).exists(), f"{stray} belongs under codex/ in the kit"
    assert not (ROOT / ".agents" / "skills").exists()


def test_a_hand_authored_sidecar_in_the_claude_half_is_refused(tmp_path):
    kit = _copy_kit(tmp_path)
    stray = kit / ".claude" / "skills" / "draft" / "agents" / "openai.yaml"
    stray.parent.mkdir()
    stray.write_text("policy:\n  allow_implicit_invocation: true\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(kit / "scripts" / "codex_sync.py")],
                          capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 1 and "generated for" in proc.stderr


def test_a_file_dropped_into_codex_skills_is_stale(tmp_path):
    kit = _copy_kit(tmp_path)
    (kit / "codex" / "skills" / "draft" / "NOTES.md").write_text("x", encoding="utf-8")
    script = str(kit / "scripts" / "codex_sync.py")
    check = subprocess.run([sys.executable, script, "--check"], capture_output=True,
                           text=True, encoding="utf-8")
    assert check.returncode == 2
    assert "codex/skills/draft/NOTES.md" in json.loads(check.stdout)["removed"]
    subprocess.run([sys.executable, script], capture_output=True, check=True)
    assert not (kit / "codex" / "skills" / "draft" / "NOTES.md").exists()


def test_skill_names_fit_codex_limits():
    for skill in SKILL_DIRS:
        fm = parse_frontmatter((skill / "SKILL.md").read_text(encoding="utf-8"))
        assert len(fm["name"]) <= 64
        assert fm["name"] == skill.name


# ---------- hooks ----------

def _wired(doc: dict) -> set[tuple[str, str]]:
    out = set()
    for event, groups in doc["hooks"].items():
        for group in groups:
            for h in group["hooks"]:
                m = re.search(r"(?:\.claude/hooks/(\w+)\.py|codex_adapter\.py (\w+))",
                              h["command"])
                out.add((event, m.group(1) or m.group(2)))
    return out


def test_every_claude_hook_is_wired_for_codex():
    assert _wired(_hooks()) == _wired(_settings())


def test_codex_matchers_cover_file_edits_and_shell():
    for event in ("PreToolUse", "PostToolUse"):
        for claude, codex in zip(_settings()["hooks"][event], _hooks()["hooks"][event], strict=True):
            tokens = set(codex["matcher"].split("|"))
            if set(claude["matcher"].split("|")) & {"Write", "Edit"}:
                assert "apply_patch" in tokens
            assert ("Bash" in tokens) == ("Bash" in claude["matcher"].split("|"))
            # Exact-alternative form: anything else Codex compiles as a regex.
            assert re.fullmatch(r"[A-Za-z0-9_|]+", codex["matcher"])


def test_hook_commands_cannot_block_from_the_wrong_directory():
    """`python <missing file>` exits 2, and Codex reads exit 2 as BLOCK. Started
    in a subdirectory, an unguarded command would deny every tool call."""
    for groups in _hooks()["hooks"].values():
        for group in groups:
            for h in group["hooks"]:
                assert h["command"].startswith("if [ -f .codex/hooks/codex_adapter.py ]; then ")
                assert h["command"].endswith("; fi")
                assert h["commandWindows"].startswith(
                    "if exist .codex\\hooks\\codex_adapter.py ")


def test_guarded_command_is_a_no_op_where_the_adapter_is_absent(tmp_path):
    command = _hooks()["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    proc = subprocess.run(["sh", "-c", command], input="{}", capture_output=True,
                          text=True, cwd=tmp_path)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")


def test_hook_timeouts_are_carried_over():
    claude = _settings()["hooks"]["PostToolUse"][0]["hooks"][0]
    codex = _hooks()["hooks"]["PostToolUse"][0]["hooks"][0]
    assert codex["timeout"] == claude["timeout"]


def test_python_flag_rewrites_the_interpreter_and_check_respects_it(tmp_path):
    kit = _copy_kit(tmp_path)
    script = str(kit / "scripts" / "codex_sync.py")
    subprocess.run([sys.executable, script, "--python", "python3"],
                   capture_output=True, check=True)
    text = (kit / "codex" / "hooks" / "hooks.json").read_text(encoding="utf-8")
    assert "then python3 .codex/hooks/codex_adapter.py" in text
    assert "then python .codex" not in text
    check = subprocess.run([sys.executable, script, "--check"], capture_output=True,
                           text=True, encoding="utf-8")
    assert check.returncode == 0, "a patched interpreter must not read as stale"


@pytest.mark.parametrize("bad", ["python3; rm -rf ~", "evil.exe", "python3 -c x",
                                 "$(whoami)", "/tmp/notpython"])
def test_python_flag_refuses_anything_that_is_not_an_interpreter(tmp_path, bad):
    kit = _copy_kit(tmp_path)
    before = (kit / "codex" / "hooks" / "hooks.json").read_text(encoding="utf-8")
    proc = subprocess.run([sys.executable, str(kit / "scripts" / "codex_sync.py"),
                           "--python", bad], capture_output=True, text=True,
                          encoding="utf-8")
    assert proc.returncode == 1
    assert (kit / "codex" / "hooks" / "hooks.json").read_text(encoding="utf-8") == before


# ---------- command rules ----------

def test_every_bash_deny_rule_is_mirrored_as_forbidden():
    rules = (CODEX / "rules" / "scholar-kit.rules").read_text(encoding="utf-8")
    denies = [d for d in _settings()["permissions"]["deny"] if d.startswith("Bash(")]
    assert denies, "precondition"
    assert rules.count("prefix_rule(") == len(denies)
    assert rules.count('decision = "forbidden"') == len(denies)
    for entry in denies:
        tokens = entry[5:-1].split()
        if tokens[-1] == "*":
            tokens = tokens[:-1]
        assert f"pattern = {json.dumps(tokens)}," in rules, entry


def test_no_allow_rule_is_generated():
    """A Codex `allow` runs the command outside the sandbox unprompted — wider
    than Claude's allow. Mirroring it would loosen the kit."""
    rules = (CODEX / "rules" / "scholar-kit.rules").read_text(encoding="utf-8")
    assert '"allow"' not in rules and '"prompt"' not in rules


# ---------- AGENTS.md ----------

def test_agents_md_ends_with_the_constitution_verbatim():
    agents = (CODEX / "AGENTS.md").read_text(encoding="utf-8")
    assert agents.endswith((ROOT / "CLAUDE.md").read_text(encoding="utf-8"))


def test_agents_md_fits_codex_default_instruction_budget():
    # project_doc_max_bytes defaults to 32 KiB; past it Codex stops reading and
    # the constitution's tail — the style core — would silently not load.
    assert len((CODEX / "AGENTS.md").read_bytes()) < 32 * 1024


def test_agents_md_tells_codex_how_to_read_the_kit():
    head = (CODEX / "AGENTS.md").read_text(encoding="utf-8").split("# Scholar-Kit Operating Rules")[0]
    for needle in ("apply_patch", "$outline", ".codex/agents/", "/hooks",
                   "update_plan", "codex mcp add"):
        assert needle in head, needle


# ---------- the adapter copy ----------

def test_shipped_adapter_is_the_source():
    assert (CODEX / "hooks" / "codex_adapter.py").read_bytes() == \
           (ROOT / "templates" / "codex" / "codex_adapter.py").read_bytes()


# ---------- project layout ----------

def _materialise(tmp_path: Path) -> Path:
    """What /new-project leaves behind before it runs codex_sync --project."""
    import shutil
    proj = tmp_path / "paper"
    proj.mkdir()
    for name in (".claude", "scripts", "templates"):
        shutil.copytree(ROOT / name, proj / name,
                        ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "CLAUDE.md", proj / "CLAUDE.md")
    (proj / "PROJECT.md").write_text("<!-- scholar-kit-project -->\n", encoding="utf-8")
    return proj


def _sync_project(proj: Path, *args):
    return subprocess.run([sys.executable, str(proj / "scripts" / "codex_sync.py"),
                           "--project", *args], capture_output=True, text=True,
                          encoding="utf-8")


def test_project_mode_writes_the_paths_codex_reads(tmp_path):
    proj = _materialise(tmp_path)
    assert _sync_project(proj).returncode == 0
    for rel in ("AGENTS.md", ".codex/hooks.json", ".codex/hooks/codex_adapter.py",
                ".codex/rules/scholar-kit.rules", ".codex/agents/qa-auditor.toml",
                ".agents/skills/draft/SKILL.md", ".agents/skills/draft/agents/openai.yaml",
                ".agents/skills/academic-writing/SKILL.md"):
        assert (proj / rel).is_file(), rel
    assert not (proj / "codex").exists(), "codex/ is the kit's layout, not a project's"
    assert not (proj / ".agents" / "skills" / "academic-writing" / "agents").exists()
    assert _sync_project(proj, "--check").returncode == 0


def test_project_files_are_the_kit_files(tmp_path):
    proj = _materialise(tmp_path)
    _sync_project(proj)
    pairs = [("AGENTS.md", "AGENTS.md"), (".codex/hooks.json", "hooks/hooks.json"),
             (".codex/agents/reviewer-critic.toml", "agents/reviewer-critic.toml"),
             (".codex/rules/scholar-kit.rules", "rules/scholar-kit.rules"),
             (".agents/skills/outline/SKILL.md", "skills/outline/SKILL.md")]
    for project_rel, kit_rel in pairs:
        assert (proj / project_rel).read_bytes() == (CODEX / kit_rel).read_bytes(), project_rel


def test_generated_project_hook_command_denies_a_protected_edit(tmp_path):
    """End to end, the way Codex runs it: the shell command from the generated
    hooks.json, in the project directory, with an apply_patch payload."""
    proj = _materialise(tmp_path)
    assert _sync_project(proj, "--python", sys.executable).returncode == 0
    hooks = json.loads((proj / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    command = hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert "protect_data_files" in command
    payload = {"hook_event_name": "PreToolUse", "tool_name": "apply_patch",
               "tool_input": {"command": "*** Begin Patch\n*** Update File: "
                                         "evidence/cards.jsonl\n@@\n-a\n+b\n*** End Patch"}}
    proc = subprocess.run(["sh", "-c", command], input=json.dumps(payload),
                          capture_output=True, text=True, cwd=proj)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    # ...and from a subdirectory it is a silent no-op, never a block.
    (proj / "drafts").mkdir(exist_ok=True)
    sub = subprocess.run(["sh", "-c", command], input=json.dumps(payload),
                         capture_output=True, text=True, cwd=proj / "drafts")
    assert (sub.returncode, sub.stdout) == (0, "")


def test_project_mode_replaces_a_legacy_skills_symlink(tmp_path):
    proj = _materialise(tmp_path)
    (proj / ".agents").mkdir()
    try:
        (proj / ".agents" / "skills").symlink_to(Path("..") / ".claude" / "skills",
                                                 target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable on this platform")
    assert _sync_project(proj, "--check").returncode == 2
    assert _sync_project(proj).returncode == 0
    assert not (proj / ".agents" / "skills").is_symlink()
    assert not list((proj / ".claude" / "skills").glob("*/agents/openai.yaml")), (
        "sidecars were written through the link into the Claude half")


def test_agents_md_is_not_generated_from_an_import_stub(tmp_path):
    """A project whose CLAUDE.md is `@AGENTS.md` keeps its constitution IN
    AGENTS.md; generating from the stub would overwrite it with a dangling
    reference."""
    proj = _materialise(tmp_path)
    (proj / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (proj / "AGENTS.md").write_text("the real constitution\n", encoding="utf-8")
    proc = _sync_project(proj)
    assert proc.returncode == 1 and "@import" in proc.stderr
    assert (proj / "AGENTS.md").read_text(encoding="utf-8") == "the real constitution\n"


# ---------- plugin manifests ----------

def _codex_plugin() -> dict:
    return json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))


def _claude_plugin() -> dict:
    return json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))


def test_codex_plugin_directory_holds_only_the_manifest():
    assert [p.name for p in (ROOT / ".codex-plugin").iterdir()] == ["plugin.json"]


def test_both_plugins_are_the_same_plugin():
    codex, claude = _codex_plugin(), _claude_plugin()
    for field in ("name", "version", "license", "repository", "keywords"):
        assert codex[field] == claude[field], field
    assert (claude["skills"], codex["skills"]) == ("./.claude/skills/", "./codex/skills/")
    assert codex["author"]["name"] == claude["author"]["name"]


def test_codex_plugin_required_fields():
    plugin = _codex_plugin()
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", plugin["name"]) and len(plugin["name"]) <= 64
    for field in ("version", "description", "interface"):
        assert plugin[field]
    assert plugin["author"]["name"]
    assert (ROOT / plugin["skills"].removeprefix("./")).is_dir()


def test_codex_plugin_ships_the_enforcement_notice_for_codex():
    hooks = _codex_plugin()["hooks"]["hooks"]
    assert list(hooks) == ["SessionStart"]
    command = hooks["SessionStart"][0]["hooks"][0]["command"]
    assert "${PLUGIN_ROOT}/.claude/hooks/enforcement_notice.py" in command
    assert command.count("--harness codex") == 2  # python || python3


def test_codex_plugin_description_directs_users_to_new_project():
    assert "$new-project" in _codex_plugin()["description"]


def test_codex_marketplace_points_at_this_plugin():
    market = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json")
                        .read_text(encoding="utf-8"))
    (entry,) = market["plugins"]
    assert entry["name"] == _codex_plugin()["name"]
    assert entry["source"] == {"source": "local", "path": "./"}
    assert entry["policy"]["installation"] == "AVAILABLE"
    assert entry["category"]


# ---------- enforcement notice, Codex mode ----------

def _notice(cwd: Path, *argv):
    return subprocess.run(
        [sys.executable, str(ROOT / ".claude" / "hooks" / "enforcement_notice.py"), *argv],
        input=json.dumps({"cwd": str(cwd)}), capture_output=True, text=True,
        encoding="utf-8").stdout


def test_notice_reports_a_project_that_is_gated_for_claude_but_not_codex(tmp_path):
    (tmp_path / "PROJECT.md").touch()
    for rel in ("scripts/registry_db.py", ".claude/hooks/phase_gate.py"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).touch()
    assert _notice(tmp_path) == ""
    out = _notice(tmp_path, "--harness", "codex")
    assert "ENFORCEMENT ABSENT" in out and "Missing: .codex/hooks.json" in out
    assert "codex_sync.py --project" in out and "/hooks" in out
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "hooks.json").touch()
    assert _notice(tmp_path, "--harness", "codex") == ""


def test_notice_stays_silent_outside_a_project_in_codex_mode(tmp_path):
    assert _notice(tmp_path, "--harness", "codex") == ""
