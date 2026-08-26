"""Tests for .claude/hooks/_degrade.py — a gate that fails open must say so.

Every enforcement hook in this kit fails OPEN by design: if evaluating the gate
raises, the call is allowed rather than blocked. That is not what these tests
check. They check the property the fail-open used to be missing — that it is
DISTINGUISHABLE from a clean pass.

`except Exception: reason = None` followed by exit 0 with no output produces
bytes identical to "checked, nothing to gate". A `verify-status.json` that
existed but raised on decode disabled the phase gate for that call, and the
only observable symptom was that the gate "didn't fire". An enforcement
mechanism that cannot be told apart from its own absence is not one.

The stdin-contract path is covered per-hook in each hook's own test file
(fails open loudly on garbage, silently on empty). What is covered HERE is the
harder path: an unforeseen error raised while EVALUATING the gate, which is a
backstop precisely because no fixture can trigger it naturally — the hooks
already handle every failure mode their authors anticipated. Each test forces
it by making an internal the hook depends on raise.
"""
import importlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
HOOKS = ROOT / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))

import _degrade  # noqa: E402

# Hook modules bind PROJECT_ROOT at import time (see agent_write_scope.py's own
# note on why). The evaluation-path tests below must therefore chdir into a
# fixture project and reload — which leaves the reloaded module in sys.modules
# with PROJECT_ROOT pointing at a deleted tmp_path, and every later test in the
# same pytest process that imports it inherits that. Found the hard way: the
# full suite failed in test_remediation_2026_07_04_round9.py, several files
# away, for a reason that file had nothing to do with.
_HOOK_MODULES = ("phase_gate", "protect_data_files", "agent_write_scope",
                 "template_supremacy_gate")


@pytest.fixture(autouse=True)
def _restore_hook_module_state():
    yield
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        for name in _HOOK_MODULES:
            if name in sys.modules:
                importlib.reload(sys.modules[name])
    finally:
        # monkeypatch.chdir undoes itself later; leaving the directory as we
        # found it keeps the two teardowns independent.
        if Path(cwd).is_dir():
            os.chdir(cwd)


# ---------- the reporter itself ----------

def test_describe_reports_type_and_origin_but_never_the_message():
    secret = "PATIENT-COHORT-1998"
    try:
        raise ValueError(secret)
    except ValueError as exc:
        described = _degrade.describe(exc)
    assert described.startswith("ValueError at ")
    assert secret not in described, (
        "the exception's message reached the notice — a hook sees draft prose "
        "and shell commands, so str(exc) is a content-leak channel")


def test_describe_prefers_the_hook_frame_over_the_stdlib_frame():
    # The real stack shape: a hook calls a helper, the helper calls into the
    # stdlib, and the stdlib is what actually raises. Naming the deepest frame
    # reports `TypeError at re/__init__.py:210` — true, and useless to whoever
    # has to fix the gate. The frame that belongs to this kit is the answer.
    import traceback as tb_mod

    import template_supremacy_gate

    with pytest.raises(Exception) as excinfo:
        # Passes a non-string down to re.split, so the raise lands inside the
        # stdlib with the gate's own frame above it.
        template_supremacy_gate.gate_reason_for_bash(123)
    frames = [f.filename for f in tb_mod.extract_tb(excinfo.value.__traceback__)]

    assert any(f.endswith("template_supremacy_gate.py") for f in frames)
    assert not frames[-1].endswith("template_supremacy_gate.py"), (
        "fixture no longer exercises the case: the stdlib must be the deepest "
        "frame for the preference to mean anything")
    described = _degrade.describe(excinfo.value)
    assert "template_supremacy_gate.py:" in described, (
        f"expected the kit's own frame to win, got {described!r}")


def test_describe_falls_back_when_no_frame_belongs_to_the_kit():
    # Raised entirely inside the stdlib from a caller that is not a hook: there
    # is no kit frame to prefer, and reporting the stdlib beats reporting
    # nothing.
    with pytest.raises(json.JSONDecodeError) as excinfo:
        json.loads("not json")
    assert _degrade.describe(excinfo.value).startswith("JSONDecodeError at ")


def test_message_states_that_the_call_was_allowed():
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        text = _degrade.message("phase_gate", "the phase gate", exc)
    assert text.startswith(_degrade.PREFIX)
    assert "ALLOWED" in text, (
        "a notice that does not say the call went through reads as a block")
    assert "phase_gate" in text and "the phase gate" in text


