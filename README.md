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

This repository includes a sophisticated agent architecture for OpenCode using GPT-5.3-Codex as the orchestrator and Fireworks Kimi K2.5 Turbo as specialized subagents.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Codex53-Kimi Orchestrator (GPT-5.3-Codex)                 │
│  • Plans and sequences work                                  │
│  • Makes routing decisions                                    │
│  • Delegates to specialized subagents                       │
└──────────────────────┬────────────────────────────────────────┘
                       │
   ┌───────────┬──────────────┬──────────────────┬──────────────┐
   │           │              │                  │              │
┌──▼────────┐ ┌▼───────────┐ ┌▼────────────────┐ ┌▼────────────┐
│ kimi-     │ │ kimi-      │ │ github-         │ │ docs-       │
│ general   │ │ explore    │ │ librarian       │ │ research    │
│ execution │ │ local find │ │ remote GitHub   │ │ official    │
└───────────┘ └────────────┘ └─────────────────┘ └─────────────┘
   │               │                 │                  │
┌──▼────────┐ ┌────▼─────┐ ┌────────▼──────┐ ┌─────────▼──────┐
│walkthrough│ │ review   │ │ deslop        │ │ pr-reviewer    │
│ diagrams  │ │ local QA │ │ code quality  │ │ PR fixes       │
└───────────┘ └──────────┘ └───────────────┘ └────────────────┘
                            │                  │
                      ┌─────▼─────┐      ┌────▼────┐
                      │ create-pr │      │ oracle  │
                      │ workflow  │      │ deep    │
                      └───────────┘      │ reasoning│
                                         └─────────┘
```

### Deterministic Routing

The orchestrator uses keyword-based deterministic routing:

| Trigger | Keywords | Agent Selected |
|---------|----------|----------------|
| PR creation | "create PR", "pull request" | **create-pr** |
| PR feedback | "PR comment", "address PR" | **pr-reviewer** |
| Code audit | "audit", "code quality" | **deslop** |
| Local review | "review changes", "uncommitted" | **review** |
| Remote repo research | GitHub URL, `owner/repo`, "reference implementation" | **github-librarian** |
| Official docs research | "official docs", "migration guide", "API docs" | **docs-research** |
| Local walkthrough | "walk me through", "diagram", "architecture" | **walkthrough** |
| Local discovery | "find", "search", "explore" | **kimi-explore** |
| Implementation | "implement", "fix", "refactor" | **kimi-general** |

### Orchestrator Safety Gates

Before routing, the orchestrator applies these safety checks (in order):

| Gate | Purpose |
|------|---------|
| **Intent Verbalization** | State routing reasoning out loud so users can catch misroutes before work begins |
| **Turn-Local Intent Reset** | Reclassify intent from the CURRENT message only — never carry "implementation mode" from prior turns |
| **Context-Completion Gate** | Block `spec-compiler` until an explicit implementation verb + concrete scope + no pending research |
| **Consecutive Failure Protocol** | After 2 No-Go results → auto-escalate to Oracle; after 3 → STOP, revert, report to user |

### Mission-Aware Implementation Workflow

For implementation/debugging/refactoring tasks, the orchestrator uses one of two paths:

1. **Standard flow** for small/medium single-milestone work:
   1. **PHASE 0 (optional): docs-research / github-librarian** → Gather official docs or upstream reference code first
   2. **PHASE 1: spec-compiler** → Compile Execution Contract (scope, risks, success criteria)
   3. **PHASE 2: kimi-general** → Execute implementation based on contract
   4. **PHASE 3: quick-validator** → Run validation tests/checks
   5. **PHASE 4 (optional): change-auditor** → Deep audit for high-risk areas

2. **Mission flow** for long-running, multi-step work:
   1. **PHASE 0 (optional): docs-research / github-librarian** → Gather external references first when needed
   2. **PHASE 1: mission-scrutiny** → Front-load scrutiny, decompose into milestones, set validation cadence
   3. **PHASE 2 (loop per milestone): spec-compiler → kimi-general → milestone-validator**
   4. **PHASE 3: quick-validator** → Final end-to-end validation across all milestones
   5. **PHASE 4 (optional): change-auditor** → Deep audit for high-risk milestone or final changes

### Directory Layout

```
~/.config/opencode/
├── opencode.json              # Main configuration (see example)
├── bin/                       # Helper scripts (e.g. opencode-gh-librarian)
├── agent/                     # Primary agent definitions
│   ├── codex53-kimi.md       # Orchestrator (routing logic)
│   ├── kimi-general.md       # Execution worker
│   ├── kimi-explore.md       # Local read-only discovery
│   ├── github-librarian.md   # Remote GitHub research
│   ├── docs-research.md      # Official docs + API research
│   ├── walkthrough.md        # Architecture walkthroughs + diagrams
│   └── oracle.md             # Deep reasoning (GPT-5.4)
└── commands/                  # Workflow prompts
    ├── review.md
    ├── deslop.md
    ├── mission-scrutiny.md
    ├── milestone-validator.md
    ├── pr-reviewer.md
    ├── create-pr.md
    ├── spec-compiler.md
    ├── quick-validator.md
    ├── change-auditor.md
    ├── plan-review.md
    └── refactor.md
