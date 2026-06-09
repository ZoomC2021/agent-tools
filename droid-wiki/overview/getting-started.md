# Getting started

## Prerequisites

- **Git** — for version control operations
- **GitHub CLI (`gh`)** — for PR operations and `github-librarian` agent
- **OpenCode** — for the primary Codex53-MiMo architecture
- **Bash** — for the installer script (macOS/Linux)

Optional:
- **Gemini CLI** — for `ultrareview` secondary review lane
- **Python 3** — for running utility tests

## Installation

### Quick install (all agents)

```bash
git clone https://github.com/ZoomC2021/agent-tools.git
cd agent-tools
./scripts/install.sh
```

### Specific agents only

```bash
./scripts/install.sh claude codex opencode warp
```

Available options: `claude`, `codex`, `opencode`, `pi`, `warp`, `antigravity`, `vscode`, `copilot-cli`, `amp`, `gemini`, `kilocode`, `cursor`, `cline`, `windsurf`

### Manual OpenCode setup (recommended)

```bash
# Create directories
mkdir -p ~/.config/opencode/commands
mkdir -p ~/.config/opencode/agent
mkdir -p ~/.config/opencode/bin

# Copy workflow prompts
for f in prompts/opencode/commands/*.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/commands/
done

# Copy agent definitions
for f in prompts/opencode/agent/*.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/agent/
done

# Copy helper scripts
cp prompts/opencode/bin/* ~/.config/opencode/bin/
chmod +x ~/.config/opencode/bin/*

# Copy and edit config (⚠️ add your API key)
cp prompts/opencode/opencode.json.example ~/.config/opencode/opencode.json
```

**Security note:** Edit `~/.config/opencode/opencode.json` and replace `YOUR_XIAOMI_API_KEY_HERE` with your actual API key. Never commit this file.

## Verification

### Python utility tests

```bash
python tests/test_utils.py
```

### OpenCode eval sanity check

```bash
prompts/opencode/bin/opencode-eval list
prompts/opencode/bin/opencode-eval run --dry-run
```

### Config file validation

```bash
jq -e . ~/.config/opencode/opencode.json
```

## Basic usage

Once installed, OpenCode commands are available:

- `/review` — Review uncommitted changes
- `/refactor` — Analyze refactoring opportunities
- `/deslop` — Code quality audit
- `/create-pr` — Create PR from current changes
- `/pr-reviewer` — Address PR feedback
- `/ultrareview` — Dual-model parallel review

Example prompts:

```
In github.com/cli/cli, find where auth token resolution happens
Walk me through how authentication works in this repo and include a Mermaid diagram
Compare our caching layer with owner/repo's implementation
```
