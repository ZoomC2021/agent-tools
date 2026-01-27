#!/bin/bash

# Agent Tools Installer
# Installs custom prompts/skills for various AI coding agents
# Supports macOS and Ubuntu/Linux

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PROMPTS_DIR="$REPO_DIR/prompts"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
log_info "Detected OS: $OS"

# Install Claude Code commands
install_claude() {
    log_info "Installing Claude Code commands..."
    local dest="$HOME/.claude/commands"
    mkdir -p "$dest"
    cp "$PROMPTS_DIR/claude/"*.md "$dest/"
    log_success "Claude Code: $dest"
}

# Install Codex skills
install_codex() {
    log_info "Installing Codex skills..."
    local dest="$HOME/.codex/skills"
    mkdir -p "$dest"
    cp "$PROMPTS_DIR/codex/"*.md "$dest/"
    log_success "Codex: $dest"
}

# Install OpenCode prompts
install_opencode() {
    log_info "Installing OpenCode prompts..."
    local dest="$HOME/.config/opencode/prompts"
    mkdir -p "$dest"
    cp "$PROMPTS_DIR/opencode/"*.md "$dest/"
    log_success "OpenCode: $dest"
}

# Install Antigravity prompts
install_antigravity() {
    log_info "Installing Antigravity prompts..."
    
    # Linux path
    local linux_dest="$HOME/.antigravity/prompts"
    mkdir -p "$linux_dest"
    cp "$PROMPTS_DIR/antigravity/"*.md "$linux_dest/"
    log_success "Antigravity (Linux): $linux_dest"
    
    # macOS path
    if [[ "$OS" == "macos" ]]; then
        local macos_dest="$HOME/Library/Application Support/Antigravity/User/prompts"
        mkdir -p "$macos_dest"
        cp "$PROMPTS_DIR/antigravity/"*.md "$macos_dest/"
        log_success "Antigravity (macOS): $macos_dest"
    fi
}

# Install VSCode Copilot prompts
install_vscode_copilot() {
    log_info "Installing VSCode Copilot prompts..."
    
    # Linux path
    local linux_dest="$HOME/.config/Code - Insiders/User/prompts"
    mkdir -p "$linux_dest"
    cp "$PROMPTS_DIR/vscode-copilot/"*.md "$linux_dest/"
    log_success "VSCode Copilot (Linux): $linux_dest"
    
    # Also install to regular VSCode
    local linux_dest_regular="$HOME/.config/Code/User/prompts"
    mkdir -p "$linux_dest_regular"
    cp "$PROMPTS_DIR/vscode-copilot/"*.md "$linux_dest_regular/"
    log_success "VSCode Copilot Regular (Linux): $linux_dest_regular"
    
    # macOS paths
    if [[ "$OS" == "macos" ]]; then
        local macos_dest="$HOME/Library/Application Support/Code - Insiders/User/prompts"
        mkdir -p "$macos_dest"
        cp "$PROMPTS_DIR/vscode-copilot/"*.md "$macos_dest/"
        log_success "VSCode Copilot Insiders (macOS): $macos_dest"
        
        local macos_dest_regular="$HOME/Library/Application Support/Code/User/prompts"
        mkdir -p "$macos_dest_regular"
        cp "$PROMPTS_DIR/vscode-copilot/"*.md "$macos_dest_regular/"
        log_success "VSCode Copilot Regular (macOS): $macos_dest_regular"
    fi
}

# Install Copilot CLI agents
install_copilot_cli() {
    log_info "Installing Copilot CLI agents..."
    local dest="$HOME/.copilot/agents"
    mkdir -p "$dest"
    cp "$PROMPTS_DIR/copilot-cli/"*.md "$dest/"
    # Rename to .agent.md format
    for f in "$dest"/*.md; do
        if [[ ! "$f" == *".agent.md" ]]; then
            mv "$f" "${f%.md}.agent.md"
        fi
    done
    log_success "Copilot CLI: $dest"
}

# Install Amp skills
install_amp() {
    log_info "Installing Amp skills..."
    local dest="$HOME/.config/agents/skills"
    mkdir -p "$dest"
    
    for skill_dir in "$PROMPTS_DIR/amp/"*/; do
        local skill_name=$(basename "$skill_dir")
        mkdir -p "$dest/$skill_name"
        cp "$skill_dir"* "$dest/$skill_name/"
    done
    log_success "Amp: $dest"
}

# Install Gemini CLI instructions
install_gemini() {
    log_info "Installing Gemini CLI instructions..."
    local dest="$HOME/.gemini"
    mkdir -p "$dest"
    cp "$PROMPTS_DIR/gemini/GEMINI.md" "$dest/"
    log_success "Gemini CLI: $dest/GEMINI.md"
}

# Install Kilo Code prompts
install_kilocode() {
    log_info "Installing Kilo Code prompts..."
    local dest="$HOME/.kilocode/prompts"
    mkdir -p "$dest"
    # Enable nullglob to handle case where no .md files exist
    shopt -s nullglob
    local files=("$PROMPTS_DIR/kilocode"/*.md)
    shopt -u nullglob
    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No .md files found in $PROMPTS_DIR/kilocode/"
        return 0
    fi
    cp "$PROMPTS_DIR/kilocode"/*.md "$dest/"
    log_success "Kilo Code: $dest"
}

# Install Cursor commands
install_cursor() {
    log_info "Installing Cursor commands..."
    local dest="$HOME/.cursor/commands"
    mkdir -p "$dest"
    cp "$PROMPTS_DIR/cursor/"*.md "$dest/"
    log_success "Cursor (global): $dest"
}

# Main installation
main() {
    echo ""
    echo "=========================================="
    echo "       Agent Tools Installer"
    echo "=========================================="
    echo ""
    
    install_claude
    install_codex
    install_opencode
    install_antigravity
    install_vscode_copilot
    install_copilot_cli
    install_amp
    install_gemini
    install_kilocode
    install_cursor
    
    echo ""
    echo "=========================================="
    log_success "Installation complete!"
    echo "=========================================="
    echo ""
    echo "Installed workflows:"
    echo "  - refactor         : Analyze codebase for refactoring opportunities"
    echo "  - review           : Review uncommitted changes"
    echo "  - pr-reviewer      : Address PR review feedback"
    echo "  - pr-reviewer-only : Generate implementation prompt for PR feedback"
    echo "  - create-pr        : Create PR from current changes"
    echo ""
    echo "You may need to restart your editors/terminals"
    echo "to pick up the new prompts/skills."
    echo ""
}

# Run with optional agent filter
if [[ $# -eq 0 ]]; then
    main
else
    for agent in "$@"; do
        case "$agent" in
            claude) install_claude ;;
            codex) install_codex ;;
            opencode) install_opencode ;;
            antigravity) install_antigravity ;;
            vscode|vscode-copilot) install_vscode_copilot ;;
            copilot-cli) install_copilot_cli ;;
            amp) install_amp ;;
            gemini) install_gemini ;;
            kilocode) install_kilocode ;;
            cursor) install_cursor ;;
            *) log_error "Unknown agent: $agent" ;;
        esac
    done
fi
