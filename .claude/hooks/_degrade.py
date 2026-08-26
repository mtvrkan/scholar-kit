"""_degrade.py — make a gate's fail-open visible instead of silent.

Every enforcement hook in this kit fails OPEN: if evaluating the gate raises,
the hook lets the tool call through rather than blocking it. That is the right
default and is not changing here — a gate exists to add friction at specific
points, not to become a new single point of failure that bricks a session when
one state file is malformed.

The defect was that it failed open *silently*. `except Exception: reason = None`
returns exit 0 with no output, which is byte-identical to "checked, nothing to
gate". So a `verify-status.json` that exists but raises on decode disabled the
phase gate for that call, and the author's next observation was that the gate
"didn't fire" — with no way to tell a passing check from a broken one. An
enforcement mechanism that cannot be distinguished from its own absence is not
an enforcement mechanism.

`systemMessage` is the fix: a top-level hook-output field the harness shows to
the user, carried alongside NO `permissionDecision`, so the tool still proceeds.
Fail-open behaviour is unchanged; only its silence is.

WHAT IS REPORTED — deliberately narrow. The exception's type and the source
location that raised it, never `str(exc)` and never any part of `tool_input`.
A hook sees draft prose, file paths and shell commands; an exception message
built from them (a KeyError carrying a quoted line, a UnicodeDecodeError
carrying raw bytes) would put manuscript content into a session-visible warning
and, via the transcript, into places the author did not choose. Type plus
location is enough to find the bug and cannot carry a payload.

THE SECOND SILENCE — payload SHAPE, not payload parsing. The original module
covered the case where stdin will not parse. It did not cover the two cases
where stdin parses and is still not what the gate assumes:

  · a payload that is valid JSON but not an object (`[]`, `"x"`, `123`). Every
    hook went straight from `json.loads` to `payload.get(...)`, which raises
    AttributeError OUTSIDE the try that was meant to contain it — so all five
    hooks answered with a traceback and a non-zero exit, in flat contradiction
    of their own docstrings ("never a traceback"). Still fail-open in effect,
    but reported as a crash rather than as a check that did not run.
  · a payload that IS an object but carries no `tool_name` — the key every
    gate dispatches on. `payload.get("tool_name", "")` yields "", no branch
    matches, and the hook exits 0 with no output: byte-identical to "checked,
    nothing to gate". This is the shape a harness contract change has, and it
    is the failure this whole module exists to make impossible: with the key
    renamed, every gate in the kit stops gating and nothing anywhere says so.

`read_payload()` and `missing_tool_name()` below close both. The notice for the
second is deliberately emitted by EVERY gate that reads the key rather than by
one nominated announcer, so the reader learns which gates went quiet, and the
gates keep the property that each announces its own degradation. Two or three
notices per call is the correct volume for "enforcement is off across the
board" — a condition that cannot arise in normal operation, unlike the
per-call warnings this kit refuses to emit elsewhere.

Change record: this module postdates DECISIONS.md's last entry for its original
half (CHANGELOG.md carries that release note); the payload-shape half is
DECISIONS.md D-091. Behaviour is locked by tests/test_degrade_visibility.py;
see `hooks` in tests/README.md.
"""
from __future__ import annotations

import json
import os
import sys
import traceback

# Marker every degradation message opens with. Tests match on it, and a user
# scanning a session can tell "a gate broke" from "a gate fired" at a glance.
PREFIX = "⚠ Scholar-Kit gate degraded"


HOOK_DIR = os.path.dirname(os.path.abspath(__file__))


def describe(exc: BaseException) -> str:
    """`TypeError at phase_gate.py:213` — type and origin, no message text.

    Prefers the deepest frame inside the hooks directory over the deepest frame
    overall. A malformed payload raises in `json/decoder.py`, and reporting
    `JSONDecodeError at decoder.py:363` names the stdlib rather than the gate
    that stopped working — true, and useless to whoever has to fix it. Falls
    back to the deepest frame when nothing in the stack is ours (an exception
    raised entirely inside an imported helper).
    """
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return f"{type(exc).__name__} at unknown location"
    ours = [f for f in frames
            if os.path.dirname(os.path.abspath(f.filename)) == HOOK_DIR]
    frame = (ours or frames)[-1]
    return f"{type(exc).__name__} at {os.path.basename(frame.filename)}:{frame.lineno}"


