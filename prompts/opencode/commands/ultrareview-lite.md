---
description: Run parallel code reviews using Kimi 2.5 Turbo (OpenCode) AND Gemini 3 Flash Preview (Gemini CLI), then consolidate results
mode: subagent
model: fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo
---

# UltraReview Lite: Parallel Kimi + Gemini Flash Code Review

Run simultaneous code reviews using **Kimi 2.5 Turbo** (via OpenCode native) AND **Gemini 3 Flash Preview** (via Gemini CLI), then consolidate findings into a unified report.

Compared with `/ultrareview`, this variant reduces cost by replacing the GPT 5.4 lane with Kimi 2.5 Turbo.

## Phase 1: Gather Context

Run these commands to understand the uncommitted changes:

```bash
git diff HEAD
git diff --cached
git status --short
```

Capture the complete set of changed files and their contents for both models.

### Phase 1.5: Build the Shared Ranged-Excerpt Review Bundle

Both models should review from the **same** input to keep consensus detection meaningful. The bundle is an extended-context diff (`git diff -U40 HEAD`) carrying each hunk with +/-40 lines of context.

Rules:
- The extended-context diff is the **primary** input for both Kimi and Gemini Flash.
- Kimi may still read a modified file in full when a hunk needs extra context.
- Gemini receives only the bundle (via file reference, not stdin).
- Never replace the bundle with hand-edited excerpts.

### Phase 1.6: Non-Interactive Path Policy

Use workspace-local temp paths for review artifacts:

```bash
REVIEW_TMP_ROOT="${PWD}/.opencode/tmp"
mkdir -p "$REVIEW_TMP_ROOT"
```

Rules:
- Do NOT read or write `/tmp` or any other external directory.
- Keep temporary review artifacts under `${REVIEW_TMP_ROOT}` only.
- Note: The Gemini CLI helper writes bundles to `~/.gemini/tmp/agent-tools/` (its allowed workspace) instead of piping via stdin.

## Phase 2: Launch Reviews

### Task 1: Kimi 2.5 Turbo Review (Primary - Always Run)

This is the **primary** review. Gemini CLI is attempted in parallel but may timeout.

Launch this task using the `task` tool:

```
description: Kimi 2.5 Turbo read-only code review
subagent_type: review
prompt: |
  TASK: Perform READ-ONLY code review using Kimi 2.5 Turbo
  MODEL OVERRIDE: fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo
  TOOLS ALLOWED: Read, Bash (for git commands only), Grep, Glob
  TOOLS FORBIDDEN: Edit, Write

  INPUT PROVIDED:
  - Shared ranged-excerpt review bundle from `git diff -U40 HEAD`
  - List of changed files from `git status --short`

  EXECUTION STEPS:
  1. Review from the shared bundle first; read full files only when needed
  2. Analyze for logic bugs, edge cases, regressions, security, and performance issues
  3. Run lint/build checks if available (read-only, no fixes)
  4. Do not modify files
  5. Use workspace-local temp paths only:
     - `REVIEW_TMP_ROOT="${PWD}/.opencode/tmp"`
     - `mkdir -p "$REVIEW_TMP_ROOT"`
     - Never use `/tmp` or other external directories

  OUTPUT FORMAT:
  - File:line location
  - Severity: Critical/Warning/Suggestion
  - Category
  - Description
  - Confidence: High/Medium/Low
  - Rationale

  Report "No issues found" if clean.
```

### Task 2: Gemini 3 Flash Preview Review (Opportunistic - May Timeout)

**Note**: The Gemini CLI helper now uses file-based review (writes bundle to `~/.gemini/tmp/agent-tools/` and references it in the prompt). This avoids shell code path extraction issues that occurred with stdin piping.

Launch this task using the `task` tool:

```
description: Gemini 3 Flash CLI review via helper (opportunistic)
subagent_type: kimi-general
prompt: |
  TASK: Execute Gemini 3 Flash Preview review via CLI helper
  
  TOOLS ALLOWED: Bash, Read
  
  EXECUTION STEPS:
  1. Run the Gemini CLI helper:
  
  ```bash
  REVIEW_TMP_ROOT="${PWD}/.opencode/tmp"
  mkdir -p "$REVIEW_TMP_ROOT"
  GEMINI_HELPER="${HOME}/.config/opencode/bin/opencode-gemini-review"
  GEMINI_PROMPT="${HOME}/.config/opencode/bin/opencode-gemini-review-prompt.txt"
  GEMINI_OUT_DIR="${REVIEW_TMP_ROOT}/gemini-$(date +%Y%m%d-%H%M%S)-$$"
  mkdir -p "$GEMINI_OUT_DIR"
  
  # Use generous timeouts - file-based review takes longer but produces cleaner results
  timeout 150 "$GEMINI_HELPER" \
    --repo . \
    --ref HEAD \
    --context-lines 40 \
    --single-call-bytes 200000 \
    --single-call-files 20 \
    --chunk-bytes 200000 \
    --gemini-timeout-seconds 120 \
    --retry-timeout-seconds 60 \
    --max-total-seconds 150 \
    --model gemini-3-flash-preview \
    --prompt-file "$GEMINI_PROMPT" \
    --output-dir "$GEMINI_OUT_DIR" \
    --verbose 2>&1 || true
  
  GEMINI_EXIT=$?
  GEMINI_SUMMARY="${GEMINI_OUT_DIR}/summary.json"
  GEMINI_OUTPUT="${GEMINI_OUT_DIR}/combined_output.txt"
  ```
  
  2. Check results:
  - If summary.json exists and status="success", Gemini review succeeded
  - If timeout or failure_reason="timeout", Gemini took too long but may have partial results
  - If failure_reason="missing_cli|auth|model_unavailable", Gemini CLI is not properly configured
  
  3. Return:
     - Exit code from helper
     - summary.json contents (status, failure_reason, units)
     - combined_output.txt contents (if exists)
     - Whether Gemini succeeded, partially succeeded, or failed
```

