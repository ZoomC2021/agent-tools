# Deslop workflow

Code quality audit using established software engineering principles.

## Purpose

Deslop (named after the open-source utility) analyzes code for violations of core software engineering principles:

- **KISS** — Keep It Simple, Stupid
- **YAGNI** — You Aren't Gonna Need It
- **SOLID** — Object-oriented design principles
- **DRY** — Don't Repeat Yourself

## How it works

```
1. Quick scan: repo shape, validation commands, risky areas
2. Selective principle application: applies principles where evidence supports
3. Build cleanup ledger:
   - Implement now
   - Needs human review
   - Defer to refactor
4. Implement high-confidence cleanup only
5. Verify results
6. Report what changed, what was deferred, and why
```

## Analysis approach

Unlike generic linters, deslop:
- Applies principles contextually (not every file needs SOLID)
- Prioritizes by severity × effort
- Separates "implement now" from "needs design decision"
- Never proposes broad redesigns for minor issues

## Output categories

| Category | Action |
|----------|--------|
| Implement now | High confidence, low risk changes |
| Needs human review | Requires context or design input |
| Defer to refactor session | Large-scale restructuring |

## Guard rails

- Does not change test semantics
- Preserves public APIs
- Flags security-sensitive code for human review
- Stops if change surface exceeds threshold

## Usage

### OpenCode
```
/deslop
```

### Other agents
Available in 14 agent targets (all except Warp). See [Agent targets](../agent-targets/index.md).

## Origin

Based on [deslop](https://github.com/Theta-Tech-AI/llm-public-utils/blob/production/slash_commands/deslop.md) by Theta Tech AI, adapted for multi-agent use.

## Related workflows

- [Refactor](refactor.md) — Detection and prioritization
- [Review](review.md) — Immediate pre-commit check
