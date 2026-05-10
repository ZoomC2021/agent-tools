# Predictive Code Analysis

Analyze codebase to predict potential problems before they impact the project.

## Strategic Thinking Process

To make accurate predictions, consider:

1. **Pattern Recognition**
   - Which code patterns commonly lead to problems?
   - Are there growing complexity hotspots?
   - Do I see anti-patterns that will cause issues at scale?
   - Are there ticking time bombs (hardcoded values, assumptions)?

2. **Risk Assessment Framework**
   - Likelihood: How probable is this issue to occur?
   - Impact: How severe would the consequences be?
   - Timeline: When might this become a problem?
   - Effort: How hard would it be to fix now vs later?

3. **Common Problem Categories**
   - Performance: O(n²) algorithms, memory leaks, inefficient queries
   - Maintainability: High complexity, poor naming, tight coupling
   - Security: Input validation gaps, exposed secrets, weak auth
   - Scalability: Hardcoded limits, single points of failure

4. **Prediction Strategy**
   - Start with highest risk areas (critical path code)
   - Look for patterns that break at 10x, 100x scale
   - Check for technical debt accumulation
   - Identify brittleness in integration points

## Analysis Approach

Use native tools for comprehensive analysis:
- **Grep tool** to search for problematic patterns
- **Glob tool** to analyze file structures and growth
- **Read tool** to examine complex functions and hotspots

Examine:
- Code complexity trends and potential hotspots
- Performance bottleneck patterns forming
- Maintenance difficulty indicators
- Architecture stress points and scaling issues
- Error handling gaps

For each prediction:
- Show specific code locations with file references
- Explain why it's likely to cause future issues
- Estimate potential timeline and impact
- Suggest preventive measures with priority levels

## Output Format

For each prediction found:

````markdown
## Predictive Analysis Report

### Predicted Issues

#### {Priority}: {Title}
**File:** `{path}` (line {line})
**Risk Level:** Critical/High/Medium/Low
**Likelihood:** High/Medium/Low
**Timeline:** Immediate / Short-term (weeks) / Medium-term (months) / Long-term (quarters)
**Impact:** High/Medium/Low

**Current code:**
```{lang}
{code snippet}
````

**Problem pattern:** {what anti-pattern or risk is present}

**Why it will fail:** {explanation of how this becomes a problem at scale or over time}

**Preventive measure:** {specific fix or refactor}

**Effort:** Small / Medium / Large
```

## Guidelines

### DO
- Focus on patterns, not one-off bugs
- Prioritize by risk (likelihood x impact)
- Provide concrete file paths and line numbers
- Estimate realistic timelines
- Suggest actionable preventive measures

### DO NOT
- Report issues that are already bugs (this is prediction, not debugging)
- Make vague predictions without code evidence
- Include AI attribution or watermarks in any output

### STOP IF
- The codebase is too small to meaningfully predict (< 3 files)
- Two passes produce no new patterns
- Analysis becomes speculative without code evidence