def message(hook: str, what: str, exc: BaseException) -> str:
    return (f"{PREFIX}: {hook} could not evaluate {what} "
            f"({describe(exc)}). The call was ALLOWED — this check did not run. "
            f"Re-run it deliberately before relying on the gate.")


def _emit(text: str) -> None:
    """Print a notice as hook JSON and mirror it to stderr.

    Printed as hook JSON so the harness surfaces it, and mirrored to stderr so
    the signal survives a harness that ignores the field, a hook run under a
    different runner, and `python .claude/hooks/x.py < payload.json` at a
    terminal. Never raises: a reporter that can fail would reintroduce exactly
    the crash-in-the-gate this module exists to keep out of the tool path.
    """
    try:
        print(json.dumps({"systemMessage": text}))
    except Exception:  # pragma: no cover — json.dumps on a str cannot fail
        pass
    try:
        print(text, file=sys.stderr)
    except Exception:  # pragma: no cover — a closed stderr must not propagate
        pass


def report(hook: str, what: str, exc: BaseException) -> None:
    """Emit a visible, non-blocking degradation notice for a raised error."""
    _emit(message(hook, what, exc))


def contract_message(hook: str, problem: str) -> str:
    """The notice for a payload whose SHAPE is wrong — no exception involved.

    `problem` must describe the shape and nothing else: a type name, a missing
    key name. It is interpolated into a message the author sees and the
    transcript keeps, so the leak rule that governs `describe()` governs it
    too — never a value out of the payload, never a path, never a command.
    """
    return (f"{PREFIX}: {hook} received a payload that does not match the hook "
            f"stdin contract ({problem}). The call was ALLOWED — this check did "
            f"not run. Every gate in this kit reads the same two keys, so if "
            f"this repeats, the kit's hook contract and the harness have "
            f"drifted apart: the gates are OFF, not passing.")


def report_contract(hook: str, problem: str) -> None:
    """Emit a visible, non-blocking notice for a payload-shape contract break."""
    _emit(contract_message(hook, problem))


def notice(text: str) -> None:
    """Emit a visible, non-blocking notice that is NOT a degradation.

    Same channel as report()/report_contract() — hook JSON plus a stderr mirror
    — deliberately, so there is exactly one way a hook speaks without blocking.
    Used for a gate that is opening but has something the author needs to know
    while it does (phase_gate.py's uncorroborated-PASS note). Kept distinct from
    report() because the two say opposite things about the check itself: report
    means "this did not run", notice means "this ran, and here is what it saw".
    """
    _emit(text)


def read_payload(hook: str, raw: str):
    """Parse a hook's stdin into the object every hook's dispatch assumes.

    Returns the payload dict, or None when the caller must give up (fail-open,
    exit 0). An EMPTY stdin returns an empty dict and stays silent: a harness
    probing the hook with no payload is not a broken gate, and a warning on
    every such call would train the author to ignore the one that matters.
    Non-empty input that will not parse, or that parses into something other
    than an object, is a real contract break and is reported.
    """
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except Exception as exc:
        report(hook, "the hook payload", exc)
        return None
    if not isinstance(payload, dict):
        # Type NAME only — `payload` itself is harness-supplied content.
        report_contract(hook, f"top-level value is a {type(payload).__name__}, "
                              f"not an object")
        return None
    return payload


def missing_tool_name(payload) -> bool:
    """True when a NON-EMPTY payload object carries no usable `tool_name`.

    An empty object is a probe, not a contract break, and follows the same
    silence rule as empty stdin. Callers must apply this only after their own
    project-scope check, so a plugin install stays quiet in repositories that
    were never this kit's to gate.
    """
    if not isinstance(payload, dict) or not payload:
        return False
    name = payload.get("tool_name")
    return not (isinstance(name, str) and name.strip())
