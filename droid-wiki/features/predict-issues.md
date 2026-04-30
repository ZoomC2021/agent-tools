# Predict-issues workflow

Proactive issue detection before changes are made.

## Purpose

The predict-issues workflow analyzes planned changes or current context to identify potential issues before they become bugs.

## How it works

```
1. Analyze current codebase context
2. Identify patterns that may cause issues:
   - Common bug patterns for the language/framework
   - Historical issues in similar code
   - Edge cases not yet handled
3. Predict potential problems
4. Suggest preventive measures
```

## Use cases

- Before implementing a feature: "What could go wrong?"
- Reviewing PR descriptions: "Anticipate issues in this approach"
- Planning refactors: "Identify breaking change risks"

## Coverage

Currently available in:
- Claude Code
- Cursor
- Pi

## Usage

### Claude Code
Slash command from `~/.claude/commands/predict-issues.md`

### Cursor
Type `predict-issues` in agent mode

### Pi
Type `predict-issues` in Pi agent mode

## Related workflows

- [Review](review.md) — Post-implementation review
- [Mission scrutiny](mission-scrutiny.md) — Pre-implementation planning
