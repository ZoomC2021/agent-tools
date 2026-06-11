# Ultrareview workflow

Parallel dual-model code review using GPT 5.5 AND Gemini 3.1 Pro Preview simultaneously.

## Purpose

Ultrareview runs two high-tier models in parallel on the same code changes, then consolidates findings. This catches issues each model might miss and surfaces conflicting interpretations.

## How it works

```
1. Build shared git diff bundle (git diff -U40 HEAD)
2. Launch parallel reviews:
   - Lane A: GPT 5.5 (via OpenCode)
   - Lane B: Gemini 3.1 Pro Preview (via Gemini CLI)
3. Wait for both results (with timeout and retry logic)
4. Consolidate findings:
   - 🔴 Consensus Critical: Issues found by BOTH
   - 🟠 Model Exclusive: Issues found by only one model with high confidence
   - 🟡 Lower Confidence: Medium/low confidence findings
   - ⚠️ Divergent Assessments: Models disagree — human review recommended
5. Never auto-resolves conflicts — both perspectives shown
6. Graceful fallback: If one model fails, return results from the other
```

## Gemini helper

The `opencode-gemini-review` helper script manages the Gemini lane:
- Deterministically builds the shared diff bundle
- Splits large reviews on file boundaries
- Retries failed chunks per file
- Records machine-readable status in `summary.json`

## Consolidation rules

| Finding type | Criteria | Action |
|--------------|----------|--------|
| Consensus Critical | Found by both models | Highest priority, likely real issue |
| Model Exclusive | Found by one model with high confidence | Include with model attribution |
| Lower Confidence | Medium/low confidence | Include for consideration |
| Divergent | Models disagree on severity/nature | Flag for human review |

## Variants

### Ultrareview
Full dual-model with GPT 5.5 + Gemini 3.1 Pro Preview.

### Ultrareview-lite
Lower-cost variant with MiMo v2.5 Pro + Gemini 3 Flash Preview.

## Usage

### OpenCode
```
/ultrareview
```

### Requirements
- Gemini CLI installed and authenticated (`gemini login`)
- Git repository with changes to review

## When to use

Reserve for critical reviews — this uses 2 high-tier models simultaneously.

## Not available for

Gemini CLI, Antigravity, Amp (these agents don't have the orchestration to run parallel reviews).

## Related workflows

- [Review](review.md) — Standard single-model review
- [Deslop](deslop.md) — Principle-based quality audit
