#!/usr/bin/env python3
"""PreToolUse hook — enforce CLAUDE.md's Invariant 3 (phase gates) with teeth.

Before this hook, "no drafting before outline approval," "no critique before
verify=PASS," and "no formatting before Major=0" existed only as instructions
inside outline/draft/critique/submit-check SKILL.md files — nothing stopped a
direct Write to drafts/*.md bypassing /draft, a direct Write to reviews/*.md
bypassing /critique's own verify-status.json check, or format-engineer
trusting the orchestrator's claim that Major issues are resolved. This hook
re-checks the same state files (outline/outline.md, verify-status.json,
reviews/round-N.md) at the tool-call layer so the gate holds even if a skill
is skipped or an agent's own self-check is wrong.

Covers three tool surfaces per gate:
  - Write/Edit of drafts/*.md            -> outline must be "**Status:** approved"
  - Write/Edit of reviews/round-*.md     -> verify-status.json result must be PASS
  - Write/Edit of build/** or exports/** -> verify PASS AND latest review Major=0
  - Bash invoking the build scripts that populate build/**/exports/** (the
    actual real-world path — format-engineer runs latex_build.sh/docx_build.sh
    via Bash, not a raw Write) is gated the same as a direct Write there.
  - Bash writing/moving/deleting into drafts/*.md, reviews/round-*.md,
    build/** or exports/** via ANY other write-sink syntax (redirect, tee,
    cp/mv, python one-liners, PowerShell cmdlets) is gated too, with the
    SAME per-path rule the Write/Edit surface uses (outline-approval for
    drafts, verify=PASS for reviews, verify+Major=0 for build/exports) — an
    earlier version only ever checked "build"/"exports" path components on
    the Bash surface, so `cat > drafts/intro.md` (bypassing the outline
    gate) or `echo ... > reviews/round-1.md` (bypassing verify=PASS) sailed
    through Bash while the identical Write/Edit call was correctly blocked.
    Shares detection with protect_data_files.py via _shell_write_sink.py.

One thing here does NOT block: when the format gate OPENS, verify_provenance_note()
reports whether the verify=PASS it just honoured carries the sanctioned writer's
`live_recheck` block at all. See that function for why that is advisory rather
than a fourth gate.

Fail-open: unexpected stdin, or state files simply not present because the
project doesn't use a given phase, don't crash the hook — they surface as a
normal deny-with-reason (== "run the earlier step first"), never a traceback.

Change record: the "an earlier version…" notes throughout this file are the
point-of-use summary, not the record. Full reasoning and rejected alternatives:
DECISIONS.md (D-062..D-065, D-069..D-071, D-073..D-081, D-083, D-091, D-092).
Behaviour is locked by tests/test_phase_gate_hook.py and the round suites listed
under `hooks` in tests/README.md.
"""
import datetime
import hashlib
import json
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).parent))
from _degrade import missing_tool_name, notice, read_payload, report, report_contract
from _project_scope import is_kit_project
from _shell_write_sink import strip_heredocs, write_targets

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

# Only the FINAL manuscript builders gate on verify=PASS + Major=0. xlsx_export.py
# (the literature/screening/synthesis matrix, /export-excel + /slr's mid-pipeline
# Excel stage) and make_reference_docx.py (the reference.docx STYLE template built
# once at /ingest-template setup) both legitimately run in the literature/setup
# phase — BEFORE any draft, citation verification or critique exists — so gating
# them behind format_gate_reason() hard-blocked three documented commands at
# exactly the moment they must run. They are deliberately NOT build scripts; see
# also gate_reason_for_path()'s exports/ carve-out for the .xlsx path they write.
BUILD_SCRIPTS = {"latex_build.sh", "docx_build.sh"}
# Matched against a token's OWN basename with a full-string anchor (not a
# substring/boundary search over the whole command) — covers python3.11,
# multi-segment versions like python3.11.2, absolute interpreter paths
# (/usr/bin/python3), zsh, the Windows py launcher, and python.exe/py.exe,
# while still refusing to treat the tail of an unrelated "...validate_kit.py"
# ARGUMENT as if it were the interpreter (full-string anchor means
# "validate_kit.py" as a whole never matches this pattern). `source` is
# matched here too (`source scripts/latex_build.sh`); the bare `.` spelling
# of dot-sourcing (`. scripts/latex_build.sh`) can't join this alternation
# (PurePosixPath(".").name is '', not "."), so it's handled as a special
# case in _invokes_build_script() below instead.
_INTERPRETER_RE = re.compile(r"^(python3?(\.\d+)*|py|bash|sh|zsh|source)(\.exe)?$", re.IGNORECASE)


