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

**IMPORTANT**: Gemini 3.1 Pro Preview is NOT available via OpenCode's model override. Use the Gemini CLI in non-interactive mode.

#### Step 2a: Diff Size Preflight

Check diff size to determine processing path:

```bash
# Measure the shared ranged-excerpt bundle (same content both models receive)
DIFF_SIZE=$(git diff -U40 HEAD | wc -c)
FILE_COUNT=$(git diff HEAD --name-only | wc -l)
echo "Bundle size: ${DIFF_SIZE} bytes, Files: ${FILE_COUNT}"
```

**Thresholds (measured on the `-U40` bundle, not raw `-U3` diff):**
- Small bundle: ≤50KB AND ≤10 files → Single call path
- Large bundle: >50KB OR >10 files → Chunked path

#### Step 2b: Small Diff Path (Single Call)

For small diffs, use a single Gemini call with explicit timeout:

```bash
# SAFE: Write the shared ranged-excerpt bundle to a temp file first, then cat to gemini
DIFF_FILE=$(mktemp)
git diff -U40 HEAD > "$DIFF_FILE"

# Single call with 240s Gemini timeout, 300s bash timeout
cat "$DIFF_FILE" | timeout 300s gemini --model gemini-3.1-pro-preview -p "Review these code changes. For each issue: file:line, severity (Critical/Warning/Suggestion), category, description, confidence (High/Medium/Low). Report 'No issues found' if clean." --timeout 240000

GEMINI_EXIT=$?
rm "$DIFF_FILE"
```

#### Step 2c: Large Diff Path (Chunked Processing)

For large diffs, split by file boundaries with chunk size limit:

```bash
# Create temp directory for chunks
CHUNK_DIR=$(mktemp -d)
git diff HEAD --name-only > "${CHUNK_DIR}/files.txt"

# Build chunks respecting file boundaries (max 50KB per chunk)
CHUNK_INDEX=0
CURRENT_CHUNK_SIZE=0
CURRENT_CHUNK_FILE="${CHUNK_DIR}/chunk_${CHUNK_INDEX}.diff"
CHUNK_FILES_LIST="${CHUNK_DIR}/chunk_files.txt"
> "$CHUNK_FILES_LIST"

while read -r file; do
    FILE_DIFF=$(git diff -U40 HEAD -- "$file" 2>/dev/null)
    FILE_SIZE=${#FILE_DIFF}

    # If single file exceeds 50KB, it gets its own chunk
    if [[ $FILE_SIZE -gt 51200 ]]; then
        if [[ $CURRENT_CHUNK_SIZE -gt 0 ]]; then
            ((CHUNK_INDEX++))
            CURRENT_CHUNK_FILE="${CHUNK_DIR}/chunk_${CHUNK_INDEX}.diff"
        fi
        echo "$FILE_DIFF" > "$CURRENT_CHUNK_FILE"
        echo "$file" >> "$CHUNK_FILES_LIST"
        ((CHUNK_INDEX++))
        CURRENT_CHUNK_FILE="${CHUNK_DIR}/chunk_${CHUNK_INDEX}.diff"
        CURRENT_CHUNK_SIZE=0
    elif [[ $((CURRENT_CHUNK_SIZE + FILE_SIZE)) -gt 51200 ]]; then
        # Start new chunk
        ((CHUNK_INDEX++))
        CURRENT_CHUNK_FILE="${CHUNK_DIR}/chunk_${CHUNK_INDEX}.diff"
        echo "$FILE_DIFF" > "$CURRENT_CHUNK_FILE"
        echo "$file" >> "$CHUNK_FILES_LIST"
        CURRENT_CHUNK_SIZE=$FILE_SIZE
    else
        # Add to current chunk
        echo "$FILE_DIFF" >> "$CURRENT_CHUNK_FILE"
        echo "$file" >> "$CHUNK_FILES_LIST"
        CURRENT_CHUNK_SIZE=$((CURRENT_CHUNK_SIZE + FILE_SIZE))
    fi
done < "${CHUNK_DIR}/files.txt"

TOTAL_CHUNKS=$((CHUNK_INDEX + 1))
echo "Total chunks created: $TOTAL_CHUNKS"
```

