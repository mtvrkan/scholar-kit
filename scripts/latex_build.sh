#!/usr/bin/env bash
# latex_build.sh — latexmk wrapper that returns ONLY digested errors (token economy:
# compile logs are a black hole; the last meaningful lines are all the model needs).
# Usage: bash scripts/latex_build.sh <main.tex> [outdir]   (default outdir: build/)
set -u
MAIN="${1:?usage: latex_build.sh <main.tex> [outdir]}"
OUTDIR="${2:-build}"

# Reject a '..' PATH COMPONENT in either argument — NOT a rejection of
# absolute paths (OUTDIR legitimately needs those; see the Windows
# drive-letter handling below and its regression tests), and not a bare
# substring match either (an early version used `*..*`, which would also
# reject an ordinary filename that merely contains two consecutive dots,
# e.g. "v1..2.tex" — matched here only when ".." sits between slashes, at
# the very start, or is the whole argument). format-engineer runs this
# script via Bash, already gated by phase_gate.py (verify=PASS + Major=0)
# and by _shell_write_sink.py detecting the invocation itself — this is a
# narrower, second-layer check against the residual case of a malicious/
# wrong path value slipping through post-gate.
case "$MAIN" in
  ..|../*|*/..|*/../*) echo "BLOCKED: main.tex path must not contain '..': $MAIN"; exit 2 ;;
esac
case "$OUTDIR" in
  ..|../*|*/..|*/../*) echo "BLOCKED: outdir path must not contain '..': $OUTDIR"; exit 2 ;;
esac

# latexmk/pdflatex resolve \input, \includegraphics, \addbibresource etc. relative
# to the CURRENT WORKING DIRECTORY, not to main.tex's own directory — so if MAIN
# is a nested path (e.g. "templates/thesis-tr/main.tex" run from the repo/project
# root), those relative paths break even though MAIN itself is found. Compile from
# main.tex's own directory instead, resolving OUTDIR against the *caller's*
# original CWD first so "build" still lands where the caller expects it.
# Recognize both POSIX absolute paths (/...) and Windows drive-letter
# absolute paths (C:\... or C:/...) — a caller on Windows passing a native
# absolute path (e.g. from Python's Path(tmp_path) / "build") previously
# fell through to the relative branch (Windows paths don't start with "/"),
# silently mangling OUTDIR into "$(pwd)/C:\Users\...\build" and breaking the
# build with a confusing latexmk failure instead of the intended path.
# NOTE: the bracket-expression form [A-Za-z]:[/\\]* looks correct but does
# NOT reliably match a literal backslash in this shell's case-pattern
# matching (verified empirically) — an unquoted backslash used as a pattern
# operator here doesn't collapse to a literal the way a plain glob would
# suggest. A single-quoted literal backslash concatenated into the pattern
# is what actually works, so the backslash case is split into its own
# clause below instead of sharing a bracket expression with the slash case.
case "$OUTDIR" in
  /*) : ;;
  [A-Za-z]:/*) : ;;
  [A-Za-z]:'\'*) : ;;
  *) OUTDIR="$(pwd)/$OUTDIR" ;;
esac
# Captured BEFORE the cd below: template-profile.md is addressed from the
# project root, which is where the caller stands, not from main.tex's directory.
ORIG_CWD="$(pwd)"
MAIN_ABS="$MAIN"
case "$MAIN_ABS" in /*|[A-Za-z]:/*|[A-Za-z]:'\'*) : ;; *) MAIN_ABS="$ORIG_CWD/$MAIN_ABS" ;; esac
MAIN_DIR="$(cd "$(dirname "$MAIN")" && pwd)" || { echo "BLOCKED: no such directory for $MAIN"; exit 2; }
MAIN="$(basename "$MAIN")"
cd "$MAIN_DIR" || { echo "BLOCKED: cannot cd into $MAIN_DIR"; exit 2; }

# Engine: pdflatex unless the document needs a Unicode engine. `-pdf` is
# pdflatex, which cannot load fontspec and cannot typeset a bare Unicode
# character — a document that sets `mainfont:` in its pandoc front matter (any
# non-Latin-1 manuscript typically must, to get its own script) compiles to
# "LaTeX Error: Unicode character X" and NO pdf at all. That is not a document
# error; it is the wrong engine. Detected from the .tex itself rather than
# configured, so a project does not have to know which engine its own font
# choice implies. LATEX_ENGINE overrides (values: pdf, xelatex, lualatex).
#
# Validated HERE, before the latexmk-availability probe: a bad engine value is
# the caller's error and should be reported as itself, not masked by whichever
# unrelated check happens to run first.
ENGINE="${LATEX_ENGINE:-}"
if [ -z "$ENGINE" ]; then
  if grep -qE '\\(usepackage(\[[^]]*\])?\{fontspec\}|setmainfont|setsansfont|setmonofont)' "$MAIN" 2>/dev/null; then
    ENGINE="xelatex"
  else
    ENGINE="pdf"
  fi
fi
case "$ENGINE" in
  pdf|xelatex|lualatex) ;;
  *) echo "BLOCKED: LATEX_ENGINE must be pdf, xelatex or lualatex: $ENGINE"; exit 2 ;;
esac

if ! command -v latexmk >/dev/null 2>&1; then
  # winget MiKTeX doesn't touch the CURRENT shell's PATH — probe its default location.
  # LOCALAPPDATA is Windows-only; ${LOCALAPPDATA:-} avoids an unbound-variable abort
  # under `set -u` on macOS/Linux, where it's never set.
  for cand in "${LOCALAPPDATA:-}/Programs/MiKTeX/miktex/bin/x64" "/c/Program Files/MiKTeX/miktex/bin/x64"; do
    [ -x "$cand/latexmk.exe" ] && { export PATH="$PATH:$cand"; break; }
  done
fi
if ! command -v latexmk >/dev/null 2>&1; then
  echo "BLOCKED: latexmk not installed. PDF build skipped; docx/xlsx pipelines still work."
  echo "  Windows: winget install --id MiKTeX.MiKTeX  (then open a NEW terminal)"
  echo "  macOS:   brew install --cask mactex-no-gui  ·  Linux: apt install texlive-full latexmk"
  exit 3
fi

mkdir -p "$OUTDIR"
LOG="$OUTDIR/latexmk-run.log"

latexmk "-$ENGINE" -interaction=nonstopmode -halt-on-error -file-line-error \
  -outdir="$OUTDIR" "$MAIN" >"$LOG" 2>&1
CODE=$?

if [ $CODE -eq 0 ]; then
  BASE="$(basename "${MAIN%.tex}")"
  PDF="$OUTDIR/$BASE.pdf"
  # count warnings from the FINAL pass log only — latexmk-run.log accumulates
  # earlier passes where citations are always undefined before biber runs
  FINAL_LOG="$OUTDIR/$BASE.log"
  [ -f "$FINAL_LOG" ] || FINAL_LOG="$LOG"
  WARNS=$(grep -Ec "LaTeX Warning|Overfull|Underfull" "$FINAL_LOG" || true)
  UNDEF=$(grep -c "Citation .* undefined" "$FINAL_LOG" || true)
  EMPTYBIB=$(grep -c "Empty bibliography" "$FINAL_LOG" || true)
  echo "OK: $PDF"
  echo "warnings: $WARNS (overfull/underfull/latex) · undefined citations: $UNDEF"
  [ "$UNDEF" -gt 0 ] && grep -m 5 "Citation .* undefined" "$FINAL_LOG"
  # "OK" alone previously buried this in the generic warning count — a build
  # with no bib/references.bib (biber vetoed, "Empty bibliography") still
  # exits 0 and looks clean unless someone reads the full log, which the
  # whole point of this script is to avoid making them do.
  [ "$EMPTYBIB" -gt 0 ] && echo "WARN: bibliography is EMPTY — bib/references.bib missing or has no resolvable entries. The PDF compiled but ships with no reference list."
  # TEMPLATE SUPREMACY (Invariant 8): the PreToolUse gate only checks that the
  # ingested class is referenced AT ALL. This compares the source against the
  # rules extracted from the template. Best-effort and never fatal: template
  # drift is a quality signal needing a human decision, not a build error —
  # the same call already made for docx_style_check.py (D-071c).
  if [ -f "$ORIG_CWD/templates/ingested/template-profile.md" ]; then
    PYBIN=""
    for cand in python python3 py; do
      command -v "$cand" >/dev/null 2>&1 && { PYBIN="$cand"; break; }
    done
    if [ -n "$PYBIN" ]; then
      TC_OUT="$(cd "$ORIG_CWD" && "$PYBIN" "$(dirname "$0")/template_compliance.py" --built "$MAIN_ABS" 2>&1)"
      TC_CODE=$?
      if [ "$TC_CODE" -eq 2 ]; then
        echo "WARN: the source does not honor every rule in template-profile.md:"
        echo "$TC_OUT" | grep -B1 -A2 '"mismatch"' | head -20
        echo "  (full report: $PYBIN scripts/template_compliance.py --built \"$MAIN\")"
      elif printf '%s' "$TC_OUT" | grep -q '"unbound"'; then
        echo "WARN: template-profile.md carries no machine-readable template-rules block — its rules cannot be checked against this build. Re-run /ingest-template."
      fi
    fi
  fi
  exit 0
fi

echo "BUILD FAILED (latexmk exit $CODE) — digested errors:"
# file-line-error format lines + classic ! errors, last 10 meaningful ones
grep -E "^(.+:[0-9]+:|!)" "$LOG" | tail -10
# biber/bibtex hints
grep -m 2 -E "(Biber|biber|bibtex).*(error|not found)" "$LOG" || true
echo "(full log: $LOG — do NOT read it into context; grep it)"
exit 1
