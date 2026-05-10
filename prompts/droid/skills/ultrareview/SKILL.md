# ultrareview

Run a dual-model review with Droid-native subagents: GPT-5.4 high-reasoning and Gemini 3.1 Pro.

This mirrors the OpenCode UltraReview workflow but **must not** use Gemini CLI helpers or external CLI review processes.

## Models Used

1. `oracle` droid (`gpt-5.4`, `reasoningEffort: high`)
2. `gemini-3-1-pro-reviewer` droid (`gemini-3.1-pro-preview`)

## Workflow

### 1) Gather shared review context

Run:

```bash
git diff HEAD
git diff --cached
git status --short
git diff -U40 HEAD
```

Use `git diff -U40 HEAD` as the primary bundle for both models so consensus matching is meaningful.

### 2) Launch both reviews in parallel (single response)

Use two `Task` tool calls in the same response:

- `subagent_type: oracle` for GPT-5.4 high-reasoning review
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
2. GPT-5.4-only issues
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
