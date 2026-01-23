---
description: Create a pull request from current git changes with auto-generated title and description
---

# Create PR

Create a pull request from current git changes with an auto-generated title and description.

## Step 1: Check Current State

```bash
git status --short
git branch --show-current
```

## Step 2: Create Feature Branch (if on main/master)

Generate descriptive branch name from changes (e.g., `feat/add-user-auth`).
```bash
git checkout -b <branch-name>
```

## Step 3: Stage and Commit

```bash
git add -A
git diff --cached --stat
```

Generate conventional commit: `<type>(<scope>): <subject>`
Types: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore`

## Step 4: Push Branch

```bash
git push -u origin HEAD
```

## Step 5: Generate PR Title and Description

```bash
git log main..HEAD --oneline
git diff main..HEAD --stat
```

PR Description:
- Summary (1-2 sentences)
- Changes (bullet points)
- Testing notes
- Related issues

## Step 6: Create the PR

```bash
gh pr create --title "<title>" --body "<description>"
```

## Step 7: Report Result

```
✅ PR created successfully
Branch: <branch-name>
PR: <pr-url>
```

## Notes

- Run build/lint checks before creating PR
- Never force push on shared branches
- If PR exists for branch, report existing URL
