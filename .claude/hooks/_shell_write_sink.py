#!/usr/bin/env python3
"""Shared shell write-sink detection for PreToolUse hooks.

Both protect_data_files.py (Invariant 6: registry/cards/venues/bib are
script-owned) and phase_gate.py (Invariant 3: build/exports need verify=PASS
+ Major=0) need to answer "does this Bash command write to path P?" via the
same shell syntax — redirects, tee (piped or not)/Tee-Object/Set-Content/
Add-Content/Out-File/New-Item, python open()/shutil/pathlib writes (incl.
os.rename/os.replace/os.remove/os.unlink/Path.unlink()),
cp/mv/Copy-Item/Move-Item/Rename-Item, in-place editors, rm/del/Remove-Item,
`find … -delete`/`-exec rm`, `… | xargs rm`, and gio-trash/trash-put.
Kept as one module so a new evasion technique hardened
in one hook doesn't silently stay unfixed in the other — phase_gate.py's
build/exports Bash check used to be a narrow interpreter+script-token
allowlist that missed `cp draft.pdf build/final.pdf` or `cat > exports/x.md`
entirely, while protect_data_files.py already had this generic detection for
its own protected filenames.

Best-effort, not a sandbox: a sufficiently obfuscated command (computed paths,
base64, exec/eval, ...) can still slip through. Simple variable indirection
(`p='a'+'b'; open(p,...)` or `p=os.path.join('a','b'); open(p,...)`) — not
adversarial obfuscation, just an ordinary way to write the same one-liner —
IS resolved via constant-folding in `_fold_simple_string_vars` before the
regexes below run. Plain shell variable indirection in a redirect target
(`F=drafts/intro.md; echo x > $F`) is likewise resolved, by
`_fold_shell_vars`.

PowerShell short aliases (`ni`, `sc`, `ac`, `cpi`, `mi`, `ri`, `rd`, `rmdir`,
`rni`, `ren`, `erase`) are recognized alongside their full cmdlet names —
found live: `sc sources/registry.jsonl '{"fake":1}'` (Set-Content's built-in
alias) defeated every hook built on this module just as completely as the
full cmdlet name would have, since PowerShell resolves the alias to the same
cmdlet and a user reaching for `sc`/`ni`/`ac` out of habit isn't attempting
adversarial evasion.

Change record: this module carries the densest defect history in the kit, and
the narratives above stay here deliberately — every one of them names a bypass
that shipped, and a reader widening a pattern needs them in view. They are the
point-of-use summary, not the record. Full reasoning, the review pass behind
each fix and the alternatives rejected: DECISIONS.md (D-069, D-073..D-078,
D-080..D-084). Behaviour is locked by tests/test_shell_write_sink.py and the
round suites listed under `hooks` in tests/README.md.
"""
from __future__ import annotations

import re
import shlex

# A quoted target ('...'/"...") is matched whole (including embedded spaces —
# `> "drafts/my draft.md"` is a single write target, not two) before falling
# back to a bare, whitespace-terminated token. An earlier version's char
# class ([^\s'\";|&]+) excluded whitespace even inside quotes, so a quoted
# path containing a space was silently truncated at the first space and
# never matched the real target — an ordinary filename, not adversarial
# obfuscation, sailed straight past every gate that calls write_targets().
_TARGET = r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\";|&]+))"


def _target_group(m: re.Match) -> str:
    return next(g for g in m.groups() if g is not None)


def _quoted_spans(text: str):
    """Index ranges (open_pos, close_pos) of every top-level shell-quoted
    region in `text`. Used to DROP a write-sink match whose command/operator
    ANCHOR falls INSIDE quotes — a `>`/`tee`/`open(`/`rm`/`cp` that appears
    within a quoted argument (`git commit -m "note > drafts/x.md"`, `echo "run
    rm -rf foo"`) is DATA, not an executed sink, and must not gate. A quoted
    TARGET after a real operator (`echo x > "drafts/my draft.md"`) is
    unaffected: its operator sits OUTSIDE the quotes, so the match anchor is
    not in any span. Single quotes are literal in POSIX (no escapes); double
    quotes honor backslash escapes. Returns None on an UNBALANCED quote — the
    caller then applies NO filtering and scans everything, i.e. fail-closed: a
    malformed-quote command keeps the pre-existing, maximally-suspicious
    behavior rather than letting one unterminated quote swallow a real sink.
    Nested-shell wrappers keep working regardless: _unwrap() re-scans each
    wrapper's inner command string from the top, where the inner sink is
    unquoted and its anchor matches cleanly."""
    spans: list[tuple[int, int]] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "'\"":
            j = i + 1
            if c == '"':
                while j < n and text[j] != '"':
                    j += 2 if text[j] == "\\" else 1
            else:
                while j < n and text[j] != "'":
                    j += 1
            if j >= n:
                return None  # unbalanced -> fail-closed (caller scans everything)
            spans.append((i, j))
            i = j + 1
        else:
            i += 1
    return spans


def _in_quotes(pos: int, spans) -> bool:
    """True if `pos` sits strictly inside one of `spans` (an anchor char at the
    quote character itself, or with spans=None, counts as NOT quoted)."""
    if spans is None:
        return False
    return any(lo < pos < hi for lo, hi in spans)


