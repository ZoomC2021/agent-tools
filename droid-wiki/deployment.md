# Deployment

Deployment guide for Agent Tools.

## Overview

Agent Tools is a **distribution repository** - it doesn't deploy as a running service. Instead, it packages and distributes prompts/skills/workflows to multiple AI coding agent platforms.

## Distribution Model

The "deployment" of Agent Tools is the installation of prompts across 15+ agent targets on a user's local machine.

| Target | Installation Method | Destination |
|--------|--------------------|-------------|
| Claude Code | Copy `.md` files | `~/.claude/commands/` |
| Codex | Copy `.md` files | `~/.codex/skills/` |
| OpenCode | Copy + config setup | `~/.config/opencode/` |
| Cursor | Copy `.md` files | `~/.cursor/commands/` |
| Cline | Copy `.md` files | `~/Documents/Cline/Rules/` |
| And 9 more... | Various | Platform-specific |

## Installation (User Deployment)

### Full Installation

```bash
cd agent-tools
./scripts/install.sh
```

This installs prompts for all supported agents.

### Selective Installation

Install for specific agents only:

```bash
./scripts/install.sh claude opencode cursor
```

### Individual Agent Install

```bash
# Claude Code only
./scripts/install.sh claude

# OpenCode only
./scripts/install.sh opencode
```

## Installation Verification

After installation, verify with the built-in self-check:

```bash
# OpenCode self-check runs automatically
# Check for: "OpenCode self-check PASSED"

# Manual verification - check agent files exist
ls ~/.claude/commands/        # Claude
ls ~/.config/opencode/agent/  # OpenCode
ls ~/.cursor/commands/        # Cursor
```

## Repository Structure

```
agent-tools/
├── prompts/           # Source prompts organized by target
│   ├── claude/
│   ├── opencode/
│   ├── cursor/
│   └── ...
├── scripts/           # Installation scripts
│   ├── install.sh     # macOS/Linux installer
│   └── install.ps1    # Windows installer (PowerShell)
├── utils.py           # Shared utilities
└── tests/             # Test suite
```

## Release Process

### Versioning

Agent Tools uses **commit-based versioning** - no formal release tags. The repository is continuously deployed (installed) by users.

### Distribution Channels

1. **GitHub Repository** (primary)
   - Users clone and run install script
   - Prompts are kept in sync with git

2. **Local Sync** (user workflow)
   ```bash
   # Update to latest
   git pull origin main
   ./scripts/install.sh
   ```

## Testing Before "Deploy"

Before committing changes that affect installation:

```bash
# Run Python utility tests
python tests/test_utils.py

# Or with pytest
pytest tests/test_utils.py
```

For OpenCode changes:

```bash
# Verify eval matrix
prompts/opencode/bin/opencode-eval list

# Dry-run eval
cd prompts/opencode && ./bin/opencode-eval run --dry-run

# Verify config JSON is valid
jq -e . prompts/opencode/opencode.json.example
```

## Installation Targets Reference

### macOS

| Agent | Path |
|-------|------|
| Claude Code | `~/.claude/commands/` |
| OpenCode | `~/.config/opencode/` |
| Cursor | `~/.cursor/commands/` |
| Cline | `~/Documents/Cline/Rules/` |
| Warp | `~/.warp/workflows/` |
| VSCode Copilot | `~/Library/Application Support/Code/User/prompts/` |
| Windsurf | `~/.codeium/windsurf/skills/` |
| Gemini CLI | `~/.gemini/skills/` |

### Linux

| Agent | Path |
|-------|------|
| Claude Code | `~/.claude/commands/` |
| OpenCode | `~/.config/opencode/` |
| Cursor | `~/.cursor/commands/` |
| Cline | `~/Documents/Cline/Rules/` |
| Warp | `~/.local/share/warp-terminal/workflows/` |
| VSCode Copilot | `~/.config/Code/User/prompts/` |
| Windsurf | `~/.codeium/windsurf/skills/` |
| Gemini CLI | `~/.gemini/skills/` |
| Pi | `~/.pi/agent/prompts/` |
| Copilot CLI | `~/.copilot/agents/` |
| Kilo Code | `~/.kilocode/prompts/` |
| Antigravity | `~/.antigravity/prompts/` |
| Amp | `~/.config/agents/skills/` |
| Codex | `~/.codex/skills/` |

## Configuration Management

### OpenCode Config

The `prompts/opencode/opencode.json.example` is the **source of truth**. Users copy this to:

- macOS: `~/.config/opencode/opencode.json`
- Linux: `~/.config/opencode/opencode.json`

**Important**: Users must edit and replace `YOUR_FIREWORKS_API_KEY_HERE` with their actual API key.

### Config Validation

Verify all `{file:...}` references resolve:

```bash
jq -r '.. | strings | select(test("^\\{file:[^}]+\\}$")) | capture("^\\{file:(?<p>[^}]+)\\}$").p' \
  prompts/opencode/opencode.json.example | sort -u | while read ref; do
    [ -f "prompts/opencode/${ref#./}" ] || echo "MISS $ref"
  done
```

## Troubleshooting Installation

| Issue | Solution |
|-------|----------|
| Permission denied | Check write permissions to destination directory |
| Missing agent files | Verify source directory exists in `prompts/` |
| Config JSON invalid | Validate with `jq -e . prompts/opencode/opencode.json.example` |
| OpenCode self-check fails | Run installer again or check file permissions |

## Future Improvements

Potential enhancements to the distribution model:

- [ ] Package manager distribution (Homebrew, apt)
- [ ] One-line curl install script
- [ ] Versioned releases with changelog
- [ ] Automatic update checker
- [ ] Web-based prompt browser/selector
