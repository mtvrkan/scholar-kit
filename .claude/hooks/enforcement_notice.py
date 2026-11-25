#!/usr/bin/env python3
"""SessionStart hook — say out loud when a kit project has NO enforcement layer.

The kit installs two ways and they give different things. A plugin install
ships the skills, the agents and the commands; it does NOT ship the
deterministic script layer or the hooks, because those have to live inside the
project (a `python scripts/...` call has to resolve, and a hook has to see your
PROJECT.md). `/new-project` is what materialises them.

Until now, a user who installed the plugin and skipped `/new-project` got the
prompts without the guarantees — and nothing said so. The READMEs warn about it
in three places, which is exactly the problem: a warning in a document is not a
mechanism, and the person who most needs it is the person who did not read it.

So this fires at session start, in the one situation where the gap is real:

    PROJECT.md is present  (this IS a paper project, not somebody else's repo)
    AND scripts/ or .claude/hooks/ is missing  (the enforcement layer is not)

Silent everywhere else, and that silence is the point — a notice that also
fired in ordinary directories would be trained away within a day. It is
deliberately not a block: an author mid-paper who wants to keep going is
entitled to, as long as nobody is telling them their citations are gated when
they are not.

Registered in `.claude-plugin/hooks.json` (the plugin surface), NOT in
.claude/settings.json — inside a properly materialised project the condition
above cannot be true, so registering it there would only add a hook that can
never fire. That asymmetry is the whole design, not an oversight. That file
holds no explanatory comment because its schema constrains its top-level keys
to hook event names, so the two things that would otherwise be written there
are written here instead:

  · It is the ONLY hook a plugin install ships. A plugin cannot carry the
    enforcement layer at all (scripts/ and .claude/hooks/ have to live inside
    the project); refusing to let that gap stay invisible is the one thing it
    can do.
  · The command is `python … || python3 …`. A clone install patches
    settings.json's hook commands to whichever interpreter it found
    (scripts/patch_hook_interpreter.py); nothing patches a plugin's hooks.json,
    because no install step runs. The chain covers the two real cases — Windows,
    where python.org's installer provides `python`, and macOS/Linux, where a
    Homebrew/apt Python commonly provides only `python3`. This script always
    exits 0, so the fallback fires on a MISSING interpreter and never on a
    notice that ran and had nothing to say (which would print it twice).

Change record: DECISIONS.md (D-085, § D-085d) holds the full reasoning,
including why this hook is NOT registered in .claude/settings.json and why it
warns rather than blocks; D-099 adds `--harness codex`. Behaviour is locked by
tests/test_enforcement_notice_hook.py — see `hooks` in tests/README.md.
"""
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

# One file per layer, each the load-bearing member of its own: registry_db.py
# is the only sanctioned writer of the source registry, phase_gate.py is the
# hook that holds the outline/verify/Major=0 gates. Checking a whole directory
# listing instead would report "present" for a half-copied runtime.
REQUIRED = (
    Path("scripts") / "registry_db.py",
    Path(".claude") / "hooks" / "phase_gate.py",
)


# Under Codex the same two layers are required, plus the file that wires the
# gates to that harness: a project materialised before the kit spoke Codex has
# scripts/ and .claude/hooks/ and is still ungated there, because nothing tells
# Codex to run them. Selected by `--harness codex` on the command line (the
# Codex plugin manifest passes it); with no flag the behaviour is unchanged.
CODEX_REQUIRED = REQUIRED + (Path(".codex") / "hooks.json",)


def _harness() -> str:
    argv = sys.argv[1:]
    if "--harness" in argv[:-1] and argv[argv.index("--harness") + 1] == "codex":
        return "codex"
    return "claude"


def missing_layers(root: Path, harness: str = "claude") -> list[str]:
    required = CODEX_REQUIRED if harness == "codex" else REQUIRED
    return [p.as_posix() for p in required if not (root / p).is_file()]


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    try:
        root = Path(payload.get("cwd") or ".")
        # The same marker every other hook scopes on (_project_scope.py). No
        # PROJECT.md means this is not a kit project and there is no gap to
        # report — it is simply somebody else's directory.
        if not (root / "PROJECT.md").is_file():
            sys.exit(0)
        harness = _harness()
        missing = missing_layers(root, harness)
        if not missing:
            sys.exit(0)
        print("=== scholar-kit: ENFORCEMENT ABSENT ===")
        print("This directory has a PROJECT.md but not the layer that enforces it.")
        print("Missing: " + ", ".join(missing))
        print("")
        print("What that means concretely — these are guidance right now, not gates:")
        print("  · the citation gate (/verify-citations must PASS before /critique)")
        print("  · the phase gates (outline approved before drafting; Major=0 before build)")
        print("  · script-ownership of sources/registry.jsonl and evidence/cards.jsonl")
        print("")
        if harness == "codex":
            print("Fix: run $new-project in this directory (it materialises scripts/,")
            print("templates/, .claude/hooks/ and .codex/, and wires the hooks to your")
            print("Python). A project that already has scripts/ needs only:")
            print("  python scripts/codex_sync.py --project --python <python|python3|py>")
            print("Then trust the project and review the gates once in /hooks —")
            print("Codex skips a hook until you have.")
        else:
            print("Fix: run /new-project in this directory (it materialises scripts/,")
            print("templates/ and .claude/hooks/, and wires the hooks to your Python),")
            print("or install the kit classically with INSTALL.sh / INSTALL.ps1.")
    except Exception:
        # Fail-open, and silently: this hook exists to prevent a false sense of
        # enforcement. Turning its own failure into a session-blocking error
        # would be a worse outcome than the gap it reports.
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
