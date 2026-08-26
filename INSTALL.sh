#!/usr/bin/env bash
# INSTALL.sh — scholar-kit setup: dependency check, optional MCP servers, index datasets.
# Usage:
#   bash INSTALL.sh                # dependency check + interactive data/MCP setup
#   bash INSTALL.sh --check       # dependency check only
#   bash INSTALL.sh --update-data # refresh data/ index datasets (SCImago, DOAJ)
#   bash INSTALL.sh --mcp         # MCP setup only
set -u
cd "$(dirname "$0")"
MODE="${1:-full}"

PY=python3; command -v python3 >/dev/null 2>&1 || PY=python
command -v "$PY" >/dev/null 2>&1 || PY=py


patch_hooks() {
  # .claude/settings.json hook commands must invoke the detected interpreter
  # ($PY). Always inspect and fix regardless of what $PY resolved to —
  # commands may have drifted to either "python " or "python3 " (this exact
  # drift has recurred three times in kit history: D-017, D-027, D-041; a
  # check that only special-cased "$PY != python" silently skipped
  # verification whenever $PY WAS "python", even if the file itself still
  # said "python3"). The actual patch logic lives in
  # scripts/patch_hook_interpreter.py — a plain Python script, unlike this
  # bash function, so it has real pytest regression coverage.
  [ -f .claude/settings.json ] || return 0
  local result
  result=$($PY scripts/patch_hook_interpreter.py --target "$PY" --json)
  case "$result" in
    *'"changed": true'*) echo "  [ok] hooks now use: $PY" ;;
    *) echo "  [ok] hooks already use: $PY" ;;
  esac
}

check_deps() {
  echo "== Dependency check =="
  local missing=0
  if command -v $PY >/dev/null 2>&1; then
    echo "  [ok] python: $($PY --version 2>&1)"
  else
    echo "  [MISSING] python 3.10+ — https://www.python.org/downloads/"; missing=1
  fi
  for mod in requests openpyxl rapidfuzz docx pymupdf4llm; do
    if $PY -c "import $mod" >/dev/null 2>&1; then echo "  [ok] python module: $mod"
    else echo "  [MISSING] python module: $mod  ->  $PY -m pip install $(echo $mod | sed "s/^docx$/python-docx/")"; missing=1; fi
  done
  if command -v pandoc >/dev/null 2>&1; then echo "  [ok] pandoc: $(pandoc --version | head -1)"
  else echo "  [optional-MISSING] pandoc (DOCX builds) — Windows: winget install --id JohnMacFarlane.Pandoc · macOS: brew install pandoc · Linux: apt install pandoc"; fi
  if command -v latexmk >/dev/null 2>&1; then echo "  [ok] latexmk"
  else echo "  [optional-MISSING] latexmk (PDF builds) — Windows: winget install --id MiKTeX.MiKTeX · macOS: brew install --cask mactex-no-gui · Linux: apt install texlive latexmk"; fi
  # Trivially true on the host running this script — it IS bash. Checked anyway
  # so the two installers stay mirrors of each other (INSTALL.ps1 is where the
  # answer can genuinely be "no"), and so the build scripts' interpreter appears
  # in the dependency list at all rather than being assumed.
  if command -v bash >/dev/null 2>&1; then echo "  [ok] bash (runs the DOCX/PDF build scripts)"
  else echo "  [optional-MISSING] bash (DOCX/PDF builds run scripts/*.sh) — Windows: Git for Windows (winget install --id Git.Git)"; fi
  if command -v claude >/dev/null 2>&1; then echo "  [ok] claude code CLI"
  else echo "  [MISSING] Claude Code CLI — https://claude.com/claude-code"; missing=1; fi
  echo
  $PY scripts/validate_kit.py >/dev/null 2>&1 \
    && echo "  [ok] kit structure valid (scripts/validate_kit.py)" \
    || echo "  [warn] kit structure problems — run: $PY scripts/validate_kit.py"
  return $missing
}

update_data() {
  echo "== Index datasets -> data/ =="
  $PY scripts/update_data.py
}

setup_mcp() {
  echo "== MCP servers (optional — kit degrades to WebSearch without them) =="
  command -v claude >/dev/null 2>&1 || { echo "  claude CLI not found; skipping"; return; }
  echo "  Suggested servers (nothing installs without your confirmation):"
  echo "   1) semantic-scholar : 200M+ papers, citation graph (free API key recommended)"
  echo "      claude mcp add semantic-scholar -- uvx semantic-scholar-mcp"
  echo "   2) paper-search     : arXiv/PubMed/OpenAlex/Crossref/PMC/DOAJ/CORE + PDF download"
  echo "      claude mcp add paper-search -- uvx paper-search-mcp"
  echo "   3) scholar-sidekick : verify_citation + check_retraction + format_citation (remote, keyless)"
  echo "      claude mcp add --transport http scholar-sidekick https://scholar-sidekick.com/api/apps/mcp"
  echo "   4) zotero (optional): claude mcp add zotero -- uvx zotero-mcp   (requires local Zotero)"
  echo
  read -r -p "  Run these now? [y/N] " yn
  case "$yn" in
    [Yy]*)
      claude mcp add semantic-scholar -- uvx semantic-scholar-mcp || true
      claude mcp add paper-search -- uvx paper-search-mcp || true
      claude mcp add --transport http scholar-sidekick https://scholar-sidekick.com/api/apps/mcp || true
      echo "  Connection test:"; claude mcp list || true
      ;;
    *) echo "  Skipped. Re-run: bash INSTALL.sh --mcp" ;;
  esac
}

case "$MODE" in
  --check) check_deps; patch_hooks ;;
  --update-data) update_data ;;
  --mcp) setup_mcp ;;
  full|*)
    check_deps
    patch_hooks
    echo
    read -r -p "Download index datasets (~40MB, SCImago+DOAJ)? [y/N] " yn
    case "$yn" in [Yy]*) update_data ;; *) echo "Skipped. Re-run: bash INSTALL.sh --update-data" ;; esac
    echo
    setup_mcp
    echo
    echo "Done. Start a new paper with:  claude  ->  /new-project makale"
    ;;
esac
