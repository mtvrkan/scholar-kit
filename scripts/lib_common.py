"""lib_common.py — shared helpers for scholar-kit scripts (JSONL I/O, minimal BibTeX parser).

Imported by sibling scripts; never invoked directly. Keep dependency-free (stdlib only).
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import threading
import time
import unicodedata
from pathlib import Path


def _tmp_sibling(p: Path) -> Path:
    """A unique temp sibling for the atomic write_* helpers below. Keyed on BOTH
    the pid and the thread id: pid alone collides if two threads in one process
    write the same file concurrently (cross-process is already pid-distinct);
    the thread id closes that residual intra-process window without relying on
    the GIL/file_lock timing."""
    return p.with_name(f"{p.name}.tmp{os.getpid()}.{threading.get_ident()}")

# Windows consoles/pipes default to cp125x — Turkish titles and em-dashes would
# crash print(). Force UTF-8 once for every script that imports this module;
# harmless no-op on macOS/Linux.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # pragma: no cover - closed/odd streams
            pass


# ---------- JSONL ----------

def read_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    # Windows can transiently deny a read (WinError 5 / PermissionError) while
    # a concurrent writer's os.replace() (see write_jsonl below) is mid-rename
    # — POSIX rename-over-an-open-handle never blocks a reader like this, but
    # Windows does. Retry with backoff rather than let an unlucky reader crash;
    # a real "file genuinely inaccessible" case still surfaces after ~1s.
    attempts, delay = 20, 0.05
    for attempt in range(attempts):
        try:
            if not p.exists():
                return []
            text = p.read_text(encoding="utf-8")
            break
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)
            delay = min(delay * 1.15, 0.5)
        except UnicodeDecodeError as e:
            die(f"{p}: not valid UTF-8 ({e}) — the file is corrupted or was saved "
                f"with the wrong encoding; fix it before re-running")
    records = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            die(f"{p}:{i}: invalid JSON line — {e.msg}. Fix or remove the line.")
        # Every kit JSONL file is one RECORD (object) per line. A bare array or
        # scalar line (e.g. `["a","b"]`) is valid JSON syntax, so it used to slip
        # through here and then crash the first consumer that read a field via
        # `.get()` with a raw AttributeError — reproduced across registry_db.py,
        # evidence_db.py and prisma_flow.py. Reject non-object lines at the
        # source so every consumer gets a clean die() instead.
        if not isinstance(rec, dict):
            die(f"{p}:{i}: each line must be a JSON object, got {type(rec).__name__} — "
                f"fix or remove the line.")
        records.append(rec)
    return records


def read_stdin_text() -> str:
    """Read stdin as text, decoded UTF-8 regardless of the console/locale codepage.

    `sys.stdin` decodes using the locale codepage (cp1254 on Turkish Windows,
    cp1252 elsewhere), which mangles every multibyte UTF-8 sequence in the
    payload: a title reading "Derin öğrenme ile karşılaştırılması" arrives as
    "Derin Ã¶ÄŸrenme ile karÅŸÄ±laÅŸtÄ±rÄ±lmasÄ±" and is written to the data
    file permanently corrupted. Verified reproducible: Python 3.13 on Windows
    with PYTHONIOENCODING unset. Greek/math symbols in an evidence card
    (ξ, π, σ, Ω, ², Σ) corrupt the same way.

    That matters most in the ingest path nobody types by hand:
    `literature-scout` holds no Write tool, so every source it finds reaches
    `sources/registry.jsonl` through `registry_db.py add --stdin`, and the file
    is script-owned and hook-protected — a user cannot repair it in an editor
    without deliberately unprotecting it first.

    `utf-8-sig`, not `utf-8`: a producer that emits a BOM is not an error to
    report back at the user. PowerShell's `$json | python ...` idiom — the
    natural spelling on the kit's Windows half — emits one, and strict utf-8
    leaves U+FEFF at the front where json.loads rejects it with "Unexpected
    UTF-8 BOM". Decoding it away costs nothing and matches what every producer
    means. A BOM-less payload decodes identically.

    Falls back to text stdin when `.buffer` is unavailable (a StringIO injected
    under test), stripping a BOM by hand for the same reason.
    """
    stdin_buffer = getattr(sys.stdin, "buffer", None)
    if stdin_buffer is None:
        return sys.stdin.read().lstrip("\ufeff").strip()
    try:
        return stdin_buffer.read().decode("utf-8-sig").strip()
    except UnicodeDecodeError as e:
        die(f"stdin is not valid UTF-8 — {e}. Ensure the producing process emits UTF-8 "
            f"(on Windows set PYTHONUTF8=1 or PYTHONIOENCODING=utf-8 before piping).")


def parse_json_or_jsonl(raw: str) -> list:
    """Parse `raw` as one JSON value (object or array) first — a
    pretty-printed object starts with "{" but contains embedded newlines, so
    a bare "\\n" not in raw" check would wrongly fall through to per-line
    JSONL parsing and fail on fragment lines like `"key": "value",`. Falls
    back to newline-delimited JSON only when the whole payload doesn't parse
    as one JSON value. Raises json.JSONDecodeError (from the JSONL attempt)
    if neither works — callers wrap that into their own die() message."""
    # A pathologically deep nesting depth (thousands of levels — not a
    # realistic real record, but a plausible adversarial/malformed payload
    # since this parses raw stdin/CLI text) blows Python's C-stack recursion
    # limit inside json.loads with a raw RecursionError, not JSONDecodeError —
    # every caller here only catches the latter, so it would otherwise crash
    # past die()'s clean-error contract.
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else [parsed]
    except RecursionError:
        die("input is too deeply nested to parse")
    except json.JSONDecodeError:
        try:
            return [json.loads(line) for line in raw.splitlines() if line.strip()]
        except RecursionError:
            die("input is too deeply nested to parse")


def next_id(records: list[dict], prefix: str) -> str:
    """Next sequential '<prefix>-####' id given existing records' 'id' fields.

    Shared by registry_db.py (SRC-####) and evidence_db.py (EV-####), which
    each carried their own copy of this before it drifted into two
    near-identical implementations differing only by prefix.
    """
    mx = 0
    for r in records:
        try:
            mx = max(mx, int(r.get("id", f"{prefix}-0000").split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"{prefix}-{mx + 1:04d}"


def append_jsonl(path: str | Path, record: dict) -> None:
    """Read-modify-atomic-write, not a raw open("a") append — a bare append can
    be killed mid-write (crash/disk-full/process-kill), leaving a torn final
    line that read_jsonl() then rejects via die(), on a file every other write
    path in this module protects with temp-file + os.replace(). Callers already
    hold file_lock() across this cycle, so no extra locking is needed here;
    the cost is an O(n) rewrite per append instead of O(1), acceptable at the
    kit's realistic scale (hundreds to low thousands of registry/card
    records, not a high-throughput log)."""
    p = Path(path)
    records = read_jsonl(p)
    records.append(record)
    write_jsonl(p, records)


# ---------- OS-level protection for the script-owned data files ----------
# Invariant 6 ("registry/cards/venues/bib change only through scripts/") had
# exactly one enforcement layer: .claude/hooks/protect_data_files.py, which
# reads the proposed Bash command and decides whether it writes to a protected
# name. That layer works, and its defect history (see _shell_write_sink.py's
# header) is the argument for this one: a detector built on shell syntax is
# only ever as good as the syntax it has been taught, and every bypass found so
# far was found by someone trying, not by the detector.
#
# So the files themselves are marked read-only after every sanctioned write.
# What that stops, with no pattern matching involved: `>` and `>>` redirects,
# `tee`, `Set-Content`/`Add-Content`/`Out-File`, `open(p, "w")`, in-place
# editors — the ordinary ways a file gets clobbered, refused by the OS whether
# or not the hook recognised the command.
#
# What it does NOT stop, stated plainly rather than left to be discovered:
# `rm`/`del`/`Remove-Item -Force` and `mv`, which are governed by the DIRECTORY
# permission, not the file's. Those remain the hook's job. This is a second
# layer, not a replacement — neither one alone is the guarantee.
PROTECTED_BASENAMES = frozenset({
    "registry.jsonl", "cards.jsonl", "venues.jsonl", "search-log.jsonl",
    "references.bib", "verify-status.json",
    # provenance.jsonl joined this set with the ledger itself: a hash chain
    # whose file anyone can rewrite is a chain that proves nothing, since the
    # cheapest attack on it is not forging a hash but replacing the whole file
    # with a shorter, tidier history. Marking it read-only after every
    # sanctioned append makes that the same kind of refusal the other six get.
    "provenance.jsonl",
    # datasets.jsonl carries the per-file SHA-256 of the data the results
    # were computed from. A drift report is only worth reading if the
    # recorded hash is harder to edit than the file it describes.
    "datasets.jsonl",
    # runs.jsonl carries the seed, the config hash and the metrics a results
    # table is read from. Its config hash is a tamper check, and a tamper
    # check in a file anyone can rewrite checks nothing.
    "runs.jsonl",
})

_WRITE_BITS = 0o222


def is_protected_data_file(path: str | Path) -> bool:
    """True for the nine script-owned data files, matched on basename only.

    Basename, not full path, for the same reason protect_data_files.py matches
    that way: the project root is wherever the user ran /new-project, and a
    path-anchored rule silently stops applying the moment someone runs a script
    from a subdirectory.
    """
    return Path(path).name.lower() in PROTECTED_BASENAMES


def unprotect(path: str | Path) -> None:
    """Restore write permission on a protected data file.

    The escape hatch, and deliberately a public one: a user who abandons a
    project must not need this module to delete their own directory, and a
    contributor debugging a half-written registry must not have to guess why
    their editor refuses to save. Silent no-op when the file does not exist or
    the filesystem does not support the bits (some network/container mounts).
    """
    p = Path(path)
    try:
        mode = p.stat().st_mode
        if not mode & _WRITE_BITS:
            os.chmod(p, mode | 0o200)  # owner-write only; group/other unchanged
    except (OSError, NotImplementedError):
        pass


def protect(path: str | Path) -> None:
    """Clear write permission on a protected data file. See unprotect()."""
    p = Path(path)
    try:
        os.chmod(p, p.stat().st_mode & ~_WRITE_BITS)
    except (OSError, NotImplementedError):
        pass


def _replace_with_retry(tmp: Path, dest: Path) -> None:
    """os.replace(tmp, dest) with Windows PermissionError retry (see write_jsonl).

    On unrecoverable failure, unlinks tmp before re-raising as a plain OSError
    so callers can catch OSError generically for a clean die() instead of a
    raw traceback, and so the .tmp<pid> file never lingers on disk.

    This is also the single chokepoint through which every sanctioned write to
    a protected data file passes (append_jsonl -> write_jsonl -> here;
    write_text_atomic -> here; write_json_atomic -> write_text_atomic -> here),
    which is why the read-only marking is applied here and nowhere else. A new
    writer that does not go through an atomic helper is a writer that skips
    both the crash-safety and the protection — which is the intended shape of
    that mistake being loud rather than silent.
    """
    protected = is_protected_data_file(dest)
    if protected:
        # Windows refuses os.replace() ONTO a read-only file (POSIX does not —
        # rename is governed by the directory). Clearing it first is what makes
        # the sanctioned path behave identically on both.
        unprotect(dest)
    attempts, delay = 60, 0.05
    for attempt in range(attempts):
        try:
            os.replace(tmp, dest)
            if protected:
                protect(dest)
            return
        except PermissionError:
            if attempt == attempts - 1:
                tmp.unlink(missing_ok=True)
                # Re-arm before giving up: the write failed, so the old file is
                # still the live one and must not be left writable by a
                # half-finished sanctioned write. Without this, one locked-file
                # failure silently disarms the protection until the next
                # successful write — the exact shape of gap this layer exists
                # to close.
                if protected:
                    protect(dest)
                raise OSError(
                    f"could not replace {dest} after {attempts} attempts "
                    f"(file locked by another process?)"
                ) from None
            time.sleep(delay)
            delay = min(delay * 1.15, 0.5)


def write_jsonl(path: str | Path, records: list[dict]) -> None:
    """Atomic full-file rewrite (temp file + os.replace) — a bare truncate+write
    leaves a window where a concurrent, unlocked reader (query/list/stats/
    xlsx_export.py/cite_audit.py/word_budget.py/prisma_flow.py) can observe a
    partially-written or empty file mid-rewrite and crash on invalid JSON.
    os.replace() is atomic on both POSIX and Windows for same-volume renames,
    so a reader always sees either the complete old file or the complete new
    one, never a partial write — this is what actually closes that race, not
    locking every reader (which set-status/set-field already serialize via
    file_lock against other WRITERS, but not against readers)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_sibling(p)
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # Windows can transiently deny os.replace() (WinError 5) — observed under
    # heavy concurrent read/write load, likely AV/indexer interference rather
    # than another scholar-kit process (a plain read doesn't hold an
    # exclusive handle) — retry with backoff rather than surface a spurious
    # failure; POSIX rename never hits this path.
    _replace_with_retry(tmp, p)


