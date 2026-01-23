---
description: Fetch PR comments, summarize issues, address them, commit and update PR
---

# PR Reviewer

Fetch all comments from a GitHub PR, summarize issues, address them, and update the PR.

## Step 1: Get Repository Info

```bash
gh repo view --json owner,name
```

## Step 2: Fetch PR Comments

Ask for the PR number, then fetch all comments using `gh api graphql`.

## Step 3: Identify Reviewer Types

Known bots:
- `qodo-merge-pro[bot]` - Structured suggestions
- `coderabbitai[bot]` - Detailed analysis
- `gemini-code-assist[bot]` - Suggestions
- `copilot[bot]` - Code suggestions
- `sonarcloud[bot]` - Security/bugs

Tag each comment as 🤖 Bot or 👤 Human.

## Step 4: Summarize Issues

Present a table:
| # | File:Line | Reviewer | Type | Issue | Status |

Group by:
- 🔴 Blocking (changes requested, security)
- 🟠 Suggestions (improvements)
- 🟡 Nitpicks (style, minor)
- 💬 Questions/Discussion

## Step 5: Checkout PR Branch

```bash
gh pr checkout {PR_NUMBER}
```

## Step 6: Address Each Issue

- Read referenced files for full context
- Make necessary code changes
- For questions: prepare response comments
- Skip resolved threads

**Bot handling:**
- Evaluate, don't blindly apply
- Security issues: always investigate
- Human feedback takes priority over bot suggestions

## Step 7: Verify Changes

Run type checking and build commands.

## Step 8: Commit and Push

```bash
git add -A
git commit -m "Address PR review feedback"
git push
```

## Step 9: Report Summary

```
✅ Addressed: X issues (Y from bots, Z from humans)
💬 Responded: N comments  
⏭️ Skipped: M (resolved/false positives)
```

## Notes

- Always preserve the original PR author's intent
- If an issue is unclear, ask for clarification instead of guessing
- Human feedback takes priority over bot suggestions when they conflict
- Security issues from any source should always be addressed
