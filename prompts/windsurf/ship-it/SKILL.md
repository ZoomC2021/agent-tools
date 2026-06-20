---
name: ship-it
description: Commit current work with meaningful boundaries and push to origin
---

## /ship-it - Commit and push current work

When asked to "ship it" or "commit and push":

1. Inspect diff: `git status --short`, `git diff`, `git diff --cached`
2. Commit focused slices with Conventional Commits; split unrelated changes
3. Push explicitly: check `@{upstream}`; if absent `git push --set-upstream origin HEAD`, else `git push`
4. Report commit(s) created and confirm push completed

Rules: use `gh`/`glab` for forge ops; prefer repo conventions; execute non-interactively; retry on failure.
