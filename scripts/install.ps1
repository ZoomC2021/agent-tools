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

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       Agent Tools Installer (Windows)"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Install-VSCodeCopilot

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
Write-Host ""
Write-Host "You may need to restart VSCode to pick up the new prompts."
Write-Host ""
