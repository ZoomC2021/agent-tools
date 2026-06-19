# Data models reference

Data structures and formats used in agent-tools.

## Execution contracts

Execution contracts are structured specifications created before implementation work begins. They define the scope, approach, and validation criteria for a task.

### Structure

```markdown
# Execution Contract: <task name>

## Scope
- **Included**: What will be delivered
- **Excluded**: What will not be delivered

## Approach
- **Pattern**: Architecture/design pattern to follow
- **Key decisions**: Major technical choices

## Implementation plan
1. Step one
2. Step two
3. ...

## Validation criteria
- [ ] Criterion one
- [ ] Criterion two
```

### Purpose

Execution contracts serve as:
- **Alignment tool** — Ensures understanding before work begins
- **Scope control** — Prevents scope creep with explicit exclusions
- **Quality gate** — Defines done criteria upfront

### Creation

Created by the `spec-compiler` subagent:
```
/spec-compiler
```

## File chunk format

Used in the Gemini review helper for bundling files:

```python
{
    "path": "relative/path/to/file.py",
    "diff_bytes": b"...",      # Raw diff content
    "size_bytes": 1234          # Size for chunking decisions
}
```

## Chunk grouping

The Gemini review helper groups files into chunks:

```python
chunk = {
    "files": ["a.py", "b.py"],  # File paths in this chunk
    "size_bytes": 45            # Total size for API limits
}
```

## Failure classification

Gemini CLI errors are classified for retry logic:

| Reason | Trigger |
|--------|---------|
| `auth` | "Please run gemini login first" |
| `model_unavailable` | "Model is unavailable for this account" |
| `rate_limited` | "quota exceeded / rate limit hit" |
| `missing_cli` | "gemini: command not found" |
| `timeout` | Exit code 124 (timeout signal) |
| `command_failed` | Any other non-zero exit |

## Date parsing formats

The `utils.parse_date()` function supports:

| Format | Example |
|--------|---------|
| `%Y-%m-%d` | `2024-03-15` |
| `%Y/%m/%d` | `2024/03/15` |
| `%d-%m-%Y` | `15-03-2024` |
| `%d/%m/%Y` | `15/03/2024` |

## Prompt frontmatter

OpenCode prompts use YAML frontmatter:

```yaml
---
description: Brief description of what this command does
mode: subagent
model: model-id
permission:
  task:
    '*': deny
    allowed_task: allow
---
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | Human-readable purpose |
| `mode` | No | `subagent` for hidden agents |
| `model` | No | Override default model |
| `permission` | No | Task and tool permissions |

## Skill format (Windsurf/Amp/Gemini)

```markdown
---
name: workflow-name
description: What this workflow does
---

# Workflow title

Content...
```

## See also

- [Configuration](configuration.md) — OpenCode config structure
- [Dependencies](dependencies.md) — Required tools
