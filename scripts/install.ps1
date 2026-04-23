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

    # Install command prompts from commands/ subdirectory
    $CommandsSource = Join-Path $SourceDir "commands"
    $CommandsDest = Join-Path $env:USERPROFILE ".config\opencode\commands"
    New-Item -ItemType Directory -Path $CommandsDest -Force | Out-Null

    if (Test-Path -PathType Container $CommandsSource) {
        $CmdFiles = Get-ChildItem -Path $CommandsSource -Filter "*.md"
        if ($CmdFiles.Count -eq 0) {
            Write-Warn "No command .md files found in $CommandsSource"
        } else {
            Copy-Item $CmdFiles.FullName -Destination $CommandsDest -Force
            Write-Success "OpenCode commands: $CommandsDest"

            # Keep legacy prompts/ in sync for backward compatibility with older configs
            $PromptsDest = Join-Path $env:USERPROFILE ".config\opencode\prompts"
            New-Item -ItemType Directory -Path $PromptsDest -Force | Out-Null
            Copy-Item "$CommandsDest\*.md" -Destination $PromptsDest -Force
            Write-Success "OpenCode legacy prompts mirror: $PromptsDest"
        }
    } else {
        Write-Warn "Commands source directory not found: $CommandsSource"
    }

    # Install agent files from agent/ subdirectory
    $AgentSource = Join-Path $SourceDir "agent"
    $AgentDest = Join-Path $env:USERPROFILE ".config\opencode\agent"
    New-Item -ItemType Directory -Path $AgentDest -Force | Out-Null

    if (Test-Path -PathType Container $AgentSource) {
        $AgentMdFiles = Get-ChildItem -Path $AgentSource -Filter "*.md"
        if ($AgentMdFiles.Count -eq 0) {
            Write-Warn "No agent .md files found in $AgentSource"
        } else {
            Copy-Item $AgentMdFiles.FullName -Destination $AgentDest -Force
            Write-Success "OpenCode agent files: $AgentDest"
        }
    } else {
        Write-Warn "Agent source directory not found: $AgentSource"
    }

    # Install .opencode/plugins (local plugins like kimi-routing-guard)
    $PluginsSource = Join-Path $SourceDir ".opencode\plugins"
    $PluginsDest = Join-Path $env:USERPROFILE ".config\opencode\plugins"

    if (Test-Path -PathType Container $PluginsSource) {
        New-Item -ItemType Directory -Path $PluginsDest -Force | Out-Null
        $PluginFiles = Get-ChildItem -Path $PluginsSource -File
        if ($PluginFiles.Count -eq 0) {
            Write-Warn "No plugin files found in $PluginsSource"
        } else {
            Copy-Item $PluginFiles.FullName -Destination $PluginsDest -Force
            Write-Success "OpenCode plugins: $PluginsDest"
        }
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

    # Install evals harness (scenarios, variants, fixtures — not output)
    $EvalsSource = Join-Path $SourceDir "evals"
    if (Test-Path -PathType Container $EvalsSource) {
        $EvalsDest = Join-Path $env:USERPROFILE ".config\opencode\evals"
        New-Item -ItemType Directory -Path $EvalsDest -Force | Out-Null

        # Copy everything except the out/ directory
        Get-ChildItem -Path $EvalsSource | Where-Object { $_.Name -ne "out" } | ForEach-Object {
            if ($_.PSIsContainer) {
                Copy-Item $_.FullName -Destination (Join-Path $EvalsDest $_.Name) -Recurse -Force
            } else {
                Copy-Item $_.FullName -Destination $EvalsDest -Force
            }
        }
        Write-Success "OpenCode evals harness: $EvalsDest"
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
        "codex53-kimi.md",
        "codex53-kimi-turbo.md",
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
        "spec-compiler.md",
        "quick-validator.md",
        "mission-scrutiny.md",
        "milestone-validator.md",
        "plan-review.md",
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
    } else {
        Repair-OpenCodeConfigReferences -ConfigFile $ConfigFile
        Sync-OpenCodePromptFrontmatterModels -ConfigFile $ConfigFile
        $missingRefs = Test-OpenCodeConfigFileReferences -ConfigFile $ConfigFile
        if ($missingRefs -gt 0) {
            $failed += $missingRefs
        }
    }

    if ($failed -eq 0) {
        Write-Success "OpenCode self-check PASSED: all required files installed"
    } else {
        Write-Warn "OpenCode self-check FAILED: $failed check(s) failed"
        Write-Warn "  → Run the installer again or check file permissions"
    }
}

