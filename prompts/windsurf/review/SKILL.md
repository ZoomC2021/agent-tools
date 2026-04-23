---
name: review
description: Review uncommitted changes for bugs, regressions, and improvements
---

## /review - Review uncommitted changes

When asked to "review" changes:

1. Run `git diff HEAD`, `git diff --cached`, `git status --short`
2. Read full files for context, not just diffs
3. Check for: logic errors, edge cases, null risks, error handling, type safety, security issues
4. Check for regressions: breaking API changes, removed functionality
5. Find optimization opportunities: redundant code, duplicate logic, performance issues
6. Fix simple issues (≤5) directly; report complex issues
7. Group findings: 🔴 Critical | 🟠 Warning | 🟡 Suggestion
