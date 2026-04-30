# Refactor workflow

Analyzes codebases for refactoring opportunities and prioritizes them by severity and effort.

## Purpose

The refactor workflow identifies code quality issues and produces an actionable cleanup ledger. It helps teams decide what to fix now vs later.

## How it works

```
1. Quick scan: repo shape, validation commands, risky areas
2. Detect issues:
   - Code duplication
   - Long functions
   - God classes
   - Dead code
   - Deep nesting
   - High-churn files (from git history)
3. Assess severity: 🔴 High | 🟠 Medium | 🟡 Low
4. Calculate priority: Severity × (1/Effort)
5. Report quick wins: High severity + low effort first
```

## Detection criteria

| Issue Type | Detection Method |
|------------|------------------|
| Duplication | Similar code blocks across files |
| Long functions | Line count thresholds |
| God classes | File size + method count |
| Dead code | Unused exports, unreachable branches |
| Deep nesting | Cyclomatic complexity, indentation depth |
| High churn | Git log analysis for frequently modified files |

## Output format

The workflow produces findings grouped by:

1. **Implement now** — High confidence, low risk changes
2. **Needs human review** — Requires context or design decisions
3. **Defer to dedicated session** — Large-scale restructuring

## Guard rails

The refactor prompt includes explicit constraints:
- Do not change test semantics
- Preserve public APIs unless explicitly broken
- Flag but do not auto-fix security-sensitive code
- Stop and ask if change surface exceeds 10 files

## Usage

Available in all 15 agent targets. In OpenCode:

```
/refactor
```

## Related workflows

- [Review](review.md) — Immediate pre-commit review
- [Deslop](deslop.md) — Principle-based quality audit
