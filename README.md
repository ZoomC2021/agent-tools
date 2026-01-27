# Agent Tools

Custom prompts, skills, and workflows for AI coding agents. Provides consistent developer workflows across multiple coding assistants.

## Workflows Included

| Workflow | Description |
|----------|-------------|
| **refactor** | Analyze codebase for refactoring opportunities, prioritize by severity/effort |
| **review** | Review uncommitted changes for bugs, regressions, and improvements |
| **pr-reviewer** | Fetch PR comments, summarize issues, address them, update PR |
| **create-pr** | Create PR with auto-generated title and description |

## Supported Agents

| Agent | Type | Prompt Location |
|-------|------|-----------------|
| [Claude Code](https://claude.ai) | CLI | `~/.claude/commands/` |
| [Codex](https://github.com/openai/codex) | CLI | `~/.codex/skills/` |
| [OpenCode](https://github.com/sst/opencode) | CLI | `~/.config/opencode/prompts/` |
| [Antigravity](https://antigravity.dev) | Editor | `~/.antigravity/prompts/` or `~/Library/.../Antigravity/User/prompts/` |
| [VSCode Copilot](https://github.com/features/copilot) | Editor | `~/.config/Code/User/prompts/` or `~/Library/.../Code/User/prompts/` |
| [Copilot CLI](https://githubnext.com/projects/copilot-cli) | CLI | `~/.copilot/agents/` |
| [Amp](https://ampcode.com) | CLI/Editor | `~/.config/agents/skills/` |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | CLI | `~/.gemini/GEMINI.md` |
| [Kilo Code](https://kilocode.com) | CLI | `~/.kilocode/prompts/` |
| [Cursor](https://cursor.com) | Editor | `~/.cursor/commands/` |
| [Cline](https://cline.bot) | Editor | `~/Documents/Cline/Rules/` |

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

Available options: `claude`, `codex`, `opencode`, `antigravity`, `vscode`, `copilot-cli`, `amp`, `gemini`, `kilocode`, `cursor`, `cline`

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
<summary>OpenCode</summary>

```bash
mkdir -p ~/.config/opencode/prompts
cp prompts/opencode/*.md ~/.config/opencode/prompts/
```
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
<summary>OpenCode</summary>

```bash
mkdir -p ~/.config/opencode/prompts
cp prompts/opencode/*.md ~/.config/opencode/prompts/
```
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
