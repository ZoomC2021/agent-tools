# PR reviewer only workflow

Fetch PR review comments and generate implementation prompts without auto-fixing.

## Purpose

The pr-reviewer-only workflow analyzes PR feedback and produces detailed implementation prompts for delegation to other agents:
1. Fetches comments from GitHub PR via GraphQL
2. Identifies human vs bot reviewers
3. Summarizes issues by severity
4. Generates self-contained prompts for implementation agents
5. Leaves the actual fixes to a faster/cheaper agent

## How it works

```
1. Query GitHub for PR comments (GraphQL)
2. Classify reviewers:
   - Human reviewers (priority)
   - Bots (qodo-merge, CodeRabbit, Gemini, Copilot, SonarCloud)
3. Group issues by severity
4. Create temporary worktree to read PR code
5. Read referenced files to extract context
6. Generate detailed implementation prompt
7. Cleanup worktree
8. Output prompt in copyable format
```

## Comment classification

| Source | Priority | Rationale |
|--------|----------|-----------|
| Human reviewers | High | Human judgment on design/context |
| Bot comments | Medium | Automated checks, may have false positives |

## Issue grouping

Issues are categorized for the implementation prompt:

| Priority | Meaning | Examples |
|----------|---------|----------|
| 🔴 Blocking | Changes requested, security | Logic bugs, API breaks |
| 🟠 Suggestions | Improvements | Refactoring, optimization |
| 🟡 Nitpicks | Style, minor | Formatting, naming |
| 💬 Questions | Discussion items | Clarifications needed |

## Output format

The generated prompt includes:
- **Context**: PR number, title, branch name
- **Setup**: Commands to create isolated worktree
- **Issues**: Detailed list with file paths, line numbers, and current code
- **Verification**: Test/typecheck commands to run
- **Commit/Deploy**: How to commit and push changes
- **Cleanup**: How to remove the worktree

## Usage

### OpenCode
```
/pr-reviewer-only
```

## Comparison with pr-reviewer

| Feature | pr-reviewer | pr-reviewer-only |
|---------|-------------|------------------|
| Fetches comments | ✓ | ✓ |
| Summarizes issues | ✓ | ✓ |
| Auto-applies fixes | ✓ | ✗ |
| Generates prompt | ✗ | ✓ |
| Delegates to subagent | ✗ | ✓ |
| Use case | Quick fixes | Complex work, delegation |

## Available in

All 14 agent targets. See [Agent targets](../agent-targets/index.md).

## Requirements

- GitHub CLI (`gh`) authenticated
- Current branch is a PR branch
- Read access to the repository

## Related workflows

- [PR reviewer](pr-reviewer.md) — Fetch and auto-fix PR comments
- [Create PR](create-pr.md) — Create PRs
- [Review](review.md) — Pre-commit review
