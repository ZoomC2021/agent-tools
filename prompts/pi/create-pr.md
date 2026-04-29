# Create PR

Create a pull request from current git changes with an auto-generated title and description.

## Workflow

1. **Check current state**
   ```bash
   git status --short
   git branch --show-current
   ```
   
   Verify:
   - There are changes to commit (staged or unstaged)
   - Not on main/master branch (create feature branch if needed)

2. **If on main/master, create feature branch**
   Generate a descriptive branch name from the changes (e.g., `feat/add-user-auth`, `fix/null-pointer-error`).
   
   ```bash
   git checkout -b <branch-name>
   ```

3. **Stage all changes**
   ```bash
   git add -A
   ```

4. **Analyze changes for commit message**
   ```bash
   git diff --cached --stat
   git diff --cached
   ```
   
   Generate a conventional commit message:
   - Type: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore`
   - Scope: affected component/area (optional)
   - Subject: imperative, lowercase, no period
   - Body: what and why (not how)

5. **Commit and push**
   ```bash
   git commit -m "<type>(<scope>): <subject>"
   git push -u origin HEAD
   ```

6. **Generate PR title and description**
   
   Analyze the commits on this branch vs main:
   ```bash
   git log main..HEAD --oneline
   git diff main..HEAD --stat
   ```
   
   **PR Title**: Clear, concise summary
   
   **PR Description**:
   - Summary (1-2 sentences)
   - Changes (bullet points)
   - Testing notes
   - Related issues

7. **Create the PR**
   ```bash
   gh pr create --title "<title>" --body "<description>"
   ```

8. **Report result**
   ```
   ✅ PR created successfully
   
   Branch: <branch-name>
   PR: <pr-url>
   Title: <title>
   ```

## Notes

- Always run build/lint checks before creating PR if commands are available
- Never force push or modify history on shared branches
- If PR already exists for this branch, report the existing PR URL instead