Process each chunk with explicit timeouts:

```bash
# Initialize tracking arrays
CHUNK_RESULTS="${CHUNK_DIR}/results.txt"
> "$CHUNK_RESULTS"
SUCCESS_COUNT=0
FAILED_CHUNKS=""

for i in $(seq 0 $CHUNK_INDEX); do
    CHUNK_FILE="${CHUNK_DIR}/chunk_${i}.diff"
    CHUNK_OUTPUT="${CHUNK_DIR}/chunk_${i}_output.txt"

    if [[ -s "$CHUNK_FILE" ]]; then
        # Process chunk with 240s Gemini timeout, 300s bash timeout
        timeout 300s gemini --model gemini-3.1-pro-preview \
            -p "Review these code changes. For each issue: file:line, severity (Critical/Warning/Suggestion), category, description, confidence (High/Medium/Low). Report 'No issues found' if clean." \
            --timeout 240000 < "$CHUNK_FILE" > "$CHUNK_OUTPUT" 2>&1

        CHUNK_EXIT=$?

        if [[ $CHUNK_EXIT -eq 0 ]] && [[ -s "$CHUNK_OUTPUT" ]]; then
            echo "CHUNK_${i}:SUCCESS" >> "$CHUNK_RESULTS"
            ((SUCCESS_COUNT++))
        else
            echo "CHUNK_${i}:FAILED:exit_${CHUNK_EXIT}" >> "$CHUNK_RESULTS"
            FAILED_CHUNKS="${FAILED_CHUNKS}${i},"
        fi
    fi
done

echo "Chunks successful: $SUCCESS_COUNT/$TOTAL_CHUNKS"
```

#### Step 2d: Retry Failed Chunks (Once)

For any failed chunks, retry once with smaller file sets:

```bash
# Retry logic for failed chunks
if [[ -n "$FAILED_CHUNKS" ]]; then
    echo "Retrying failed chunks..."
    RETRY_FAILED=""

    # Remove trailing comma and iterate
    FAILED_LIST="${FAILED_CHUNKS%,}"

    for chunk_idx in $(echo "$FAILED_LIST" | tr ',' ' '); do
        CHUNK_FILE="${CHUNK_DIR}/chunk_${chunk_idx}.diff"
        CHUNK_OUTPUT="${CHUNK_DIR}/chunk_${chunk_idx}_output.txt"
        CHUNK_RETRY_DIR="${CHUNK_DIR}/retry_${chunk_idx}"
        mkdir -p "$CHUNK_RETRY_DIR"

        # Split failed chunk into individual files for separate processing (preserve ±40-line context)
        grep '^diff --git' "$CHUNK_FILE" | while read -r diff_line; do
            file_path=$(echo "$diff_line" | sed 's|diff --git a/||;s| b/.*||')
            file_diff=$(git diff -U40 HEAD -- "$file_path" 2>/dev/null)
            file_name=$(basename "$file_path")
            echo "$file_diff" > "${CHUNK_RETRY_DIR}/${file_name}.diff"
        done

        # Process each file separately with shorter timeout
        RETRY_SUCCESS=0
        for retry_file in "${CHUNK_RETRY_DIR}"/*.diff; do
            if [[ -f "$retry_file" ]]; then
                retry_output="${retry_file%.diff}.out"
                timeout 240s gemini --model gemini-3.1-pro-preview \
                    -p "Review these code changes. For each issue: file:line, severity (Critical/Warning/Suggestion), category, description, confidence (High/Medium/Low). Report 'No issues found' if clean." \
                    --timeout 180000 < "$retry_file" > "$retry_output" 2>&1

                if [[ $? -eq 0 ]] && [[ -s "$retry_output" ]]; then
                    cat "$retry_output" >> "$CHUNK_OUTPUT"
                    RETRY_SUCCESS=1
                fi
            fi
        done

        if [[ $RETRY_SUCCESS -eq 1 ]]; then
            # Update result to success
            sed -i "s/CHUNK_${chunk_idx}:FAILED.*/CHUNK_${chunk_idx}:SUCCESS/" "$CHUNK_RESULTS"
            ((SUCCESS_COUNT++))
        else
            RETRY_FAILED="${RETRY_FAILED}${chunk_idx},"
        fi
    done

    # Update final failed list
    FAILED_CHUNKS="$RETRY_FAILED"
    echo "Final chunks successful after retry: $SUCCESS_COUNT/$TOTAL_CHUNKS"
fi
```

