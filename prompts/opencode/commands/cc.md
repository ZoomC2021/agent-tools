---
description: Execute Claude CLI commands and code reviews from OpenCode
mode: subagent
model: fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo
---

# CC: Claude CLI Command Execution

Execute **Claude Code CLI** (`claude`) commands and code reviews from within OpenCode.

## Overview

The `cc` command provides access to Claude Code's Agent SDK CLI for:
- **Code review** (via helper script with file-based review)
- **Quick queries** (direct CLI invocation)
- **Structured output** (JSON responses for programmatic use)

### Default Configuration

The helper uses high-quality defaults for thorough analysis:
- **Model**: `opus` (Claude's most capable model)
- **Effort**: `high` (more thorough reasoning)
- **Permissions**: Auto-skipped for non-interactive use

## Prerequisites

- Claude CLI installed (`claude --version` should work)
- Authenticated (`claude auth` or `ANTHROPIC_API_KEY` env var)

## Quick Usage

### Direct Query

```bash
# Ask Claude a quick question
claude -p "Explain what this code does" --bare

# Review code with specific model
claude -p "Review this file for bugs" --model sonnet --bare --allowedTools "Read"
```

### Code Review (via Helper)

For comprehensive code reviews with proper artifact capture:

```bash
REVIEW_TMP_ROOT="${PWD}/.opencode/tmp"
mkdir -p "$REVIEW_TMP_ROOT"
CLAUDE_HELPER="${HOME}/.config/opencode/bin/opencode-claude-review"
CLAUDE_PROMPT="${HOME}/.config/opencode/bin/opencode-claude-review-prompt.txt"
CLAUDE_OUT_DIR="${REVIEW_TMP_ROOT}/claude-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$CLAUDE_OUT_DIR"

"$CLAUDE_HELPER" \
  --repo . \
  --ref HEAD \
  --context-lines 40 \
  --claude-timeout-seconds 180 \
  --max-total-seconds 240 \
  --prompt-file "$CLAUDE_PROMPT" \
  --output-dir "$CLAUDE_OUT_DIR" \
  --verbose 2>&1

CLAUDE_EXIT=$?
CLAUDE_SUMMARY="${CLAUDE_OUT_DIR}/summary.json"
CLAUDE_OUTPUT="${CLAUDE_OUT_DIR}/output.txt"
```

## Phase 1: Gather Context (for Review Mode)

```bash
git diff HEAD
git diff --cached
git status --short
```

### Build Review Bundle

```bash
REVIEW_TMP_ROOT="${PWD}/.opencode/tmp"
mkdir -p "$REVIEW_TMP_ROOT"
git diff -U40 HEAD > "$REVIEW_TMP_ROOT/bundle.diff"
```

## Phase 2: Execute Claude CLI

### Task: Claude Code Review

```
description: Claude CLI review via helper
subagent_type: kimi-general
prompt: |
  TASK: Execute Claude CLI review via helper
  
  TOOLS ALLOWED: Bash, Read
  
  EXECUTION STEPS:
  1. Run the Claude CLI helper:
  
  ```bash
  REVIEW_TMP_ROOT="${PWD}/.opencode/tmp"
  mkdir -p "$REVIEW_TMP_ROOT"
  CLAUDE_HELPER="${HOME}/.config/opencode/bin/opencode-claude-review"
  CLAUDE_PROMPT="${HOME}/.config/opencode/bin/opencode-claude-review-prompt.txt"
  CLAUDE_OUT_DIR="${REVIEW_TMP_ROOT}/claude-$(date +%Y%m%d-%H%M%S)-$$"
  mkdir -p "$CLAUDE_OUT_DIR"
  
  timeout 240 "$CLAUDE_HELPER" \
    --repo . \
    --ref HEAD \
    --context-lines 40 \
    --claude-timeout-seconds 180 \
    --max-total-seconds 240 \
    --prompt-file "$CLAUDE_PROMPT" \
    --output-dir "$CLAUDE_OUT_DIR" \
    --verbose 2>&1 || true
  
  CLAUDE_EXIT=$?
  CLAUDE_SUMMARY="${CLAUDE_OUT_DIR}/summary.json"
  CLAUDE_OUTPUT="${CLAUDE_OUT_DIR}/output.txt"
  ```
  
  2. Read and interpret results:
  - Check summary.json for status and failure_reason
  - Read output.txt for the review findings
  
  3. Return:
     - Exit code from helper
     - summary.json contents
     - output.txt contents (review output)
     - Status: success/failed/timeout
```

## CLI Options Reference

### Mode Flags

| Flag | Description |
|------|-------------|
| `-p, --print` | **Required** for headless/non-interactive mode |
| `--model <model>` | Model to use (default: `opus`) |
| `--effort <level>` | Effort level: `low`, `medium`, `high`, `xhigh`, `max` (default: `high`) |
| `--dangerously-skip-permissions` | **Enabled by default** - bypass all permission checks for non-interactive use |
| `--bare` | Skip auto-discovery (hooks, skills, plugins, MCP) - requires `ANTHROPIC_API_KEY` env var |

### Tool Control

| Flag | Description |
|------|-------------|
| `--allowedTools <list>` | Comma-separated tools to auto-approve (e.g., "Read,Edit,Bash") |
| `--permission-mode <mode>` | Baseline: `acceptEdits`, `dontAsk`, `bypassPermissions` |
| `--tools <list>` | Specify available tools ("" for none, "default" for all) |

### Output Control

| Flag | Description |
|------|-------------|
| `--output-format <fmt>` | `text` (default), `json`, or `stream-json` |
| `--json-schema <schema>` | JSON Schema for structured output validation |

### Context Control

| Flag | Description |
|------|-------------|
| `--system-prompt <prompt>` | Replace default system prompt |
| `--append-system-prompt <prompt>` | Add to default system prompt |
| `--add-dir <dirs>` | Additional directories to allow tool access |

## Common Patterns

### Quick Question

```bash
claude -p "What does this function do?" --bare
```

### File Review

```bash
claude -p "Review auth.py for security issues" --bare --allowedTools "Read"
```

### Structured Output

```bash
claude -p "Extract all function names from main.py" \
  --bare \
  --allowedTools "Read" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"functions":{"type":"array","items":{"type":"string"}}},"required":["functions"]}' \
  | jq '.structured_output'
```

### Continue Conversation

```bash
# First request
claude -p "Start a code review"

# Continue the conversation
claude -p "Now check for security issues" --continue
```

## Error Handling

### Common Failure Reasons

| Reason | Cause | Resolution |
|--------|-------|------------|
| `auth` | Not authenticated | Run `claude auth` or set `ANTHROPIC_API_KEY` |
| `missing_cli` | Claude CLI not found | Install Claude Code |
| `timeout` | Request took too long | Increase timeout or simplify prompt |
| `rate_limited` | API rate limit hit | Wait and retry |
| `command_failed` | Other error | Check stderr for details |

### Exit Codes

The helper returns:
- `0`: Success
- `20`: Failed (see summary.json for failure_reason)
- `21`: Git/setup error

## Security Notes

- **Never** commit API keys
- Use `--bare` in CI/CD to avoid picking up local user config
- Use `--allowedTools` to restrict what Claude can do
- `--permission-mode dontAsk` is safest for automated runs (denies unknown tools)

## Comparison with Other Workflows

| Workflow | Primary Model | Use Case |
|----------|---------------|----------|
| `/review` | Kimi 2.5 Turbo | Standard single-model review |
| `/ultrareview` | GPT 5.4 + Gemini 3.1 Pro | Dual high-tier model review |
| `/ultrareview-lite` | Kimi 2.5 Turbo + Gemini 3 Flash | Cost-effective dual review |
| `/cc` | Claude Sonnet/Opus | Claude-specific analysis or multi-step tasks |

Claude Code excels at:
- Multi-step reasoning tasks
- Tool use (file read/edit, bash commands)
- Longer conversations with context
- Agent-style workflows
