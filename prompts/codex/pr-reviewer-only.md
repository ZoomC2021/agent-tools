# PR Reviewer (Review Only)

Fetch all comments from a GitHub PR, summarize issues, and generate a detailed implementation prompt for a faster coding agent to resolve them.

## Step 1: Get Repository Info

```bash
gh repo view --json owner,name
```

## Step 2: Fetch PR Comments

Ask the user for the PR number, then fetch all comments:

```bash
gh api graphql -f query='
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      title
      body
      author { login }
      reviews(first: 100) {
        nodes {
          author { login }
          body
          state
          comments(first: 100) {
            nodes {
              body
              path
              line
              author { login }
            }
          }
        }
      }
      comments(first: 100) {
        nodes {
          author { login }
          body
        }
      }
      reviewThreads(first: 100) {
        nodes {
          isResolved
          path
          line
          comments(first: 50) {
            nodes {
              author { login }
              body
            }
          }
        }
      }
    }
  }
}' -F owner='{owner}' -F repo='{repo}' -F pr={PR_NUMBER}
```

## Step 3: Identify Reviewer Types

Known bots to recognize:
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

## Step 5: Read Referenced Files

For each issue, read the referenced file to understand the full context. This is essential for generating accurate implementation instructions.

## Step 6: Generate Implementation Prompt

Output a detailed, self-contained prompt that a less capable coding agent can follow to resolve all issues. The prompt must include:

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

**Problem:** {clear explanation of what's wrong}

**Required change:** {explicit instructions on what to do}

**Expected result:**
```{lang}
{example of correct code if applicable}
```

---

### Issue 2: ...
(repeat for each issue)

## Verification
After making changes, run:
```bash
{type check / build / test commands}
```

## Commit and Push
```bash
git add -A
git commit -m "Address PR review feedback

- <bullet point per issue addressed>"
git push
```

## Cleanup
After pushing, remove the worktree:
```bash
cd ..
git worktree remove pr-{PR_NUMBER}
```
```

## Step 7: Prompt Quality Guidelines

The generated prompt must be:
- **Self-contained**: Agent should not need to search for context
- **Explicit**: No ambiguity about what changes to make
- **Ordered**: Blocking issues first, then suggestions, then nitpicks
- **Verified**: Include exact file paths and line numbers
- **Actionable**: Each issue has clear before/after expectations

**Bot handling in prompt:**
- Include rationale for why bot suggestion should/shouldn't be applied
- Flag security issues prominently
- Note when human feedback contradicts bot suggestions

## Step 8: Output Format

Present the final prompt in a fenced code block so it can be easily copied and passed to another agent.

## Notes

- Always preserve the original PR author's intent
- Skip resolved threads
- Human feedback takes priority over bot suggestions when they conflict
- Security issues from any source should always be included
- If an issue is unclear, include it with a note asking the implementing agent to clarify
