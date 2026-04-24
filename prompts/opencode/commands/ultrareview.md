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

## Phase 2: Launch Parallel Reviews

Launch TWO review processes concurrently using different invocation methods:

### Process 1: GPT 5.4 Review (Native OpenCode)

**IMPORTANT**: Use a READ-ONLY review approach. Do NOT use the standard `review` agent as it may auto-fix issues.

Use bash to run GPT 5.4 review directly:

```bash
# Get the diff content
DIFF_CONTENT=$(git diff HEAD)

# Launch GPT 5.4 review via OpenCode with read-only constraints
```

**READ-ONLY EXECUTION PATTERN:**
```
TASK: Perform READ-ONLY code review using GPT 5.4
MODEL OVERRIDE: openai/gpt-5.4
TOOLS ALLOWED: Read, Bash (for git commands only), Grep, Glob
TOOLS FORBIDDEN: Edit, Write (must NOT modify any files)

INPUT PROVIDED:
- Shared ranged-excerpt review bundle from `git diff -U40 HEAD` (primary input)
- List of changed files from `git status --short`
- Read access to modified files for targeted follow-up when a hunk requires cross-reference beyond ±40 lines

EXECUTION STEPS:
1. **Review from the shared bundle first**; read a full file only when a specific hunk needs context outside its ±40-line window
2. **Analyze each file** for:
   - Logic errors, edge cases, null access risks
   - Error handling gaps, type safety issues
   - Security vulnerabilities
   - Regressions (breaking API changes, removed functionality)
   - Optimization opportunities (redundancy, duplication, complexity, performance)
3. **Run lint/build checks** if available (read-only, don't fix)
4. **DO NOT modify any files** - this is analysis only

OUTPUT FORMAT - For each finding include:
- File:line location
- Severity: Critical/Warning/Suggestion (preserve original severity)
- Category: Logic/Security/Performance/Regression/etc
- Description: Clear explanation
- Confidence: High/Medium/Low
- Rationale: Why this is an issue

Report "No issues found" if clean.
```

**⚠️ CRITICAL**: The review agent used here must NOT have Edit/Write permissions. If using `review` agent, verify it's configured as read-only for this task.

### Process 2: Gemini 3.1 Pro Review (Gemini CLI)

**IMPORTANT**: Gemini 3.1 Pro Preview is NOT available via OpenCode's model override. Use the Gemini CLI in non-interactive mode via the OpenCode helper so bundle generation, chunking, retries, and output capture stay deterministic.

#### Step 2a: Run the Helper

Use the helper binary instead of hand-writing Gemini shell pipelines:

```bash
GEMINI_HELPER="${HOME}/.config/opencode/bin/opencode-gemini-review"
GEMINI_PROMPT="${HOME}/.config/opencode/bin/opencode-gemini-review-prompt.txt"
GEMINI_OUT_DIR=$(mktemp -d)

"$GEMINI_HELPER" \
  --repo . \
  --ref HEAD \
  --context-lines 40 \
  --single-call-bytes 51200 \
  --single-call-files 10 \
  --chunk-bytes 51200 \
  --gemini-timeout-seconds 240 \
  --retry-timeout-seconds 180 \
  --model gemini-3.1-pro-preview \
  --prompt-file "$GEMINI_PROMPT" \
  --output-dir "$GEMINI_OUT_DIR"

GEMINI_EXIT=$?
GEMINI_SUMMARY="${GEMINI_OUT_DIR}/summary.json"
GEMINI_OUTPUT="${GEMINI_OUT_DIR}/combined_output.txt"
```

The helper always writes:
- `bundle.diff` - the shared `git diff -U40 HEAD` bundle Gemini reviewed
- `files.txt` - changed files included in the bundle
- `summary.json` - machine-readable status, thresholds, retry results, failed files, and artifact paths
- `combined_output.txt` - merged Gemini findings from the successful full-bundle/chunk/retry runs

#### Step 2b: Interpret Exit Codes and Summary

The helper returns stable exit codes:

| Exit | Meaning | Action |
|------|---------|--------|
| `0` | Full Gemini review succeeded | Use `combined_output.txt` normally |
| `10` | Partial success after chunking/retries | Use successful Gemini output and show warning banner |
| `20` | Gemini review failed | Fallback to GPT 5.4-only result |
| `21` | Usage/setup problem (bad repo/prompt args) | Treat as Gemini failure and report setup issue |

Read the summary before consolidation:

```bash
python - <<'PY' "$GEMINI_SUMMARY"
import json
import pathlib
import sys

summary_path = pathlib.Path(sys.argv[1])
summary = json.loads(summary_path.read_text())
print(f"Gemini status: {summary['status']}")
print(f"Gemini mode: {summary['mode']}")
print(f"Bundle bytes: {summary['bundle']['size_bytes']}")
print(f"Bundle files: {summary['bundle']['file_count']}")
units = summary.get('units', {})
if units:
    print(f"Units: {units.get('successful', 0)}/{units.get('total', 0)} successful")
failed_files = summary.get('files', {}).get('failed', [])
if failed_files:
    print("Failed Gemini files:")
    for file_path in failed_files:
        print(f"- {file_path}")
PY
```

#### Step 2c: Use the Produced Artifacts

- Use `combined_output.txt` as the Gemini findings input for Phase 4.
- Use `summary.json` for partial-success metrics and failed-file reporting.
- If the helper reports `missing_cli`, `auth`, `model_unavailable`, or another failure reason, treat that as a Gemini failure and continue with GPT 5.4 alone.

**CRITICAL SECURITY NOTES:**
- **NEVER** interpolate diff contents into shell arguments.
- The helper feeds Gemini via subprocess stdin only; the diff bundle is written to files for reproducibility, not shell expansion.
- Prompt text is read from a shipped file so the non-interactive Gemini invocation stays consistent across runs.

**REQUIRED CLI OPTIONS (handled by the helper):**
- `--model gemini-3.1-pro-preview`
- `-p/--prompt` with a fixed review prompt file
- stdin input using the generated bundle or chunk files

**NOTE**: The Gemini CLI must still be installed and authenticated separately. If the CLI is unavailable, report this as a Gemini failure and fallback to single-model review.

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

PARTIAL_SUCCESS_COUNT=$(python - <<'PY' "$GEMINI_SUMMARY"
import json, sys
summary = json.load(open(sys.argv[1]))
print(summary.get("units", {}).get("successful", 0))
PY
)

PARTIAL_TOTAL_COUNT=$(python - <<'PY' "$GEMINI_SUMMARY"
import json, sys
summary = json.load(open(sys.argv[1]))
print(summary.get("units", {}).get("total", 0))
PY
)
```

Handle failures gracefully:

- If GPT 5.4 fails → Return Gemini CLI results alone with warning
- If Gemini CLI fails (not installed, auth error, or model error) → Return GPT 5.4 results alone with warning
- If Gemini CLI has **partial success** (some chunks succeeded) → Use successful chunks with warning banner
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
3. Add warning banner: "⚠️ UltraReview degraded to single-model review due to <model> failure"
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

**Warning Banner Format:**
```
⚠️ UltraReview partial: X/Y chunks completed
- Successfully reviewed: <file list or count>
- Failed chunks: <chunk indices or file list>
- Gemini results may be incomplete; GPT 5.4 results are complete
```

**Implementation:**
```bash
python - <<'PY' "$GEMINI_SUMMARY"
import json
import sys

summary = json.load(open(sys.argv[1]))
units = summary.get("units", {})
failed_files = summary.get("files", {}).get("failed", [])
if summary.get("status") == "partial" and units.get("successful", 0) > 0:
    print(f"⚠️ UltraReview partial: {units.get('successful', 0)}/{units.get('total', 0)} units completed")
    print(f"- Successfully reviewed files: {len(summary.get('files', {}).get('successful', []))}")
    if failed_files:
        print("- Failed Gemini files:")
        for file_path in failed_files:
            print(f"  - {file_path}")
    print("- Gemini results incomplete; using available chunks only")
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