def _invokes_build_script(command: str) -> bool:
    """Require actual invocation, not a bare mention — `wc -l scripts/latex_build.sh`
    or `cat scripts/xlsx_export.py` must NOT gate. Two invocation shapes count:
    (1) an interpreter token immediately followed by a build-script path token
    (`bash scripts/latex_build.sh ...` / `python scripts/xlsx_export.py ...`,
    incl. `/usr/bin/python3`, `python3.11`, `py.exe`, `source ...`, `. ...`),
    or (2) the build-script token itself sitting in COMMAND position — the
    first token of the whole command or of any sub-command after
    `;`/`&&`/`||`/`|` — which covers a direct, no-interpreter-prefix execution
    (`./scripts/latex_build.sh ...`, a normal shebang-run shell invocation)
    that shape (1) alone would miss entirely, since there is no interpreter
    token to match against. Dot-sourcing (`source scripts/latex_build.sh` or
    the POSIX `. scripts/latex_build.sh` spelling) is shape (1) too — it runs
    the script in the current shell exactly like an interpreter prefix does,
    and was previously invisible to both shapes: no interpreter-token match
    (bare `.`/`source` aren't python/bash/sh) and no command-position match
    (the build-script name is the SECOND token, not the first).

    Build-script names are compared case-insensitively (`name.lower()`): both
    of the kit's primary platforms have a case-insensitive filesystem, so
    `bash scripts/LATEX_BUILD.SH` runs the identical real script as
    `latex_build.sh` while an exact-case `in BUILD_SCRIPTS` check let it skip
    the verify=PASS/Major=0 gate entirely (found live on Windows)."""
    command = strip_heredocs(command)
    for sub in re.split(r"&&|\|\||;|\||\n", command):
        tokens = sub.split()
        i = 0
        while i < len(tokens) and re.match(r"^[A-Za-z_]\w*=", tokens[i]):
            i += 1  # skip leading FOO=bar env-var assignments
        if i >= len(tokens):
            continue
        first_tok = tokens[i].strip("'\"")
        if first_tok == ".":
            if i + 1 < len(tokens):
                name = PurePosixPath(tokens[i + 1].strip("'\"").replace("\\", "/")).name
                if name.lower() in BUILD_SCRIPTS:
                    return True
            continue
        first_name = PurePosixPath(first_tok.replace("\\", "/")).name
        if _INTERPRETER_RE.match(first_name):
            if i + 1 < len(tokens):
                name = PurePosixPath(tokens[i + 1].strip("'\"").replace("\\", "/")).name
                if name.lower() in BUILD_SCRIPTS:
                    return True
        elif first_name.lower() in BUILD_SCRIPTS:
            return True
    return False


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Any read failure (missing, permission-denied, undecodable bytes)
        # flows through the same None -> "unknown/not-found" path so the
        # gate blocks with a clear reason consistently, rather than only
        # some failure modes being handled gracefully and others silently
        # falling through to main()'s broad fail-open backstop.
        return None


PROJECT_ROOT = Path.cwd().resolve()

# Field names the outline's approval marker may carry. English first — it is what
# /outline's template writes and what the docs quote — with the Turkish label
# accepted because the same skill instructs the session to write user-facing
# strings in Turkish, and a session obeying both ends up localising this one too.
APPROVED_MARKERS = ("Status", "Durum")