def test_report_emits_hook_json_without_a_permission_decision(capsys):
    try:
        raise KeyError("k")
    except KeyError as exc:
        _degrade.report("phase_gate", "the phase gate", exc)
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["systemMessage"].startswith(_degrade.PREFIX)
    assert "permissionDecision" not in captured.out, (
        "a degraded gate must never deny — fail-open is the contract")
    assert payload["systemMessage"] in captured.err, (
        "the notice must also reach stderr, so it survives a runner that "
        "ignores systemMessage")


def test_report_never_raises_even_with_stdout_closed(capsys):
    # A reporter that can fail would reintroduce the crash-in-the-gate this
    # module exists to keep out of the tool path.
    with capsys.disabled():
        real_out, real_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = io.StringIO()
        sys.stdout.close()
        try:
            try:
                raise ValueError("x")
            except ValueError as exc:
                _degrade.report("phase_gate", "the phase gate", exc)  # must not raise
        finally:
            sys.stdout, sys.stderr = real_out, real_err


# ---------- the evaluation path, per gate ----------

def _drive(monkeypatch, tmp_path, module_name, break_attr, payload, capsys):
    """Import a hook, make one of its internals raise, and run main()."""
    (tmp_path / "PROJECT.md").touch()
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module(module_name)
    importlib.reload(module)  # PROJECT_ROOT and friends are read at import time

    def _boom(*_a, **_k):
        raise TypeError("forced: an internal the gate depends on changed shape")

    monkeypatch.setattr(module, break_attr, _boom)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    with pytest.raises(SystemExit) as excinfo:
        module.main()
    return excinfo.value.code, capsys.readouterr()


@pytest.mark.parametrize("module_name,break_attr,payload", [
    ("phase_gate", "gate_reason_for_path",
     {"tool_name": "Write", "tool_input": {"file_path": "drafts/intro.md"}}),
    ("protect_data_files", "_protected_name",
     {"tool_name": "Write", "tool_input": {"file_path": "sources/registry.jsonl"}}),
    ("agent_write_scope", "_in_scope",
     {"agent_type": "data-scientist", "tool_name": "Write",
      "tool_input": {"file_path": "build/paper.tex"}}),
    ("template_supremacy_gate", "gate_reason_for_bash",
     {"tool_name": "Bash",
      "tool_input": {"command": "bash scripts/docx_build.sh a b c"}}),
])
def test_gate_that_breaks_mid_evaluation_allows_and_announces(
        monkeypatch, tmp_path, capsys, module_name, break_attr, payload):
    code, captured = _drive(monkeypatch, tmp_path, module_name, break_attr,
                            payload, capsys)
    assert code == 0, "fail-open: a broken gate must not block the call"
    assert "permissionDecision" not in captured.out, "a broken gate must not deny"
    notice = json.loads(captured.out)["systemMessage"]
    assert notice.startswith(_degrade.PREFIX)
    assert module_name in notice, (
        f"the notice does not name the gate that broke: {notice!r}")
    assert "ALLOWED" in notice


def test_a_working_gate_stays_quiet(monkeypatch, tmp_path, capsys):
    # The control. Without this, every assertion above would still pass if the
    # hooks announced a degradation on every single call.
    (tmp_path / "PROJECT.md").touch()
    monkeypatch.chdir(tmp_path)
    module = importlib.import_module("protect_data_files")
    importlib.reload(module)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": "drafts/intro.md"}})))
    with pytest.raises(SystemExit):
        module.main()
    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    assert _degrade.PREFIX not in captured.err


def test_every_gate_imports_the_reporter():
    # A fifth gate added later without wiring _degrade in would fail open
    # silently again, and nothing else would notice.
    for name in ("phase_gate", "protect_data_files", "agent_write_scope",
                 "template_supremacy_gate"):
        src = (HOOKS / f"{name}.py").read_text(encoding="utf-8")
        # Matched as a name in the import list rather than as a literal prefix:
        # the gates now import several helpers from this module, and binding the
        # check to one particular ORDER of those names would fail this test for
        # a re-ordered import that changes nothing.
        assert re.search(r"^from _degrade import .*\breport\b", src, re.M), (
            f"{name}.py does not import the degradation reporter")
        # `reason = None` as an INITIALIZER is fine; as the entire body of an
        # `except` block it is the silent fail-open this change removed.
        silent = re.search(
            r"except\s+Exception[^\n]*:\n(?:[ \t]*#[^\n]*\n|[ \t]*\n)*"
            r"[ \t]*(?:reason\s*=\s*None|pass)\b", src)
        assert not silent, (
            f"{name}.py still swallows a gate-evaluation error silently at "
            f"offset {silent.start()} — that path must call report()")


