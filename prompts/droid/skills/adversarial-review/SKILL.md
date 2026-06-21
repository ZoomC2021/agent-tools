---
name: adversarial-review
description: Spawn fresh subagents to adversarially review uncommitted changes, validate their findings against the repo, and fix confirmed issues.
---

# Adversarial Review

Use independent subagents to review current changes, then evaluate and fix only verified findings.

## Workflow

1. Inspect `git status --short`, `git diff --cached`, `git diff HEAD`, and `git diff -U40 HEAD`.
2. Build a shared review brief with the task goal, status output, and unified diff. Identify unrelated pre-existing changes.
3. Spawn at least two fresh read-only droids in parallel, such as `oracle` and `gemini-3-1-pro-reviewer` when available.
4. Ask each droid to review only the diff, read full files for context, and report `severity | category | file:line | issue | rationale | confidence | suggested fix`, or `NO_ISSUES`.
5. Consolidate findings. Agreement increases confidence, but every finding still needs verification.
6. Verify each finding against live code and tests before editing. Mark it `valid`, `invalid`, `duplicate`, `pre-existing`, or `needs human decision`.
7. Fix valid issues directly when the fix is clear and scoped. Do not fix speculative or unrelated findings.
8. Run the smallest relevant validation. If fixes changed behavior, run one more adversarial review pass unless the change was trivial.

Report reviewers run, findings fixed, findings rejected with evidence, validation, and remaining risks.
