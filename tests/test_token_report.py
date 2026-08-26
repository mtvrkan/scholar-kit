"""Tests for token_report.py.

Every test builds a synthetic transcript in a temp directory. The script's whole
point is that it reports measured numbers rather than invented ones, so the tests
are about arithmetic fidelity and about the two ways a measurement tool lies:
reporting zero when it means "I found nothing", and reporting a cost it had no
basis to compute.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "token_report.py"
sys.path.insert(0, str(ROOT / "scripts"))

import token_report as tr  # noqa: E402


def usage(inp=0, out=0, cw=0, cr=0):
    return {"input_tokens": inp, "output_tokens": out,
            "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr}


def assistant(session="s1", model="claude-opus-5", sidechain=False, **kw):
    return {"type": "assistant", "sessionId": session, "isSidechain": sidechain,
            "message": {"model": model, "usage": usage(**kw)}}


def command(name):
    return {"type": "user",
            "message": {"content": f"<command-name>{name}</command-name>"}}


@pytest.fixture
def tdir(tmp_path):
    d = tmp_path / "transcripts"
    d.mkdir()
    return d


def write(tdir, name, records):
    (tdir / name).write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8")


def run(tdir, *args):
    proc = subprocess.run([sys.executable, str(SCRIPT), "--transcripts", str(tdir),
                           *args], capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout, proc.stderr


# ---------- arithmetic ----------

def test_totals_sum_every_token_category(tdir):
    write(tdir, "a.jsonl", [assistant(inp=100, out=50, cw=20, cr=1000)])
    out = tr.report(tdir, None, False, False)
    assert out["total"]["input_tokens"] == 100
    assert out["total"]["output_tokens"] == 50
    assert out["total"]["cache_creation_input_tokens"] == 20
    assert out["total"]["cache_read_input_tokens"] == 1000
    assert out["total"]["total_tokens"] == 1170


def test_usage_accumulates_across_turns_and_files(tdir):
    write(tdir, "a.jsonl", [assistant(out=10), assistant(out=15)])
    write(tdir, "b.jsonl", [assistant(out=25)])
    out = tr.report(tdir, None, False, False)
    assert out["total"]["output_tokens"] == 50
    assert out["assistant_turns"] == 3
    assert out["files_read"] == 2


def test_subagent_turns_are_separated_from_the_main_session(tdir):
    # The kit's architecture claim is that read-heavy work goes to subagents.
    # Folding their spend into the main total would make that unmeasurable.
    write(tdir, "a.jsonl", [assistant(out=10), assistant(out=90, sidechain=True)])
    out = tr.report(tdir, None, False, False)
    assert out["main_session"]["output_tokens"] == 10
    assert out["subagents"]["output_tokens"] == 90
    assert out["main_session"]["turns"] == 1 and out["subagents"]["turns"] == 1


def test_models_are_reported_separately(tdir):
    write(tdir, "a.jsonl", [assistant(model="claude-opus-5", out=10),
                            assistant(model="claude-haiku-4-5-20251001", out=4)])
    by_model = tr.report(tdir, None, False, False)["by_model"]
    assert by_model["claude-opus-5"]["output_tokens"] == 10
    assert by_model["claude-haiku-4-5-20251001"]["output_tokens"] == 4


def test_sessions_are_counted_by_id_not_by_file(tdir):
    write(tdir, "a.jsonl", [assistant(session="s1"), assistant(session="s2")])
    assert tr.report(tdir, None, False, False)["sessions"] == 2


def test_cache_read_share_is_computed_over_prompt_tokens_only(tdir):
    # Output tokens are not prompt tokens; including them would make the share
    # depend on how much the model wrote.
    write(tdir, "a.jsonl", [assistant(inp=100, cw=100, cr=800, out=9999)])
    assert tr.report(tdir, None, False, False)["cache_read_share"] == pytest.approx(0.8)


# ---------- per-command attribution ----------

def test_turns_are_attributed_to_the_command_that_preceded_them(tdir):
    write(tdir, "a.jsonl", [
        command("/lit-review"), assistant(out=100), assistant(out=50),
        command("/draft"), assistant(out=25),
    ])
    rows = {r["command"]: r for r in tr.report(tdir, None, True, False)["by_command"]}
    assert rows["/lit-review"]["output_tokens"] == 150
    assert rows["/draft"]["output_tokens"] == 25


def test_turns_before_any_command_are_not_attributed_to_one(tdir):
    write(tdir, "a.jsonl", [assistant(out=40), command("/draft"), assistant(out=10)])
    rows = {r["command"]: r for r in tr.report(tdir, None, True, False)["by_command"]}
    assert rows["(no command — direct conversation)"]["output_tokens"] == 40
    assert rows["/draft"]["output_tokens"] == 10


def test_builtin_claude_code_commands_are_excluded_not_misattributed(tdir):
    # /compact is real spend but it is not one of this kit's commands, and
    # letting it inherit the previous command's bucket would inflate that
    # command with the cost of compaction.
    write(tdir, "a.jsonl", [
        command("/draft"), assistant(out=10),
        command("/compact"), assistant(out=500),
    ])
    rows = {r["command"]: r for r in tr.report(tdir, None, True, False)["by_command"]}
    assert "/compact" not in rows
    assert rows["/draft"]["output_tokens"] == 10
    assert rows["(no command — direct conversation)"]["output_tokens"] == 500


def test_invocations_are_counted_independently_of_turns(tdir):
    write(tdir, "a.jsonl", [
        command("/draft"), assistant(out=10), assistant(out=10),
        command("/draft"), assistant(out=20),
    ])
    row = next(r for r in tr.report(tdir, None, True, False)["by_command"]
               if r["command"] == "/draft")
    assert row["invocations"] == 2
    assert row["turns"] == 3
    assert row["tokens_per_invocation"] == 20


def test_a_command_with_no_turns_of_its_own_still_shows_its_invocation(tdir):
    # A command that produced nothing (errored out, or gated immediately) must
    # not vanish from the table — absent reads as never run.
    write(tdir, "a.jsonl", [assistant(out=5), command("/submit-check")])
    row = next(r for r in tr.report(tdir, None, True, False)["by_command"]
               if r["command"] == "/submit-check")
    assert row["invocations"] == 1
    assert row["turns"] == 0 and row["total_tokens"] == 0


def test_excluded_commands_are_named_with_their_reason(tdir):
    # Dropping a bucket from a cost report without saying so is the same defect
    # as inventing one.
    write(tdir, "a.jsonl", [command("/draft"), assistant(out=10),
                            command("/compact"), assistant(out=5)])
    excluded = {e["command"]: e for e in
                tr.report(tdir, None, True, False)["excluded_commands"]}
    assert excluded["/compact"]["invocations"] == 1
    assert "builtin" in excluded["/compact"]["reason"]


def test_a_name_shared_with_a_builtin_is_reported_as_ambiguous(tdir):
    # /status exists in BOTH Claude Code and this kit. The transcript records
    # only the name, so attributing it either way would be a guess.
    write(tdir, "a.jsonl", [command("/status"), assistant(out=10)])
    excluded = {e["command"]: e for e in
                tr.report(tdir, None, True, False)["excluded_commands"]}
    assert "ambiguous" in excluded["/status"]["reason"]
    assert tr.AMBIGUOUS_COMMANDS <= tr.BUILTIN_COMMANDS


def test_command_attribution_does_not_leak_across_transcript_files(tdir):
    # Each session starts with no command in flight; carrying one over would
    # attribute a new session's opening turns to the previous session's command.
    write(tdir, "a.jsonl", [command("/lit-review"), assistant(out=10)])
    write(tdir, "b.jsonl", [assistant(out=70)])
    rows = {r["command"]: r for r in tr.report(tdir, None, True, False)["by_command"]}
    assert rows["/lit-review"]["output_tokens"] == 10
    assert rows["(no command — direct conversation)"]["output_tokens"] == 70


def test_the_attribution_rule_is_stated_in_the_output(tdir):
    write(tdir, "a.jsonl", [command("/draft"), assistant(out=10)])
    rule = tr.report(tdir, None, True, False)["attribution_rule"]
    assert "until the next command" in rule


# ---------- cost: refuses to invent one ----------

def test_no_cost_is_reported_without_a_rates_file(tdir):
    write(tdir, "a.jsonl", [assistant(inp=1000, out=1000)])
    out = tr.report(tdir, None, False, False)
    assert "cost_usd" not in out
    assert "no --rates file" in out["cost_note"]


def test_cost_is_computed_from_the_supplied_rates(tdir):
    # 1M input at $5 + 1M output at $25 = $30 exactly.
    write(tdir, "a.jsonl", [assistant(inp=1_000_000, out=1_000_000)])
    rates = {"claude-opus-5": {"input": 5.0, "output": 25.0}}
    out = tr.report(tdir, rates, False, False)
    assert out["cost_usd"]["claude-opus-5"] == pytest.approx(30.0)
    assert out["cost_usd"]["_total"] == pytest.approx(30.0)


def test_cache_tokens_are_priced_separately_when_rates_provide_them(tdir):
    write(tdir, "a.jsonl", [assistant(cw=1_000_000, cr=1_000_000)])
    rates = {"claude-opus-5": {"cache_write": 6.25, "cache_read": 0.5}}
    assert tr.report(tdir, rates, False, False)["cost_usd"]["claude-opus-5"] == \
        pytest.approx(6.75)


def test_a_model_missing_from_the_rates_file_reports_null_not_zero(tdir):
    # Zero would read as "this model was free". Null reads as "not priced".
    write(tdir, "a.jsonl", [assistant(model="claude-sonnet-5", out=1_000_000)])
    out = tr.report(tdir, {"claude-opus-5": {"output": 25.0}}, False, False)
    assert out["cost_usd"]["claude-sonnet-5"] is None
    assert out["cost_usd"]["_total"] == 0


def test_a_missing_rate_key_counts_as_zero_for_that_category_only(tdir):
    write(tdir, "a.jsonl", [assistant(inp=1_000_000, out=1_000_000)])
    out = tr.report(tdir, {"claude-opus-5": {"output": 25.0}}, False, False)
    assert out["cost_usd"]["claude-opus-5"] == pytest.approx(25.0)


# ---------- missing data is said, never zeroed ----------

def test_a_missing_transcript_directory_says_so(tdir):
    out = tr.report(tdir / "nope", None, False, False)
    assert out["status"] == "no-transcripts"
    assert "~/.claude/projects" in out["note"]


def test_an_empty_transcript_directory_says_so(tdir):
    out = tr.report(tdir, None, False, False)
    assert out["status"] == "no-transcripts"


def test_transcripts_without_usage_report_no_usage_not_zero_tokens(tdir):
    # "0 tokens" would be a measurement. "nothing to measure" is the truth.
    write(tdir, "a.jsonl", [{"type": "user", "message": {"content": "hi"}}])
    out = tr.report(tdir, None, False, False)
    assert out["status"] == "no-usage"
    assert "total" not in out


def test_a_truncated_final_line_does_not_break_the_scan(tdir):
    # A transcript being written to while the report runs ends mid-line.
    (tdir / "a.jsonl").write_text(
        json.dumps(assistant(out=10)) + "\n" + '{"type":"assistant","mess',
        encoding="utf-8")
    assert tr.report(tdir, None, False, False)["total"]["output_tokens"] == 10


def test_non_numeric_usage_values_are_skipped_not_coerced(tdir):
    write(tdir, "a.jsonl", [{"type": "assistant", "sessionId": "s1",
                             "message": {"model": "m",
                                         "usage": {"output_tokens": "lots"}}},
                            assistant(out=7)])
    assert tr.report(tdir, None, False, False)["total"]["output_tokens"] == 7


# ---------- transcript location ----------

def test_the_transcript_directory_is_derived_from_the_project_path():
    d = tr.default_transcript_dir(Path("/home/u/my proj"))
    assert d.parent.name == "projects"
    assert "-" in d.name and " " not in d.name


def test_output_states_what_the_numbers_are_not(tdir):
    write(tdir, "a.jsonl", [assistant(out=10)])
    measures = tr.report(tdir, None, False, False)["measures"]
    assert "not a prediction" in measures.lower()


# ---------- CLI ----------

def test_cli_emits_json(tdir):
    write(tdir, "a.jsonl", [assistant(out=10)])
    code, out, err = run(tdir, "--json")
    assert code == 0, err
    assert json.loads(out)["status"] == "ok"


def test_cli_per_command_and_per_session_flags(tdir):
    write(tdir, "a.jsonl", [command("/draft"), assistant(out=10)])
    code, out, err = run(tdir, "--per-command", "--per-session")
    assert code == 0, err
    data = json.loads(out)
    assert data["by_command"] and data["by_session"]


def test_cli_rejects_a_missing_rates_file(tdir):
    write(tdir, "a.jsonl", [assistant(out=10)])
    code, out, err = run(tdir, "--rates", "no-such-rates.json")
    assert code != 0
    assert "not found" in (out + err)


def test_cli_rejects_a_corrupt_rates_file(tmp_path, tdir):
    write(tdir, "a.jsonl", [assistant(out=10)])
    bad = tmp_path / "r.json"
    bad.write_text("{not json", encoding="utf-8")
    code, out, err = run(tdir, "--rates", str(bad))
    assert code != 0
    assert "rates file" in (out + err)


def test_cli_rejects_a_rates_file_that_is_not_an_object(tmp_path, tdir):
    write(tdir, "a.jsonl", [assistant(out=10)])
    bad = tmp_path / "r.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")
    assert run(tdir, "--rates", str(bad))[0] != 0
