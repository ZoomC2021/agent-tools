# By the numbers

*Data collected on 2026-04-30*

## Repository size

### File count by type

| Type | Count |
|------|-------|
| Markdown files (.md) | ~120 |
| JSON files (.json) | 5 |
| Python files (.py) | 3 |
| Shell scripts (.sh) | 1 |
| PowerShell scripts (.ps1) | 1 |
| YAML files (.yaml) | 10 |
| **Total source files** | **~146** |

### Language breakdown

```mermaid
xychart-beta
    title "Lines of code by language (estimated)"
    x-axis [Markdown, Python, Shell, JSON, YAML]
    y-axis "Files" 0 120
    bar [120, 3, 2, 5, 10]
```

Markdown dominates because the repository is primarily prompt and documentation content.

## Activity

### Recent commits (last 10)

| Commit | Date | Message |
|--------|------|---------|
| afb5d32 | Apr 29 2025 | Add Warp support and predict-issues command |
| 982dcef | Apr 29 2025 | Add Pi agent support with prompt templates and installer integration |
| 887ed9f | Apr 25 2025 | Enhance delegation and review processes for spec-compiler and mission-scrutiny |
| fadc1c1 | Apr 25 2025 | Fix git_output signature to support remaining_seconds keyword arg |
| 772e2db | Apr 25 2025 | Refactor review helpers to eliminate code duplication |
| 18ab8bb | Apr 25 2025 | Add cc command for Claude CLI code review with robust error handling |
| 21efddb | Apr 25 2025 | Add ultrareview-lite command and update documentation |
| 6a49084 | Apr 16 2025 | Harden OpenCode Gemini ultrareview flow |
| 8b477d3 | Apr 16 2025 | Fix opencode remaining PR review follow-ups |
| 82ddfee | Apr 16 2025 | Harden gemini helper and partial reporting |

### Most active areas (last 30 days)

| Directory | Change frequency |
|-----------|------------------|
| `prompts/opencode/` | High — agent definitions and commands |
| `prompts/warp/` | Medium — new agent support |
| `prompts/pi/` | Medium — new agent support |
| `scripts/` | Medium — installer updates |
| `README.md` | High — documentation sync |

## Structure metrics

### Agent targets supported

13 agent platforms: amp, antigravity, claude, cline, codex, copilot-cli, cursor, gemini, kilocode, opencode, pi, warp, windsurf

### Workflow coverage

| Workflow | Agents supporting |
|----------|-------------------|
| review | All 13 agents |
| refactor | All 13 agents |
| create-pr | All 13 agents |
| pr-reviewer | All 13 agents |
| deslop | 13 agents (not Warp) |
| ultrareview | 9 agents |
| handoff | 8 agents |
| predict-issues | 3 agents (claude, cursor, pi) |