function Repair-OpenCodeConfigReferences {
    param([string]$ConfigFile)

    if (-not (Test-Path $ConfigFile)) { return }

    $content = Get-Content -Raw -Path $ConfigFile
    if ($content -notmatch "\{file:\./prompts/") { return }

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backup = "$ConfigFile.backup-$timestamp-normalize-refs"
    Copy-Item -Path $ConfigFile -Destination $backup -Force

    $updated = $content -replace "\{file:\./prompts/", "{file:./commands/"
    Set-Content -Path $ConfigFile -Value $updated -NoNewline

    Write-Warn "Normalized OpenCode config refs: ./prompts -> ./commands"
    Write-Warn "  Backup written to: $backup"
}

function Sync-OpenCodePromptFrontmatterModels {
    param([string]$ConfigFile)

    if (-not (Test-Path $ConfigFile)) { return }

    try {
        $config = Get-Content -Raw -Path $ConfigFile | ConvertFrom-Json
    } catch {
        Write-Warn "Skipping prompt frontmatter model sync; invalid JSON in $ConfigFile"
        return
    }

    if (-not ($config.PSObject.Properties.Name -contains "agent")) { return }

    $configDir = Split-Path -Parent $ConfigFile

    foreach ($entry in $config.agent.PSObject.Properties) {
        $agentName = $entry.Name
        $agentConfig = $entry.Value

        if ($null -eq $agentConfig) { continue }
        if (-not ($agentConfig.PSObject.Properties.Name -contains "model")) { continue }
        if (-not ($agentConfig.PSObject.Properties.Name -contains "prompt")) { continue }

        $agentModel = [string]$agentConfig.model
        $promptRef = [string]$agentConfig.prompt

        if ($promptRef -notmatch '^\{file:(.+)\}$') { continue }
        $promptPathRef = $Matches[1]

        $promptPath =
            if ([System.IO.Path]::IsPathRooted($promptPathRef)) {
                $promptPathRef
            } else {
                Join-Path $configDir ($promptPathRef -replace '^\./', '')
            }

        if (-not (Test-Path $promptPath)) { continue }

        $lines = Get-Content -Path $promptPath
        if ($lines.Count -lt 3) { continue }
        if ($lines[0] -ne "---") { continue }

        $frontmatterEnd = -1
        for ($i = 1; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -eq "---") {
                $frontmatterEnd = $i
                break
            }
        }
        if ($frontmatterEnd -lt 0) { continue }

        $modelLineIndex = -1
        $frontmatterModel = $null
        for ($i = 1; $i -lt $frontmatterEnd; $i++) {
            if ($lines[$i] -match '^model:\s*(.+)$') {
                $modelLineIndex = $i
                $frontmatterModel = $Matches[1].Trim()
                break
            }
        }
        if ($modelLineIndex -lt 0) { continue }

        if ($frontmatterModel -ne $agentModel) {
            $lines[$modelLineIndex] = "model: $agentModel"
            Set-Content -Path $promptPath -Value $lines
            Write-Warn "Aligned frontmatter model for $agentName to config model: $agentModel"
        }
    }
}

function Get-OpenCodeFileRefs {
    param([object]$Object)

    $refs = @()

    if ($null -eq $Object) { return $refs }

    if ($Object -is [string]) {
        if ($Object -match '^\{file:(.+)\}$') {
            return @($Matches[1])
        }
        return $refs
    }

    if ($Object -is [System.Collections.IDictionary]) {
        foreach ($value in $Object.Values) {
            $refs += Get-OpenCodeFileRefs -Object $value
        }
        return $refs
    }

    if ($Object -is [System.Collections.IEnumerable] -and -not ($Object -is [string])) {
        foreach ($item in $Object) {
            $refs += Get-OpenCodeFileRefs -Object $item
        }
        return $refs
    }

    foreach ($prop in $Object.PSObject.Properties) {
        $refs += Get-OpenCodeFileRefs -Object $prop.Value
    }

    return $refs
}

function Test-OpenCodeConfigFileReferences {
    param([string]$ConfigFile)

    if (-not (Test-Path $ConfigFile)) { return 0 }

    $configDir = Split-Path -Parent $ConfigFile
    $missing = 0

    try {
        $configObj = Get-Content -Raw -Path $ConfigFile | ConvertFrom-Json
    } catch {
        Write-Err "Invalid OpenCode config JSON: $ConfigFile"
        return 1
    }

    $refs = Get-OpenCodeFileRefs -Object $configObj | Sort-Object -Unique
    foreach ($ref in $refs) {
        $resolved =
            if ([System.IO.Path]::IsPathRooted($ref)) {
                $ref
            } else {
                Join-Path $configDir ($ref -replace '^\./', '')
            }

        if (-not (Test-Path $resolved)) {
            Write-Err "Bad file reference in opencode.json: {file:$ref} -> $resolved"
            $missing++
        }
    }

    return $missing
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
