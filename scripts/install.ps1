# Agent Tools Installer for Windows
# Installs VSCode Copilot prompts

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoDir = Split-Path -Parent $ScriptDir
$PromptsDir = Join-Path $RepoDir "prompts"

function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor Blue }
function Write-Success { param($Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warn { param($Message) Write-Host "[!] $Message" -ForegroundColor Yellow }
function Write-Err { param($Message) Write-Host "[X] $Message" -ForegroundColor Red }

function Install-VSCodeCopilot {
    Write-Info "Installing VSCode Copilot prompts..."
    
    $SourceDir = Join-Path $PromptsDir "vscode-copilot"
    
    if (-not (Test-Path -PathType Container $SourceDir)) {
        Write-Warn "Source directory not found: $SourceDir"
        return
    }
    
    $SourceFiles = Get-ChildItem -Path $SourceDir -Filter "*.md"
    if ($SourceFiles.Count -eq 0) {
        Write-Warn "No .md files found in $SourceDir"
        return
    }
    
    # VSCode Insiders
    $InsidersDest = Join-Path $env:APPDATA "Code - Insiders\User\prompts"
    if (Test-Path (Split-Path -Parent $InsidersDest)) {
        New-Item -ItemType Directory -Path $InsidersDest -Force | Out-Null
        Copy-Item "$SourceDir\*.md" -Destination $InsidersDest -Force
        Write-Success "VSCode Insiders: $InsidersDest"
    } else {
        Write-Warn "VSCode Insiders not found, skipping"
    }
    
    # VSCode Regular
    $RegularDest = Join-Path $env:APPDATA "Code\User\prompts"
    if (Test-Path (Split-Path -Parent $RegularDest)) {
        New-Item -ItemType Directory -Path $RegularDest -Force | Out-Null
        Copy-Item "$SourceDir\*.md" -Destination $RegularDest -Force
        Write-Success "VSCode: $RegularDest"
    } else {
        Write-Warn "VSCode not found, skipping"
    }
}

function Install-Cursor {
    Write-Info "Installing Cursor commands..."
    
    $SourceDir = Join-Path $PromptsDir "cursor"
    
    if (-not (Test-Path -PathType Container $SourceDir)) {
        Write-Warn "Source directory not found: $SourceDir"
        return
    }
    
    $SourceFiles = Get-ChildItem -Path $SourceDir -Filter "*.md"
    if ($SourceFiles.Count -eq 0) {
        Write-Warn "No .md files found in $SourceDir"
        return
    }
    
    $Dest = Join-Path $env:USERPROFILE ".cursor\commands"
    
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Copy-Item "$SourceDir\*.md" -Destination $Dest -Force
    Write-Success "Cursor: $Dest"
}

function Install-Windsurf {
    Write-Info "Installing Windsurf global rules..."
    
    $SourceFile = Join-Path $PromptsDir "windsurf\global_rules.md"
    
    if (-not (Test-Path $SourceFile)) {
        Write-Warn "Source file not found: $SourceFile"
        return
    }
    
    $DestDir = Join-Path $env:USERPROFILE ".codeium\windsurf\memories"
    $DestFile = Join-Path $DestDir "global_rules.md"
    
    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null
    Copy-Item $SourceFile -Destination $DestFile -Force
    Write-Success "Windsurf: $DestFile"
}

function Install-OpenCode {
    Write-Info "Installing OpenCode commands and agent files..."

    $SourceDir = Join-Path $PromptsDir "opencode"

    if (-not (Test-Path -PathType Container $SourceDir)) {
        Write-Warn "Source directory not found: $SourceDir"
        return
    }

    # Agent files that go to agent/ directory
    $AgentFiles = @(
        "codex53-kimi.md",
        "kimi-general.md",
        "kimi-explore.md",
        "github-librarian.md",
        "docs-research.md",
        "walkthrough.md",
        "oracle.md",
        "spec-compiler.md",
        "quick-validator.md"
    )

    # Install command prompts (workflows) to commands/
    $CommandsDest = Join-Path $env:USERPROFILE ".config\opencode\commands"
    New-Item -ItemType Directory -Path $CommandsDest -Force | Out-Null

    $SourceFiles = Get-ChildItem -Path $SourceDir -Filter "*.md"
    $CommandFiles = $SourceFiles | Where-Object { $AgentFiles -notcontains $_.Name }

    if ($CommandFiles.Count -eq 0) {
        Write-Warn "No command .md files found in $SourceDir"
    } else {
        Copy-Item $CommandFiles.FullName -Destination $CommandsDest -Force
        Write-Success "OpenCode commands: $CommandsDest"
    }

    # Install agent files to agent/
    $AgentDest = Join-Path $env:USERPROFILE ".config\opencode\agent"
    New-Item -ItemType Directory -Path $AgentDest -Force | Out-Null

    $AgentSourceFiles = $SourceFiles | Where-Object { $AgentFiles -contains $_.Name }
    if ($AgentSourceFiles.Count -eq 0) {
        Write-Warn "No agent .md files found in $SourceDir"
    } else {
        Copy-Item $AgentSourceFiles.FullName -Destination $AgentDest -Force
        Write-Success "OpenCode agent files: $AgentDest"
    }

    # Install helper scripts to bin/
    $BinSourceDir = Join-Path $SourceDir "bin"
    if (Test-Path -PathType Container $BinSourceDir) {
        $BinDest = Join-Path $env:USERPROFILE ".config\opencode\bin"
        New-Item -ItemType Directory -Path $BinDest -Force | Out-Null

        $BinFiles = Get-ChildItem -Path $BinSourceDir -File
        if ($BinFiles.Count -eq 0) {
            Write-Warn "No helper scripts found in $BinSourceDir"
        } else {
            Copy-Item $BinFiles.FullName -Destination $BinDest -Force
            Write-Success "OpenCode helper scripts: $BinDest"
        }
    }

    # Setup config directory and copy example config
    $ConfigDir = Join-Path $env:USERPROFILE ".config\opencode"
    $ConfigFile = Join-Path $ConfigDir "opencode.json"
    $ExampleFile = Join-Path $RepoDir "prompts\opencode\opencode.json.example"

    New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null

    if (Test-Path $ExampleFile) {
        if (-not (Test-Path $ConfigFile)) {
            Copy-Item $ExampleFile -Destination $ConfigFile -Force
            Write-Success "OpenCode config created: $ConfigFile"
        } else {
            Write-Warn "OpenCode config already exists: $ConfigFile (not overwriting)"
        }
    } else {
        Write-Warn "Example config not found: $ExampleFile"
    }

    Write-Warn "  ⚠️  IMPORTANT: Edit $ConfigFile and replace YOUR_FIREWORKS_API_KEY_HERE with your actual API key (DO NOT commit)"

    # Self-check: verify installed files
    Test-OpenCodeInstallation -AgentDest $AgentDest -CommandsDest $CommandsDest -ConfigFile $ConfigFile
}

function Test-OpenCodeInstallation {
    param(
        [string]$AgentDest,
        [string]$CommandsDest,
        [string]$ConfigFile
    )

    Write-Info "Running OpenCode self-check..."
    $failed = 0

    # Check required agent files
    $requiredAgentFiles = @(
        "spec-compiler.md",
        "quick-validator.md",
        "codex53-kimi.md",
        "kimi-general.md",
        "kimi-explore.md",
        "github-librarian.md",
        "docs-research.md",
        "walkthrough.md",
        "oracle.md"
    )

    foreach ($file in $requiredAgentFiles) {
        $fullPath = Join-Path $AgentDest $file
        if (-not (Test-Path $fullPath)) {
            Write-Err "Missing agent file: $fullPath"
            $failed++
        }
    }

    # Check required command files
    $requiredCommandFiles = @(
        "mission-scrutiny.md",
        "milestone-validator.md",
        "pr-reviewer-only.md",
        "refactor.md",
        "review.md",
        "pr-reviewer.md",
        "change-auditor.md",
        "deslop.md",
        "create-pr.md"
    )

    foreach ($file in $requiredCommandFiles) {
        $fullPath = Join-Path $CommandsDest $file
        if (-not (Test-Path $fullPath)) {
            Write-Err "Missing command file: $fullPath"
            $failed++
        }
    }

    # Check config file exists
    if (-not (Test-Path $ConfigFile)) {
        Write-Err "Missing config file: $ConfigFile"
        $failed++
    }

    if ($failed -eq 0) {
        Write-Success "OpenCode self-check PASSED: all required files installed"
    } else {
        Write-Warn "OpenCode self-check FAILED: $failed check(s) failed"
        Write-Warn "  → Run the installer again or check file permissions"
    }
}

function Install-RooCode {
    Write-Info "Installing Roo Code commands..."
    
    $SourceDir = Join-Path $PromptsDir "roocode"
    
    if (-not (Test-Path -PathType Container $SourceDir)) {
        Write-Warn "Source directory not found: $SourceDir"
        return
    }
    
    $SourceFiles = Get-ChildItem -Path $SourceDir -Filter "*.md"
    if ($SourceFiles.Count -eq 0) {
        Write-Warn "No .md files found in $SourceDir"
        return
    }
    
    $Dest = Join-Path $env:USERPROFILE ".roo\commands"
    
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Copy-Item "$SourceDir\*.md" -Destination $Dest -Force
    Write-Success "Roo Code: $Dest"
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       Agent Tools Installer (Windows)"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Install-VSCodeCopilot
Install-Cursor
Install-RooCode
Install-Windsurf
Install-OpenCode

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Success "Installation complete!"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Installed workflows:"
Write-Host "  - Refactor         : Analyze codebase for refactoring opportunities"
Write-Host "  - Review           : Review uncommitted changes"
Write-Host "  - PR-Reviewer      : Address PR review feedback"
Write-Host "  - PR-Reviewer-Only : Generate implementation prompt for PR feedback"
Write-Host "  - Create-PR        : Create PR from current changes"
Write-Host "  - Deslop           : Analyze code for quality issues using coding principles"
Write-Host ""
Write-Host "You may need to restart your editors to pick up the new prompts."
Write-Host ""
