---
name: ultrareview
description: Run parallel dual-model code review using Claude and Gemini 3.1 Pro Preview simultaneously, then consolidate findings
---

# UltraReview: Parallel Dual-Model Code Review

Run simultaneous code reviews using **GPT 5.4** AND **Gemini 3.1 Pro Preview** (via Gemini CLI), then consolidate findings into a unified report.

⚠️ **Cost Warning**: This uses 2 high-tier models simultaneously. Use for critical reviews only.

## Overview

This workflow performs parallel code reviews using two different AI models:
1. **GPT 5.4** - Primary model for reasoning-heavy analysis (Windsurf uses Claude)
2. **Gemini 3.1 Pro Preview** - Secondary model for pattern recognition (via Gemini CLI)

The results are consolidated to catch issues each model might miss and surface conflicting interpretations.

## Prerequisites

- **Gemini CLI** must be installed: `npm install -g @google/gemini-cli`
- **Gemini CLI** must be authenticated: `gemini login`

## Phase 1: Gather Context

Run these commands to understand the uncommitted changes:

```bash
git diff HEAD
git diff --cached
git status --short
```

Capture the complete set of changed files and their contents.

## Phase 2: Launch Parallel Reviews

Launch TWO review processes concurrently:

### Process 1: Claude Review (Windsurf)

**READ-ONLY REVIEW - Do NOT modify files during review**

Review all uncommitted changes:
1. Read full files for context (not just diff hunks)
2. Check for: logic errors, edge cases, null access risks, error handling gaps, type safety, security vulnerabilities
3. Check for regressions: breaking API changes, removed functionality
4. Find optimization opportunities: redundancy, duplication, complexity, performance
5. Run lint/build checks if available

**DO NOT apply fixes during this phase.** This is analysis only.

### Process 2: Gemini 3.1 Pro Review (Gemini CLI)

Run in Windsurf terminal:

```bash
# Write diff to temp file (safe method, no shell injection risk)
DIFF_FILE=$(mktemp)
git diff HEAD > "$DIFF_FILE"
cat "$DIFF_FILE" | gemini --model gemini-3.1-pro-preview -p "Review these code changes. For each issue found, provide: file:line location, severity (Critical/Warning/Suggestion), category (Logic/Security/Performance/etc), clear description, and confidence level (High/Medium/Low). Format clearly. Report 'No issues found' if clean."
rm "$DIFF_FILE"
```

## Phase 3: Wait for Both Results

Collect findings from both reviews:
- Claude findings (from Windsurf)
- Gemini 3.1 Pro findings (from CLI output)

Handle failures gracefully:
- If Claude review fails → Use Gemini results alone
- If Gemini CLI fails → Use Claude results alone
- If both fail → Report failure, suggest using standard `/review` instead

## Phase 4: Consolidate Findings

### Step 4.1: Normalize and Categorize

For each finding from both models:
1. Normalize file paths (strip leading ./ if present)
2. Create normalized signature: `file:line:category:description`
3. Match findings between models (fuzzy match on file/line/category)

### Step 4.2: Apply Consolidation Rules (Preserve Original Severity)

**IMPORTANT**: Always preserve the ORIGINAL severity from each model. Consensus status is ADDITIONAL metadata, not a replacement.

| Match Pattern | Consensus Status | Icon | Severity Handling |
|--------------|------------------|------|-------------------|
| BOTH models find same issue | **Consensus** | 🔴 | Keep original severity |
| ONE model finds with HIGH confidence | **Exclusive** | 🟠 | Keep original severity |
| ONE model finds with MEDIUM/LOW confidence | **Exclusive** | 🟡 | Keep original severity |
| CONFLICTING assessments | **Divergent** | ⚠️ | Show both original severities |

### Step 4.3: Build Consolidated Report

#### Section 1: 🔴 Consensus Issues (Both Models Agree)
Issues found by BOTH models. Original severity preserved.

Format:
```
🔴 [<Original_Severity>] [Category] filename:line
   Consensus: Claude + Gemini 3.1 Pro
   Original Severity: <Critical/Warning/Suggestion>
   Problem: <description>
   Fix: <recommendation>
```

#### Section 2: 🟠 Claude Exclusive Findings
Issues found ONLY by Claude.

Format:
```
🟠 [<Severity>] [Category] filename:line
   Source: Claude
   Confidence: <High/Medium/Low>
   Problem: <description>
   Fix: <recommendation>
```

#### Section 3: 🟠 Gemini 3.1 Pro Exclusive Findings
Issues found ONLY by Gemini 3.1 Pro.

Format:
```
🟠 [<Severity>] [Category] filename:line
   Source: Gemini 3.1 Pro
   Confidence: <High/Medium/Low>
   Problem: <description>
   Fix: <recommendation>
```

#### Section 4: 🟡 Lower Confidence Findings
Issues from either model with medium/low confidence.

Format:
```
🟡 [<Severity>] [Category] filename:line
   Source: <Model> (<confidence> confidence)
   Problem: <description>
   Consider: <lightweight recommendation>
```

#### Section 5: ⚠️ Divergent Assessments
Same code location, but models disagree.

Format:
```
⚠️ filename:line
   Claude: <assessment>
   Gemini 3.1 Pro: <assessment>
   Human Review Recommended: The models disagree significantly.
```

## Phase 5: Output Final Report

```
## UltraReview Summary
- Consensus Critical: <count>
- Claude Exclusive: <count>
- Gemini 3.1 Pro Exclusive: <count>
- Lower Confidence: <count>
- Divergent Assessments: <count>
- Total Models Used: <2 or note if fallback>
- Cost Level: High (2 premium models)

Recommendation: <prioritized next steps>
```

## Error Handling

### Gemini CLI Not Installed
```
Error: gemini: command not found
Suggestion: Run `npm install -g @google/gemini-cli` to install
```

### Gemini CLI Not Authenticated
```
Error: Authentication required
Suggestion: Run `gemini login` to authenticate
```

### Single Model Failure
Continue with the successful model's results. Add warning: "⚠️ UltraReview degraded to single-model review."

### Both Models Failure
Report: "UltraReview failed: Both Claude and Gemini 3.1 Pro unavailable. Use standard /review instead."

## Divergence Resolution Policy

**NEVER auto-resolve conflicts between models.** When models disagree:
- Report both assessments with full attribution
- Add "Human Review Recommended" label
- Let the user decide which assessment is correct

Conflicting model outputs often indicate subtle issues worth human attention.
