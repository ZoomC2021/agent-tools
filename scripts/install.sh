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

# Generic install function
install_agent() {
    local agent_name="$1"
    local source_dir="$2"
    local dest="$3"

    log_info "Installing $agent_name..."

    # Check if source directory exists
    if [[ ! -d "$source_dir" ]]; then
        log_warn "Source directory not found: $source_dir"
        return 0
    fi

    mkdir -p "$dest"

    # Enable nullglob to handle case where no files exist
    shopt -s nullglob
    local files=("$source_dir"/*.md)
    shopt -u nullglob

    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No .md files found in $source_dir"
        return 0
    fi

    cp "$source_dir"/*.md "$dest/"

    log_success "$agent_name: $dest"
}

# Install Claude Code commands
install_claude() {
    install_agent "Claude Code" "$PROMPTS_DIR/claude" "$HOME/.claude/commands"
}

# Install Codex skills
install_codex() {
    install_agent "Codex" "$PROMPTS_DIR/codex" "$HOME/.codex/skills"
}

# Install OpenCode commands and agent files
install_opencode() {
    log_info "Installing OpenCode..."
    local source_dir="$PROMPTS_DIR/opencode"

    if [[ ! -d "$source_dir" ]]; then
        log_warn "Source directory not found: $source_dir"
        return 0
    fi

    # Install command prompts (workflows)
    local commands_dest="$HOME/.config/opencode/commands"
    mkdir -p "$commands_dest"

    # Copy non-agent workflow prompts to commands/
    for f in "$source_dir"/*.md; do
        if [[ -f "$f" ]]; then
            local basename=$(basename "$f")
            # Skip agent files (they go to agent/)
            if [[ "$basename" != "codex53-kimi.md" && \
                  "$basename" != "kimi-general.md" && \
                  "$basename" != "kimi-explore.md" && \
                  "$basename" != "oracle.md" ]]; then
                cp "$f" "$commands_dest/"
            fi
        fi
    done
    log_success "OpenCode commands: $commands_dest"

    # Install agent files to agent/
    local agent_dest="$HOME/.config/opencode/agent"
    mkdir -p "$agent_dest"

    # Copy agent-specific files
    for agent_file in "codex53-kimi.md" "kimi-general.md" "kimi-explore.md" "oracle.md"; do
        if [[ -f "$source_dir/$agent_file" ]]; then
            cp "$source_dir/$agent_file" "$agent_dest/"
        fi
    done
    log_success "OpenCode agent files: $agent_dest"

    # Note about config file
    log_info "OpenCode config: Copy prompts/opencode/opencode.json.example to ~/.config/opencode/opencode.json"
    log_info "  ⚠️  IMPORTANT: Replace YOUR_FIREWORKS_API_KEY_HERE with your actual API key (DO NOT commit)"
}

# Install Antigravity prompts
install_antigravity() {
    log_info "Installing Antigravity prompts..."
    local source_dir="$PROMPTS_DIR/antigravity"
    
    if [[ ! -d "$source_dir" ]]; then
        log_warn "Source directory not found: $source_dir"
        return 0
    fi
    
    # Enable nullglob to handle case where no files exist
    shopt -s nullglob
    local files=("$source_dir"/*.md)
    shopt -u nullglob
    
    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No .md files found in $source_dir"
        return 0
    fi
    
    # Linux path
    local linux_dest="$HOME/.antigravity/prompts"
    mkdir -p "$linux_dest"
    cp "$source_dir"/*.md "$linux_dest/"
    log_success "Antigravity (Linux): $linux_dest"
    
    # macOS path
    if [[ "$OS" == "macos" ]]; then
        local macos_dest="$HOME/Library/Application Support/Antigravity/User/prompts"
        mkdir -p "$macos_dest"
        cp "$source_dir"/*.md "$macos_dest/"
        log_success "Antigravity (macOS): $macos_dest"
    fi
}

# Install VSCode Copilot prompts
install_vscode_copilot() {
    log_info "Installing VSCode Copilot prompts..."
    local source_dir="$PROMPTS_DIR/vscode-copilot"
    
    if [[ ! -d "$source_dir" ]]; then
        log_warn "Source directory not found: $source_dir"
        return 0
    fi
    
    # Enable nullglob to handle case where no files exist
    shopt -s nullglob
    local files=("$source_dir"/*.md)
    shopt -u nullglob
    
    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No .md files found in $source_dir"
        return 0
    fi
    
    # Linux path
    local linux_dest="$HOME/.config/Code - Insiders/User/prompts"
    mkdir -p "$linux_dest"
    cp "$source_dir"/*.md "$linux_dest/"
    log_success "VSCode Copilot (Linux): $linux_dest"
    
    # Also install to regular VSCode
    local linux_dest_regular="$HOME/.config/Code/User/prompts"
    mkdir -p "$linux_dest_regular"
    cp "$source_dir"/*.md "$linux_dest_regular/"
    log_success "VSCode Copilot Regular (Linux): $linux_dest_regular"
    
    # macOS paths
    if [[ "$OS" == "macos" ]]; then
        local macos_dest="$HOME/Library/Application Support/Code - Insiders/User/prompts"
        mkdir -p "$macos_dest"
        cp "$source_dir"/*.md "$macos_dest/"
        log_success "VSCode Copilot Insiders (macOS): $macos_dest"
        
        local macos_dest_regular="$HOME/Library/Application Support/Code/User/prompts"
        mkdir -p "$macos_dest_regular"
        cp "$source_dir"/*.md "$macos_dest_regular/"
        log_success "VSCode Copilot Regular (macOS): $macos_dest_regular"
    fi
}

# Install Copilot CLI agents
install_copilot_cli() {
    log_info "Installing Copilot CLI agents..."
    local source_dir="$PROMPTS_DIR/copilot-cli"
    local dest="$HOME/.copilot/agents"
    
    if [[ ! -d "$source_dir" ]]; then
        log_warn "Source directory not found: $source_dir"
        return 0
    fi
    
    mkdir -p "$dest"
    
    # Enable nullglob to handle case where no files exist
    shopt -s nullglob
    local files=("$source_dir"/*.md)
    shopt -u nullglob
    
    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No .md files found in $source_dir"
        return 0
    fi
    
    cp "$source_dir"/*.md "$dest/"
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
    local source_dir="$PROMPTS_DIR/amp"
    local dest="$HOME/.config/agents/skills"
    
    if [[ ! -d "$source_dir" ]]; then
        log_warn "Source directory not found: $source_dir"
        return 0
    fi
    
    mkdir -p "$dest"
    
    for skill_dir in "$source_dir/"*/; do
        if [[ ! -d "$skill_dir" ]]; then
            continue
        fi
        local skill_name=$(basename "$skill_dir")
        mkdir -p "$dest/$skill_name"
        cp "$skill_dir"* "$dest/$skill_name/"
    done
    log_success "Amp: $dest"
}

# Install Gemini CLI instructions
install_gemini() {
    log_info "Installing Gemini CLI instructions..."
    local source="$PROMPTS_DIR/gemini/GEMINI.md"
    local dest="$HOME/.gemini"
    
    if [[ ! -f "$source" ]]; then
        log_warn "Source file not found: $source"
        return 0
    fi
    
    mkdir -p "$dest"
    cp "$source" "$dest/"
    log_success "Gemini CLI: $dest/GEMINI.md"
}

# Install Kilo Code prompts
install_kilocode() {
    install_agent "Kilo Code" "$PROMPTS_DIR/kilocode" "$HOME/.kilocode/prompts"
}

# Install Cursor commands
install_cursor() {
    install_agent "Cursor" "$PROMPTS_DIR/cursor" "$HOME/.cursor/commands"
}

# Install Cline rules
install_cline() {
    install_agent "Cline" "$PROMPTS_DIR/cline" "$HOME/Documents/Cline/Rules"
}

# Install Roo Code commands
install_roocode() {
    install_agent "Roo Code" "$PROMPTS_DIR/roocode" "$HOME/.roo/commands"
}

# Install Windsurf global rules
install_windsurf() {
    log_info "Installing Windsurf global rules..."
    local source="$PROMPTS_DIR/windsurf/global_rules.md"
    local dest="$HOME/.codeium/windsurf/memories"
    
    if [[ ! -f "$source" ]]; then
        log_warn "Source file not found: $source"
        return 0
    fi
    
    mkdir -p "$dest"
    cp "$source" "$dest/"
    log_success "Windsurf: $dest/global_rules.md"
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
    install_cline
    install_roocode
    install_windsurf
    
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
    echo "  - deslop           : Analyze code for quality issues using coding principles"
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
            cline) install_cline ;;
            roocode) install_roocode ;;
            windsurf) install_windsurf ;;
            *) log_error "Unknown agent: $agent" ;;
        esac
    done
fi
