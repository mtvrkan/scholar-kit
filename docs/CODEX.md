# Scholar-Kit under OpenAI Codex

The kit is one body of work read by two harnesses. Its skills, agents, hooks and
constitution are authored once, in Claude Code's formats, under `.claude/`. The
Codex half is generated from them by `scripts/codex_sync.py` into one folder,
`codex/`, and a test fails when it is stale. Nothing in `codex/` is written by
hand, and the gates exist once: Codex reaches the hooks in `.claude/hooks/`
through an adapter.

```text
.claude/            authored: skills, agents, hooks, settings      (Claude Code)
.claude-plugin/     Claude Code plugin manifest
codex/              GENERATED: skills, agents, hooks, rules, AGENTS.md  (Codex)
.codex-plugin/      Codex plugin manifest      } the two paths Codex
.agents/plugins/    Codex marketplace entry    } requires at the root
```

Checked against Codex CLI 0.172.

## Install

```text
codex plugin marketplace add mtvrkan/scholar-kit
codex plugin add scholar-kit@scholar-kit
```

As in Claude Code, the plugin gives you the commands and the knowledge skills,
and **not** the script layer, the gates or the agents — those live inside your
project. The first command is always:

```text
$new-project paper
```

Then, once per project:

1. **Trust the project** when Codex asks. Codex ignores a project's `.codex/`
   directory — hooks, agents, rules — until you have.
2. **Open `/hooks` and approve the Scholar-Kit gates.** Codex does not run a
   hook it has not been shown. Until you approve them, the phase gates and the
   data-file protection are guidance, not gates. A kit update that changes a
   gate asks for the review again; that is Codex's design, not a fault.

A project created earlier, from Claude Code, needs only its Codex wiring —
copy the kit's current `scripts/codex_sync.py` and `templates/codex/` into it,
then:

```bash
python scripts/codex_sync.py --project --python <python|python3|py>
```

In a project the same files are written where Codex looks for them:
`AGENTS.md`, `.codex/hooks.json`, `.codex/agents/`, `.codex/rules/` and
`.agents/skills/`.

## What maps to what

| Claude Code | Codex | How |
|---|---|---|
| `/draft methods` | `$draft methods` | the same `SKILL.md`, copied byte for byte into `codex/skills/` |
| a command only you can start (`disable-model-invocation: true`) | `policy.allow_implicit_invocation: false` | `agents/openai.yaml` beside each such skill, generated |
| the 11 knowledge skills, loaded when relevant | the same | no sidecar, so Codex may load them implicitly |
| `CLAUDE.md` | `codex/AGENTS.md` | the constitution verbatim under a short reading guide, generated |
| `.claude/agents/*.md` | `codex/agents/*.toml` | role text verbatim; generated |
| `model: opus / sonnet / haiku` | `model_reasoning_effort: high / medium / low` | the agent inherits your session's model; no model name is written down |
| `.claude/settings.json` hooks | `codex/hooks/hooks.json` | same six gates, same events, routed through `codex_adapter.py` |
| `Bash(rm -rf *)`-style deny rules | `codex/rules/scholar-kit.rules` (`forbidden`) | generated |
| `claude mcp add …` | `codex mcp add …` | `INSTALL.sh --mcp` does both when both CLIs are present |

## How the gates reach Codex

Codex's hook contract is close to Claude Code's: the same event names, the same
`permissionDecision: "deny"` reply, shell commands arriving as `Bash`. One thing
differs and it is the important one. Codex edits files with a single tool,
`apply_patch`, whose payload is the patch text — there is no `file_path`. A gate
written for `Write`/`Edit` sees a tool it does not know and answers with nothing,
which is indistinguishable from "checked, nothing to gate".

The adapter (`templates/codex/codex_adapter.py`, shipped as
`codex/hooks/codex_adapter.py`) reads the patch's `*** Add File:` /
`*** Update File:` / `*** Delete File:` / `*** Move to:` headers and asks the
gate once per touched path. One denial denies the patch. Everything else passes
through byte for byte. The gates themselves are not modified and not copied.

## What is weaker under Codex, stated plainly

- **A read-only agent is read-only by contract and by hook, not by toolset.**
  Claude Code enforces `tools: Read, Grep` by not handing the agent anything
  else. A Codex custom agent inherits the session's tools and its file can only
  ask. The adapter closes the gap that can be closed: any agent whose
  frontmatter grants no write tool is held to an empty write scope by
  `agent_write_scope`. That rests on Codex passing `agent_type` to the hook,
  which its hook schema declares and which this kit has tested against the
  schema, not against every Codex release.
- **The gates depend on your approval in `/hooks`.** There is no equivalent in
  Claude Code, where a project's hooks run once the project is trusted. Nothing
  inside the kit can detect that a hook was left unapproved.
- **`Read(./.env)`-style denies are not mirrored.** Codex expresses them as a
  permission profile, and a profile shipped by the kit would replace your own
  sandbox choice. To add them yourself, in the project's `.codex/config.toml`:

  ```toml
  default_permissions = "scholar-kit"

  [permissions.scholar-kit]
  extends = ":workspace"

  [permissions.scholar-kit.filesystem.":workspace_roots"]
  "**/.env" = "deny"
  "**/.env.*" = "deny"
  "**/*.pem" = "deny"
  "**/*.key" = "deny"
  ```

  Do not combine this with `sandbox_mode`; Codex treats the two as alternatives.
- **`permissions.allow` is not mirrored.** A Codex `allow` rule runs the command
  outside the sandbox without asking, which is a wider grant than Claude's.
- **Codex's own documentation calls tool hooks "a useful guardrail, not a
  complete enforcement boundary".** The same is true in Claude Code and
  [SECURITY.md](../SECURITY.md) says so; the OS-permission half of Invariant 6
  (the script-owned files are read-only on disk) does not depend on either
  harness.
- **`scripts/token_report.py`** reads Claude Code transcripts and reports
  nothing for a Codex session.

## Changing the kit

Edit the Claude half, then regenerate:

```bash
python scripts/codex_sync.py          # write
python scripts/codex_sync.py --check  # what CI runs
```

Anything edited by hand under `codex/` is overwritten, and a file there that
no source produces is removed. The two hand-written Codex sources live in
`templates/codex/`: the adapter, and `AGENTS.preamble.md` — the reading guide
at the top of `AGENTS.md`.