def write_json_atomic(path: str | Path, obj) -> None:
    """Same temp-file + os.replace (with Windows retry) atomicity as write_jsonl,
    for callers writing a single JSON document (e.g. .claude/settings.json)
    instead of a JSONL record list — a bare write_text() truncate-write leaves
    the same partial-file window write_jsonl's docstring warns about."""
    write_text_atomic(path, json.dumps(obj, indent=2) + "\n")


def write_text_atomic(path: str | Path, text: str) -> None:
    """Same temp-file + os.replace (with Windows retry) atomicity as write_jsonl,
    for callers writing arbitrary non-JSONL text (e.g. bib/references.bib)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_sibling(p)
    tmp.write_text(text, encoding="utf-8", newline="\n")
    _replace_with_retry(tmp, p)


def write_bytes_atomic(path: str | Path, data: bytes) -> None:
    """Same temp-file + os.replace (with Windows retry) atomicity as write_jsonl,
    for callers writing raw bytes (e.g. a downloaded data/*.csv index) — a bare
    `Path.write_bytes()` truncates the destination immediately, so a write
    interrupted partway (process killed, disk full, Windows AV/indexer lock)
    leaves a corrupted file that PERMANENTLY overwrites the previously-good
    data with no recovery short of re-downloading."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp_sibling(p)
    tmp.write_bytes(data)
    _replace_with_retry(tmp, p)


# ---------- cross-process file locking ----------
# Parallel subagents (e.g. source-analyst under --fast) call evidence_db.py /
# registry_db.py concurrently. Without locking, two processes racing on
# read-all -> compute-next-id -> append lose records and mint duplicate IDs.
# This wraps that cycle in an advisory exclusive lock over a `<path>.lock`
# sidecar file so concurrent writers serialize instead of racing.

def _lock_backend():
    try:
        import fcntl

        def acquire(f, timeout):
            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return
                except OSError:
                    if time.monotonic() > deadline:
                        # `from None`: the OSError is "lock currently held" —
                        # expected control flow, not a cause worth chaining. A
                        # bare raise here would print an EAGAIN traceback above
                        # the message that actually says what happened.
                        raise TimeoutError(
                            f"could not acquire lock within {timeout}s") from None
                    time.sleep(0.05)

        def release(f):
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        return acquire, release
    except ImportError:
        import msvcrt

        def acquire(f, timeout):
            deadline = time.monotonic() + timeout
            while True:
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    return
                except OSError:
                    if time.monotonic() > deadline:
                        raise TimeoutError(  # from None: see the fcntl branch
                            f"could not acquire lock within {timeout}s") from None
                    time.sleep(0.05)

        def release(f):
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)

        return acquire, release


_LOCK_ACQUIRE, _LOCK_RELEASE = _lock_backend()


@contextlib.contextmanager
def file_lock(path: str | Path, timeout: float = 30.0):
    """Serialize the read-modify-write cycle for `path` across processes."""
    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    f = lock_path.open("a+b")
    try:
        f.seek(0, 2)
        if f.tell() == 0:
            f.write(b"\0")
            f.flush()
        f.seek(0)
        _LOCK_ACQUIRE(f, timeout)
        try:
            yield
        finally:
            _LOCK_RELEASE(f)
    finally:
        f.close()


# ---------- DOI ----------

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")


def clean_doi(raw: str) -> str:
    """Strip a doi.org URL prefix/scheme from a user- or agent-supplied DOI
    string. Does not validate format — pair with DOI_RE.match() for that."""
    return (raw or "").strip().removeprefix("https://doi.org/").removeprefix(
        "http://doi.org/").removeprefix("doi:")


# ---------- optional-dependency degradation ----------

_rapidfuzz_warned = False


def warn_missing_rapidfuzz():
    """Call from every `except ImportError:` fallback around `from rapidfuzz
    import fuzz` (doi2bib.py, bib_doctor.py, registry_db.py, venue_check.py).
    Without rapidfuzz, fuzzy title/venue matching silently collapses to exact
    string equality — the citation-verification "FIX band" (similarity 70-97)
    disappears entirely, so a wrong-DOI attachment that fuzzy matching would
    flag for review can instead score as a clean exact-mismatch, quietly
    weakening the zero-fabrication guarantee. rapidfuzz is already a stated
    requirement (requirements.txt, README install step) — this only fires when
    that requirement wasn't actually met. Printed once per process (not once
    per call site) so a single `doi2bib.py --verify` run over many entries
    doesn't spam the same warning per entry."""
    global _rapidfuzz_warned
    if not _rapidfuzz_warned:
        _rapidfuzz_warned = True
        print("WARN: rapidfuzz not installed — fuzzy title/venue matching has "
              "fallen back to exact-string comparison, weakening duplicate and "
              "citation-verification checks. Run: pip install rapidfuzz",
              file=sys.stderr)


# ---------- HTTP ----------

def http_get_with_retry(url: str, retries: int = 2, backoff: float = 1.5,
                        timeout: float = 20, **kwargs):
    """requests.get with retry-with-backoff on transient connection/timeout
    errors only — 4xx/5xx HTTP responses are returned as-is for the caller to
    decide (raise_for_status(), status_code checks), never retried here.
    doi2bib.py and update_data.py each had their own copy of this that had
    already drifted (different retries/backoff); kept as one function-local
    `import requests` (not top-level) so lib_common.py stays importable
    without requests installed for scripts that don't need it."""
    import requests
    last_exc = None
    for attempt in range(retries):
        try:
            return requests.get(url, timeout=timeout, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
            if attempt < retries - 1:
                time.sleep(backoff)
    raise last_exc


# ---------- minimal BibTeX ----------

_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)


def parse_bibtex(text: str) -> list[dict]:
    """Parse BibTeX into [{type, key, fields:{lowername: value}}].

    Handles brace-delimited and quote-delimited values with nested braces.
    Good enough for machine-fetched entries (doi2bib output); not a full parser.
    """
    entries = []
    for m in _ENTRY_RE.finditer(text):
        etype, key = m.group(1).lower(), m.group(2)
        if etype in ("comment", "preamble", "string"):
            continue
        body_start = m.end()
        depth = 1  # we are inside the entry's outer brace
        i = body_start
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[body_start : i - 1]
        entries.append({"type": etype, "key": key, "fields": _parse_fields(body)})
    return entries


def _parse_fields(body: str) -> dict:
    fields = {}
    i, n = 0, len(body)
    while i < n:
        m = re.compile(r"\s*(\w[\w\-]*)\s*=\s*").match(body, i)
        if not m:
            i += 1
            continue
        name = m.group(1).lower()
        i = m.end()
        if i >= n:
            break
        if body[i] == "{":
            depth, j = 1, i + 1
            while j < n and depth > 0:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                j += 1
            value, i = body[i + 1 : j - 1], j
        elif body[i] == '"':
            j = i + 1
            while j < n and body[j] != '"':
                j += 1
            value, i = body[i + 1 : j], j + 1
        else:  # bare number
            m2 = re.compile(r"[^,\n]*").match(body, i)
            value, i = m2.group(0).strip(), m2.end()
        fields[name] = re.sub(r"\s+", " ", value).strip()
        comma = body.find(",", i)
        i = comma + 1 if comma != -1 else n
    return fields


def serialize_bibtex(entry: dict) -> str:
    lines = [f"@{entry['type']}{{{entry['key']},"]
    for k, v in entry["fields"].items():
        lines.append(f"  {k} = {{{v}}},")
    lines.append("}")
    return "\n".join(lines)


_TR_TRANSLIT = str.maketrans({
    "ş": "s", "Ş": "S", "ç": "c", "Ç": "C", "ğ": "g", "Ğ": "G",
    "ö": "o", "Ö": "O", "ü": "u", "Ü": "U", "ı": "i", "İ": "I",
})


def transliterate(text: str) -> str:
    """ASCII-fold Turkish and other Latin-diacritic text for machine keys.

    Turkish ı/İ/ğ/ş/ç/ö/ü don't all reliably decompose via Unicode NFKD
    (ı/İ/ğ/ş are atomic codepoints), so map them explicitly first; then
    NFKD + drop combining marks handles any other accented Latin letters
    (é, à, ñ, ...). Used by bib-key generation so "Şahin" -> "sahin", not
    the silently-truncated "ahin" that a raw ASCII filter would produce.
    """
    text = (text or "").translate(_TR_TRANSLIT)
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def normalize_title(title: str) -> str:
    """Lowercase, strip braces/punctuation/whitespace — for fuzzy identity checks."""
    t = re.sub(r"[{}]", "", title or "")
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def normalize_issn(issn: str) -> str:
    """Strip hyphens/spaces, uppercase (X check digit)."""
    return re.sub(r"[^0-9Xx]", "", issn or "").upper()


# ---------- Markdown frontmatter ----------

_FRONTMATTER_RE = re.compile(r"﻿?---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """Parse a Markdown file's leading YAML-ish frontmatter into a flat dict
    of key -> string value. Handles folded multi-line values (continuation
    lines after "key:", accumulated until the next top-level "key:" line) —
    validate_kit.py and extract_skill_descriptions.py each had their own
    copy of this that had already drifted (validate_kit.py's version
    silently truncated any multi-line "description:" to its first line, e.g.
    citation-verifier.md's). Not a real YAML parser — good enough for
    SKILL.md/agent .md frontmatter (name, description, tools, model,
    disable-model-invocation), which is all this kit ever puts there."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm, buf, key = {}, [], None
    for line in m.group(1).splitlines():
        km = re.match(r"^([\w-]+):\s*(.*)$", line)
        if km and not line.startswith(" "):
            if key:
                fm[key] = " ".join(buf).strip().strip("\"'")
            key, buf = km.group(1), [km.group(2)]
        elif key:
            buf.append(line.strip())
    if key:
        fm[key] = " ".join(buf).strip().strip("\"'")
    return fm


# ---------- CLI plumbing ----------

def read_paper_type(project: str | Path = "PROJECT.md") -> str:
    """PROJECT.md's `- **Type:**` value, lowercased, trailing HTML comment stripped.

    Several checks mean different things for different paper types — an included
    study that contributes no data is normal in a narrative review and a silent
    loss in a systematic one — so the type has to be readable from anywhere.
    Returns "" when PROJECT.md is absent or carries no Type line; callers must
    treat that as "unknown", never as a default type, because guessing here
    turns a check off without saying so.

    FWD: `replication_pack.paper_type()` parses the same line with the same
    regex. Not merged in this change (no refactoring while fixing), but the two
    should become one call.
    """
    path = Path(project)
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("- **Type:**"):
            value = line.split("**", 2)[-1].strip(": ").strip()
            return re.sub(r"<!--.*?-->", "", value, flags=re.S).strip().lower()
    return ""


def require_within_cwd(path_str: str, flag_name: str) -> str:
    """Reject a --file/--registry/--cards-style path argument that would
    write outside the current project directory (via '..' traversal or an
    absolute path elsewhere). These scripts are the SOLE sanctioned writers
    for registry/cards/etc (a PreToolUse hook blocks direct Write/Edit/Bash
    to the canonical files) — that guarantee is only meaningful if the
    destination the script actually writes to stays inside the project;
    an override pointing outside it would silently escape that protection.
    Returns path_str unchanged if it's safe (relative paths remain relative,
    so error messages/tests keep seeing the original string, not an
    absolute one)."""
    resolved = Path(path_str).resolve()
    cwd = Path.cwd().resolve()
    if resolved != cwd and cwd not in resolved.parents:
        die(f"{flag_name} must resolve inside the current project directory "
            f"({cwd}), got {resolved}")
    return path_str


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def emit(payload, as_json: bool):
    """Print a script result. Structured payloads (dict/list) are ALWAYS JSON —
    the kit's "output is always JSON" invariant holds regardless of `as_json`,
    so consumers can parse any structured result unconditionally. `as_json`
    therefore only governs SCALAR payloads (a bare string/number): pass True to
    JSON-encode it, False to print it raw. It is intentionally NOT a master
    switch that can turn structured output into plain text."""
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if isinstance(payload, (dict, list)):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(payload)