def _parts(path: str) -> tuple[str, ...]:
    """Project-relative path components, lexically normalized (collapse
    `..`/`.`) before splitting — without the normalization,
    `drafts/../reviews/round-1.md` contains "drafts" as a literal path
    component and gets misrouted to the outline gate instead of the reviews
    gate, even though it resolves on disk to reviews/round-1.md.
    posixpath.normpath is purely lexical (no filesystem access), so this
    works identically whether or not the target exists.

    An absolute path is resolved relative to PROJECT_ROOT first — matching
    agent_write_scope.py's _scope_parts() exactly, and for the same reason: a
    plain `"drafts" in parts` / `"build" in parts` membership test (the prior
    version of gate_reason_for_path) matches that component ANYWHERE in the
    path, not just at the project root, so an absolute path like
    .../some/other/tree/drafts/x.md or a nested lookalike such as
    notes/drafts/x.md triggers the drafts gate even though it isn't actually
    this project's drafts/ directory — surprising over-gating, and the
    unanchored form is the same class of bug agent_write_scope.py's own
    _scope_parts() docstring documents finding live (a scope name appearing
    as a component anywhere, not just as a genuine path prefix). Returns ()
    for an absolute path that doesn't resolve under PROJECT_ROOT at all,
    which then matches no gate — consistent with "outside the project" being
    out of this hook's jurisdiction, same posture as _scope_parts()."""
    raw = path.replace("\\", "/")
    # Native Path, not PurePosixPath, for the absoluteness check: PurePosixPath
    # only recognizes a leading "/" as absolute, so a Windows drive-letter
    # path like "C:/Users/x/drafts/y.md" tests False and falls through
    # un-resolved — matching agent_write_scope.py's _scope_parts() exactly.
    if Path(raw).is_absolute():
        try:
            rel = Path(raw).resolve().relative_to(PROJECT_ROOT).as_posix()
        except (ValueError, OSError):
            return ()
        return PurePosixPath(posixpath.normpath(rel)).parts
    return PurePosixPath(posixpath.normpath(raw)).parts


# ---------- provenance: the recorded approval, read (never written) here ----------
# scripts/provenance.py owns the ledger; this hook only ever READS it. A
# PreToolUse hook that appended to a protected, locked file on every gated call
# would be doing a write on the tool path — in the one component whose whole
# contract is to be fast and to fail open. Recording is the sanctioned writers'
# job (write_verify_status.py) and the skills' (outline, submit-check).
LEDGER = "provenance.jsonl"
GENESIS = "0" * 64
# Must stay identical to provenance.py's HASHED_FIELDS. The duplication is
# deliberate — hooks import nothing from scripts/ (they run standalone, from a
# plugin directory or a project copy) — and it is pinned by a test that hashes
# one fixture record with both implementations and requires the same digest.
HASHED_FIELDS = ("seq", "ts", "event", "path", "sha256", "prev", "note")


def _record_hash(record: dict) -> str:
    payload = {k: record.get(k) for k in HASHED_FIELDS}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def latest_attestation(target: str) -> dict | None:
    """The most recent self-consistent ledger record for `target`, or None.

    Self-consistent means the record's own hash recomputes — a record edited in
    place is not evidence, and treating it as evidence would make the ledger
    worse than no ledger. The FULL chain (each `prev` linking to the record
    before it) is deliberately not walked here: that is `provenance.py --verify`,
    run by /submit-check, and doing it on every Write would put an O(n) hash walk
    on the tool path to re-answer a question one command already answers.
    """
    path = Path(LEDGER)
    if not path.is_file():
        return None
    wanted = PurePosixPath(target).as_posix()
    found = None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict) and rec.get("path") == wanted \
                    and rec.get("hash") == _record_hash(rec):
                found = rec
    except OSError:
        return None
    return found


