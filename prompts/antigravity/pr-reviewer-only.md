---
description: Fetch PR comments, summarize issues, and generate implementation prompt for another agent
---

# PR Reviewer (Review Only)

Fetch all comments from a GitHub PR, summarize issues, and generate a detailed implementation prompt for a faster coding agent to resolve them.

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

## Step 5: Create Worktree to Read PR Code

Create a temporary worktree to access the PR's current code:

```bash
PR_BRANCH=$(gh pr view {PR_NUMBER} --json headRefName -q .headRefName)
git worktree add ../pr-{PR_NUMBER}-review "$PR_BRANCH"
cd ../pr-{PR_NUMBER}-review
```

## Step 6: Read Referenced Files

For each issue, read the referenced file from the worktree to understand the full context. Extract the relevant code snippets to include in the implementation prompt.

## Step 7: Cleanup Review Worktree

After reading all files, remove the temporary worktree:

```bash
cd -
git worktree remove ../pr-{PR_NUMBER}-review
```

## Step 8: Generate Implementation Prompt

Output a detailed, self-contained prompt for another agent:

```markdown
# PR Review Implementation Task

## Context
- PR #{number}: {title}
- Branch: {branch_name}

## Setup
Create an isolated worktree for this PR (allows parallel work on multiple PRs):
```bash
# Get the PR branch name
PR_BRANCH=$(gh pr view {PR_NUMBER} --json headRefName -q .headRefName)

# Create worktree in sibling directory
git worktree add ../pr-{PR_NUMBER} "$PR_BRANCH"

# Change to the worktree directory
cd ../pr-{PR_NUMBER}
```

**Working directory:** `../pr-{PR_NUMBER}`

## Issues to Address

### Issue 1: {short description}
**File:** `{path}` (line {line})
**Priority:** {🔴/🟠/🟡}
**Requested by:** {reviewer} ({human/bot})

**Current code:**
```{lang}
{relevant code snippet}
```

**Problem:** {clear explanation}

**Required change:** {explicit instructions}

**Expected result:**
```{lang}
{example of correct code}
```

---

(repeat for each issue)

## Verification
```bash
{type check / build / test commands}
```

## Commit and Push
```bash
git add -A
git commit -m "Address PR review feedback"
git push
```

## Cleanup
After pushing, remove the worktree:
```bash
cd ..
git worktree remove pr-{PR_NUMBER}
```
```

## Step 9: Prompt Quality Guidelines

The prompt must be:
- **Self-contained**: No searching for context
- **Explicit**: No ambiguity
- **Ordered**: Blocking issues first
- **Verified**: Exact file paths and lines
- **Actionable**: Clear before/after expectations

## Step 10: Output Format

Present the final prompt in a fenced code block for easy copying.

## Notes

- Always preserve the original PR author's intent
- Skip resolved threads
- Human feedback takes priority over bot suggestions
- Security issues should always be included
