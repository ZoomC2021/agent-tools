# PR reviewer workflow

Fetches PR review comments and addresses them with fixes.

## Purpose

The pr-reviewer workflow automates the process of responding to PR feedback:
1. Fetches comments from GitHub PR via GraphQL
2. Identifies human vs bot reviewers
3. Summarizes issues by severity
4. Addresses feedback with code changes
5. Commits and pushes fixes
6. Updates PR with summary

## How it works

```
1. Query GitHub for PR comments (GraphQL)
2. Classify reviewers:
   - Human reviewers (priority)
   - Bots (secondary)
3. Group issues by severity/file
4. Plan fixes addressing human feedback first
5. Implement fixes
6. Run validation
7. Commit with descriptive message
8. Push to PR branch
9. Update PR with summary of changes
```

## Comment classification

| Source | Priority | Rationale |
|--------|----------|-----------|
| Human reviewers | High | Human judgment on design/context |
| Bot comments (dependabot, etc.) | Medium | Automated checks, may have false positives |

## Fix planning

The workflow creates a plan that:
- Addresses related comments together
- Preserves existing functionality
- Adds tests for fixed bugs
- Updates documentation if API changes

## Usage

### OpenCode
```
/pr-reviewer
```

### Claude Code
Slash command from `~/.claude/commands/pr-reviewer.md`

### Cursor
Type `pr-reviewer` in agent mode

## Available in

All 14 agent targets. See [Agent targets](../agent-targets/index.md).

## Requirements

- GitHub CLI (`gh`) authenticated
- Current branch is a PR branch
- Write access to the repository

## Related workflows

- [Create PR](create-pr.md) — Create PRs
- [Review](review.md) — Pre-commit review
- [PR reviewer only](pr-reviewer-only.md) — Fetch comments and generate implementation prompts without auto-fixing