def outline_approved() -> tuple[bool, str]:
    """A file-based gate, not a signed one: the same session that authored
    outline/outline.md has ordinary Write access to it, so nothing here stops
    it from also writing "**Status:** approved" itself without genuine user
    sign-off — the same class of limitation verify_passed() below documents
    for verify-status.json, just without an external oracle (a real DOI, a
    real citation key) available to cross-check against. This closes the
    careless bypass (an agent that never even shows the outline to the user
    before marking it approved is now at least leaving a literal, checkable
    string), not a determined one.

    Staleness, two ways. Preferred: the provenance ledger's recorded approval
    carries the SHA-256 of the outline as approved, so the comparison is against
    the bytes (see latest_attestation above). Fallback, when no ledger record
    exists: outline/SKILL.md's approval step writes both "**Status:** approved"
    and an "**Approved at:** <ISO8601>" line together, and an mtime meaningfully
    AFTER that timestamp means the outline was edited post-approval — the same
    asymmetry verify_passed() closes for verify-status.json (bib mtime vs.
    verify-status.json mtime), via the one timestamp this file already carries.

    Neither closes the forgery, and the ledger does not pretend to: an
    orchestrator that appends its own approval record has produced a valid
    record. What the ledger changes is that the approval is now a dated, hashed,
    ordered line somebody can read afterwards, instead of a claim that left no
    trace at all."""
    text = _read("outline/outline.md")
    if text is None:
        return False, ("outline not approved (outline/outline.md not found) — "
                        "run /outline and approve it before drafting.")
    # The marker is machine-readable, but /outline's own language rule tells the
    # session to write every user-facing string in Turkish — so a session following
    # both instructions writes "**Durum:** approved" and the gate then reports an
    # APPROVED outline as unapproved. Accepting the localised field name costs
    # nothing: what carries the authorisation is the word "approved" plus the
    # provenance record below, never which language the label is in.
    if not any(f"**{label}:** approved" in text for label in APPROVED_MARKERS):
        # Separated from the no-marker-at-all case on purpose: an outline that says
        # "pending-approval" was never approved, while one whose marker is merely
        # absent may have been approved and then mangled. They need different fixes,
        # so telling the reader "not approved" for both sends half of them to
        # regenerate a file whose content was already right.
        if "pending-approval" in text:
            return False, ("outline not approved (outline/outline.md still says "
                            "\"pending-approval\") — run /outline and approve it before drafting.")
        return False, ("outline/outline.md carries no approval marker — expected a line "
                        f"reading \"**{APPROVED_MARKERS[0]}:** approved\" (or "
                        f"\"**{APPROVED_MARKERS[1]}:** approved\"). If you approved it "
                        "already, the marker line is missing or was renamed; restore it "
                        "rather than re-running /outline.")

    # Content-bound staleness, when the project keeps a provenance ledger: the
    # recorded approval carries the SHA-256 of the outline as approved, so "was
    # this edited afterwards" stops being a question about a hand-typed
    # timestamp and a filesystem clock, and becomes a question about the bytes.
    # Strictly stronger in both directions — it catches an edit that preserved
    # the mtime, and it stops flagging a re-save that changed the mtime without
    # changing a character. Absent a ledger (every project created before it, and
    # every author who never runs /outline's record step) this falls through to
    # the timestamp heuristic below, unchanged.
    record = latest_attestation("outline/outline.md")
    if record is not None:
        if _sha256_file(Path("outline/outline.md")) == record.get("sha256"):
            return True, ""
        return False, ("outline/outline.md no longer matches the version recorded as "
                        f"approved (provenance seq {record.get('seq')}, {record.get('ts')}) — "
                        "re-approve it via /outline before drafting.")

    m = re.search(r"\*\*Approved at:\*\*\s*(\S+)", text)
    if not m:
        return True, ""  # no timestamp recorded — can't check staleness, fall back to lenient
    try:
        approved_at = datetime.datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
        if approved_at.tzinfo is None:
            # A naive timestamp (no "Z"/offset — the documented format always
            # has one, but this is hand-editable Markdown) would otherwise
            # raise TypeError comparing against the tz-aware mtime below;
            # that TypeError previously escaped this try/except entirely and
            # was swallowed by main()'s outer fail-open backstop, silently
            # disabling the staleness check rather than falling back to
            # lenient on purpose. Assume UTC, matching the "Z" convention.
            approved_at = approved_at.replace(tzinfo=datetime.timezone.utc)
        mtime = datetime.datetime.fromtimestamp(
            Path("outline/outline.md").stat().st_mtime, tz=datetime.timezone.utc)
        # A few seconds' tolerance for the same write that adds the approval
        # lines itself (its own mtime lands at-or-after "Approved at" by
        # construction, not before it).
        stale = mtime > approved_at + datetime.timedelta(seconds=5)
    except (ValueError, OSError, TypeError):
        return True, ""  # unparseable timestamp / unreadable mtime — can't check, fall back
    if stale:
        return False, ("outline/outline.md was modified after its \"**Approved at:**\" "
                        "timestamp — re-approve it (add a fresh Status/Approved-at pair) "
                        "before drafting.")
    return True, ""


