# Cleanup opportunities

Code quality issues and technical debt tracking for the agent-tools repository.

## Summary

The agent-tools codebase is well-maintained with minimal accumulated technical debt. The repository follows proactive cleanup practices:

- **No active TODO/FIXME markers** in production code
- **Regular refactoring** via built-in workflows (deslop, refactor)
- **Prompt-driven quality** — AGENTS.md explicitly discourages leaving TODOs in prompts

## TODO/FIXME archaeology

A comprehensive grep of the codebase found **0 actionable TODO or FIXME comments** in:

- Source code (`utils.py`)
- Test files (`tests/`)
- Shell scripts (`scripts/`)
- Installer logic

All TODO/FIXME references found were in:
- Documentation explaining how to find and handle TODOs in other codebases
- Prompt files that instruct agents to grep for TODOs during refactoring

## What the prompts say about TODOs

The deslop and refactor workflows across all 15 agent targets include TODO detection as a standard practice:

| Workflow | Action |
|----------|--------|
| **deslop** | Flag "TODO graveyards" (old TODOs with dates) |
| **refactor** | Grep for `TODO\|FIXME\|HACK\|XXX\|REFACTOR` |

Guidance to agents:
- Create tickets for legitimate TODOs
- Delete stale TODOs that will never be addressed
- Treat TODO graveyards as code smell

## Current state

```
Codebase health: ✓ HEALTHY

Metrics:
- Active TODOs in source: 0
- FIXME markers: 0
- HACK comments: 0
- Stale dated TODOs: 0
```

## Maintenance practices

The codebase stays clean through:

1. **Built-in quality workflows** — deslop, refactor, and ultrareview run regularly
2. **Prompt hygiene** — No TODOs left in prompts (AGENTS.md guideline)
3. **Single-purpose commits** — Changes are focused and complete
4. **Immediate resolution** — Issues addressed rather than deferred

## See also

- [Deslop workflow](../features/deslop.md) — Code quality audit
- [Refactor workflow](../features/refactor.md) — Refactoring prioritization
- [Patterns and conventions](../how-to-contribute/patterns-and-conventions.md)
