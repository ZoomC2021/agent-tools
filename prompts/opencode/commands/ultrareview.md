---
description: Run parallel code reviews using GPT 5.4 (OpenCode) AND Gemini 3.1 Pro Preview (Gemini CLI) simultaneously, then consolidate results
mode: subagent
model: fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo
---

# UltraReview: Parallel Dual-Model Code Review

Run simultaneous code reviews using **GPT 5.4** (via OpenCode native) AND **Gemini 3.1 Pro Preview** (via Gemini CLI), then consolidate findings into a unified report.

⚠️ **Cost Warning**: This uses 2 high-tier models simultaneously. Use for critical reviews only.

## Phase 1: Gather Context

Run these commands to understand the uncommitted changes:

```bash
git diff HEAD
git diff --cached
git status --short
```

Capture the complete set of changed files and their contents for both models.

### Phase 1.5: Build the Shared Ranged-Excerpt Review Bundle

Both models should review from the **same** input to make consensus detection in Phase 4 meaningful. The bundle is an extended-context diff (`git diff -U40 HEAD`) that carries each hunk together with ±40 lines of surrounding context, so reviewers see enough code around every change without reading whole files off disk for unchanged modules.

Rules:
- The extended-context diff is the **primary** input for both GPT 5.4 and Gemini 3.1 Pro.
- GPT 5.4 may still read a modified file in full when a specific hunk requires it (e.g. cross-reference with a helper far from the change). Gemini receives only the bundle (chunked per Phase 2c when large).
- Never replace the bundle with hand-edited excerpts; it must be deterministically generated from git so both models see identical content.
- Subsequent phases (size preflight, chunking, retry) operate on this bundle, not on raw `-U3` diffs.

### Phase 1.6: Non-Interactive Path Policy

Use workspace-local temp paths only to avoid permission stalls in non-interactive runs.

```bash
REVIEW_TMP_ROOT="${PWD}/.opencode/tmp"
mkdir -p "$REVIEW_TMP_ROOT"
```

Rules:
- Do NOT read or write `/tmp` or any other external directory.
- Keep temporary review artifacts under `${REVIEW_TMP_ROOT}` only.
- If a command example uses temp files, rewrite it to `${REVIEW_TMP_ROOT}` before execution.

## Phase 2: Launch Parallel Reviews

You can call multiple tools in a single response. When multiple independent pieces of information are requested and all commands are likely to succeed, run multiple tool calls in parallel for optimal performance.

**CRITICAL**: Launch BOTH review tasks in the SAME response for true parallel execution. Do NOT wait for one to complete before starting the other.

### Task 1: GPT 5.4 Review (Read-Only)

Launch this task using the `task` tool:

```
description: GPT 5.4 read-only code review
subagent_type: review
prompt: |
  TASK: Perform READ-ONLY code review using GPT 5.4
  MODEL OVERRIDE: openai/gpt-5.4
  TOOLS ALLOWED: Read, Bash (for git commands only), Grep, Glob
  TOOLS FORBIDDEN: Edit, Write (must NOT modify any files)

  INPUT PROVIDED:
  - Shared ranged-excerpt review bundle from `git diff -U40 HEAD` (primary input)
  - List of changed files from `git status --short`
  - Read access to modified files for targeted follow-up when a hunk requires cross-reference beyond ±40 lines

  EXECUTION STEPS:
  1. Review from the shared bundle first; read a full file only when a specific hunk needs context outside its ±40-line window
  2. Analyze each file for:
     - Logic errors, edge cases, null access risks
     - Error handling gaps, type safety issues
     - Security vulnerabilities
     - Regressions (breaking API changes, removed functionality)
     - Optimization opportunities (redundancy, duplication, complexity, performance)
  3. Run lint/build checks if available (read-only, don't fix)
  4. DO NOT modify any files - this is analysis only
  5. Use workspace-local temp paths only:
     - `REVIEW_TMP_ROOT="${PWD}/.opencode/tmp"`
     - `mkdir -p "$REVIEW_TMP_ROOT"`
     - Never use `/tmp` or other external directories

  OUTPUT FORMAT - For each finding include:
  - File:line location
  - Severity: Critical/Warning/Suggestion (preserve original severity)
  - Category: Logic/Security/Performance/Regression/etc
  - Description: Clear explanation
  - Confidence: High/Medium/Low
  - Rationale: Why this is an issue

  Report "No issues found" if clean.
```