def verify_passed() -> tuple[bool, str]:
    """citation-verifier holds no Write tool (CLAUDE.md) — the orchestrator
    itself writes verify-status.json from the agent's returned fields. That
    means nothing stops the orchestrator from hand-writing
    `{"result":"PASS"}` without ever actually running /verify-citations; a
    file-based gate can't fully close that (no signature ties the file to a
    real check), but it can refuse the two cheapest, most careless versions
    of that bypass: a PASS that's internally inconsistent with its own
    fabricated/retracted/missing/unresolved counts or "checked"==0, and a
    PASS left stale after the bibliography changed underneath it."""
    text = _read("verify-status.json")
    if text is None:
        return False, "verify-status.json not found — run /verify-citations first."
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False, "verify-status.json is not valid JSON — re-run /verify-citations."
    if data.get("result") != "PASS":
        return False, f"citations not verified (result: {data.get('result', 'MISSING')}) — resolve via /verify-citations."
    for field in ("fabricated", "retracted", "missing", "unresolved"):
        val = data.get(field)
        if isinstance(val, (int, float)) and val > 0:
            return False, (f"verify-status.json claims PASS but {field}={val} — "
                           f"internally inconsistent, re-run /verify-citations.")
    checked = data.get("checked")
    if not isinstance(checked, (int, float)) or checked <= 0:
        return False, ("verify-status.json claims PASS but \"checked\" is missing/zero — "
                       "nothing appears to have actually been verified, re-run /verify-citations.")
    try:
        bib_path = Path("bib/references.bib")
        if bib_path.exists() and bib_path.stat().st_mtime > Path("verify-status.json").stat().st_mtime:
            return False, ("bib/references.bib was modified after verify-status.json — "
                           "re-run /verify-citations to re-verify the current bibliography.")
    except OSError:
        pass
    return True, ""


def latest_review_major_count() -> tuple[bool, int | None]:
    """Returns (a validly-numbered round file exists, Major-issue count in the
    highest round). The count is None if a round file exists but its count
    could not be parsed — callers must treat that as "unknown, block", not
    silently as zero. Files not matching "round-<digits>.md" exactly (e.g. a
    malformed "round-abc.md") are excluded from consideration entirely rather
    than falling back to an arbitrary -1 sort key that could let a single
    unparseable file masquerade as "the latest round"."""
    reviews_dir = Path("reviews")
    if not reviews_dir.exists():
        return False, None
    numbered = []
    for p in reviews_dir.glob("round-*.md"):
        m = re.fullmatch(r"round-(\d+)\.md", p.name)
        if m:
            numbered.append((int(m.group(1)), p))
    if not numbered:
        return False, None

    _, latest = max(numbered, key=lambda t: t[0])
    text = _read(str(latest))
    if text is None:
        return True, None  # exists but unreadable — unknown, not "clean"
    m = re.search(r"Major issues:\s*(\d+)", text)
    if m:
        return True, int(m.group(1))
    section = re.search(r"##\s*MAJOR ISSUES\s*\n(.*?)(\n##|\Z)", text, re.S | re.I)
    if section is None:
        return True, None  # unparseable — do not silently treat as "clean"
    body = section.group(1).strip()

    # An empty section, or a bare "None." / "Yok." / "-", means zero. Anything
    # longer has to be counted, and if it cannot be counted it is not zero.
    if len(re.sub(r"[\s*_.\-—–]", "", body)) <= 8:
        return True, 0

    # Anchored at column 0: an INDENTED numbered line is a sub-point under a
    # Major issue, not its own issue, and must not inflate the count. But the
    # number may be wearing bold (`**1. ...`) or be a heading (`### 1. ...`) —
    # measured across nine review rounds of one manuscript, a digit-only anchor
    # missed every bolded and every heading-style item and returned 0 for
    # reviews carrying up to four real Major issues. Under-counting is the
    # dangerous direction: a gate that silently returns zero is indistinguishable
    # from a gate that passed.
    #
    # Accepted residual: a single issue whose "what would fix it" list is
    # numbered at column 0 counts as that many extra issues. Nothing in the
    # markup separates a problem from its remedy, so no pattern fixes this —
    # the explicit "Major issues: N" line does. Left over-counting because that
    # direction blocks visibly instead of passing silently.
    n = len(re.findall(r"^(?:\*\*|###\s+)?\d+\.", body, re.M))
    if n == 0:
        # Substantial prose under the heading that yields no parseable item.
        # Unknown, not clean — the caller blocks and asks for an explicit
        # "Major issues: N" line, which critique/SKILL.md now requires.
        return True, None
    return True, n