# Backslash immediately followed by a non-space character — a Windows path
# separator, never a POSIX escaped-space idiom (which needs `\ `, excluded by
# the lookahead). See _tokens() below for why this must run before shlex.
_BACKSLASH_SEP = re.compile(r"\\(?=\S)")

# Command-position anchor: `\b` alone matches at a hyphen/letter boundary too
# (`-mv` has a word-boundary right before the "m"), so a plain `\bmv\b` reads
# an option flag like `-mv`/`-rm` as if it were the actual mv/rm command. Only
# match at the true start of a (sub)command — start-of-string or right after
# a separator (whitespace incl. newline, `;`, `&`, `|`) — never right after `-`.
# Defined here (used by _PS_PATH_CMDLET below too, not just _COPY_MOVE/_DELETE
# further down) so PowerShell's short aliases (`ni`, `sc`, `ac`, ...) are only
# matched in actual command position, not as a substring of some other token.
#
# NOTE: this anchor is deliberately NARROW (no quote/paren in the set). Nested-
# shell wrappers — where the real command sits right after a quote (`bash -c
# "cp ..."`, `sh -c 'rm ...'`, `powershell -Command "Remove-Item ..."`, `python
# -c "...os.system('cp ...')"`) — are handled NOT by widening this anchor (which
# over-matched ordinary prose like `git commit -m "mv x refactor"` or `echo
# "move the file"` as real commands, a live false-positive DENY) but by
# _unwrap() below, which extracts each wrapper's inner command string and
# re-scans it from the top, where the inner command legitimately IS at position
# 0 and this narrow anchor matches it cleanly.
_CMD_START = r"(?:^|(?<=[\s;&|]))"

# Shell redirection and bare `tee`, followed by the target path. The leading
# pipe is OPTIONAL — `tee file <<< data` or `tee -a file < input` are valid,
# pipe-less invocations that a pipe-required pattern would silently miss.
# `(?!-)` after `tee\b` stops this from also matching the "Tee" in
# "Tee-Object" (word-boundary-wise `\btee\b` matches there too, since a
# hyphen is a non-word char) — Tee-Object and its PowerShell siblings are
# handled by _ps_cmdlet_targets() below instead, since their path parameter
# isn't always the token immediately after the cmdlet name.
# `>>?\|?` also matches the noclobber-override redirect `>|` (bash/zsh), which
# an earlier `>>?`-only operator matched the `>` of but then failed to find a
# target for, since the following `|` isn't a valid target character.
_WRITE_SINK = re.compile(
    r"(?:>>?\|?|(?:\|\s*)?tee\b(?!-)(?:\s+-a)?)\s*" + _TARGET,
    re.IGNORECASE,
)
# Same three target alternatives as _TARGET, but the bare-token alternative
# excludes a leading '-' — used only for the positional-argument fallback in
# _ps_cmdlet_targets(), where a flag name (e.g. "-Value") must never be
# mistaken for the positional path argument.
_TARGET_NO_FLAG = r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\";|&-][^\s'\";|&]*))"
# PowerShell cmdlets whose destination is a NAMED parameter that can appear
# ANYWHERE among the cmdlet's other named parameters — `Set-Content -Value
# "x" -Path foo.md` is exactly as valid as `Set-Content -Path foo.md -Value
# "x"`. A regex requiring the path flag immediately after the cmdlet name
# (as the redirect-style patterns above do) misses every reordering — found
# live: `Set-Content -Value "x" -Path drafts/intro.md`, `Out-File -Encoding
# utf8 -FilePath drafts/intro.md`, `New-Item -ItemType File -Path
# drafts/intro.md`, `Tee-Object -Append -FilePath drafts/intro.md` all
# defeated the old adjacent-flag-only regex. Handled by scanning each
# cmdlet's whole sub-command for -Path/-FilePath/-LiteralPath instead.
# Clear-Content (alias clc) wipes a file's contents in place — a mutation of a
# protected file every bit as destructive as Set-Content, so it belongs here.
_PS_PATH_CMDLET = re.compile(
    _CMD_START + r"(?:Set-Content|sc|Add-Content|ac|Clear-Content|clc|Out-File|New-Item|ni|Tee-Object)\b",
    re.IGNORECASE)
_PS_PATH_FLAG = re.compile(r"-(?:Path|FilePath|LiteralPath)\b\s*" + _TARGET, re.IGNORECASE)
_SEGMENT_BOUNDARY = re.compile(r"[;&|\n]")


def _ps_cmdlet_targets(command: str, spans=None) -> list[str]:
    """For each Set-Content/Add-Content/Out-File/New-Item/Tee-Object
    invocation, search the REST OF ITS SUB-COMMAND (up to the next `;`/`&`/
    `|`/newline) for -Path/-FilePath/-LiteralPath, so parameter order can't
    hide the target. Falls back to the cmdlet's first positional argument
    only when no such flag is present anywhere in the segment. A cmdlet name
    that itself sits inside a quoted argument (`-m "... Set-Content ..."`) is
    data, not an invocation — skipped via `spans` (see _quoted_spans)."""
    targets: list[str] = []
    for cm in _PS_PATH_CMDLET.finditer(command):
        if _in_quotes(cm.start(), spans):
            continue
        boundary = _SEGMENT_BOUNDARY.search(command, cm.end())
        segment = command[cm.end():boundary.start() if boundary else len(command)]
        flag_m = _PS_PATH_FLAG.search(segment)
        if flag_m:
            targets.append(_target_group(flag_m))
            continue
        pos_m = re.match(r"\s*" + _TARGET_NO_FLAG, segment)
        if pos_m:
            targets.append(_target_group(pos_m))
    return targets
