---
name: create-pr
description: Create a PR from current changes with auto-generated title and description
---

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