def verify_provenance_note() -> str | None:
    """A PASS the gate is about to honour, with no evidence anything corroborated it.

    scripts/write_verify_status.py is the sanctioned writer, and it does far
    more than persist the agent's numbers: before writing a PASS it re-runs
    doi2bib.py --verify and cite_audit.py against the bib and drafts actually
    on disk, then records what that recheck could confirm in a `live_recheck`
    block. verify_passed() above cannot use any of that — it only ever asked
    whether the FIELDS are self-consistent, which a hand-authored file satisfies
    trivially.

    So this reads the one thing a hand-authored file does not carry, and says so
    at the single moment it matters: the build/export gate, where the final
    submission artifact is produced. It does NOT block, for the same reason
    write_verify_status.py only WARNs about the same condition — an offline
    machine and a fresh project both degrade here legitimately, and a fourth
    blocking gate is a scope decision (CONTRIBUTING.md), not a hook detail. What
    it removes is the silence: an uncorroborated PASS used to be indistinguishable
    from a corroborated one at exactly the point of no return, and the writer's
    own warning was emitted once, possibly hundreds of turns earlier.

    Returns None when there is nothing to say (including on any read/parse
    failure — verify_passed() has already reported those as a deny)."""
    text = _read("verify-status.json")
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    live = data.get("live_recheck")
    if not isinstance(live, dict):
        return ("Scholar-Kit note: verify-status.json carries no \"live_recheck\" block, "
                "so it was not written by scripts/write_verify_status.py — nothing "
                "independently re-checked this PASS against the bibliography and drafts "
                "on disk. The gate is opening on a self-reported result. Re-run "
                "/verify-citations if this build is the submission copy.")
    if not (live.get("doi2bib_confirmed") and live.get("cite_audit_confirmed")):
        return (f"Scholar-Kit note: this PASS was written with an incomplete live recheck "
                f"(doi2bib_confirmed={bool(live.get('doi2bib_confirmed'))}, "
                f"cite_audit_confirmed={bool(live.get('cite_audit_confirmed'))}) — it is "
                f"NOT independently corroborated. Usually an offline run or a fresh "
                f"project; if neither applies, check the --bib/--drafts paths and re-run "
                f"/verify-citations.")
    return None


# Set by format_gate_reason() so main() can tell whether the call it is about to
# ALLOW was one the format gate actually evaluated — without re-deriving the
# path/command classification a second time and risking the two disagreeing.
# A hook process handles exactly one tool call, so a module-level flag is the
# whole of the state involved.
_format_gate_ran = False


def format_gate_reason() -> str | None:
    global _format_gate_ran
    _format_gate_ran = True
    ok, reason = verify_passed()
    if not ok:
        return reason
    found, major = latest_review_major_count()
    if not found:
        return "no reviews/round-N.md found — run /critique before formatting/exporting."
    if major is None:
        return ("could not determine the Major-issue count from the latest review — "
                "expected a \"Major issues: N\" line or a \"## MAJOR ISSUES\" section.")
    if major:
        return f"latest review has {major} unresolved Major issue(s) — resolve via /revise, then re-run /critique."
    return None


def gate_reason_for_path(path: str) -> str | None:
    """Each gate is anchored at parts[0] — the project's own top-level
    drafts/reviews/build/exports directory — not a bare "in parts" membership
    test. The latter matched a same-named component ANYWHERE in the path
    (notes/drafts/x.md, an absolute path through an unrelated tree that
    happens to pass through a build/ directory, project-template/'s own
    scaffold drafts/), gating paths this hook has no real jurisdiction over."""
    parts = [p.lower() for p in _parts(path)]
    if not parts:
        return None
    top, name = parts[0], parts[-1]

    if top == "drafts" and name.endswith(".md") and name != "status.md":
        ok, reason = outline_approved()
        return reason if not ok else None

    if top == "reviews" and re.match(r"round-\d+\.md$", name):
        ok, reason = verify_passed()
        return reason if not ok else None

    if top == "build":
        return format_gate_reason()

    if top == "exports":
        # exports/ holds BOTH the early literature deliverables (the screening/
        # synthesis matrix .xlsx from /export-excel + /slr, and any .csv/.xls
        # companion) AND the final manuscript renders (.docx/.pdf/.tex from
        # docx_build.sh/latex_build.sh). Only the latter are phase-gated; the
        # literature matrix legitimately predates citation verification, so
        # gating every exports/ write behind verify=PASS + Major=0 (the prior
        # `top in ("build","exports")`) blocked /export-excel and /slr's Excel
        # stage at exactly the moment they run. Carve out the known literature
        # spreadsheet types; everything else in exports/ stays gated (default to
        # gated so a new manuscript output type isn't silently ungated).
        if name.endswith((".xlsx", ".xls", ".csv")):
            return None
        return format_gate_reason()

    return None


