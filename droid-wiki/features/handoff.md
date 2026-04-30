# Handoff workflow

Generates context for continuing work in a new session.

## Purpose

The handoff workflow captures current state, pending tasks, and important context so work can continue seamlessly in a new conversation session.

## How it works

```
1. Gather current state:
   - Branch name and commit
   - Files modified (staged/unstaged)
   - TODO/FIXME comments in changed files
2. Identify pending tasks from context
3. Capture key decisions and rationale
4. Format handoff document with:
   - Current status
   - Next steps
   - Blockers or questions
   - Relevant file paths
```

## Output format

```markdown
## Handoff Context

**Branch:** feature/my-branch
**Commit:** abc1234

### Current Status
What was completed in this session

### Next Steps
1. Task to continue
2. Another pending task

### Files Modified
- src/file1.py
- src/file2.py

### Notes
Important context for continuation
```

## Usage

### OpenCode
```
/handoff
```

### Other agents
Available in 8 agent targets.

## When to use

- Long-running tasks spanning multiple sessions
- Before switching contexts
- End of day handoff to next-day session
- Sharing work state with another developer

## Permissions

The handoff agent has restricted permissions (read-only, no write/edit) to safely capture state without side effects.

## Related

- [Mission scrutiny](mission-scrutiny.md) — For complex multi-step tasks
- [Oracle](../opencode/oracle.md) — Deep reasoning for complex problems