**⚠️ CRITICAL**: The review agent used here must NOT have Edit/Write permissions.

### Task 2: Gemini 3.1 Pro Review (Gemini CLI Helper)

Launch this task using the `task` tool:

```
description: Gemini 3.1 Pro CLI review via helper
subagent_type: kimi-general
prompt: |
  TASK: Execute Gemini 3.1 Pro Preview review via CLI helper
  TOOLS ALLOWED: Bash, Read
  
  EXECUTION STEPS:
  1. Run the Gemini CLI helper to perform the review:
  
  ```bash
  REVIEW_TMP_ROOT="${PWD}/.opencode/tmp"
  mkdir -p "$REVIEW_TMP_ROOT"
  GEMINI_HELPER="${HOME}/.config/opencode/bin/opencode-gemini-review"
  GEMINI_PROMPT="${HOME}/.config/opencode/bin/opencode-gemini-review-prompt.txt"
  GEMINI_OUT_DIR="${REVIEW_TMP_ROOT}/gemini-$(date +%Y%m%d-%H%M%S)-$$"
  mkdir -p "$GEMINI_OUT_DIR"
  
  # Use generous timeouts for file-based review (avoids shell code path extraction issues)
  timeout 180 "$GEMINI_HELPER" \
    --repo . \
    --ref HEAD \
    --context-lines 40 \
    --single-call-bytes 200000 \
    --single-call-files 20 \
    --chunk-bytes 200000 \
    --gemini-timeout-seconds 120 \
    --retry-timeout-seconds 60 \
    --max-total-seconds 180 \
    --model gemini-3.1-pro-preview \
    --prompt-file "$GEMINI_PROMPT" \
    --output-dir "$GEMINI_OUT_DIR" \
    --verbose 2>&1 || true
  
  GEMINI_EXIT=$?
  GEMINI_SUMMARY="${GEMINI_OUT_DIR}/summary.json"
  GEMINI_OUTPUT="${GEMINI_OUT_DIR}/combined_output.txt"
  ```
  
  2. Read and interpret the summary.json to determine success/partial/failure:
  
  The helper returns stable exit codes:
  - Exit 0: Full Gemini review succeeded
  - Exit 10: Partial success after chunking/retries
  - Exit 20: Gemini review failed
  - Exit 21: Usage/setup problem
  
  The helper always writes:
  - `bundle.diff` - the shared `git diff -U40 HEAD` bundle
  - `files.txt` - changed files included in the bundle
  - `summary.json` - machine-readable status, thresholds, retry results, failed files, and artifact paths
  - `combined_output.txt` - merged Gemini findings from successful runs
  
  3. Return the following information:
     - Exit code from the helper
     - Path to summary.json
     - Path to combined_output.txt
     - Summary of Gemini status, mode, and any failure_reason
     - Count of successful vs total units (if chunked)
     - List of failed files (if any)
  
  NOTES:
  - The helper writes bundles to `~/.gemini/tmp/agent-tools/` (Gemini CLI's allowed workspace) 
  - Uses `--yolo --skip-trust` flags for non-interactive approval
  - File-based review prevents shell code path extraction issues that occurred with stdin piping
  - Signal handlers ensure summary.json is written even on interrupt/timeout
  - Use workspace-local temp paths only (`${PWD}/.opencode/tmp`), never `/tmp`
  - If Gemini CLI is unavailable (missing_cli, auth, model_unavailable), report as Gemini failure
```

**IMPORTANT**: Gemini 3.1 Pro Preview is NOT available via OpenCode's model override. The helper binary must be used for deterministic bundle generation, chunking, retries, and output capture.

Windows note:
- The helper is installed as `opencode-gemini-review` (Unix shebang script). On Windows, run this workflow from WSL or Git Bash so `"$GEMINI_HELPER"` executes correctly.

## Phase 3: Wait for Both Results

Wait for completion from both review processes:
- GPT 5.4 review (from OpenCode review agent)
- Gemini 3.1 Pro review (from gemini CLI bash command)

### Partial Success Tracking

Track which chunks succeeded or failed:

| Status | Action |
|--------|--------|
| All chunks success | Proceed with full consolidation |
| Partial success | Use successful chunks, report failures |
| All chunks failed | Treat as Gemini failure, fallback to GPT 5.4 |

