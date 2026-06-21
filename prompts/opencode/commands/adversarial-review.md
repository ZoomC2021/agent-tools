---
description: Spawn fresh subagents to adversarially review changes, verify findings, and fix valid issues.
mode: subagent
model: openai/gpt-5.5
reasoningEffort: high
---

# Adversarial Review

Use independent subagents to review current changes, then evaluate and fix only verified findings.

## Workflow

1. Inspect the change set:

```bash
git status --short
git diff --cached
git diff HEAD
git diff -U40 HEAD
```

2. Build a shared review brief containing the task goal, `git status --short`, and the unified diff. Mention any known pre-existing unrelated changes so reviewers do not ask to revert them.

3. Spawn at least two fresh subagents in parallel. Keep them read-only. Ask each reviewer to:
   - Review only the current diff, while reading full files for context.
   - Look for correctness bugs, regressions, security or secret issues, race conditions, error-handling gaps, and missing tests.
   - Output findings with `severity | category | file:line | issue | rationale | confidence | suggested fix`.
   - Return `NO_ISSUES` if clean.

4. Consolidate findings. Treat agreement as stronger evidence, but do not accept any finding blindly.

5. Verify every finding against the live repo before editing:
   - Re-read the relevant file and surrounding code.
   - Check whether the issue is introduced by this change or pre-existing.
   - Confirm tests, types, schemas, docs, or runtime behavior where relevant.
   - Mark each item `valid`, `invalid`, `duplicate`, `pre-existing`, or `needs human decision`.

6. Fix valid issues directly when the fix is clear and scoped. Do not fix invalid, speculative, or unrelated findings. Do not revert user changes outside the task.

7. Run the smallest relevant validation for the fixed surface. If tests cannot run, state why.

8. If fixes changed behavior, run one more adversarial review pass over the updated diff unless the change was trivial.

## Report

End with:

- Reviewers run and whether any were unavailable.
- Findings accepted and fixed.
- Findings rejected, with short evidence.
- Validation commands and results.
- Remaining risks or human decisions.
