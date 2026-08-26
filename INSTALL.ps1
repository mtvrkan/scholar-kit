# INSTALL.ps1 — scholar-kit setup for Windows PowerShell (mirror of INSTALL.sh).
# Usage:
#   .\INSTALL.ps1               # dependency check + interactive data/MCP setup
#   .\INSTALL.ps1 -Check       # dependency check only
#   .\INSTALL.ps1 -UpdateData  # refresh data/ index datasets (SCImago, DOAJ)
#   .\INSTALL.ps1 -Mcp         # MCP setup only
param(
    [switch]$Check,
    [switch]$UpdateData,
    [switch]$Mcp
)
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

function Get-Python {
    foreach ($cand in @("python", "python3", "py")) {
        if (Get-Command $cand -ErrorAction SilentlyContinue) { return $cand }
    }
    return $null
}

function Test-Deps {
    Write-Host "== Dependency check =="
    $missing = 0
    $py = Get-Python
    if ($py) { Write-Host "  [ok] python: $(& $py --version 2>&1)" }
    else { Write-Host "  [MISSING] python 3.10+ - https://www.python.org/downloads/"; $missing = 1 }
    if ($py) {
        foreach ($mod in @("requests", "openpyxl", "rapidfuzz", "docx", "pymupdf4llm")) {
            & $py -c "import $mod" 2>$null
            if ($LASTEXITCODE -eq 0) { Write-Host "  [ok] python module: $mod" }
            else {
                $pkg = if ($mod -eq "docx") { "python-docx" } else { $mod }
                Write-Host "  [MISSING] python module: $mod  ->  $py -m pip install $pkg"
                $missing = 1
            }
        }
    }
    if (Get-Command pandoc -ErrorAction SilentlyContinue) {
        Write-Host "  [ok] pandoc: $((pandoc --version | Select-Object -First 1))"
    } else {
        Write-Host "  [optional-MISSING] pandoc (DOCX builds) - winget install --id JohnMacFarlane.Pandoc"
    }
    if (Get-Command latexmk -ErrorAction SilentlyContinue) { Write-Host "  [ok] latexmk" }
    else { Write-Host "  [optional-MISSING] latexmk (PDF builds) - MiKTeX: winget install --id MiKTeX.MiKTeX" }
    # Both final-output builders are shell scripts (scripts/docx_build.sh,
    # scripts/latex_build.sh) and every skill/agent invokes them as
    # `bash scripts/...`. On Windows that interpreter comes from Git for
    # Windows, which this check never mentioned - so a machine with pandoc and
    # MiKTeX both present still failed at /submit-check's build step with
    # "bash is not recognized", after every other check had said [ok].
    if (Get-Command bash -ErrorAction SilentlyContinue) { Write-Host "  [ok] bash (runs the DOCX/PDF build scripts)" }
    else { Write-Host "  [optional-MISSING] bash (DOCX/PDF builds run scripts/*.sh) - Git for Windows: winget install --id Git.Git" }
    if (Get-Command claude -ErrorAction SilentlyContinue) { Write-Host "  [ok] claude code CLI" }
    else { Write-Host "  [MISSING] Claude Code CLI - https://claude.com/claude-code"; $missing = 1 }
    if ($py) {
        & $py scripts/validate_kit.py *>$null
        if ($LASTEXITCODE -eq 0) { Write-Host "  [ok] kit structure valid (scripts/validate_kit.py)" }
        else { Write-Host "  [warn] kit structure problems - run: $py scripts/validate_kit.py" }
    }
    return $missing
}

function Update-HookInterpreter {
    # settings.json hooks must invoke the detected interpreter. Delegates to
    # scripts/patch_hook_interpreter.py (single source of truth shared with
    # INSTALL.sh) instead of a third independent reimplementation of this
    # logic — that interpreter-drift bug (python <-> python3) has already
    # recurred three times across separate implementations (D-017/D-027/D-041).
    $py = Get-Python
    if (-not $py -or -not (Test-Path ".claude/settings.json")) { return }
    $result = & $py scripts/patch_hook_interpreter.py --target $py --json | ConvertFrom-Json
    if ($result.changed) {
        Write-Host "  [ok] hooks now use: $py"
    } else {
        Write-Host "  [ok] hooks already use: $py"
    }
}

function Update-Data {
    Write-Host "== Index datasets -> data/ =="
    $py = Get-Python
    if (-not $py) { Write-Host "  [fail] python required"; return }
    New-Item -ItemType Directory -Force -Path data | Out-Null
    & $py scripts/update_data.py
}

function Setup-Mcp {
    Write-Host "== MCP servers (optional - kit degrades to WebSearch without them) =="
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        Write-Host "  claude CLI not found; skipping"; return
    }
    Write-Host "  1) semantic-scholar : claude mcp add semantic-scholar -- uvx semantic-scholar-mcp"
    Write-Host "  2) paper-search     : claude mcp add paper-search -- uvx paper-search-mcp"
    Write-Host "  3) scholar-sidekick : claude mcp add --transport http scholar-sidekick https://scholar-sidekick.com/api/apps/mcp"
    Write-Host "  4) zotero (optional): claude mcp add zotero -- uvx zotero-mcp"
    $yn = Read-Host "  Run 1-3 now? [y/N]"
    if ($yn -match '^[Yy]') {
        claude mcp add semantic-scholar -- uvx semantic-scholar-mcp
        claude mcp add paper-search -- uvx paper-search-mcp
        claude mcp add --transport http scholar-sidekick https://scholar-sidekick.com/api/apps/mcp
        Write-Host "  Connection test:"; claude mcp list
    } else {
        Write-Host "  Skipped. Re-run: .\INSTALL.ps1 -Mcp"
    }
}

if ($Check) { Test-Deps | Out-Null; Update-HookInterpreter; exit 0 }
if ($UpdateData) { Update-Data; exit 0 }
if ($Mcp) { Setup-Mcp; exit 0 }

Test-Deps | Out-Null
Update-HookInterpreter
$yn = Read-Host "Download index datasets (~40MB, SCImago+DOAJ)? [y/N]"
if ($yn -match '^[Yy]') { Update-Data } else { Write-Host "Skipped. Re-run: .\INSTALL.ps1 -UpdateData" }
Setup-Mcp
Write-Host ""
Write-Host "Done. Start a new paper with:  claude  ->  /new-project makale"
