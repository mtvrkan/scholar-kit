#!/usr/bin/env python3
"""token_report.py — what this kit actually cost, measured from your own sessions.

The kit is built under a stated twin constraint: maximum output quality at
minimum token spend. That is a claim, and until now nothing in the repository
could check it. Publishing a hand-made "typical cost per command" table would
have been the easy option and the wrong one — the numbers would be invented, in
a kit whose entire positioning is that invented numbers are the defect it
exists to prevent.

So this ships the instrument instead of the answer. It reads Claude Code's own
session transcripts for THIS project and reports the tokens they actually
recorded: totals, main session vs subagents, per model, and per slash command.
The numbers are yours, from your work, on your data.

Attribution rule, stated because it is a choice and not a fact: a slash command
"owns" every assistant turn from its invocation until the next slash command or
the end of the session. Anything you did in between — a follow-up question, a
correction, a tangent — is counted against the command that was running. That
inflates long conversational commands and is why `--per-command` prints turn
counts alongside tokens: a command with 40 turns behind it was a conversation,
not a command.

NOT measured here, and not inferable from a transcript: money. Prices differ by
plan, tier and time, and are not recorded in the transcript. Supply your own
`--rates` file to get a cost column; without one, none is printed. A rate table
baked into this repository would go stale silently and be believed anyway.

  rates file: {"claude-opus-5": {"input": 5.0, "output": 25.0,
                                 "cache_write": 6.25, "cache_read": 0.5}}
  (USD per million tokens; keys optional, missing ones count as 0)

Usage:
  python scripts/token_report.py
  python scripts/token_report.py --per-command --per-session
  python scripts/token_report.py --rates my-rates.json --json
  python scripts/token_report.py --transcripts <dir>     # explicit location
Output: single JSON object. Exit codes: 0 ok · 1 error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib_common import die, emit

COMMAND_RE = re.compile(r"<command-name>\s*(/?[\w-]+)\s*</command-name>")
# Claude Code's own UI commands. They are real spend, but they are not this
# kit's commands, and folding them into a per-command table would misattribute
# the cost of compaction to whatever ran before it.
BUILTIN_COMMANDS = {"/compact", "/clear", "/exit", "/help", "/init", "/cost",
                    "/model", "/config", "/status", "/resume", "/login",
                    "/logout", "/doctor", "/memory", "/review", "/pr-comments"}
# Names that are BOTH a Claude Code builtin and a command this kit defines. The
# transcript records only the name, so the two are indistinguishable — attributing
# them either way would be a guess. They are excluded from the per-command table
# and named in `excluded_commands` instead, because a bucket silently missing from
# a cost report is the same defect as a fabricated one.
AMBIGUOUS_COMMANDS = {"/status"}
TOKEN_FIELDS = ("input_tokens", "output_tokens",
                "cache_creation_input_tokens", "cache_read_input_tokens")
RATE_KEYS = {"input_tokens": "input", "output_tokens": "output",
             "cache_creation_input_tokens": "cache_write",
             "cache_read_input_tokens": "cache_read"}


def default_transcript_dir(project_root: Path) -> Path:
    """Claude Code stores transcripts under ~/.claude/projects/<mangled-cwd>/.

    The directory name is the absolute project path with every non-alphanumeric
    character replaced by a dash, which is why this is derived rather than
    guessed at.
    """
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(project_root.resolve()))
    return Path.home() / ".claude" / "projects" / slug


def _empty() -> dict:
    return {f: 0 for f in TOKEN_FIELDS}


def _add(into: dict, usage: dict) -> None:
    for f in TOKEN_FIELDS:
        value = usage.get(f)
        if isinstance(value, (int, float)):
            into[f] += int(value)


def _totals(bucket: dict) -> dict:
    billable = bucket["input_tokens"] + bucket["output_tokens"] \
        + bucket["cache_creation_input_tokens"] + bucket["cache_read_input_tokens"]
    return {**bucket, "total_tokens": billable}


def cost_of(bucket: dict, rates: dict | None, model: str) -> float | None:
    if not rates:
        return None
    table = rates.get(model)
    if not isinstance(table, dict):
        return None
    return round(sum(bucket[f] * float(table.get(RATE_KEYS[f], 0) or 0) / 1_000_000
                     for f in TOKEN_FIELDS), 6)


def scan(transcript_dir: Path) -> dict:
    """Walk every transcript, bucketing usage by session, model, agent and command."""
    sessions: dict[str, dict] = {}
    models: dict[str, dict] = {}
    commands: dict[str, dict] = {}
    excluded: dict[str, int] = {}
    main, sub = _empty(), _empty()
    turns_main = turns_sub = 0
    files = sorted(transcript_dir.glob("*.jsonl"))

    for path in files:
        current = None  # command owning the turns that follow
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # a transcript being written to can end mid-line
            if not isinstance(rec, dict):
                continue
            message = rec.get("message") if isinstance(rec.get("message"), dict) else {}

            if rec.get("type") == "user":
                content = message.get("content")
                text = content if isinstance(content, str) else json.dumps(content or "")
                found = COMMAND_RE.search(text)
                if found:
                    name = found.group(1)
                    if not name.startswith("/"):
                        name = "/" + name
                    # A builtin ends the previous command's ownership rather than
                    # extending it: the turns after /compact belong to compaction,
                    # not to whatever the kit was doing before it.
                    current = None if name in BUILTIN_COMMANDS else name
                continue

            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue
            is_sub = bool(rec.get("isSidechain"))
            _add(sub if is_sub else main, usage)
            if is_sub:
                turns_sub += 1
            else:
                turns_main += 1

            sid = str(rec.get("sessionId") or rec.get("session_id") or path.stem)
            sessions.setdefault(sid, {"usage": _empty(), "turns": 0, "file": path.name})
            _add(sessions[sid]["usage"], usage)
            sessions[sid]["turns"] += 1

            model = str(message.get("model") or "unknown")
            models.setdefault(model, {"usage": _empty(), "turns": 0})
            _add(models[model]["usage"], usage)
            models[model]["turns"] += 1

            key = current or "(no command — direct conversation)"
            commands.setdefault(key, {"usage": _empty(), "turns": 0, "invocations": 0,
                                      "models": set()})
            _add(commands[key]["usage"], usage)
            commands[key]["turns"] += 1
            commands[key]["models"].add(model)

        # Second pass over this file's command markers, to count invocations
        # independently of how many turns each produced.
        for line in lines:
            if "<command-name>" not in line:
                continue
            found = COMMAND_RE.search(line)
            if not found:
                continue
            name = found.group(1)
            if not name.startswith("/"):
                name = "/" + name
            if name in BUILTIN_COMMANDS:
                excluded[name] = excluded.get(name, 0) + 1
                continue
            commands.setdefault(name, {"usage": _empty(), "turns": 0, "invocations": 0,
                                       "models": set()})
            commands[name]["invocations"] += 1

    return {"files": files, "sessions": sessions, "models": models,
            "commands": commands, "excluded_commands": excluded, "main": main,
            "sub": sub, "turns_main": turns_main, "turns_sub": turns_sub}


def report(transcript_dir: Path, rates: dict | None, per_command: bool,
           per_session: bool) -> dict:
    if not transcript_dir.is_dir():
        return {"status": "no-transcripts", "transcript_dir": str(transcript_dir),
                "note": ("no session transcripts found for this project. They appear "
                         "under ~/.claude/projects/<project-path-slug>/ after you have "
                         "worked in the project with Claude Code; pass --transcripts "
                         "if yours live elsewhere.")}
    data = scan(transcript_dir)
    if not data["files"]:
        return {"status": "no-transcripts", "transcript_dir": str(transcript_dir),
                "note": f"{transcript_dir} contains no .jsonl transcripts"}

    overall = _empty()
    _add(overall, data["main"])
    _add(overall, data["sub"])
    turns = data["turns_main"] + data["turns_sub"]
    if turns == 0:
        return {"status": "no-usage", "transcript_dir": str(transcript_dir),
                "files_read": len(data["files"]),
                "note": ("transcripts found but none record token usage — nothing to "
                         "measure rather than a measurement of zero")}

    out = {
        "status": "ok",
        "transcript_dir": str(transcript_dir),
        "files_read": len(data["files"]),
        "sessions": len(data["sessions"]),
        "assistant_turns": turns,
        "total": _totals(overall),
        "main_session": {**_totals(data["main"]), "turns": data["turns_main"]},
        "subagents": {**_totals(data["sub"]), "turns": data["turns_sub"]},
        "by_model": {m: {**_totals(v["usage"]), "turns": v["turns"]}
                     for m, v in sorted(data["models"].items())},
        "measures": ("tokens Claude Code recorded for THIS project's sessions. Not a "
                     "benchmark, not comparable across projects, and not a prediction "
                     "of what your next paper will cost."),
    }
    read = overall["cache_read_input_tokens"]
    fresh = overall["input_tokens"] + overall["cache_creation_input_tokens"]
    if read + fresh:
        out["cache_read_share"] = round(read / (read + fresh), 4)
        out["cache_note"] = ("share of prompt tokens served from cache rather than "
                             "re-sent. High is good and is what the kit's disk-state "
                             "design is for; it is also billed at a lower rate, so a "
                             "raw token total overstates spend.")
    if per_session:
        out["by_session"] = {
            sid: {**_totals(v["usage"]), "turns": v["turns"], "file": v["file"]}
            for sid, v in sorted(data["sessions"].items(),
                                 key=lambda kv: -sum(kv[1]["usage"].values()))}
    if per_command:
        rows = []
        for name, v in data["commands"].items():
            totals = _totals(v["usage"])
            rows.append({"command": name, **totals, "turns": v["turns"],
                         "invocations": v["invocations"],
                         "tokens_per_invocation": (round(totals["total_tokens"]
                                                         / v["invocations"])
                                                   if v["invocations"] else None),
                         "models": sorted(v["models"])})
        rows.sort(key=lambda r: -r["total_tokens"])
        out["by_command"] = rows
        if data["excluded_commands"]:
            out["excluded_commands"] = [
                {"command": name, "invocations": n,
                 "reason": ("ambiguous — this name is both a Claude Code builtin and a "
                            "command this kit defines, and the transcript records only "
                            "the name"
                            if name in AMBIGUOUS_COMMANDS
                            else "Claude Code builtin, not one of this kit's commands"),
                 "spend_went_to": "(no command — direct conversation)"}
                for name, n in sorted(data["excluded_commands"].items())]
        out["attribution_rule"] = (
            "a command owns every assistant turn from its invocation until the next "
            "command or end of session — follow-up questions and tangents included. "
            "Read `turns` next to `tokens_per_invocation`: a high figure with many "
            "turns was a conversation, not the command's intrinsic cost. Claude Code's "
            "own commands (/compact, /clear, …) are excluded rather than "
            "misattributed.")
    if rates:
        out["cost_usd"] = {}
        total_cost = 0.0
        for model, block in data["models"].items():
            c = cost_of(block["usage"], rates, model)
            if c is None:
                out["cost_usd"][model] = None
                continue
            out["cost_usd"][model] = c
            total_cost += c
        out["cost_usd"]["_total"] = round(total_cost, 4)
        out["cost_note"] = ("computed from the rates YOU supplied, for the models this "
                            "kit ships no prices for. A model with no entry in your "
                            "rates file reports null, not zero.")
    else:
        out["cost_note"] = ("no --rates file given, so no cost is reported. Prices vary "
                            "by plan and change over time, and none are recorded in the "
                            "transcript — a table baked into this repo would go stale "
                            "silently and still be believed.")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--transcripts", help="transcript directory (default: derived "
                                          "from the current project path)")
    ap.add_argument("--project", default=".", help="project root (default: cwd)")
    ap.add_argument("--rates", help="JSON file of per-million-token prices by model")
    ap.add_argument("--per-command", action="store_true")
    ap.add_argument("--per-session", action="store_true")
    ap.add_argument("--json", dest="json_out", action="store_true")
    args = ap.parse_args()

    rates = None
    if args.rates:
        path = Path(args.rates)
        if not path.exists():
            die(f"rates file {path} not found")
        try:
            rates = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            die(f"could not parse the rates file — {e}")
        if not isinstance(rates, dict):
            die("the rates file must be a JSON object keyed by model name")

    # NOTE: deliberately NOT require_within_cwd. Transcripts live in the user's
    # home directory by design, outside every project; the sandbox rule the other
    # scripts apply protects project DATA files from being written elsewhere, and
    # this script only reads.
    transcript_dir = Path(args.transcripts) if args.transcripts \
        else default_transcript_dir(Path(args.project))
    emit(report(transcript_dir, rates, args.per_command, args.per_session), True)


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        die(f"failed to read transcripts — {e}")
