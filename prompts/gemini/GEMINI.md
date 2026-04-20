# Custom Workflows

## /refactor - Analyze codebase for refactoring opportunities

When asked to "refactor" or analyze code quality:

1. Gather context with git log (high churn files), grep for TODO/FIXME, find large files
2. Detect: Code duplication, long functions (>50 lines), god classes (>300 lines), dead code, deep nesting, primitive obsession, long parameter lists
3. Assess severity: 🔴 High (bug risk, critical path) | 🟠 Medium (tech debt) | 🟡 Low (code smell)
4. Map to techniques: Extract Method, Extract Class, Guard Clauses, Value Object, Parameter Object
5. Priority = Severity × (1/Effort). Report quick wins first.

## /review - Review uncommitted changes

When asked to "review" changes:

1. Run `git diff HEAD`, `git diff --cached`, `git status --short`
2. Read full files for context, not just diffs
3. Check for: logic errors, edge cases, null risks, error handling, type safety, security issues
4. Check for regressions: breaking API changes, removed functionality
5. Find optimization opportunities: redundant code, duplicate logic, performance issues
6. Fix simple issues (≤5) directly; report complex issues
7. Group findings: 🔴 Critical | 🟠 Warning | 🟡 Suggestion

## /pr-reviewer - Address PR review feedback

When asked to review PR feedback:

1. Get repo info: `gh repo view --json owner,name`
2. Fetch PR comments via `gh api graphql`
3. Identify bots vs humans (qodo-merge-pro, coderabbitai, copilot, sonarcloud)
4. Summarize issues in table: File:Line | Reviewer | Type | Issue | Status
5. Group: 🔴 Blocking | 🟠 Suggestions | 🟡 Nitpicks | 💬 Questions
6. Checkout PR: `gh pr checkout {PR_NUMBER}`
7. Address issues (human feedback > bot suggestions, always investigate security)
8. Verify, commit, push
9. Report: ✅ Addressed: X | 💬 Responded: N | ⏭️ Skipped: M

## /create-pr - Create PR from current changes

When asked to "create pr" or "make a pr":

1. Check state: `git status --short`, `git branch --show-current`
2. If on main/master, create feature branch with descriptive name
3. Stage all: `git add -A`
4. Generate conventional commit: `<type>(<scope>): <subject>`
5. Push: `git push -u origin HEAD`
6. Generate PR title and description with Summary, Changes, Testing, Related Issues
7. Create: `gh pr create --title "<title>" --body "<description>"`
8. Report: Branch, PR URL, Title, Commits, Files changed

## /deslop - Analyze code for quality issues

When asked to "deslop" or analyze code quality:

1. Treat `deslop` as a safe cleanup workflow, not a general refactor command
2. Do a quick scan first: repo shape, language/tooling, likely validation commands, and risky generated/vendor/public API areas
3. Read the relevant target files, then apply only the engineering principles that match the issues you actually find
4. Inspect cleanup findings across these lanes:
   - duplication / DRY with clear ownership
   - weak types or shared type cleanup
   - unused code, exports, or dependencies
   - circular dependencies or boundary tangles
   - error handling that hides failures
   - deprecated, legacy, or fallback leftovers
   - AI slop, stubs, stale comments, placeholder code
   - local complexity, cognitive load, or naming problems
5. Produce an evidence-backed report for each finding with:
   - principle(s) involved
   - location in code (`file:line`)
   - evidence and why it matters
   - smallest behavior-preserving fix
   - risk: `Low`, `Medium`, or `High`
   - status: `Implement now`, `Needs human review`, or `Defer to refactor`
6. Include before/after code only when it clarifies a non-obvious or high-value change
7. If the user asked for cleanup, implement only the high-confidence `Implement now` items and run the narrowest relevant validation first
8. If the user asked only for an audit, stop after the report and clearly separate deferred refactor work from safe cleanup