# python -c "...open('path', <mode>...)..." one-liners. The mode is a write mode
# if it contains w/a/x (truncate/append/exclusive-create) OR a `+` (r+/w+/a+ all
# open for writing) — an earlier `[wa]`-only check missed `open('f','r+')`
# followed by `.truncate(0)`, a real content-wipe.
_PYOPEN_WRITE = re.compile(
    r"open\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"][^'\"]*[wax+]", re.IGNORECASE)
# os.open('path', flags) with a write-intent flag (O_WRONLY/O_RDWR/O_CREAT/
# O_TRUNC/O_APPEND) — the low-level sibling of open() that _PYOPEN_WRITE's
# mode-string check can't see (os.open takes integer flags, not a mode string).
_PY_OS_OPEN = re.compile(
    r"os\.open\(\s*['\"]([^'\"]+)['\"]\s*,[^)]*O_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND)",
    re.IGNORECASE)
# .NET write APIs reachable from PowerShell/pwsh: [IO.File]::WriteAllText(path,
# ...)/WriteAllBytes/WriteAllLines/AppendAllText/AppendAllLines — the path is
# the first argument. Create/OpenWrite/AppendText added: found live,
# `[IO.File]::Create("sources/registry.jsonl")` (and ::OpenWrite/::AppendText,
# same [Type]::Method(path) shape) opens a protected file for writing exactly
# like WriteAllText but was entirely unmatched by the original alternation.
_DOTNET_WRITE = re.compile(
    r"(?:WriteAllText|WriteAllBytes|WriteAllLines|AppendAllText|AppendAllLines|"
    r"Create|OpenWrite|AppendText)"
    r"\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
# StreamWriter/FileStream construction — a second, constructor-based route to
# an open write handle that ::Create/::OpenWrite above don't cover: both
# `New-Object IO.StreamWriter("path", ...)` (PowerShell's positional-args
# constructor sugar) and the `[IO.StreamWriter]::new("path", ...)` static
# factory form reach the same write capability as [IO.File]::Create.
_DOTNET_CTOR = re.compile(
    r"(?:New-Object\s+(?:-TypeName\s+)?(?:System\.)?IO\.(?:StreamWriter|FileStream)\b|"
    r"(?:System\.)?IO\.(?:StreamWriter|FileStream)\]::new)"
    r"\s*\(?\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
# fileinput.input('path', ..., inplace=True) rewrites the file in place — only a
# write when inplace is set, so require `inplace` to appear before the close paren.
_PY_FILEINPUT = re.compile(
    r"fileinput\.input\(\s*['\"]([^'\"]+)['\"](?=[^)]*inplace)", re.IGNORECASE)
# dd ... of=DEST — the of= operand is the write destination.
_DD_OF = re.compile(r"\bof=" + _TARGET, re.IGNORECASE)
# shutil.copy/copyfile/copy2/move('src', 'dest') — dest is the write target.
_PY_SHUTIL_WRITE = re.compile(
    r"shutil\.(?:copy2?|copyfile|move)\(\s*[^,]+,\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
# pathlib.Path('path').write_text(...)/.write_bytes(...)/.unlink(...)/.open('w'/'a', ...)
_PY_PATHLIB_WRITE = re.compile(
    r"Path\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\.\s*(?:write_text|write_bytes|unlink\b|"
    r"open\(\s*['\"][^'\"]*[wax+])", re.IGNORECASE)
# Path('src').replace('dest') / .rename('dest') — unlike the other pathlib
# writes above, the mutated file is the ARGUMENT (destination), not the path in
# Path(); capture the destination.
_PY_PATHLIB_RENAME = re.compile(
    r"Path\(\s*['\"][^'\"]+['\"]\s*\)\s*\.\s*(?:replace|rename)\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE)
# os.remove('path') / os.unlink('path') — outright deletion via the os module.
_PY_OS_REMOVE = re.compile(r"os\.(?:remove|unlink)\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
# shutil.rmtree('path') — deletes an entire directory tree, not just one file;
# a real path to `sources`/`evidence`/etc. destroys every protected file inside
# at once. Not covered by _PY_SHUTIL_WRITE (that pattern only matches the
# copy/move family, which take two arguments; rmtree takes one).
_PY_SHUTIL_RMTREE = re.compile(r"shutil\.rmtree\(\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
# os.rename('src', 'dest') / os.replace('src', 'dest') — both the source
# (moved AWAY from its required location) and the destination are targets,
# same reasoning as cp/mv below; unlike the single-target patterns above,
# both capture groups are meaningful simultaneously, not alternatives.
_PY_OS_RENAME = re.compile(
    r"os\.(?:rename|replace)\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
# cp/mv/rename SRC DEST (best-effort: every non-flag whitespace-separated
# token, not just the destination — `mv registry.jsonl /tmp/out.bak` moves a
# protected file AWAY from its required location, which is data loss, not
# just an unauthorized overwrite; checking only the last token would miss
# this). Includes the PowerShell cmdlet forms (Copy-Item/Move-Item/Rename-Item)
# and their built-in short aliases (cpi/mi/rni/ren). `install` (coreutils)
# copies its source args to a final destination exactly like cp, but is NOT in
# this verb list — see _INSTALL below for why its whitespace-permissive anchor
# would misfire on `pip install <pkg>` and how the stricter anchor fixes it.
# Stops at a single `;`/`&`/`|` (which of course also covers `&&`/`||`) —
# an earlier version's stop-set only recognized the doubled forms, so
# `mv a.txt b.txt & cat registry.jsonl` (single `&`, a background-job
# separator) or a bare `|` pipe kept consuming past the mv command entirely,
# scooping the NEXT, unrelated command's arguments in as if they were mv
# targets — a false-positive DENY on a harmless read-only command.
_COPY_MOVE = re.compile(
    _CMD_START + r"(?:cp|mv|cpi|mi|copy|move|ren|rni|Copy-Item|Move-Item|Rename-Item)\s+"
    r"((?:(?!['\"]?\s*[;&|]).)+)",
    re.IGNORECASE)
# `install` (coreutils) copies its source args to a final destination exactly
# like cp — `install -m644 evil sources/registry.jsonl` must be caught. It is
# kept OUT of _COPY_MOVE's verb list on purpose: _CMD_START matches after ANY
# whitespace, so `install` folded in there also fires on the SECOND word of the
# vastly more common `pip install <pkg>` / `npm install <pkg>` / `apt install
# <pkg>`, capturing the package name as a bogus write target — a live
# false-positive DENY of ordinary package installs by scoped agents
# (agent_write_scope.py). A real coreutils `install` is a COMMAND, so it sits
# at TRUE command position — start of the (sub-)command or right after a
# `;`/`&`/`|` separator — never as an argument after another command's name.
# Anchoring to that stricter position (not the whitespace-permissive
# _CMD_START) leaves `pip install requests` unmatched while `install ...
# sources/registry.jsonl` and `foo && install ...` still match.
_INSTALL = re.compile(
    r"(?:^|[;&|]\s*)install\s+((?:(?!['\"]?\s*[;&|]).)+)", re.IGNORECASE)
# rm/del/Remove-Item TARGET — outright deletion is not a "write" but is
# exactly the mutation these gates exist to prevent. Includes Remove-Item's
# built-in short aliases (ri/rd/rmdir/erase).
# Includes `truncate` (`truncate -s 0 file` wipes a file's contents) — its file
# operand is a non-flag token like rm's, so the same token extraction applies.
_DELETE = re.compile(
    _CMD_START + r"(?:rm|del|ri|rd|rmdir|erase|truncate|Remove-Item)\b\s*((?:(?!['\"]?\s*[;&|]).)+)",
    re.IGNORECASE)
# sed/awk/perl -i ... FILE  (in-place editors; target is the trailing file arg).
# The in-place flag is matched as `-[A-Za-z]*i` (a dash, any clustered flag
# letters, an `i`), not a literal `-i`: single-dash flags cluster, so
# `perl -pi -e ...` and `sed -ni ...` write in place exactly like `-i` but
# contain no adjacent `-i` substring — found live, both defeated the old
# `-i\S*` pattern. `-e`/`-n`/`-F,` (no `i` in the cluster) still don't match.
#
# The flag must START A TOKEN — `(?:(?<=\s)|(?<=^))` — and that anchor is the
# whole difference between reading a hyphenated filename and being told you
# tried to write it. Without it the dash could sit anywhere, INCLUDING inside a
# path: `sed -n '34p' drafts/ek-e-cihaz-eslemesi.md` matched on `-ci`, and
# `src/api-client.ts`, `notes/pre-training.md`, `data-cleaning.py` all match the
# same way. Every one of those is a plain read, and the phase gate denied them
# as writes into a gated directory — a hook that blocks `sed -n` on a file whose
# name happens to contain a hyphen-then-i is one people learn to route around,
# which costs more than the bypass it was closing. Found live on this kit's own
# manuscript, where four of five appendix filenames matched.
_INPLACE_EDIT = re.compile(
    r"\b(?:sed|gawk|awk|perl)\b[^;&|]*?(?:(?<=\s)|(?<=^))-[A-Za-z]*i\S*[^;&|]*",
    re.IGNORECASE)

# `find <roots> [-name X] -delete` / `-exec rm|unlink|shred {} \;` — the deletion
# actions of find. The plain rm/del pattern above never fires here: the file to
# delete is named by a `-name`/`-path` predicate (or is a positional root),
# NEVER a token immediately after an `rm` verb (`-exec rm {}` binds the literal
# `{}`, not the file). Found live: `find sources -name registry.jsonl -delete`,
# `find . -name registry.jsonl -exec rm {} \;`, and `find sources/registry.jsonl
# -delete` each deleted a script-owned file with every gate on this module
# active, because no `find` verb was modeled at all.
_FIND_CMD = re.compile(_CMD_START + r"find\b", re.IGNORECASE)
_FIND_DELETE_ACTION = re.compile(
    r"-delete\b|-exec(?:dir)?\s+(?:\S*/)?(?:rm|unlink|shred|trash|trash-put)\b",
    re.IGNORECASE)
# `-name`/`-iname`/`-path`/`-ipath`/`-wholename`/`-regex` value: the filename or
# glob find matches on. A glob value (`-name '*.jsonl'`) is deliberately kept as
# the target — protect_data_files._protected_name fnmatches protected basenames
# against it exactly as the shell would expand it.
_FIND_NAME_PRED = re.compile(
    r"-i?(?:name|path|wholename|regex)\s+" + _TARGET, re.IGNORECASE)
# `... | xargs rm|unlink|shred` — xargs feeds paths from stdin into a deletion
# verb; the paths themselves are produced upstream in the same pipeline
# (`echo sources/registry.jsonl | xargs rm`, `ls sources/*.jsonl | xargs rm`).
# Since the targets can't be read from xargs's own arguments, this triggers a
# fail-closed sweep of every path-like literal in the whole command (see
# _xargs_delete_targets) — conservative by design, as the audit recommended for
# constructs whose real targets are not statically visible.
_XARGS_DELETE = re.compile(
    r"\bxargs\b[^|\n;&]*?\b(?:rm|unlink|shred|del|erase|trash|trash-put)\b", re.IGNORECASE)
# `gio trash FILE` / `trash-put FILE` / `trash FILE` — trash-to-recycle-bin
# utilities. Not a "delete" verb the _DELETE pattern models, but relocates a
# protected file out of its required path just like mv, so its file operands are
# targets. Found live: `gio trash sources/registry.jsonl` slipped every gate.
_GIO_TRASH = re.compile(
    _CMD_START + r"(?:gio\s+trash|trash-put|trash)\b\s*((?:(?!['\"]?\s*[;&|]).)+)",
    re.IGNORECASE)


def _is_pathlike(tok: str) -> bool:
    """A token that names a file/path: contains a slash, or has a filename
    extension (`name.ext`). Deliberately excludes bare words (`rm`, `echo`) and
    find-exec syntax tokens (`{}`, `+`) so the fail-closed xargs sweep stays
    quiet on commands that touch no actual path."""
    return "/" in tok or re.search(r"\w\.\w", tok) is not None


def _find_delete_targets(command: str, spans=None) -> list[str]:
    """Targets of a `find ... -delete`/`-exec rm` command: the `-name`/`-path`
    predicate values plus any positional root paths (the tokens between `find`
    and its first `-flag`). Only fires when a deletion action is present in the
    same find segment — a read-only `find sources -name '*.md'` is untouched.
    A `find` that sits inside a quoted argument is data, not an invocation —
    skipped via `spans` (see _quoted_spans)."""
    targets: list[str] = []
    for fm in _FIND_CMD.finditer(command):
        if _in_quotes(fm.start(), spans):
            continue
        boundary = _SEGMENT_BOUNDARY.search(command, fm.end())
        segment = command[fm.end():boundary.start() if boundary else len(command)]
        if not _FIND_DELETE_ACTION.search(segment):
            continue
        targets += [_target_group(nm) for nm in _FIND_NAME_PRED.finditer(segment)]
        roots = re.match(r"\s*((?:(?!\s-)\S+\s*)+)", segment)
        if roots:
            targets += list(_tokens(roots.group(1)))
    return targets


def _xargs_delete_targets(command: str, spans=None) -> list[str]:
    """Fail-closed: when the command pipes into `xargs rm`/`unlink`/`shred`/…,
    every path-like literal anywhere in the command is a candidate delete
    target, since the real targets arrive via stdin and aren't statically
    visible. No-op when no xargs-delete construct is present, or when the only
    `xargs …` match sits inside a quoted argument (data, not an invocation)."""
    m = _XARGS_DELETE.search(command)
    if not m or _in_quotes(m.start(), spans):
        return []
    return [t for t in _tokens(command) if _is_pathlike(t)]


_STR_LITERAL = r"""['"](?:[^'"\\]|\\.)*['"]"""
# NAME = 'lit1' + 'lit2' + ...   (pure string-literal concatenation only)
_ASSIGN_CONCAT = re.compile(
    r"\b([A-Za-z_]\w*)\s*=\s*(" + _STR_LITERAL + r"(?:\s*\+\s*" + _STR_LITERAL + r")*)")
# NAME = os.path.join('a', 'b', ...)   (literal segments only)
_ASSIGN_JOIN = re.compile(
    r"\b([A-Za-z_]\w*)\s*=\s*os\.path\.join\(\s*(" + _STR_LITERAL +
    r"(?:\s*,\s*" + _STR_LITERAL + r")*)\s*,?\s*\)")
_WRITE_CALL_HEAD = re.compile(r"\b(open|Path|shutil\.(?:copy2?|copyfile|move))\(\s*")


def _fold_simple_string_vars(command: str) -> str:
    """Best-effort constant-folding for the most common NON-adversarial way the
    quoted-literal regexes below get bypassed: a Python one-liner that builds a
    write-target path in a variable before handing it to open()/Path()/
    shutil.* — e.g. `p='sources/reg'+'istry.jsonl'; open(p,'a')` or
    `p=os.path.join('sources','registry.jsonl'); open(p,'a')`. Resolving these
    turns the substituted command back into the plain-literal shape the other
    regexes already understand. Only pure string-literal concatenation/join is
    folded — this is constant folding, not a Python interpreter, and does NOT
    close deliberately adversarial obfuscation (computed paths, base64,
    exec/eval, f-strings with variables, ...); see the module docstring."""
    values: dict[str, str] = {}
    for m in _ASSIGN_CONCAT.finditer(command):
        name, chain = m.group(1), m.group(2)
        values[name] = "".join(lit[1:-1] for lit in re.findall(_STR_LITERAL, chain))
    for m in _ASSIGN_JOIN.finditer(command):
        name, parts = m.group(1), m.group(2)
        values[name] = "/".join(lit[1:-1] for lit in re.findall(_STR_LITERAL, parts))
    if not values:
        return command
    names = "|".join(re.escape(n) for n in values)
    call_var = re.compile(_WRITE_CALL_HEAD.pattern + r"(" + names + r")\b")

    def repl(m):
        resolved = values[m.group(2)].replace("\\", "\\\\").replace("'", "\\'")
        return f"{m.group(1)}('{resolved}'"

    return call_var.sub(repl, command)


# NAME=value shell assignment (no spaces around `=`, as real shell syntax
# requires) — value is either a quoted literal or a bare unquoted token with
# no embedded separator.
_SHELL_ASSIGN = re.compile(
    _CMD_START + r"([A-Za-z_]\w*)=(" + _STR_LITERAL + r"|[^\s;&|]+)")
_SHELL_VAR_REF = re.compile(r"\$\{?([A-Za-z_]\w*)\}?")


def _fold_shell_vars(command: str) -> str:
    """Best-effort constant-folding for plain shell variable indirection in a
    redirect target — `F=drafts/intro.md; echo x > $F` is an ordinary shell
    idiom (assign once, reuse in a redirect), not adversarial obfuscation, and
    none of the write-sink regexes above resolve `$F`/`${F}` back to the
    literal path they name. Only a simple `NAME=literal` assignment (quoted or
    bare, no command substitution/parameter expansion) is folded — this is
    constant folding, not a shell interpreter, same scope limitation as
    `_fold_simple_string_vars` above."""
    values: dict[str, str] = {}
    for m in _SHELL_ASSIGN.finditer(command):
        name, raw = m.group(1), m.group(2)
        values[name] = raw[1:-1] if raw[:1] in ("'", '"') else raw
    if not values:
        return command
    return _SHELL_VAR_REF.sub(lambda m: values.get(m.group(1), m.group(0)), command)


_HEREDOC_START = re.compile(r"<<[-~]?\s*(['\"]?)([A-Za-z_]\w*)\1")


def strip_heredocs(command: str) -> str:
    """Remove heredoc BODIES (everything between `<<DELIM` and the closing DELIM
    line) before write-sink detection. A heredoc body is data, not commands — a
    note or draft authored via `cat <<'EOF' > file ... EOF` that merely MENTIONS
    a write-sink pattern (a redirect, a cmdlet name, a protected filename) on a
    body line must not be read as an actual invocation. Originally added only
    in phase_gate.py (found live: a false-positive DENY on writing unrelated
    prose that happened to mention a build command); protect_data_files.py and
    agent_write_scope.py shared the exact same gap (found live: a heredoc body
    merely documenting a write-sink pattern, e.g. an example in a comment, was
    denied by protect_data_files.py even though nothing was actually written to
    a protected file) since they call write_targets()/write_destinations()
    directly without this step — moved here so every caller gets it uniformly.
    The line that OPENS the heredoc is kept — it carries the redirect target,
    so a genuine `cat <<EOF > drafts/intro.md ... EOF` is still gated on that
    target.

    ONE EXCEPTION, and it is the whole reason this function needs a test suite:
    when the heredoc is stdin to an INTERPRETER (`python - <<'PY'`, `bash -s
    <<EOF`, `cat <<'PY' | python -`), the body is not data — it is the program.
    Stripping it removed every write it performs from view, so

        python - <<'PY'
        import pathlib
        pathlib.Path("drafts/methods.md").write_text(...)
        PY

    reported NO write targets at all and walked straight through the phase gate,
    while the identical `python -c "open('drafts/methods.md','w')..."` was
    correctly denied. This module's own docstring already promised that "python
    one-liners" are gated; the heredoc spelling of the same one-liner was not.
    Found live, in a session that had been writing gated files this way for an
    hour without a single deny.

    `python script.py <<EOF` keeps stripping: there the body really is data fed
    to a script, and the script is the thing that would be gated."""
    lines = command.splitlines()
    out, i = [], 0
    while i < len(lines):
        m = _HEREDOC_START.search(lines[i])
        out.append(lines[i])
        i += 1
        if m:
            delim = m.group(2)
            keep = _heredoc_body_is_code(lines[i - 1])
            while i < len(lines) and lines[i].strip() != delim:
                if keep:
                    out.append(lines[i])
                i += 1  # drop body line unless it is executable code
            if i < len(lines):
                i += 1  # drop the closing delimiter line itself
    return "\n".join(out)


# An interpreter reading its program from stdin: a bare `-`, `-s`, or no script
# argument at all before the `<<`. A script PATH argument (`python run.py <<EOF`)
# means the body is that script's input data, not a program, so it is excluded.
_STDIN_INTERPRETER = re.compile(
    r"(?:^|[|;&]|\s)(?:\S*/)?"
    r"(?:python\d?(?:\.\d+)*|py|ipython|bash|sh|zsh|ksh|dash|node|deno|perl|ruby|"
    r"pwsh|powershell)(?:\.exe)?"
    r"(?:\s+-[A-Za-z]*)*"          # flags: -s, -u, -E, -NoProfile-style singles
    r"(?:\s+-)?"                   # the explicit bare `-` (python - <<'PY')
    r"\s*(?:<<|\||$)",
    re.IGNORECASE)


def _heredoc_body_is_code(opening_line: str) -> bool:
    """Does this heredoc feed a program to an interpreter, or data to a command?

    Conservative in the direction that matters: a false 'yes' only means the
    body is SCANNED for write sinks (a stricter gate on text that is usually
    inert), while a false 'no' means an executed write is invisible. The second
    is the failure this exception exists to close, so ties go to 'yes'."""
    return bool(_STDIN_INTERPRETER.search(opening_line))


def _tokens(text: str):
    # shlex.split respects quoting, so a quoted argument containing a space
    # ("cp scratch/a.md 'drafts/my draft.md'") stays one token instead of
    # being split in two by a bare whitespace split — the latter silently
    # dropped the write target's second half, letting an ordinary spaced
    # filename slip past cp/mv/rm detection entirely.
    # shlex's posix=True mode treats a lone backslash as an escape character,
    # so an UNQUOTED Windows-style path (`mv sources\registry.jsonl old.bak`)
    # would otherwise have its backslashes silently consumed and adjacent
    # components merged into one token ("sourcesregistry.jsonl"), which then
    # fails the protected-filename basename match entirely — found live: this
    # is the DEFAULT path style on the kit's primary platform (win32/
    # PowerShell/cmd), not obfuscation. Fixed by converting a backslash to a
    # forward slash wherever it's followed by a non-space character, BEFORE
    # shlex sees it: this recovers the correct token boundary for a Windows
    # separator while leaving a genuinely escaped space (`a\ b.txt`, a
    # legitimate POSIX idiom this same function supports) untouched, since
    # backslash-space never matches the lookahead.
    text = _BACKSLASH_SEP.sub("/", text)
    # Falls back to the naive split on unbalanced-quote input (e.g. an apostrophe in prose)
    # rather than raising, since this is best-effort detection, not a parser.
    try:
        toks = shlex.split(text, posix=True)
    except ValueError:
        toks = [t.strip("'\"") for t in text.split()]
    for tok in toks:
        # shlex doesn't treat a backtick as a quote character (POSIX command
        # substitution isn't shell QUOTING), so an unresolved `` `cmd` ``
        # wrapped around a target leaves a literal leading/trailing backtick
        # attached to the adjacent token — e.g. `` rm `echo path` `` yields a
        # token ending in "path`", whose basename no longer exactly equals the
        # real protected filename. Stripping backticks from the token edges
        # (same spirit as the quote-strip on the fallback branch above) closes
        # that specific mismatch without attempting to actually evaluate the
        # substitution, which stays out of scope (this module is best-effort
        # pattern matching, not a shell).
        tok = tok.strip("`")
        if tok and not tok.startswith("-"):
            yield tok


def _last_token(text: str) -> str | None:
    toks = list(_tokens(text))
    return toks[-1] if toks else None


# A nested-shell/interpreter wrapper's inner command string: the quoted argument
# after `-c`/`-Command` of bash/sh/zsh/dash/ksh/pwsh/powershell/python, plus the
# quoted argument of os.system/os.popen/subprocess.* (a Python one-liner shelling
# out). _unwrap() extracts these so _collect_targets can re-scan them FROM THE
# TOP — where the inner command is legitimately at position 0 and the narrow
# _CMD_START anchor matches it — instead of widening the anchor to accept a
# command after any quote (which over-matched ordinary prose, see _CMD_START).
_WRAPPER_INNER = re.compile(
    r"\b(?:bash|sh|zsh|dash|ksh|pwsh|powershell|cmd(?:\.exe)?|python3?(?:\.\d+)*)(?:\.exe)?\b"
    r"[^\n]*?\s-(?:c|Command)\b\s+(?:'([^']*)'|\"([^\"]*)\")"
    # cmd.exe spells its inline-command flag "/c", not "-c"/"-Command".
    r"|\bcmd(?:\.exe)?\b[^\n]*?\s/c\s+(?:'([^']*)'|\"([^\"]*)\")",
    re.IGNORECASE)
_SHELLOUT_INNER = re.compile(
    r"(?:os\.system|os\.popen|"
    r"subprocess\.(?:run|call|Popen|check_output|check_call|getoutput))"
    r"\(\s*(?:'([^']*)'|\"([^\"]*)\")",
    re.IGNORECASE)
# PowerShell's `&` call operator invoking a script block: `& {Remove-Item ...}`.
# Best-effort (no nested-brace tracking — the first `}` closes the block, same
# "not a parser" scope every other pattern here already accepts).
_CALL_OPERATOR_INNER = re.compile(r"&\s*\{([^}]*)\}")
# Invoke-Expression / iex — PowerShell's most common string-to-code idiom, both
# the direct form (iex 'cmd') and the pipeline form ('cmd' | iex).
_IEX_INNER = re.compile(
    r"(?:Invoke-Expression|iex)\b\s+(?:'([^']*)'|\"([^\"]*)\")"
    r"|(?:'([^']*)'|\"([^\"]*)\")\s*\|\s*(?:Invoke-Expression|iex)\b",
    re.IGNORECASE)


def _unwrap(command: str) -> list[str]:
    inners: list[str] = []
    for pat in (_WRAPPER_INNER, _SHELLOUT_INNER, _CALL_OPERATOR_INNER, _IEX_INNER):
        for m in pat.finditer(command):
            g = next((g for g in m.groups() if g is not None), None)
            if g is not None:
                inners.append(g)
    return inners


def _collect_targets(command: str, *, full_args_for_move: bool, _depth: int = 0) -> list[str]:
    if _depth == 0:
        command = strip_heredocs(command)
    command = _fold_shell_vars(command)
    command = _fold_simple_string_vars(command)
    # Quoted-region map of the FINAL (post-fold) command string every pattern
    # below runs over. A sink whose command/operator anchor lands inside a
    # quoted argument is data, not an executed sink, and is filtered out here
    # (see _quoted_spans). Real quoted TARGETS after a genuine operator are
    # unaffected — their operator anchor sits outside the quotes. spans is None
    # on unbalanced quotes, and _unq/_in_quotes then filter nothing (fail-closed).
    spans = _quoted_spans(command)

    def _unq(matches):
        return [m for m in matches if not _in_quotes(m.start(), spans)]

    targets: list[str] = []
    for pattern in (_WRITE_SINK, _PYOPEN_WRITE, _PY_SHUTIL_WRITE, _PY_PATHLIB_WRITE,
                    _PY_PATHLIB_RENAME, _PY_OS_REMOVE, _PY_SHUTIL_RMTREE, _PY_OS_OPEN,
                    _DOTNET_WRITE, _DOTNET_CTOR, _PY_FILEINPUT, _DD_OF):
        targets += [_target_group(m) for m in _unq(pattern.finditer(command))]
    targets += _ps_cmdlet_targets(command, spans)
    for m in _unq(_PY_OS_RENAME.finditer(command)):
        targets += [m.group(1), m.group(2)] if full_args_for_move else [m.group(2)]
    for m in _unq(_COPY_MOVE.finditer(command)):
        toks = list(_tokens(m.group(1)))
        targets += toks if full_args_for_move else toks[-1:]
    for m in _unq(_INSTALL.finditer(command)):
        toks = list(_tokens(m.group(1)))
        targets += toks if full_args_for_move else toks[-1:]
    for m in _unq(_DELETE.finditer(command)):
        targets += list(_tokens(m.group(1)))
    for m in _unq(_GIO_TRASH.finditer(command)):
        targets += list(_tokens(m.group(1)))
    targets += _find_delete_targets(command, spans)
    targets += _xargs_delete_targets(command, spans)
    m = _INPLACE_EDIT.search(command)
    if m and not _in_quotes(m.start(), spans):
        last = _last_token(m.group(0))
        if last:
            targets.append(last)
    # Recurse one level into nested-shell/interpreter wrappers (bounded depth so
    # a pathological input can't spin) — see _unwrap.
    if _depth < 2:
        for inner in _unwrap(command):
            targets += _collect_targets(inner, full_args_for_move=full_args_for_move,
                                        _depth=_depth + 1)
    return targets


def write_targets(command: str) -> list[str]:
    """Every path-like write/move/delete target this Bash command touches,
    across all recognized write-sink syntaxes. Order/duplicates aren't
    significant — callers only test membership/containment against their
    own filename or directory-component predicate. cp/mv/os.rename/os.replace
    report EVERY argument (source AND destination) — relocating a protected
    file AWAY from its required path is data loss even though nothing new is
    "written" to it; see write_destinations() for the opposite need."""
    return _collect_targets(command, full_args_for_move=True)


def write_destinations(command: str) -> list[str]:
    """Same as write_targets(), except cp/mv/Copy-Item/Move-Item/Rename-Item/
    os.rename/os.replace report ONLY their destination (the last positional
    argument for cp/mv-family; the second argument for os.rename/os.replace),
    never the read-only source. write_targets()'s "every argument" behavior is
    correct for a DENYLIST check (protect_data_files.py: did this command
    relocate a protected file away from its required path?) but wrong for an
    ALLOWLIST check (a per-agent write-scope gate: is every new-content
    destination inside this agent's declared scope?) — there, an ordinary
    `cp templates/x.tex build/x.tex` has a legitimate read-only source outside
    the agent's writable prefixes, and treating that source as a target would
    be a false-positive deny on a normal, in-scope copy."""
    return _collect_targets(command, full_args_for_move=False)
