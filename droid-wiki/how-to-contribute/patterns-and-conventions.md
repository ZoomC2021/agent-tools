# Patterns and conventions

Coding and documentation style for the agent-tools repository.

## Prompt structure

### Markdown prompts with frontmatter

Most agents use YAML frontmatter:

```markdown
---
description: Short description of what this prompt does
mode: subagent
model: fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo
permission:
  task:
    '*': deny
    read: allow
---

# Prompt title

Content...
```

### SKILL.md format

Windsurf, Amp, and Gemini CLI use SKILL.md files:

```markdown
# Skill Name

## Metadata

- **Name**: skill-name
- **Model**: kimi-k2p5-turbo

## Description

What this skill does...

## Instructions

The actual prompt content...
```

## Writing style for prompts

- **Concise and deterministic** — Avoid vague instructions
- **No contradictory guidance** across agents
- **Complete workflows** — Prompts should specify full steps, not partial
- **Safety gates** — Include checkpoints before destructive actions

## Code style

### Python (`utils.py`)

- Type hints for function signatures
- Docstrings with Args/Returns/Raises/Examples
- Raise specific exceptions with helpful messages

Example:

```python
def parse_date(value: Optional[str], default: Optional[date] = None) -> Optional[date]:
    """Parse a date string using multiple common formats.

    Supported formats:
        - %Y-%m-%d (e.g., "2024-03-15")
        ...

    Args:
        value: The date string to parse, or None/empty string.
        default: The value to return if input is None or empty.

    Returns:
        A date object if parsing succeeds, or the default value.

    Raises:
        ValueError: If the string cannot be parsed with any supported format.
    """
```

### Shell scripts (`install.sh`)

- Use functions for each agent install
- Log with color-coded messages (info, success, warn, error)
- Support nullglob for empty directories
- Handle both macOS and Linux paths

## Deterministic routing pattern

The OpenCode orchestrator uses keyword-based routing:

```markdown
| Trigger | Keywords | Agent Selected |
|---------|----------|----------------|
| PR creation | "create PR", "pull request" | **create-pr** |
| PR feedback | "PR comment", "address PR" | **pr-reviewer** |
```

This pattern ensures the same input always routes to the same agent.

## Safety gate patterns

### Intent verbalization

```markdown
Before following any routing rule, identify what the user actually wants
and state your reasoning out loud.
```

### Context-completion gate

```markdown
You may invoke spec-compiler only when ALL of these are true:
1. Explicit implementation verb present
2. Scope is concrete enough
3. No pending research results
```

### Consecutive failure protocol

```markdown
After 2 No-Go results → auto-escalate to Oracle
After 3 No-Go results → STOP, revert, report to user
```

## File organization

- One workflow per file for clarity
- Related workflows grouped in same directory
- Agent-specific adaptations in dedicated subdirectories

## Configuration patterns

The `opencode.json.example` uses `{file:./path/to/file.md}` references:

```json
{
  "prompt": "{file:./agent/codex53-kimi.md}",
  "permission": {
    "task": {
      "*": "deny",
      "kimi-general": "allow"
    }
  }
}
```

These resolve at runtime to the actual file contents.
