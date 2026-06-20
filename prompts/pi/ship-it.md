# Ship It

Commit current work with meaningful commit boundaries and push cleanly.

Invoke with `/ship-it` or when the user says "ship it" or "commit and push".

## Rules

- Use standard git plus the repository forge CLI for review operations: `gh` for GitHub, `glab` for GitLab.
- Inspect the current repo and review request state before choosing commit messages, titles, bodies, or review replies.
- Prefer repository conventions and existing templates when present.
- Create meaningful commit boundaries: split unrelated changes into separate commits and keep each commit focused.
- Use Conventional Commits for all new commits (`type(scope): summary` or `type: summary`; types: feat, fix, chore, docs, refactor, test, perf, build, ci, style).
- Use explicit push logic: check upstream with `git rev-parse --abbrev-ref --symbolic-full-name @{upstream}`; if absent, run `git push --set-upstream origin HEAD`, else run `git push`.
- Execute commands non-interactively and continue until the requested outcome is complete.
- For multi-line review request content, write it to a temp file or heredoc and pass the file to the forge CLI instead of inline multi-line body text.
- If a command fails, resolve the issue and retry rather than stopping early.

## Workflow

1. **Inspect the diff**
   ```bash
   git status --short
   git diff
   git diff --cached
   ```
   Review changes before choosing commit boundaries and messages.

2. **Commit in focused slices**
   Split unrelated changes into separate commits. Stage and commit each slice with a concise imperative Conventional Commit message grounded in the diff:
   ```bash
   git add <paths>
   git commit -m "<type>(<scope>): <subject>"
   ```
   Repeat until all uncommitted changes are committed.

3. **Push explicitly**
   ```bash
   git rev-parse --abbrev-ref --symbolic-full-name @{upstream}
   ```
   If that fails, run `git push --set-upstream origin HEAD`; otherwise run `git push`.

## Done

- The working tree is clean.
- The branch is pushed to origin (with upstream configured if needed).

## Report

Briefly report the commit(s) you created and confirm the push completed.