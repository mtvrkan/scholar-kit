#!/usr/bin/env bash
# docx_build.sh — Pandoc pipeline: markdown sections + CSL + reference.docx → Word.
# Template supremacy: pass the ingested reference doc when template-profile.md exists.
# Usage: bash scripts/docx_build.sh <out.docx> <csl-file> <reference.docx|-> <section1.md> [section2.md ...]
#   Use "-" for reference.docx to build with pandoc defaults (draft preview only).
set -u
OUT="${1:?usage: docx_build.sh <out.docx> <csl> <refdoc|-> <sections...>}"
CSL="${2:?csl file required (templates/csl/*.csl)}"
REFDOC="${3:?reference docx required, or - for pandoc defaults}"
shift 3
[ $# -ge 1 ] || { echo "ERROR: no section files given"; exit 1; }

# Reject a '..' PATH COMPONENT in any argument — NOT a rejection of absolute
# paths (OUT/section files are routinely absolute in real invocations and in
# this script's own tests), and not a bare substring match either (an early
# version used `*..*`, which would also reject an ordinary filename that
# merely contains two consecutive dots, e.g. "v1..2.md" — matched here only
# when ".." sits between slashes, at the very start, or is the whole
# argument). format-engineer runs this script via Bash, already gated by
# phase_gate.py (verify=PASS + Major=0) and by _shell_write_sink.py detecting
# the invocation itself — this is a narrower, second-layer check against the
# residual case of a malicious/wrong path value slipping through post-gate.
for _p in "$OUT" "$CSL" "$@"; do
  case "$_p" in
    ..|../*|*/..|*/../*) echo "BLOCKED: path must not contain '..': $_p"; exit 2 ;;
  esac
done
if [ "$REFDOC" != "-" ]; then
  case "$REFDOC" in
    ..|../*|*/..|*/../*) echo "BLOCKED: path must not contain '..': $REFDOC"; exit 2 ;;
  esac
fi

if ! command -v pandoc >/dev/null 2>&1; then
  # winget installs pandoc without touching the CURRENT shell's PATH — probe it.
  # LOCALAPPDATA is Windows-only; ${LOCALAPPDATA:-} avoids an unbound-variable
  # abort under `set -u` on macOS/Linux (and CI), where it's never set — the
  # same bug latex_build.sh had (D-068a) before it was fixed there.
  for cand in "${LOCALAPPDATA:-}/Microsoft/WinGet/Packages"/JohnMacFarlane.Pandoc*/pandoc-*/; do
    [ -x "${cand}pandoc.exe" ] && { export PATH="$PATH:${cand%/}"; break; }
  done
fi
if ! command -v pandoc >/dev/null 2>&1; then
  echo "BLOCKED: pandoc not installed. Install from https://pandoc.org/installing.html"
  echo "  Windows: winget install --id JohnMacFarlane.Pandoc  (then open a NEW terminal)"
  echo "  macOS:   brew install pandoc   ·   Linux: apt/dnf install pandoc"
  exit 3
fi
[ -f "$CSL" ] || { echo "ERROR: CSL file not found: $CSL (templates/csl/)"; exit 1; }

ARGS=(--citeproc --csl "$CSL" --bibliography bib/references.bib
      --from markdown+smart --to docx --output "$OUT"
      --metadata link-citations=true)
if [ "$REFDOC" != "-" ]; then
  [ -f "$REFDOC" ] || { echo "ERROR: reference doc not found: $REFDOC"; exit 1; }
  ARGS+=(--reference-doc "$REFDOC")
fi

LOG="$(dirname "$OUT")/pandoc-run.log"
mkdir -p "$(dirname "$OUT")"
# `--` before the section files: a section filename starting with '-' (e.g.
# a stray "-something.md") would otherwise be parsed as a pandoc OPTION
# instead of an input file (verified: `pandoc --to=plain -weird.md` fails
# with "Unknown output format 'eird.md'"; `pandoc --to=plain -- -weird.md`
# correctly treats it as a filename).
pandoc "${ARGS[@]}" -- "$@" >"$LOG" 2>&1
CODE=$?

if [ $CODE -eq 0 ]; then
  MISSING=$(grep -c "citeproc.*not found\|reference .* not found" "$LOG" || true)
  echo "OK: $OUT"
  [ "$MISSING" -gt 0 ] && { echo "citeproc warnings:"; grep -m 5 "not found" "$LOG"; }
  # Style-compliance drift previously only surfaced if someone remembered to
  # run docx_style_check.py as a separate manual step (docx-output/SKILL.md
  # §9) — nothing detected it automatically, so a make_reference_docx.py
  # style-default change could silently stop being honored. Run it here,
  # best-effort: never fail the build over this (a missing python/style
  # mismatch is a quality signal, not a build error), just surface it loudly.
  if [ "$REFDOC" != "-" ]; then
    PYBIN=""
    for cand in python python3 py; do
      command -v "$cand" >/dev/null 2>&1 && { PYBIN="$cand"; break; }
    done
    if [ -n "$PYBIN" ]; then
      STYLE_OUT="$("$PYBIN" "$(dirname "$0")/docx_style_check.py" --built "$OUT" --reference "$REFDOC" 2>&1)"
      STYLE_CODE=$?
      if [ "$STYLE_CODE" -eq 2 ]; then
        echo "WARN: $OUT does not fully honor $REFDOC's styles — details:"
        echo "$STYLE_OUT" | grep -A2 '"mismatches"' | head -10
        echo "  (full report: $PYBIN scripts/docx_style_check.py --built \"$OUT\" --reference \"$REFDOC\")"
      fi
    fi
  fi
  # docx_style_check above asks "does the build match the reference doc it was
  # rendered with"; this asks the question Invariant 8 actually makes — "does
  # it match the rules extracted FROM THE TEMPLATE" — which the reference doc
  # can itself get wrong. Runs regardless of REFDOC (a "-" draft preview is
  # exactly where template drift is likeliest), best-effort, never fatal.
  if [ -f "templates/ingested/template-profile.md" ]; then
    PYBIN2=""
    for cand in python python3 py; do
      command -v "$cand" >/dev/null 2>&1 && { PYBIN2="$cand"; break; }
    done
    if [ -n "$PYBIN2" ]; then
      TC_OUT="$("$PYBIN2" "$(dirname "$0")/template_compliance.py" --built "$OUT" 2>&1)"
      TC_CODE=$?
      if [ "$TC_CODE" -eq 2 ]; then
        echo "WARN: $OUT does not honor every rule in template-profile.md:"
        echo "$TC_OUT" | grep -B1 -A2 '"mismatch"' | head -20
        echo "  (full report: $PYBIN2 scripts/template_compliance.py --built \"$OUT\")"
      elif printf '%s' "$TC_OUT" | grep -q '"unbound"'; then
        echo "WARN: template-profile.md carries no machine-readable template-rules block — its rules cannot be checked against this build. Re-run /ingest-template."
      fi
    fi
  fi
  exit 0
fi
echo "BUILD FAILED (pandoc exit $CODE) — digested errors:"
tail -10 "$LOG"
exit 1
