---
description: Analyze codebase for refactoring opportunities and prioritize by impact
---

# Refactor

Analyze the codebase for refactoring opportunities and prioritize by impact.

## Guard Rails

Before applying any refactoring:

- **Skip stable code** that won't change again — speculative refactoring has no payoff.
- **Require tests first** on critical paths. Without tests you're editing, not refactoring; flag the area and stop.
- **Preserve behavior exactly** — never mix refactoring with feature or bug-fix changes.
- **One technique per commit** so regressions are bisectable.
- **Don't introduce abstractions** (Strategy, Builder, wrapper types, Result types) unless they remove more code than they add. Three similar lines beats a premature framework.

## Step 1: Identify Scope

Ask the user what area to analyze:
- Specific file or directory
- Entire codebase
- Particular pattern or concern

## Step 2: Analyze Code Quality

Look for:
- **Code duplication**: Similar code blocks that could be extracted
- **Long functions**: Functions over 50 lines
- **Deep nesting**: More than 3 levels of indentation
- **Large files**: Files over 500 lines
- **Complex conditionals**: Multiple nested if/else or switch statements
- **Dead code**: Unused functions, variables, imports

## Step 3: Prioritize Issues

Present findings in a table:
| Priority | Issue | Location | Impact | Effort |

Priority levels:
- 🔴 High: Affects maintainability significantly
- 🟠 Medium: Improvement opportunity
- 🟡 Low: Nice to have

## Step 4: Propose Solutions

For each high-priority issue:
1. Describe the current problem
2. Propose a specific refactoring approach
3. Estimate the impact on codebase

## Step 5: Execute Refactoring

If user approves:
1. Make the changes
2. Run tests to verify
3. Commit with descriptive message

## Notes

- Never break existing functionality
- Run tests after each refactoring step
- Keep commits atomic and focused
- Document any API changes
