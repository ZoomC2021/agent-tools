# Code Review

Review all uncommitted changes in the current repository.

## Workflow

1. **Get uncommitted changes**
   ```bash
   git diff HEAD
   git diff --cached
   git status --short
   ```

2. **Analyze each changed file**
   - Read the full file for context (not just the diff)
   - Understand the purpose of the changes
   - Check imports and dependencies affected

3. **Check for issues**
   - Logic errors or bugs introduced
   - Edge cases not handled
   - Null/undefined access risks
   - Error handling gaps
   - Type safety issues
   - Security vulnerabilities (exposed secrets, injection risks)

4. **Check for regressions**
   - Breaking changes to existing APIs or contracts
   - Removed functionality that may be needed
   - Changed behavior that could affect callers
   - Test coverage for modified code paths

5. **Optimize implementation**
   - Redundant code that can be removed
   - Duplicate logic that should be consolidated
   - Unnecessary complexity that can be simplified
   - Performance issues (N+1 queries, excessive loops, memory leaks)

6. **Verify code quality**
   Run lint and build commands to check for errors.

7. **Fix simple issues**
   If there are only a few issues (≤5) or they are straightforward:
   - Apply the fixes directly without asking
   
   For complex issues requiring design decisions: report and recommend

8. **Report findings**
   Group by severity:
   - 🔴 Critical
   - 🟠 Warning
   - 🟡 Suggestion

   Format:
   ```
   ✅ Fixed: [Category] filename:line
      Was: <description>
      Now: <what was changed>

   🔴/🟠/🟡 [Category] filename:line
      Problem: <description>
      Fix: <recommendation>
   ```

   End with summary: fixed count, remaining issues by severity, overall assessment.
