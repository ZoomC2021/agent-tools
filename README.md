# Agent Tools

Custom prompts, skills, and workflows for AI coding agents. Provides consistent developer workflows across multiple coding assistants.

## Workflows Included

| Workflow | Description |
|----------|-------------|
| **refactor** | Analyze codebase for refactoring opportunities, prioritize by severity/effort |
| **review** | Review uncommitted changes for bugs, regressions, and improvements |
| **pr-reviewer** | Fetch PR comments, summarize issues, address them, update PR |
| **create-pr** | Create PR with auto-generated title and description |
| **deslop** | Analyze code for quality issues using established software engineering principles |

## Opencode Codex53-Kimi Setup (Primary Agent Architecture)

This repository includes a sophisticated agent architecture for OpenCode using GPT-5.3-Codex as the orchestrator and Fireworks Kimi K2.5 Turbo as subagents.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Codex53-Kimi Orchestrator (GPT-5.3-Codex)                 │
│  • Plans and sequences work                                  │
│  • Makes routing decisions                                    │
│  • Delegates to specialized subagents                       │
└──────────────────────┬────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼─────┐
│ kimi-general │ │ kimi-explore │ │ review    │
│ (execution)  │ │ (discovery)  │ │ (audit)   │
└─────────────┘ └─────────────┘ └───────────┘
       │               │               │
┌──────▼──────┐ ┌──────▼──────┐ ┌─────▼─────┐
│ pr-reviewer │ │ deslop       │ │ create-pr │
│ (PR fixes)   │ │ (quality)    │ │ (workflow)│
└─────────────┘ └─────────────┘ └───────────┘
```

### Deterministic Routing

The orchestrator uses keyword-based deterministic routing:

| Trigger | Keywords | Agent Selected |
|---------|----------|----------------|
| PR creation | "create PR", "pull request" | **create-pr** |
| PR feedback | "PR comment", "address PR" | **pr-reviewer** |
| Code audit | "audit", "code quality" | **deslop** |
| Local review | "review changes", "uncommitted" | **review** |
| Discovery | "find", "search", "explore" | **kimi-explore** |
| Implementation | "implement", "fix", "refactor" | **kimi-general** |

### 4-Phase Implementation Workflow

For implementation/debugging/refactoring tasks, the orchestrator follows:

1. **PHASE 1: spec-compiler** → Compile Execution Contract (scope, risks, success criteria)
2. **PHASE 2: kimi-general** → Execute implementation based on contract
3. **PHASE 3: quick-validator** → Run validation tests/checks
4. **PHASE 4 (optional): change-auditor** → Deep audit for high-risk areas

### Directory Layout

```
~/.config/opencode/
├── opencode.json              # Main configuration (see example)
├── agent/                     # Primary agent definitions
│   ├── codex53-kimi.md       # Orchestrator (routing logic)
│   ├── kimi-general.md       # Execution worker
│   ├── kimi-explore.md       # Read-only discovery
│   └── oracle.md             # Deep reasoning (GPT-5.4)
└── commands/                  # Workflow prompts
    ├── review.md
    ├── deslop.md
    ├── pr-reviewer.md
    ├── create-pr.md
    ├── spec-compiler.md
    ├── quick-validator.md
    └── change-auditor.md