**CRITICAL SECURITY NOTES:**
- **NEVER** use `echo "$variable"` with untrusted diff content - prevents shell injection
- **ALWAYS** use `cat file | gemini` or file redirection, never variable interpolation
- The temp file approach ensures special characters in diffs are handled safely

**REQUIRED CLI OPTIONS:**
- `-m, --model gemini-3.1-pro-preview` - Use the Gemini 2.5 Pro Preview model
- `-p, --prompt <prompt>` - Run in non-interactive (headless) mode
- Input via stdin from `cat` command (safe file reading)

**NOTE**: The gemini CLI must be installed and authenticated separately. If CLI is unavailable, report this as a Gemini failure and fallback to single-model review.

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
```bash
# Aggregate results from all successful chunks
COMBINED_GEMINI_OUTPUT="${CHUNK_DIR}/combined_gemini_results.txt"
> "$COMBINED_GEMINI_OUTPUT"

if [[ -f "$CHUNK_RESULTS" ]]; then
    while read -r result_line; do
        chunk_idx=$(echo "$result_line" | cut -d: -f1 | sed 's/CHUNK_//')
        status=$(echo "$result_line" | cut -d: -f2)

        if [[ "$status" == "SUCCESS" ]]; then
            chunk_output="${CHUNK_DIR}/chunk_${chunk_idx}_output.txt"
            if [[ -s "$chunk_output" ]]; then
                echo "=== CHUNK $chunk_idx OUTPUT ===" >> "$COMBINED_GEMINI_OUTPUT"
                cat "$chunk_output" >> "$COMBINED_GEMINI_OUTPUT"
                echo "" >> "$COMBINED_GEMINI_OUTPUT"
            fi
        fi
    done < "$CHUNK_RESULTS"
fi

# Store partial success metrics for reporting
PARTIAL_SUCCESS_COUNT=$SUCCESS_COUNT
PARTIAL_TOTAL_COUNT=$TOTAL_CHUNKS
```

Handle failures gracefully:

- If GPT 5.4 fails → Return Gemini CLI results alone with warning
- If Gemini CLI fails (not installed, auth error, or model error) → Return GPT 5.4 results alone with warning
- If Gemini CLI has **partial success** (some chunks succeeded) → Use successful chunks with warning banner
- If both fail → Report failure, suggest using `/review` instead

**Gemini CLI Specific Errors:**
- `gemini: command not found` → CLI not installed, treat as Gemini failure
- Authentication errors → Treat as Gemini failure
- Model not available → Treat as Gemini failure
- Chunk timeout → Mark chunk failed, attempt retry, track for partial success

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
# Display partial success warning if applicable
if [[ -n "$FAILED_CHUNKS" ]] && [[ $PARTIAL_SUCCESS_COUNT -gt 0 ]]; then
    echo "⚠️ UltraReview partial: ${PARTIAL_SUCCESS_COUNT}/${PARTIAL_TOTAL_COUNT} chunks completed"
    echo "- Successfully reviewed files from successful chunks"
    echo "- Failed chunks: ${FAILED_CHUNKS%,}"  # Remove trailing comma
    echo "- Gemini results incomplete; using available chunks only"
fi
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