# ---------- the payload-SHAPE path (D-091) ----------
#
# The evaluation-path tests above cover a gate that breaks while thinking. These
# cover the two ways a gate never starts thinking at all, both of which shipped:
#
#   · stdin is valid JSON but not an object. `json.loads("[]")` succeeds and the
#     very next line, `payload.get(...)`, raises AttributeError OUTSIDE the try
#     that was supposed to contain it — so every hook answered with a traceback
#     and exit 1, contradicting its own docstring ("never a crash").
#   · stdin IS an object but carries no `tool_name`. Every gate dispatches on
#     that key; without it no branch matches and the hook exits 0 silently,
#     which is byte-identical to a clean pass. That is the shape a harness
#     contract change has: the gates stop gating, all at once, and say nothing.
#
# Driven as subprocesses on purpose. The defect was an uncaught exception and a
# non-zero exit — properties of the PROCESS that an in-process `main()` call
# cannot observe.

GATES = ("protect_data_files", "phase_gate", "agent_write_scope",
         "template_supremacy_gate", "cite_warn")

# Per gate, a payload that carries everything the gate needs to reach its own
# dispatch EXCEPT `tool_name`: agent_write_scope legitimately exits before the
# dispatch when no scoped agent is claimed (a main-session call has no
# `agent_type`), so for it the drift is only observable with one present.
NO_TOOL_NAME = {
    "protect_data_files": {"tool_input": {"file_path": "sources/registry.jsonl"}},
    "phase_gate": {"tool_input": {"file_path": "drafts/intro.md"}},
    "agent_write_scope": {"agent_type": "data-scientist",
                          "tool_input": {"file_path": "build/paper.tex"}},
    "template_supremacy_gate": {"tool_input": {"command": "bash scripts/docx_build.sh"}},
    "cite_warn": {"tool_input": {"file_path": "drafts/intro.md"}},
}


def _run_hook(hook: str, raw: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOKS / f"{hook}.py")], input=raw,
        capture_output=True, text=True, cwd=str(cwd),
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def _notice(proc: subprocess.CompletedProcess) -> str:
    """The systemMessage the harness would surface, or "" if there is none."""
    out = proc.stdout.strip()
    if not out:
        return ""
    return json.loads(out).get("systemMessage", "")


@pytest.fixture
def project(tmp_path):
    """A directory the hooks recognise as a kit project (see _project_scope.py)."""
    (tmp_path / "PROJECT.md").touch()
    return tmp_path


@pytest.mark.parametrize("hook", GATES)
@pytest.mark.parametrize("raw", ["[]", '"a string"', "123", "null"])
def test_json_that_is_not_an_object_is_announced_not_crashed(project, hook, raw):
    proc = _run_hook(hook, raw, project)
    assert proc.returncode == 0, (
        f"{hook} exited {proc.returncode} on a non-object payload — fail-open "
        f"means exit 0:\n{proc.stderr}")
    assert "Traceback" not in proc.stderr, (
        f"{hook} answered a shape change with a traceback:\n{proc.stderr}")
    assert "gate degraded" in _notice(proc), (
        f"{hook} took a non-object payload silently — indistinguishable from "
        f"a clean pass")
    assert "permissionDecision" not in proc.stdout, "a degraded gate must not deny"


@pytest.mark.parametrize("hook", GATES)
@pytest.mark.parametrize("raw", ["", "   \n", "{}"])
def test_an_empty_payload_stays_silent(project, hook, raw):
    """The probe rule, unchanged: no stdin — or an empty object — is a harness
    probe, not a broken gate. Warning on those would train the author to ignore
    the warning that matters, which is the whole point of the notice."""
    proc = _run_hook(hook, raw, project)
    assert proc.returncode == 0
    assert proc.stdout.strip() == "", f"{hook} warned on an empty probe"
    assert "gate degraded" not in proc.stderr