```

### ⚠️ Security Warning

**NEVER commit your `opencode.json` with real API keys to version control.**

- Use environment variables: `OPENCODE_FIREWORKS_API_KEY`
- Or keep the config file in a secure location with `apiKey: "YOUR_KEY_HERE"`
- The example file includes placeholder warnings to help prevent accidental commits

### Reference Example

A local reference setup uses:
- Fireworks Kimi K2.5 Turbo for build mode and subagents
- GPT-5.3-Codex for the orchestrator (plan mode)
- Specialized subagents for different task types

See `prompts/opencode/opencode.json.example` for the full configuration structure.

## Supported Agents

| Agent | Type | Prompt Location |
|-------|------|-----------------|
| [Claude Code](https://claude.ai) | CLI | `~/.claude/commands/` |
| [Codex](https://github.com/openai/codex) | CLI | `~/.codex/skills/` |
| [OpenCode](https://opencode.ai) | CLI | `~/.config/opencode/commands/` |
| [Antigravity](https://antigravity.dev) | Editor | `~/.antigravity/prompts/` or `~/Library/.../Antigravity/User/prompts/` |
| [VSCode Copilot](https://github.com/features/copilot) | Editor | `~/.config/Code/User/prompts/` or `~/Library/.../Code/User/prompts/` |
| [Copilot CLI](https://githubnext.com/projects/copilot-cli) | CLI | `~/.copilot/agents/` |
| [Amp](https://ampcode.com) | CLI/Editor | `~/.config/agents/skills/` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | CLI | `~/.gemini/GEMINI.md` |
| [Kilo Code](https://kilocode.com) | CLI | `~/.kilocode/prompts/` |
| [Cursor](https://cursor.com) | Editor | `~/.cursor/commands/` |
| [Cline](https://cline.bot) | Editor | `~/Documents/Cline/Rules/` |
| [Roo Code](https://roocode.com) | Editor | `~/.roo/commands/` |
| [Windsurf](https://codeium.com/windsurf) | Editor | `~/.codeium/windsurf/memories/global_rules.md` |

## Quick Install

### All Agents

```bash
git clone https://github.com/YOUR_USERNAME/agent-tools.git
cd agent-tools
./scripts/install.sh
```

### Specific Agents

```bash
./scripts/install.sh claude codex amp
```

Available options: `claude`, `codex`, `opencode`, `antigravity`, `vscode`, `copilot-cli`, `amp`, `gemini`, `kilocode`, `cursor`, `cline`, `roocode`, `windsurf`

## Manual Installation

### macOS

<details>
<summary>Claude Code</summary>

```bash
mkdir -p ~/.claude/commands
cp prompts/claude/*.md ~/.claude/commands/
```
</details>

<details>
<summary>Codex</summary>

```bash
mkdir -p ~/.codex/skills
cp prompts/codex/*.md ~/.codex/skills/
```
</details>

<details>
<summary>OpenCode (Codex53-Kimi Architecture)</summary>

```bash
# Create directories
mkdir -p ~/.config/opencode/commands
mkdir -p ~/.config/opencode/agent

# Copy workflow prompts to commands/
for f in prompts/opencode/review.md prompts/opencode/deslop.md \
         prompts/opencode/pr-reviewer.md prompts/opencode/create-pr.md \
         prompts/opencode/spec-compiler.md prompts/opencode/quick-validator.md \
         prompts/opencode/change-auditor.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/commands/
done

# Copy agent definitions to agent/
for f in prompts/opencode/codex53-kimi.md prompts/opencode/kimi-general.md \
         prompts/opencode/kimi-explore.md prompts/opencode/oracle.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/agent/
done

# Copy and edit config (⚠️ NEVER commit with real API key)
cp prompts/opencode/opencode.json.example ~/.config/opencode/opencode.json
```

**⚠️ Security Warning**: Edit `~/.config/opencode/opencode.json` and replace `YOUR_FIREWORKS_API_KEY_HERE` with your actual API key. **Do not commit this file.**

See [Opencode Codex53-Kimi Setup](#opencode-codex53-kimi-setup-primary-agent-architecture) for architecture details.
</details>

<details>
<summary>Antigravity</summary>

```bash
mkdir -p ~/Library/Application\ Support/Antigravity/User/prompts
cp prompts/antigravity/*.md ~/Library/Application\ Support/Antigravity/User/prompts/
```
</details>

<details>
<summary>VSCode Copilot</summary>

```bash
# VSCode Insiders
mkdir -p ~/Library/Application\ Support/Code\ -\ Insiders/User/prompts
cp prompts/vscode-copilot/*.md ~/Library/Application\ Support/Code\ -\ Insiders/User/prompts/

# VSCode Regular
mkdir -p ~/Library/Application\ Support/Code/User/prompts
cp prompts/vscode-copilot/*.md ~/Library/Application\ Support/Code/User/prompts/
```
</details>

<details>
<summary>Copilot CLI</summary>

```bash
mkdir -p ~/.copilot/agents
cp prompts/copilot-cli/*.md ~/.copilot/agents/
# Rename files to .agent.md format
for f in ~/.copilot/agents/*.md; do mv "$f" "${f%.md}.agent.md"; done
```
</details>

<details>
<summary>Amp</summary>

```bash
mkdir -p ~/.config/agents/skills
cp -r prompts/amp/* ~/.config/agents/skills/
```
</details>

<details>
<summary>Gemini CLI</summary>

```bash
cp prompts/gemini/GEMINI.md ~/.gemini/
```
</details>

<details>
<summary>Kilo Code</summary>

```bash
mkdir -p ~/.kilocode/prompts
cp prompts/kilocode/*.md ~/.kilocode/prompts/
```
</details>

<details>
<summary>Cursor</summary>

```bash
mkdir -p ~/.cursor/commands
cp prompts/cursor/*.md ~/.cursor/commands/
```
</details>

<details>
<summary>Cline</summary>

```bash
mkdir -p ~/Documents/Cline/Rules
cp prompts/cline/*.md ~/Documents/Cline/Rules/
```
</details>

<details>
<summary>Roo Code</summary>

```bash
mkdir -p ~/.roo/commands
cp prompts/roocode/*.md ~/.roo/commands/
```
</details>

<details>
<summary>Windsurf</summary>

```bash
mkdir -p ~/.codeium/windsurf/memories
cp prompts/windsurf/global_rules.md ~/.codeium/windsurf/memories/
```
</details>

### Ubuntu/Linux

<details>
<summary>Claude Code</summary>

```bash
mkdir -p ~/.claude/commands
cp prompts/claude/*.md ~/.claude/commands/
```
</details>

<details>
<summary>Codex</summary>

```bash
mkdir -p ~/.codex/skills
cp prompts/codex/*.md ~/.codex/skills/
```
</details>

<details>
<summary>OpenCode (Codex53-Kimi Architecture)</summary>

```bash
# Create directories
mkdir -p ~/.config/opencode/commands
mkdir -p ~/.config/opencode/agent

# Copy workflow prompts to commands/
for f in prompts/opencode/review.md prompts/opencode/deslop.md \
         prompts/opencode/pr-reviewer.md prompts/opencode/create-pr.md \
         prompts/opencode/spec-compiler.md prompts/opencode/quick-validator.md \
         prompts/opencode/change-auditor.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/commands/
done

# Copy agent definitions to agent/
for f in prompts/opencode/codex53-kimi.md prompts/opencode/kimi-general.md \
         prompts/opencode/kimi-explore.md prompts/opencode/oracle.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/agent/
done

# Copy and edit config (⚠️ NEVER commit with real API key)
cp prompts/opencode/opencode.json.example ~/.config/opencode/opencode.json
```

**⚠️ Security Warning**: Edit `~/.config/opencode/opencode.json` and replace `YOUR_FIREWORKS_API_KEY_HERE` with your actual API key. **Do not commit this file.**

See [Opencode Codex53-Kimi Setup](#opencode-codex53-kimi-setup-primary-agent-architecture) for architecture details.
</details>

<details>
<summary>Antigravity</summary>

```bash
mkdir -p ~/.antigravity/prompts
cp prompts/antigravity/*.md ~/.antigravity/prompts/
```
</details>

<details>
<summary>VSCode Copilot</summary>

```bash
# VSCode Insiders
mkdir -p ~/.config/Code\ -\ Insiders/User/prompts
cp prompts/vscode-copilot/*.md ~/.config/Code\ -\ Insiders/User/prompts/

# VSCode Regular
mkdir -p ~/.config/Code/User/prompts
cp prompts/vscode-copilot/*.md ~/.config/Code/User/prompts/
```
</details>

<details>
<summary>Copilot CLI</summary>

```bash
mkdir -p ~/.copilot/agents
cp prompts/copilot-cli/*.md ~/.copilot/agents/
for f in ~/.copilot/agents/*.md; do mv "$f" "${f%.md}.agent.md"; done
```
</details>

<details>
<summary>Amp</summary>

```bash
mkdir -p ~/.config/agents/skills
cp -r prompts/amp/* ~/.config/agents/skills/
```
</details>

<details>
<summary>Gemini CLI</summary>

```bash
cp prompts/gemini/GEMINI.md ~/.gemini/
```
</details>

<details>
<summary>Kilo Code</summary>

```bash
mkdir -p ~/.kilocode/prompts
cp prompts/kilocode/*.md ~/.kilocode/prompts/
```
</details>

<details>
<summary>Cursor</summary>

```bash
mkdir -p ~/.cursor/commands
cp prompts/cursor/*.md ~/.cursor/commands/
```
</details>

<details>
<summary>Cline</summary>

```bash
mkdir -p ~/Documents/Cline/Rules
cp prompts/cline/*.md ~/Documents/Cline/Rules/
```
</details>

<details>
<summary>Roo Code</summary>

```bash
mkdir -p ~/.roo/commands
cp prompts/roocode/*.md ~/.roo/commands/
```
</details>

<details>
<summary>Windsurf</summary>

```bash
mkdir -p ~/.codeium/windsurf/memories
cp prompts/windsurf/global_rules.md ~/.codeium/windsurf/memories/
```
</details>

## Workflow Details

### refactor

Analyzes your codebase for refactoring opportunities:

1. **Gathers context**: High-churn files, TODO/FIXME markers, large files
2. **Detects issues**: Code duplication, long functions, god classes, dead code, deep nesting
3. **Assesses severity**: 🔴 High | 🟠 Medium | 🟡 Low
4. **Calculates priority**: `Severity × (1/Effort)`
5. **Reports quick wins**: High severity + low effort items first

### review

Reviews uncommitted changes:

1. **Gets changes**: `git diff HEAD`, staged changes
2. **Checks for issues**: Logic errors, edge cases, type safety, security
3. **Checks for regressions**: Breaking API changes, removed functionality
4. **Optimizes**: Finds redundant code, duplicate logic, performance issues
5. **Fixes simple issues** automatically (≤5 straightforward fixes)

### pr-reviewer

Addresses PR review feedback:

1. **Fetches comments** from GitHub PR via GraphQL
2. **Identifies reviewers**: Distinguishes bots vs humans
3. **Summarizes issues** in a table grouped by severity
4. **Addresses issues**: Human feedback takes priority over bots
5. **Commits and pushes** with summary of changes

### create-pr

Creates a PR from current changes:

1. **Creates feature branch** if on main/master
2. **Generates conventional commit** message
3. **Creates PR** with auto-generated title and description
4. **Reports result** with PR URL and summary

### deslop

Analyzes code for quality issues using established software engineering principles:

1. **Reads target code**: Files, directories, or entire codebase
2. **Cross-references principles**: KISS, YAGNI, SOLID, DRY, Separation of Concerns, and 30+ more
3. **Reports violations** with before/after code examples
4. **Groups by severity**: 🔴 Critical | 🟠 Warning | 🟡 Suggestion
5. **Offers automatic fixes** for simple issues

*Based on [deslop](https://github.com/Theta-Tech-AI/llm-public-utils/blob/production/slash_commands/deslop.md) by Theta Tech AI.*

## Requirements

- **Git** for version control operations
- **GitHub CLI (`gh`)** for PR operations
- The respective coding agent installed and configured

## Contributing

1. Fork this repository
2. Add or modify prompts in `prompts/<agent>/`
3. Test with the target agent
4. Submit a pull request

## License

MIT
