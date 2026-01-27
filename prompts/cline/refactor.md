# Refactoring Agent

Analyze the codebase to identify and prioritize refactoring opportunities.

## Workflow

1. **Gather codebase context**
   ```bash
   # Find frequently modified files (high churn)
   git log --pretty=format: --name-only --since="6 months ago" | sort | uniq -c | sort -rn | head -30
   
   # Find tech debt markers
   grep -rn "TODO\|FIXME\|HACK\|XXX\|REFACTOR" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.jsx" .
   
   # Get file sizes to spot potential god files
   find . -name "*.ts" -o -name "*.tsx" | xargs wc -l | sort -rn | head -20
   ```

2. **Analyze for issue types**

   Scan each significant file for:
   
   | Issue Type | Detection Criteria |
   |------------|-------------------|
   | **Code Duplication** | Similar code blocks across files, copy-paste patterns |
   | **Long Functions** | >50 lines or cyclomatic complexity >10 |
   | **God Classes** | Classes with >10 methods or >300 lines |
   | **Feature Envy** | Methods using other class's data more than their own |
   | **Dead Code** | Unused exports, unreachable branches, commented code |
   | **Deep Nesting** | >3 levels of conditionals/loops |
   | **Primitive Obsession** | Repeated primitive combos (e.g., `lat, lng` instead of `Coordinate`) |
   | **Long Parameter Lists** | Functions with >4 parameters |
   | **Inconsistent Patterns** | Different approaches for same problem across codebase |
   | **Missing Abstractions** | Repeated inline logic that should be extracted |

3. **Assess severity**

   Rate each issue **High / Medium / Low** based on:
   - Git churn (how often the file is modified)
   - Bug risk from current state
   - Impact on readability/maintainability
   - Whether it's in a critical code path

4. **Determine refactoring technique**

   Map issues to specific techniques:
   - Long Function → **Extract Method**
   - God Class → **Extract Class**, **Single Responsibility Split**
   - Duplication → **Extract Function**, **Pull Up Method**, **Template Method**
   - Deep Nesting → **Guard Clauses**, **Extract Method**, **Replace Nested Conditional with Guard Clauses**
   - Feature Envy → **Move Method**, **Move Field**
   - Long Parameter List → **Introduce Parameter Object**, **Builder Pattern**
   - Primitive Obsession → **Replace Primitive with Object**, **Value Object**
   - Conditionals → **Replace Conditional with Polymorphism**, **Strategy Pattern**

5. **Estimate effort**

   | Effort | Time | Examples |
   |--------|------|----------|
   | Small | < 1 hour | Extract single method, add guard clause, remove dead code |
   | Medium | 1-4 hours | Extract class, introduce parameter object, consolidate duplicates |
   | Large | > 4 hours | Major architectural changes, introduce new patterns across codebase |

6. **Calculate priority score**

   ```
   Priority = Severity × (1 / Effort) 
   ```
   
   Where: High=3, Medium=2, Low=1 and Small=1, Medium=2, Large=3

7. **Verify with tooling**
   - Run linting and type checking on flagged files
   - Ensure refactoring won't break existing tests

## Output Format

```
## Refactoring Opportunities (Ranked by Priority)

### 1. 🔴 [Issue Type] `path/to/file.ts:L10-L85`
   **Severity**: High | **Effort**: Small | **Priority Score**: 3.0
   
   **Problem**: <description of the issue> 
   
   **Refactoring**: <specific technique>
   
   **Action**: 
   ```typescript
   // Before (conceptual)
   // After (conceptual)
   ```

### 2. 🟠 [Issue Type] `path/to/file.ts:L120-L180`
   ...
```

## Severity Legend

- 🔴 **High**: Actively causing bugs, blocking progress, or in critical hot path
- 🟠 **Medium**: Technical debt accumulating, moderate maintenance burden  
- 🟡 **Low**: Code smell, minor readability issue, nice-to-have improvement

## Summary Section

End with:
```
## Summary

| Severity | Count | Effort Distribution |
|----------|-------|---------------------|
| 🔴 High  | X     | S: X, M: X, L: X    |
| 🟠 Medium| X     | S: X, M: X, L: X    |
| 🟡 Low   | X     | S: X, M: X, L: X    |

**Quick Wins** (High severity + Small effort): List top 3
**Technical Debt Hotspots**: List files appearing multiple times
**Recommended Sprint Focus**: Top 5 items to tackle first
```

## Execution Mode

When asked to **apply refactorings**:
1. Start with highest priority Small-effort items
2. Make atomic commits per refactoring
3. Run tests after each change
4. Stop if tests fail and report the issue
