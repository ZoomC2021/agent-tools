---
name: pr-reviewer
description: Fetch PR review comments, summarize issues by severity, address them, and update the PR
---

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
