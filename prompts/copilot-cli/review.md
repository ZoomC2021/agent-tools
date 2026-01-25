---
description: Review uncommitted changes for issues, regressions, and optimization opportunities
---

# Review

Review uncommitted changes for issues, regressions, and optimization opportunities.

## Step 1: Get Changes

```bash
git diff
git diff --cached
```

## Step 2: Analyze Changes

Review for:
- **Bugs**: Logic errors, off-by-one, null checks
- **Security**: Exposed secrets, injection vulnerabilities, auth issues
- **Performance**: N+1 queries, unnecessary loops, memory leaks
- **Style**: Naming, formatting, code organization
- **Tests**: Missing test coverage for new code

## Step 3: Present Findings

| # | File:Line | Severity | Issue | Suggestion |

Severity levels:
- 🔴 Critical: Must fix before commit
- 🟠 Warning: Should address
- 🟡 Note: Consider improving

## Step 4: Recommendations

Provide:
- Specific line-by-line feedback
- Suggested fixes for critical issues
- Questions about unclear code

## Notes

- Focus on substantive issues over style nitpicks
- Consider the context of the change
- Suggest improvements, don't just criticize
- Check for missing error handling