@pytest.mark.parametrize("hook", GATES)
def test_a_payload_without_tool_name_is_announced(project, hook):
    payload = {"cwd": str(project), **NO_TOOL_NAME[hook]}
    proc = _run_hook(hook, json.dumps(payload), project)
    assert proc.returncode == 0
    notice = _notice(proc)
    assert "gate degraded" in notice and "tool_name" in notice, (
        f"{hook} exited silently on a payload with no tool_name — that is the "
        f"shape of a harness contract change, and it reads as a clean pass")
    assert "ALLOWED" in notice or "was ALLOWED" in notice or "OFF, not passing" in notice
    assert "permissionDecision" not in proc.stdout


@pytest.mark.parametrize("hook", ["protect_data_files", "phase_gate",
                                  "template_supremacy_gate", "cite_warn"])
def test_the_contract_notice_stays_out_of_unrelated_repositories(tmp_path, hook):
    """No PROJECT.md means this was never the kit's directory to gate. A plugin
    install runs these hooks in every session; a notice that fired there would
    be a bug report about somebody else's repo."""
    payload = {"cwd": str(tmp_path), **NO_TOOL_NAME[hook]}
    proc = _run_hook(hook, json.dumps(payload), tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.strip() == "", f"{hook} warned outside a kit project"


@pytest.mark.parametrize("hook", GATES)
def test_the_contract_notice_carries_no_payload_content(project, hook):
    """Same leak rule as describe(): a hook sees draft prose, file paths and
    shell commands, and the notice reaches the session and the transcript."""
    secret = "PATIENT-COHORT-1998"
    payload = {"cwd": str(project), "prompt": secret,
               "tool_input": {"file_path": f"drafts/{secret}.md",
                              "command": f"echo {secret}"}}
    proc = _run_hook(hook, json.dumps(payload), project)
    assert secret not in proc.stdout and secret not in proc.stderr, (
        f"{hook}'s contract notice echoed the payload back")


def test_a_real_gated_call_still_denies(project):
    """The control for the whole section: routing stdin through the shared
    loader must not have loosened the gate it protects."""
    (project / "sources").mkdir()
    payload = {"cwd": str(project), "tool_name": "Write",
               "tool_input": {"file_path": "sources/registry.jsonl"}}
    proc = _run_hook("protect_data_files", json.dumps(payload), project)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_every_gate_parses_stdin_through_the_shared_loader():
    """A gate that goes back to a bare `json.loads(raw)` reintroduces both
    defects at once, and no behavioural test of the OTHER gates would notice."""
    for name in GATES:
        src = (HOOKS / f"{name}.py").read_text(encoding="utf-8")
        assert "read_payload(" in src, (
            f"{name}.py parses its own stdin instead of using _degrade.read_payload")
        assert not re.search(r"^\s*payload\s*=\s*json\.loads?\(", src, re.M), (
            f"{name}.py still parses stdin directly")


# ---------- the loader's own contract ----------

def test_read_payload_treats_empty_stdin_as_a_probe(capsys):
    assert _degrade.read_payload("h", "") == {}
    assert _degrade.read_payload("h", "  \n\t ") == {}
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_read_payload_reports_unparseable_stdin(capsys):
    assert _degrade.read_payload("h", "{not json") is None
    # Read through json, not as raw text: the marker is non-ASCII and
    # json.dumps escapes it to ⚠ on the way out.
    assert json.loads(capsys.readouterr().out)["systemMessage"].startswith(_degrade.PREFIX)


def test_read_payload_names_the_type_it_got_but_not_the_value(capsys):
    assert _degrade.read_payload("h", '["PATIENT-COHORT-1998"]') is None
    out = capsys.readouterr().out
    assert "list" in out, "the notice does not say what shape arrived"
    assert "PATIENT-COHORT-1998" not in out


def test_read_payload_returns_the_object_unchanged(capsys):
    assert _degrade.read_payload("h", '{"tool_name": "Write"}') == {"tool_name": "Write"}
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("payload,expected", [
    ({}, False),                       # empty object: a probe, by the same rule as empty stdin
    ([], False),                       # not an object at all — read_payload's problem, not this one
    ({"tool_name": "Write"}, False),
    ({"tool_name": "Bash", "tool_input": {}}, False),
    ({"tool_input": {"file_path": "x"}}, True),
    ({"tool_name": ""}, True),
    ({"tool_name": "   "}, True),
    ({"tool_name": 7}, True),
    ({"tool_name": None}, True),
])
def test_missing_tool_name_only_fires_on_a_non_empty_object(payload, expected):
    assert _degrade.missing_tool_name(payload) is expected
