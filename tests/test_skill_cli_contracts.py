"""Regression guard for a bug class that recurred across four remediation
passes (D-043 · D-045/D-046 class · D-052 · D-059): skill docs
(.claude/skills/*/SKILL.md) and agent docs (.claude/agents/*.md) hand-write
example invocations of `python scripts/X.py --flag ...` that drift out of
sync with X.py's real argparse definition — a flag gets renamed/removed in
the script, or was never real to begin with, and the doc keeps citing it
until a real run fails on "unrecognized arguments." Nothing mechanically
checked doc examples against source before this test existed.

Deliberately permissive on WHICH flags count as valid: a flag is considered
"valid" for a script if it is defined ANYWHERE in that script (top-level
parser OR any subcommand's subparser), not scoped to the exact subcommand
used in the doc example. That misses subcommand-positional bugs, but it
reliably catches the dominant recurring pattern in this kit's history: a
flag that does not exist ANYWHERE in the script (`--lang`, `--cache-only`,
`--strict` on bib_doctor.py, `--year-min`, `--section`, `--all` on
evidence_db.py query, `--title` vs `--title-search` on doi2bib.py, etc.).

NOT permissive on WHERE it looks: a doc example can appear in two shapes,
and a first version of this test only handled one of them correctly —
- fenced code blocks (```bash ... ```): each line is its own command;
  a line ending in a backslash continues onto the next line.
- inline code spans (`...`): Markdown line-wraps long inline commands across
  source lines with no continuation marker — the whole backtick-delimited
  span (newlines and all) is ONE logical command. A first version of this
  test stopped matching at the first newline, so multi-line inline spans
  (e.g. `python scripts/registry_db.py log-query --db <db>\n --query "..."
  --hits N`, wrapped by Markdown inside a single pair of backticks) only had
  their first line checked — `--query`/`--hits` slipped through unchecked.
  Both shapes are now parsed by their own real boundary (line vs backtick),
  not a shared regex that only understood one of them.
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = ROOT / "scripts"
DOC_DIRS = [ROOT / ".claude" / "skills", ROOT / ".claude" / "agents"]

FLAG_DEF_RE = re.compile(r'add_argument\(\s*"(--[\w-]+)"')
FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
INLINE_SPAN_RE = re.compile(r"`([^`]+)`")
SCRIPT_RE = re.compile(r"python\s+scripts/([\w.-]+\.py)")
FLAG_USE_RE = re.compile(r"(--[a-zA-Z][\w-]*)")

# Shell-script sibling of SCRIPT_RE — the bug class this test guards against
# (documented invocation drifts from what the script actually requires) is not
# unique to `python scripts/*.py`; `bash scripts/*.sh` wrappers have required
# positional args too, and a doc example that omits them fails immediately
# (`latex_build.sh`'s `${1:?usage: ...}` / `docx_build.sh`'s `${1:?...}` etc.
# abort with "usage:" rather than running). Minimums below come from each
# script's own `set -u` positional-parameter-expansion guards, not argparse.
SH_SCRIPT_RE = re.compile(r"bash\s+scripts/([\w.-]+\.sh)")
MIN_POSITIONAL_ARGS = {
    "latex_build.sh": 1,   # <main.tex> required; [outdir] optional
    "docx_build.sh": 4,    # <out.docx> <csl> <refdoc|-> <section1.md> [more...]
}


def _script_flags(py_file: Path) -> set:
    text = py_file.read_text(encoding="utf-8")
    return set(FLAG_DEF_RE.findall(text))


def _script_flag_index() -> dict:
    return {p.name: _script_flags(p) for p in SCRIPTS_DIR.glob("*.py")}


def _fenced_block_commands(text: str):
    """Each fenced code block's lines are independent commands; a trailing
    `\\` continues a command onto the next line (real bash/PowerShell
    continuation syntax used throughout this kit's docs)."""
    for fence in FENCE_RE.finditer(text):
        buf = ""
        for line in fence.group(1).split("\n"):
            stripped = line.rstrip()
            if stripped.endswith("\\"):
                buf += stripped[:-1] + " "
                continue
            buf += stripped
            if buf.strip():
                yield buf
            buf = ""
        if buf.strip():
            yield buf


def _inline_span_commands(text: str):
    """Inline `code spans` may contain a bare newline where Markdown
    line-wrapped a long command — that newline is NOT a command boundary,
    unlike in a fenced block. Strip fenced blocks first so their content
    (which may itself contain backticks/triple-backticks) isn't re-parsed
    here as if it were prose."""
    text_wo_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    for m in INLINE_SPAN_RE.finditer(text_wo_fences):
        yield m.group(1).replace("\n", " ")


def _doc_invocations():
    """Yield (doc_path, script_name, flags_used) for every documented
    `python scripts/X.py ...` call across skills + agents."""
    for d in DOC_DIRS:
        for md in sorted(d.rglob("*.md")):
            text = md.read_text(encoding="utf-8")
            commands = list(_fenced_block_commands(text)) + list(_inline_span_commands(text))
            for cmd in commands:
                m = SCRIPT_RE.search(cmd)
                if not m:
                    continue
                script = m.group(1)
                rest = cmd[m.end():].split("#", 1)[0]  # strip inline comments
                flags = set(FLAG_USE_RE.findall(rest))
                yield md.relative_to(ROOT), script, flags


# The permissive union-based check above cannot see subcommand scoping (its own
# docstring says so). In practice that blind spot let ONE specific pattern
# recur at least 5 times across this kit's history: `--json` is defined on
# evidence_db.py/registry_db.py's TOP-LEVEL parser only (must precede the
# subcommand name) and NOT on their `stats`/`query`/`get`/`conflicts`/`list`/
# `set-status`/`set-field`/`log-query` subparsers, or on qa_inspect.py's
# `pdf-pages`/`xlsx-sheets` subparsers — a doc example that writes
# `evidence_db.py query --json` (flag AFTER the subcommand) fails with
# "unrecognized arguments" even though `--json` is a real flag of the script.
# Narrow, string-based check for exactly this recurring shape (not a general
# subcommand-scoping parser — that would need real argparse/AST introspection
# for marginal extra coverage; this targets the pattern that has actually
# recurred).
NO_OWN_JSON_SUBCOMMANDS = {
    "evidence_db.py": {"query", "get", "set-field", "stats", "conflicts"},
    "registry_db.py": {"set-status", "set-field", "list", "stats", "log-query"},
    "qa_inspect.py": {"pdf-pages", "xlsx-sheets"},
}


def test_json_flag_not_placed_after_subcommands_that_lack_their_own():
    failures = []
    for doc_path, script, flags in _doc_invocations():
        if script not in NO_OWN_JSON_SUBCOMMANDS or "--json" not in flags:
            continue
        # Re-derive the raw command text to check token order (flags is an
        # unordered set; we need to know whether --json came after the
        # subcommand name, so re-scan the source invocation for this doc).
        text = (ROOT / doc_path).read_text(encoding="utf-8")
        for cmd in list(_fenced_block_commands(text)) + list(_inline_span_commands(text)):
            m = SCRIPT_RE.search(cmd)
            if not m or m.group(1) != script:
                continue
            rest = cmd[m.end():].split("#", 1)[0]
            tokens = rest.split()
            if "--json" not in tokens:
                continue
            json_idx = tokens.index("--json")
            for subcmd in NO_OWN_JSON_SUBCOMMANDS[script]:
                if subcmd in tokens and tokens.index(subcmd) < json_idx:
                    failures.append(
                        f"{doc_path}: `{script} {subcmd} ... --json` — --json is "
                        f"top-level-only on {script} and must precede the "
                        f"subcommand, e.g. `{script} --json {subcmd} ...`")
    assert not failures, "\n".join(failures)


def test_documented_script_invocations_use_real_flags():
    flag_index = _script_flag_index()
    failures = []
    checked = 0
    for doc_path, script, flags in _doc_invocations():
        if script not in flag_index:
            continue  # not a scholar-kit script (e.g. a shell script name mentioned in prose)
        checked += 1
        flags -= {"--help"}  # argparse auto-adds this to every parser
        unknown = sorted(f for f in flags if f not in flag_index[script])
        if unknown:
            failures.append(
                f"{doc_path}: `{script}` documented with unknown flag(s) {unknown} "
                f"— real flags: {sorted(flag_index[script])}")
    assert checked >= 30, f"only found {checked} documented invocations — regex likely broken"
    assert not failures, "\n".join(failures)


def _sh_doc_invocations():
    """Yield (doc_path, script_name, positional_tokens) for every documented
    `bash scripts/X.sh ...` call across skills + agents."""
    for d in DOC_DIRS:
        for md in sorted(d.rglob("*.md")):
            text = md.read_text(encoding="utf-8")
            commands = list(_fenced_block_commands(text)) + list(_inline_span_commands(text))
            for cmd in commands:
                m = SH_SCRIPT_RE.search(cmd)
                if not m:
                    continue
                script = m.group(1)
                rest = cmd[m.end():].split("#", 1)[0]
                tokens = [t for t in rest.split() if t]
                yield md.relative_to(ROOT), script, tokens


def test_documented_shell_script_invocations_pass_required_positional_args():
    failures = []
    checked = 0
    for doc_path, script, tokens in _sh_doc_invocations():
        min_args = MIN_POSITIONAL_ARGS.get(script)
        if min_args is None:
            continue
        checked += 1
        if len(tokens) < min_args:
            failures.append(
                f"{doc_path}: `bash scripts/{script}` documented with only "
                f"{len(tokens)} positional arg(s) {tokens} — needs >= {min_args}")
    assert checked >= 5, f"only found {checked} documented bash-script invocations — regex likely broken"
    assert not failures, "\n".join(failures)


def test_fenced_and_inline_parsers_both_see_multiline_examples():
    """Regression lock for the fixed blind spot: an inline span line-wrapped
    by Markdown must have its SECOND line's flags checked too."""
    sample = (
        "log EVERY executed query: `python scripts/registry_db.py log-query --db x\n"
        '    --query "..." --hits 3`,\n'
    )
    # _doc_invocations reads from disk by design; exercise the two parsers directly instead.
    commands = list(_fenced_block_commands(sample)) + list(_inline_span_commands(sample))
    combined = " ".join(commands)
    for flag in ("--db", "--query", "--hits"):
        assert flag in combined, f"{flag} from the second line of a wrapped inline span was not captured"
