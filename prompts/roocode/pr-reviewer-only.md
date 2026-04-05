# PR Reviewer (Summary Only)

Fetch all comments from a GitHub PR and summarize issues without making changes.

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

## Step 5: Generate Implementation Prompt

Output a structured prompt that can be given to another agent to implement the fixes:

```markdown
## PR Review Implementation Task

**PR #<number>**: <title>

### Issues to Address

#### 🔴 Blocking
1. **<file>:<line>** - <issue description>
   - Requested by: <reviewer>
   - Action: <specific fix required>

#### 🟠 Suggestions
1. **<file>:<line>** - <issue description>
   - Requested by: <reviewer>
   - Action: <specific fix required>

#### 🟡 Nitpicks
1. **<file>:<line>** - <issue description>
   - Requested by: <reviewer>
   - Action: <specific fix required>

### Implementation Notes
- <any context needed for implementation>
- Human feedback takes priority over bot suggestions
- Security issues must always be addressed

### After Implementation
1. Run tests and linting
2. Commit with message: "Address PR review feedback"
3. Push changes
```

## Notes

- Do NOT make any code changes
- Do NOT commit or push anything
- Only analyze and summarize the feedback
- Output should be copy-paste ready for another agent