**Chunk Result Aggregation:**
The helper already aggregates every successful chunk/retry into `combined_output.txt` and records per-unit status in `summary.json`.

```bash
COMBINED_GEMINI_OUTPUT="$GEMINI_OUTPUT"

read -r PARTIAL_SUCCESS_COUNT PARTIAL_TOTAL_COUNT GEMINI_FAILURE_REASON < <(python - <<'PY' "$GEMINI_SUMMARY"
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    summary = json.load(f)
units = summary.get("units", {})
print(
    units.get("successful", 0),
    units.get("total", 0),
    summary.get("failure_reason") or "none",
)
PY
)
```

Handle failures gracefully:

- If GPT 5.4 fails → Return Gemini CLI results alone with warning
- If Gemini CLI fails (not installed, auth error, or model error) → Return GPT 5.4 results alone with warning
- If Gemini CLI has **partial success** (some chunks succeeded) → Use successful chunks with the standardized partial warning banner
- If both fail → Report failure, suggest using `/review` instead

**Gemini CLI Specific Errors:**
- `missing_cli` → CLI not installed, treat as Gemini failure
- `auth` → authentication/login issue, treat as Gemini failure
- `model_unavailable` → treat as Gemini failure
- `timeout` / `rate_limited` / `command_failed` → use helper summary and fallback rules

## Phase 4: Consolidate Findings

### Step 4.1: Normalize and Categorize

For each finding from both models:
1. Normalize file paths (strip leading ./ if present)
2. Create normalized signature: `file:line:category:description`
3. Match findings between models (fuzzy match on file/line/category)

### Step 4.2: Apply Consolidation Rules (Preserve Original Severity)

**IMPORTANT**: Always preserve the ORIGINAL severity from each model. Consensus status is ADDITIONAL metadata, not a replacement for severity.

| Match Pattern | Consensus Status | Icon | Severity Handling |
|--------------|------------------|------|-------------------|
| BOTH models find same issue | **Consensus** | 🔴 | Keep original severity (Critical/Warning/Suggestion) |
| ONE model finds with HIGH confidence | **Exclusive** | 🟠 | Keep original severity |
| ONE model finds with MEDIUM/LOW confidence | **Exclusive** | 🟡 | Keep original severity |
| CONFLICTING assessments (same location, different verdicts) | **Divergent** | ⚠️ | Show both original severities |

**Consolidation Logic:**
- Consensus = Agreement between models (both found it) → ADDS confidence boost
- Severity = Original classification from finding model → NEVER overwritten
- Example: A "Warning" found by both models becomes "🔴 Consensus Warning" (not "Critical")

### Step 4.3: Build Consolidated Report

Structure the output into sections:

#### Section 1: 🔴 Consensus Issues (Both Models Agree)
Issues found by BOTH models. Original severity preserved - sorted by severity.

Format for each:
```
🔴 [<Original_Severity>] [Category] filename:line
   Consensus: GPT 5.4 + Gemini 3.1 Pro
   Original Severity: <Critical/Warning/Suggestion>
   Problem: <description>
   Fix: <recommendation>
```

#### Section 2: 🟠 GPT 5.4 Exclusive Findings
Issues found ONLY by GPT 5.4. Original severity preserved.

Format for each:
```
🟠 [<Severity>] [Category] filename:line
   Source: GPT 5.4
   Confidence: <High/Medium/Low>
   Original Severity: <Critical/Warning/Suggestion>
   Problem: <description>
   Fix: <recommendation>
```

#### Section 3: 🟠 Gemini 3.1 Pro Exclusive Findings
Issues found ONLY by Gemini 3.1 Pro Preview. Original severity preserved.

Format for each:
```
🟠 [<Severity>] [Category] filename:line
   Source: Gemini 3.1 Pro
   Confidence: <High/Medium/Low>
   Original Severity: <Critical/Warning/Suggestion>
   Problem: <description>
   Fix: <recommendation>
```

#### Section 4: 🟡 Lower Confidence Findings
Issues from either model with medium/low confidence. Original severity preserved.

Format for each:
```
🟡 [<Severity>] [Category] filename:line
   Source: <Model> (<confidence> confidence)
   Original Severity: <Critical/Warning/Suggestion>
   Problem: <description>
   Consider: <lightweight recommendation>
```

