---
description: Create a pull request from current git changes with auto-generated title and description
---

# Create PR

Create a pull request from current git changes with an auto-generated title and description.

## Step 1: Check Current State

```bash
git status
git branch --show-current
```

## Step 2: Review Changes

```bash
git diff --stat
git log origin/main..HEAD --oneline
```

## Step 3: Generate PR Title

Create a concise title based on the commits:
- Use conventional commit format if the project uses it
- Keep under 72 characters
- Be specific about what changed

## Step 4: Generate PR Description

Include:
- **Summary**: What this PR does
- **Changes**: Bullet list of key changes
- **Testing**: How it was tested
- **Related**: Link to related issues if any

## Step 5: Create the PR

```bash
gh pr create --title "{title}" --body "{description}"
```

## Step 6: Report

```
✅ PR created: {url}
   Title: {title}
   Base: {base_branch}
   Head: {head_branch}
```

## Notes

- Always ensure the branch is pushed before creating PR
- Use draft PRs for work in progress
- Add reviewers if specified in project conventions
