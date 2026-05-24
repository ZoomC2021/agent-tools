# Review workflow

Reviews uncommitted changes for bugs, regressions, and improvements.

## Purpose

The review workflow analyzes git diffs (staged and unstaged) to catch issues before they are committed. It checks for:

- Logic errors and edge cases
- Type safety issues
- Security problems
- Regressions (breaking changes, removed functionality)
- Performance issues
- Code quality (redundancy, duplication)

## How it works

```
1. Gather changes via git diff HEAD and git diff --staged
2. Analyze for issues (categorized by severity)
3. Check for regressions against existing functionality
4. Identify optimization opportunities
5. Report findings with severity (🔴 High | 🟠 Medium | 🟡 Low)
6. Auto-fix simple issues (≤5 straightforward fixes)
```

## Severity classification

| Level | Criteria |
|-------|----------|
| 🔴 High | Logic errors, security issues, breaking changes |
| 🟠 Medium | Edge cases, type issues, performance concerns |
| 🟡 Low | Style, minor redundancy, documentation gaps |

## Usage by agent

### OpenCode
```
/review
```

### Claude Code
Slash command from `~/.claude/commands/review.md`

### Cursor
Type `review` in Cursor agent mode

### Other agents
Available in all 14 supported agent platforms. See [Agent targets](../agent-targets/index.md) for specifics.

## Implementation

The review prompt specifies:
- How to gather diff context
- What categories to check
- How to format findings
- When to auto-fix vs report only

## Related workflows

- [Ultrareview](ultrareview.md) — Dual-model parallel review for critical code
- [Deslop](deslop.md) — Principle-based code quality audit