#### Section 5: ⚠️ Divergent Assessments
Same code location, but models disagree on severity or existence of issue.

Format for each:
```
⚠️ filename:line
   GPT 5.4: <assessment>
   Gemini 3.1 Pro: <assessment>
   Human Review Recommended: The models disagree significantly.
```

#### Section 6: Summary

```
## UltraReview Summary
- Consensus Critical: <count>
- GPT 5.4 Exclusive: <count>
- Gemini 3.1 Pro Exclusive: <count>
- Lower Confidence: <count>
- Divergent Assessments: <count>
- Total Models Used: <2 or note if fallback>
- Execution: GPT 5.4 (OpenCode native) + Gemini 3.1 Pro (CLI)
- Cost Level: High (2 premium models)

Recommendation: <prioritized next steps>
```

## Phase 5: Output Final Report

Present the consolidated report with:
1. All sections in order above
2. Clear model attribution for every finding
3. No auto-resolution of conflicts - always show both perspectives
4. Actionable recommendations
5. Summary statistics

## Error Handling

### Single Model Failure
If one review process fails during Phase 2:
1. Log the failure (including CLI errors for Gemini)
2. Continue with the successful model's results
3. Add warning banner: "⚠️ UltraReview degraded to single-model review due to <model> failure (reason: <failure_reason>)"
4. Present remaining results with full consolidation format (but only one source)

**Common Gemini CLI Failures:**
- CLI not installed: Suggest `npm install -g @google/gemini-cli`
- Not authenticated: Suggest `gemini login`
- Model unavailable: Report as temporary failure

### Partial Success Fallback (Chunked Gemini Review)
When Gemini CLI uses chunked processing, some chunks may succeed while others fail:

1. **Track Results**: Store `$PARTIAL_SUCCESS_COUNT` and `$PARTIAL_TOTAL_COUNT` from Phase 3
2. **Use Successful Chunks**: Even if some chunks failed, use results from successful chunks
3. **Warning Banner**: Display partial completion status
4. **Report Failed Chunks**: List which files/chunks could not be reviewed

**Warning Banner Format (use exactly this shape):**
```
⚠️ UltraReview partial (Gemini): X/Y units completed
- Failure reason: <summary.failure_reason or partial_results>
- Successfully reviewed files: <count>
- Failed Gemini files: <file list or "none">
- Consolidation uses available Gemini results plus full GPT 5.4 results
```

**Implementation:**
```bash
python - <<'PY' "$GEMINI_SUMMARY"
import json
import sys

summary = json.load(open(sys.argv[1]))
units = summary.get("units", {})
failed_files = summary.get("files", {}).get("failed", [])
failure_reason = summary.get("failure_reason") or "partial_results"
if summary.get("status") == "partial" and units.get("successful", 0) > 0:
    print(f"⚠️ UltraReview partial (Gemini): {units.get('successful', 0)}/{units.get('total', 0)} units completed")
    print(f"- Failure reason: {failure_reason}")
    print(f"- Successfully reviewed files: {len(summary.get('files', {}).get('successful', []))}")
    if failed_files:
        print("- Failed Gemini files:")
        for file_path in failed_files:
            print(f"  - {file_path}")
    else:
        print('- Failed Gemini files: none')
    print("- Consolidation uses available Gemini results plus full GPT 5.4 results")
PY
```

**Phase 4 Compatibility:**
- Consolidation rules remain unchanged
- Successful chunk results feed into Gemini findings normally
- Missing chunks result in fewer Gemini-exclusive findings
- Consensus detection works with available data only

### Both Models Failure
If both review processes fail:
1. Report: "UltraReview failed: Both GPT 5.4 (OpenCode) and Gemini 3.1 Pro (CLI) unavailable"
2. Suggest: "Use `/review` for single-model review with GPT 5.3-Codex"
3. Provide any partial results that were captured (including successful chunk outputs)
4. Include specific error for Gemini CLI if applicable

## Divergence Resolution Policy

**NEVER auto-resolve conflicts between models.** When models disagree:
- Report both assessments with full attribution
- Add "Human Review Recommended" label
- Let the user decide which assessment is correct

This is intentional - conflicting model outputs often indicate subtle issues worth human attention.
