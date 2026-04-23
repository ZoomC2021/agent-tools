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
- Complete git diff output from `git diff HEAD`
- List of changed files from `git status --short`
- Full file contents of modified files (read for context)

EXECUTION STEPS:
1. **Read all modified files** for full context (not just diff hunks)
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

Use bash to invoke the gemini CLI with SAFE file handling:

```bash
# SAFE: Write diff to temp file first, then cat to gemini
DIFF_FILE=$(mktemp)
git diff HEAD > "$DIFF_FILE"
cat "$DIFF_FILE" | gemini --model gemini-2.5-pro-preview-05-06 -p "Review these code changes. For each issue: file:line, severity (Critical/Warning/Suggestion), category, description, confidence (High/Medium/Low). Report 'No issues found' if clean."
rm "$DIFF_FILE"
```

**CRITICAL SECURITY NOTES:**
- **NEVER** use `echo "$variable"` with untrusted diff content - prevents shell injection
- **ALWAYS** use `cat file | gemini` or file redirection, never variable interpolation
- The temp file approach ensures special characters in diffs are handled safely

**REQUIRED CLI OPTIONS:**
- `-m, --model gemini-2.5-pro-preview-05-06` - Use the Gemini 2.5 Pro Preview model
- `-p, --prompt <prompt>` - Run in non-interactive (headless) mode
- Input via stdin from `cat` command (safe file reading)

**NOTE**: The gemini CLI must be installed and authenticated separately. If CLI is unavailable, report this as a Gemini failure and fallback to single-model review.

## Phase 3: Wait for Both Results

Wait for completion from both review processes:
- GPT 5.4 review (from OpenCode review agent)
- Gemini 3.1 Pro review (from gemini CLI bash command)

Handle failures gracefully:

- If GPT 5.4 fails → Return Gemini CLI results alone with warning
- If Gemini CLI fails (not installed, auth error, or model error) → Return GPT 5.4 results alone with warning
- If both fail → Report failure, suggest using `/review` instead

**Gemini CLI Specific Errors:**
- `gemini: command not found` → CLI not installed, treat as Gemini failure
- Authentication errors → Treat as Gemini failure
- Model not available → Treat as Gemini failure

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

### Both Models Failure
If both review processes fail:
1. Report: "UltraReview failed: Both GPT 5.4 (OpenCode) and Gemini 3.1 Pro (CLI) unavailable"
2. Suggest: "Use `/review` for single-model review with GPT 5.3-Codex"
3. Provide any partial results that were captured
4. Include specific error for Gemini CLI if applicable

## Divergence Resolution Policy

**NEVER auto-resolve conflicts between models.** When models disagree:
- Report both assessments with full attribution
- Add "Human Review Recommended" label
- Let the user decide which assessment is correct

This is intentional - conflicting model outputs often indicate subtle issues worth human attention.