```

### Subagent Reference

| Subagent | Purpose | Model | Reasoning Effort |
|----------|---------|-------|------------------|
| **codex53-kimi** | Primary orchestrator (plans, routes, delegates) | GPT-5.3-Codex | High |
| **codex53-kimi-turbo** | Alternative orchestrator using Kimi | Kimi K2.5 Turbo | — |
| **kimi-general** | Implementation, debugging, refactoring execution | Kimi K2.5 Turbo | — |
| **kimi-explore** | Local read-only codebase discovery and search | Kimi K2.5 Turbo | — |
| **github-librarian** | Remote GitHub research (default branches, history) | Kimi K2.5 Turbo | — |
| **docs-research** | Official docs, API behavior, release notes | Kimi K2.5 Turbo | — |
| **walkthrough** | Architecture walkthroughs with Mermaid diagrams | Kimi K2.5 Turbo | — |
| **oracle** | Deep reasoning for complex problems | GPT-5.4 | **High** |
| **spec-compiler** | Compile Execution Contracts before implementation | Kimi K2.5 Turbo | — |
| **plan-review** | Binary validation of Execution Contracts | Kimi K2.5 Turbo | — |
| **quick-validator** | Fast validation of implementation output | Kimi K2.5 Turbo | — |
| **mission-scrutiny** | Front-load scrutiny, milestone planning | GPT-5.3-Codex | — |
| **milestone-validator** | Validate each milestone before advancing | GPT-5.3-Codex | — |
| **change-auditor** | Deep audit for security, breaking changes | GPT-5.3-Codex | **High** |
| **review** | Review uncommitted changes | GPT-5.3-Codex | **High** |
| **deslop** | Code quality audit against principles | Kimi K2.5 Turbo | — |
| **pr-reviewer** | Fetch PR comments and apply fixes | Kimi K2.5 Turbo | — |
| **pr-reviewer-only** | Fetch PR comments, produce implementation prompt | Kimi K2.5 Turbo | — |
| **create-pr** | Create PR with auto-generated title/description | Kimi K2.5 Turbo | — |
| **refactor** | Analyze and prioritize refactoring opportunities | Kimi K2.5 Turbo | — |

### ⚠️ Security Warning

**NEVER commit your `opencode.json` with real API keys to version control.**

- Use environment variables: `OPENCODE_FIREWORKS_API_KEY`
- Or keep the config file in a secure location with `apiKey: "YOUR_KEY_HERE"`
- The example file includes placeholder warnings to help prevent accidental commits

### Reference Example

A local reference setup uses:
- Fireworks Kimi K2.5 Turbo for build mode and subagents
- GPT-5.3-Codex for the orchestrator (plan mode)
- Specialized subagents for local discovery, remote GitHub research, docs research, architecture walkthroughs, and execution

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
mkdir -p ~/.config/opencode/bin

# Copy workflow prompts to commands/
for f in prompts/opencode/review.md prompts/opencode/deslop.md \
         prompts/opencode/mission-scrutiny.md prompts/opencode/milestone-validator.md \
         prompts/opencode/pr-reviewer.md prompts/opencode/create-pr.md \
         prompts/opencode/spec-compiler.md prompts/opencode/quick-validator.md \
         prompts/opencode/change-auditor.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/commands/
done

# Copy agent definitions to agent/
for f in prompts/opencode/codex53-kimi.md prompts/opencode/kimi-general.md \
         prompts/opencode/kimi-explore.md prompts/opencode/github-librarian.md \
         prompts/opencode/docs-research.md prompts/opencode/walkthrough.md \
         prompts/opencode/oracle.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/agent/
done

# Copy helper scripts used by subagents
cp prompts/opencode/bin/* ~/.config/opencode/bin/
chmod +x ~/.config/opencode/bin/*

# Copy and edit config (⚠️ NEVER commit with real API key)
cp prompts/opencode/opencode.json.example ~/.config/opencode/opencode.json
```

