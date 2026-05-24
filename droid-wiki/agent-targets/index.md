# Agent targets

The 14 AI coding agent platforms supported by agent-tools.

## Overview

| Agent | Type | Directory | Format |
|-------|------|-----------|--------|
| [OpenCode](opencode.md) | CLI | `prompts/opencode/` | Markdown + frontmatter |
| [Claude Code](claude.md) | CLI | `prompts/claude/` | Markdown |
| [Codex](codex.md) | CLI | `prompts/codex/` | Markdown |
| [Cursor](cursor.md) | Editor | `prompts/cursor/` | Markdown |
| [Pi](pi.md) | CLI | `prompts/pi/` | Markdown |
| [Warp](warp.md) | CLI/Editor | `prompts/warp/` | YAML |
| [Cline](cline.md) | Editor | `prompts/cline/` | Markdown |
| [Windsurf](windsurf.md) | Editor | `prompts/windsurf/` | SKILL.md |
| [Amp](amp.md) | CLI/Editor | `prompts/amp/` | SKILL.md |
| [Gemini CLI](gemini.md) | CLI | `prompts/gemini/` | SKILL.md |
| [Kilo Code](kilocode.md) | CLI | `prompts/kilocode/` | Markdown |
| [VSCode Copilot](vscode-copilot.md) | Editor | `prompts/vscode-copilot/` | .agent.md |
| [Copilot CLI](copilot-cli.md) | CLI | `prompts/copilot-cli/` | Markdown |
| [Antigravity](antigravity.md) | Editor | `prompts/antigravity/` | Markdown |

## Configuration locations

### macOS

| Agent | Path |
|-------|------|
| OpenCode | `~/.config/opencode/` |
| Claude Code | `~/.claude/commands/` |
| Codex | `~/.codex/skills/` |
| Cursor | `~/.cursor/commands/` |
| Pi | `~/.pi/agent/prompts/` |
| Warp | `~/.warp/workflows/` |
| Windsurf | `~/.codeium/windsurf/skills/` |
| Amp | `~/.config/agents/skills/` |
| VSCode Copilot | `~/Library/Application Support/Code/User/prompts/` |
| Antigravity | `~/Library/Application Support/Antigravity/User/prompts/` |

### Linux

| Agent | Path |
|-------|------|
| OpenCode | `~/.config/opencode/` |
| Claude Code | `~/.claude/commands/` |
| Codex | `~/.codex/skills/` |
| Cursor | `~/.cursor/commands/` |
| Pi | `~/.pi/agent/prompts/` |
| Warp | `${XDG_DATA_HOME:-$HOME/.local/share}/warp-terminal/workflows/` |
| Windsurf | `~/.codeium/windsurf/skills/` |
| Amp | `~/.config/agents/skills/` |
| VSCode Copilot | `~/.config/Code/User/prompts/` |
| Antigravity | `~/.antigravity/prompts/` |

## Workflow coverage by agent

| Workflow | Count |
|----------|-------|
| review | 14/14 |
| refactor | 14/14 |
| create-pr | 14/14 |
| pr-reviewer | 14/14 |
| deslop | 13/14 |
| ultrareview | 9/14 |
| handoff | 8/14 |
| predict-issues | 3/14 |

## Related pages

- [OpenCode](opencode.md) — Primary orchestrator architecture
- [Feature workflows](../features/index.md) — Available commands