def gate_reason_for_bash(command: str) -> str | None:
    """Every write/move/delete target this Bash command touches (redirect,
    tee, cp/mv, python one-liners, PowerShell cmdlets — see
    _shell_write_sink.py) is run through the exact same gate_reason_for_path()
    a direct Write/Edit to that path would get, so drafts/reviews/build/exports
    are all covered identically regardless of which tool surface wrote them.

    Heredoc bodies are stripped (see strip_heredocs — write_targets() does this
    internally; _invokes_build_script() does it separately below since it
    doesn't go through write_targets()) so a draft/note's own text mentioning a
    redirect or build command isn't mistaken for one — the heredoc's OPENING
    line (which carries the real redirect target) is preserved, so a genuine
    `cat <<EOF > drafts/x.md ... EOF` is still gated."""
    for target in write_targets(command):
        reason = gate_reason_for_path(target)
        if reason:
            return reason
    if _invokes_build_script(command):
        return format_gate_reason()
    return None


def main():
    # Fail-open on any unusable stdin, and never with a traceback: empty input
    # stays silent, input that will not parse — or that parses into something
    # other than an object — is reported. See _degrade.py.
    payload = read_payload('phase_gate', sys.stdin.read())
    if payload is None:
        sys.exit(0)
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    # The paths this hook gates — drafts/, build/, exports/, reviews/ — are
    # ordinary directory names outside this kit. Installed as a plugin, the hook
    # runs in every session, so without this check it would block writes to
    # `build/` in unrelated projects. See _project_scope.py.
    if not is_kit_project():
        sys.exit(0)

    # Inside a kit project, a payload carrying no `tool_name` is the harness
    # contract having moved, not an ordinary call — and a gate that answers a
    # moved contract with zero bytes is indistinguishable from one that checked
    # and found nothing to gate. See _degrade.py.
    if missing_tool_name(payload):
        report_contract('phase_gate', "no 'tool_name' key")
        sys.exit(0)

    reason = None
    try:
        if tool in ("Write", "Edit", "NotebookEdit"):
            # NotebookEdit's payload key is "notebook_path", not "file_path" —
            # build/** and exports/** aren't restricted to *.md, so a notebook
            # dropped straight into build/analysis.ipynb or
            # exports/results.ipynb would otherwise skip the verify+Major=0
            # gate entirely (protect_data_files.py already reads both keys
            # for the same reason; matched here now too).
            path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
            if isinstance(path, str) and path:
                reason = gate_reason_for_path(path)
        elif tool == "Bash":
            command = tool_input.get("command", "")
            if isinstance(command, str) and command:
                reason = gate_reason_for_bash(command)
    except Exception as exc:
        # Fail-open backstop: an unexpected error while evaluating the gate
        # (e.g. a state file that exists but raises on decode) must never
        # block every Write/Edit/Bash call in the project — the whole point
        # of a gate is to add friction at specific points, not become a new
        # single point of failure for the entire session.
        #
        # Open, but no longer silent. Without the notice this path is
        # indistinguishable from "checked, nothing to gate", so a broken gate
        # reads as a passing one. See _degrade.py.
        report(f"phase_gate ({tool})", "the phase gate", exc)
        sys.exit(0)

    if reason:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Phase gate (Invariant 3): {reason}",
            }
        }))
    elif _format_gate_ran:
        # Allowing a build/export. Say so if the PASS it rests on was never
        # independently corroborated — see verify_provenance_note(). Guarded the
        # same way the gate itself is: a fault in an advisory note must not
        # become the thing that breaks the tool path.
        try:
            note = verify_provenance_note()
        except Exception as exc:
            report(f"phase_gate ({tool})", "the verify-status provenance note", exc)
            note = None
        if note:
            notice(note)
    sys.exit(0)


if __name__ == "__main__":
    main()