**⚠️ Security Warning**: Edit `~/.config/opencode/opencode.json` and replace `YOUR_FIREWORKS_API_KEY_HERE` with your actual API key. **Do not commit this file.**

**Note**: `github-librarian` requires `gh` to be installed and authenticated. `docs-research` works best when `websearch` is available, which OpenCode enables when using the OpenCode provider or when `OPENCODE_ENABLE_EXA=1` is set.

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
mkdir -p ~/.config/opencode/bin

# Copy workflow prompts to commands/
for f in prompts/opencode/review.md prompts/opencode/deslop.md \
         prompts/opencode/mission-scrutiny.md prompts/opencode/milestone-validator.md \
         prompts/opencode/pr-reviewer.md prompts/opencode/create-pr.md \
         prompts/opencode/spec-compiler.md prompts/opencode/quick-validator.md \
         prompts/opencode/change-auditor.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/commands/
done

# Copy agent definitions to agent/
for f in prompts/opencode/codex53-kimi.md prompts/opencode/kimi-general.md \
         prompts/opencode/kimi-explore.md prompts/opencode/github-librarian.md \
         prompts/opencode/docs-research.md prompts/opencode/walkthrough.md \
         prompts/opencode/oracle.md; do
  [ -f "$f" ] && cp "$f" ~/.config/opencode/agent/
done

# Copy helper scripts used by subagents
cp prompts/opencode/bin/* ~/.config/opencode/bin/
chmod +x ~/.config/opencode/bin/*

# Copy and edit config (⚠️ NEVER commit with real API key)
cp prompts/opencode/opencode.json.example ~/.config/opencode/opencode.json
```

**⚠️ Security Warning**: Edit `~/.config/opencode/opencode.json` and replace `YOUR_FIREWORKS_API_KEY_HERE` with your actual API key. **Do not commit this file.**

**Note**: `github-librarian` requires `gh` to be installed and authenticated. `docs-research` works best when `websearch` is available, which OpenCode enables when using the OpenCode provider or when `OPENCODE_ENABLE_EXA=1` is set.

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

1. **Starts with a quick scan**: repo shape, validation commands, and risky generated/public areas
2. **Uses principles selectively**: applies KISS, YAGNI, SOLID, DRY, and related guidance where the evidence supports it
3. **Builds a cleanup ledger**: `Implement now` vs `Needs human review` vs `Defer to refactor`
4. **Implements only high-confidence cleanup** when the user wants changes, not broad redesigns
5. **Verifies results** and reports what changed, what was deferred, and why

*Based on [deslop](https://github.com/Theta-Tech-AI/llm-public-utils/blob/production/slash_commands/deslop.md) by Theta Tech AI.*

## Requirements

- **Git** for version control operations
- **GitHub CLI (`gh`)** for PR operations and `github-librarian`
- **OpenCode `webfetch`** for `docs-research`
- **OpenCode `websearch`** for best `docs-research` discovery results when URLs are not provided
- The respective coding agent installed and configured

## Example OpenCode Prompts

- `In github.com/cli/cli, find where auth token resolution happens`
- `Use official docs to verify how SvelteKit remote functions work before changing our implementation`
- `Walk me through how authentication works in this repo and include a Mermaid diagram`
- `Compare our caching layer with owner/repo's implementation before proposing changes`
- `Show me recent commits affecting src/auth.ts in owner/repo`

## Contributing

1. Fork this repository
2. Add or modify prompts in `prompts/<agent>/`
3. Test with the target agent
4. Submit a pull request

## License

MIT
