---
name: handoff
description: Generate structured handoff context for continuing work in a new session
---

# Handoff Command

Generate a structured handoff context for continuing work in a new session.

## When to Use /handoff

Use the handoff command when:
- Context is getting too long and you want a fresh start
- Approaching the context window limit
- Switching to a different session or agent
- Need to pass work to another team member
- Want to checkpoint complex multi-step work

## Phased Workflow

### Phase 0: Validate Request

Check that meaningful context exists to handoff:
- Verify there is session history, file changes, or active work
- Confirm the workspace has been modified or tasks are in progress
- If no meaningful context exists, report: "No active work context to handoff"

### Phase 1: Gather Context

Collect all relevant information from the current session:

1. **Review session history** - understand the conversation flow and decisions made
2. **Check todos** - identify active, pending, and completed tasks
3. **Git status** - get current branch and uncommitted changes overview
4. **Git diff** - capture specific code changes made
5. **File exploration** - identify key files modified or created

Use tools to gather:
- `git status --short` for file change overview
- `git diff HEAD` for unstaged changes
- `git diff --cached` for staged changes
- File read for todo files or key documents

### Phase 2: Extract Context

Transform gathered information into first-person continuation context:

1. **What we were doing**: Summarize the original goal in 1-2 sentences
2. **What got done**: List completed work with file references
3. **Current state**: Describe exactly where we left off
4. **What's next**: Identify the immediate next step
5. **Blockers**: Note any issues that need resolution
6. **Decisions**: Capture key decisions made and their rationale

Write as if YOU were continuing the work - use first person perspective.

### Phase 3: Format Output

Structure the extracted context into the HANDOFF CONTEXT format:

```
HANDOFF CONTEXT
===============

USER REQUESTS (AS-IS)
---------------------
[Paste the original user request verbatim]

GOAL
----
[One-line summary of the task goal]

WORK COMPLETED
--------------
- [Item 1: description with file path]
- [Item 2: description with file path]
- [...]

CURRENT STATE
-------------
[Detailed description of where we left off, including file contents, test results, or pending operations]

PENDING TASKS
-------------
1. [Next immediate step]
2. [Subsequent step]
3. [...]

KEY FILES (max 10)
------------------
1. `path/to/file1` - [purpose in the current task]
2. `path/to/file2` - [purpose in the current task]
3. [...]

IMPORTANT DECISIONS
-------------------
- [Decision 1]: [rationale]
- [Decision 2]: [rationale]
- [...]

EXPLICIT CONSTRAINTS
--------------------
- [Constraint 1]
- [Constraint 2]
- [...]

CONTEXT FOR CONTINUATION
------------------------
[1-2 paragraph narrative explaining what needs to happen next, written as first-person continuation instructions]
```

### Phase 4: Provide Instructions

After generating the HANDOFF CONTEXT, provide clear continuation instructions:

1. Tell the user to copy the handoff context
2. Instruct them to start a new session
3. Explain how to use the handoff context (paste at start of new session)
4. Remind them to verify workspace state matches the handoff description

## Constraints

- Do NOT create new sessions programmatically
- Handoff is READ-ONLY analysis - do not modify files
- All file paths must be workspace-relative (no absolute paths)
- Never include secrets, API keys, or credentials
- Maximum 10 key files listed
- Keep handoff self-contained and continuation-ready
- Summarize code changes rather than pasting full diffs
