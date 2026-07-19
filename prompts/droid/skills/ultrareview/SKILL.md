---
name: ultrareview
description: Run a dual-model review with Droid-native oracle and Gemini 3.1 Pro subagents.
---

# ultrareview

Run a dual-model review with Droid-native subagents: the GPT-5.6 Sol high-reasoning oracle droid and Gemini 3.1 Pro.

This mirrors the OpenCode UltraReview workflow but **must not** use Gemini CLI helpers or external CLI review processes.

## Models Used

1. `oracle` droid (`model: gpt-5.6-sol`, `reasoningEffort: high`)
2. `gemini-3-1-pro-reviewer` droid (`gemini-3.1-pro-preview`)

## Workflow

### 1) Establish shared review scope

Run:

```bash
git diff HEAD
git diff --cached
git status --short
git diff -U40 HEAD
```

Use these commands to identify the intent, changed paths, risky symbols, and
concise evidence shared by both prompts. Give each droid those pointers and
tell it to inspect the current diff and named files directly through its
read-only tools; do not paste a generated diff or complete files into the
Oracle prompt.

### 2) Launch both reviews in parallel (single response)

Use two `Task` tool calls in the same response:

- `subagent_type: oracle` for GPT-5.6 Sol high-reasoning review
- `subagent_type: gemini-3-1-pro-reviewer` for Gemini 3.1 Pro review

Each prompt should require read-only analysis and this output shape per finding:
- File:line
- Severity (Critical/Warning/Suggestion)
- Category
- Confidence (High/Medium/Low)
- Problem
- Rationale
- Recommended fix

### 3) Consolidate findings

Normalize and compare findings by `file:line:category:description` (fuzzy matching allowed for wording drift).

Report sections:
1. Consensus issues (both models)
2. Oracle-only issues
3. Gemini-only issues
4. Lower-confidence issues
5. Divergent assessments
6. Final summary counts

Preserve each model's original severity; consensus is additional metadata, not a severity override.

### 4) Failure handling

- If one model fails, continue with the other and mark review as degraded.
- If both fail, report failure and suggest `/review`.
- Never hide model disagreement; explicitly mark divergent results.

## Installation Note

If `gemini-3-1-pro-reviewer` is unavailable, install Droid assets from this repo:

```bash
./scripts/install.sh droid
```
