# Create PR workflow

Creates a pull request from current git changes with auto-generated title and description.

## Purpose

Automates the PR creation process:
1. Creates a feature branch if on main/master
2. Generates a conventional commit message
3. Creates the PR with descriptive title and body
4. Reports the PR URL

## How it works

```
1. Check current branch
2. If on main/master:
   - Create feature branch with descriptive name
   - Push branch to origin
3. Generate PR title (conventional commit style)
4. Generate PR description with:
   - Summary of changes
   - Files modified
   - Testing notes
5. Create PR via GitHub CLI
6. Report PR URL
```

## Branch naming

The workflow generates branch names based on change content:
- `feat/<description>` for features
- `fix/<description>` for fixes
- `refactor/<description>` for refactoring

## PR title format

Follows conventional commit style:
- `feat: add user authentication`
- `fix: resolve race condition in cache`
- `refactor: extract validation logic`

## PR description structure

```markdown
## Summary
Brief description of changes

## Files changed
- file1.py — what changed
- file2.py — what changed

## Testing
How to verify these changes
```

## Requirements

- Git repository with GitHub remote
- GitHub CLI (`gh`) installed and authenticated
- Uncommitted or unpushed changes

## Usage

### OpenCode
```
/create-pr
```

### Other agents
Available in all 15 agent targets. See [Agent targets](../agent-targets/index.md).

## Safety notes

- Creates branch automatically if on main/master
- Never force-pushes
- Preserves uncommitted changes during branch creation