**Implementation Notes**:
- The helper writes bundles to `~/.gemini/tmp/agent-tools/` (Gemini CLI's allowed workspace)
- Uses `--yolo --skip-trust` flags for non-interactive approval
- The prompt references the bundle file path instead of piping via stdin
- This prevents the model from misinterpreting shell code in diffs as file paths
- Signal handlers ensure summary.json is written even on interrupt

## Phase 3: Consolidate Results

### Expected Outcomes

| Scenario | Kimi Result | Gemini Result | Action |
|----------|-------------|---------------|--------|
| Ideal | Success | Success | Full dual-model consolidation |
| Typical | Success | Timeout | Kimi-only report with note about Gemini timeout |
| Degraded | Success | Fail | Kimi-only report with Gemini failure reason |

### Processing Gemini Results

```bash
if [ -f "$GEMINI_SUMMARY" ]; then
  GEMINI_STATUS=$(python3 -c "import json; print(json.load(open('$GEMINI_SUMMARY')).get('status', 'unknown'))")
  GEMINI_REASON=$(python3 -c "import json; print(json.load(open('$GEMINI_SUMMARY')).get('failure_reason', 'none'))")
  
  if [ "$GEMINI_STATUS" = "success" ]; then
    echo "✅ Gemini review succeeded"
  elif [ "$GEMINI_STATUS" = "partial" ]; then
    echo "⚠️ Gemini partial success ($GEMINI_REASON)"
  else
    echo "⚠️ Gemini failed ($GEMINI_REASON)"
  fi
else
  echo "⚠️ No Gemini output"
fi
```

### Consolidation Rules

| Match Pattern | Consensus Status | Icon |
|--------------|------------------|------|
| Both models find same issue | Consensus | 🔴 |
| One model finds with high confidence | Exclusive | 🟠 |
| Lower confidence | Exclusive | 🟡 |
| Conflicting assessments | Divergent | ⚠️ |

## Phase 4: Output Final Report

### Standard Header

```
## UltraReview Lite Summary
- Kimi 2.5 Turbo: <status>
- Gemini 3 Flash: <status> (<failure_reason if not success>)
- Consensus Critical: <count>
- Kimi Exclusive: <count>
- Gemini Exclusive: <count>
- Total Models Used: <1 or 2>
- Execution: Kimi 2.5 Turbo (OpenCode) + Gemini 3 Flash Preview (CLI)
- Cost Level: Medium (Kimi + optional Gemini Flash)
```

### Gemini Failure Banner (when Gemini fails/times out)

```
⚠️ Gemini 3 Flash CLI timeout or failure
- Status: <status>
- Reason: <failure_reason>
- Review based on Kimi 2.5 Turbo results
```

### Report Structure

1. **Kimi 2.5 Turbo Findings** (always present)
2. **Gemini 3 Flash Findings** (if available and successful)
3. **Consensus Issues** (if both models succeeded)
4. **Divergent Assessments** (if any)
5. **Summary** with model availability notes

## Error Handling

### Gemini CLI Common Outcomes

| Outcome | Status | Meaning |
|---------|--------|---------|
| success | success | Full review completed with findings |
| partial | partial | Some chunks/files succeeded, others failed |
| timeout | failed | Review took longer than timeout limit |
| missing_cli | failed | Gemini CLI not installed |
| auth | failed | Not authenticated (`gemini login` required) |
| model_unavailable | failed | gemini-3-flash-preview not accessible |

### Fallback Strategy

1. **Always complete Kimi review first** - this is the reliable path
2. **Attempt Gemini in parallel** with generous timeouts (120s)
3. **Expect occasional timeouts** - file-based review is thorough but slower
4. **Consolidate with Kimi as primary** - don't fail if Gemini times out

### Both Models Unavailable

If even Kimi fails:
1. Report: `UltraReview Lite failed: Unable to complete code review`
2. Suggest: `Use /review for standard single-model review`
3. Check: Git repository status, network connectivity, model availability

## Divergence Resolution Policy

**Never auto-resolve model conflicts.** When both models report and disagree:
1. Show both assessments
2. Mark as `⚠️ Divergent` 
3. Note: "Human review recommended - models disagree"
