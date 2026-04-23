---
name: refactor
description: Analyze codebase for refactoring opportunities, prioritize by severity and effort
---

## /refactor - Analyze codebase for refactoring opportunities

When asked to "refactor" or analyze code quality:

1. Gather context with git log (high churn files), grep for TODO/FIXME, find large files
2. Detect: Code duplication, long functions (>50 lines), god classes (>300 lines), dead code, deep nesting, primitive obsession, long parameter lists
3. Assess severity: 🔴 High (bug risk, critical path) | 🟠 Medium (tech debt) | 🟡 Low (code smell)
4. Map to techniques: Extract Method, Extract Class, Guard Clauses, Value Object, Parameter Object
5. Priority = Severity × (1/Effort). Report quick wins first.
