# Oracle

Invoke GPT-5.4 for deep reasoning when stuck on complex problems. Bundles your prompt and relevant files so the oracle can provide informed guidance.

## When to Use

- **Stuck on complex bugs**: After initial investigation, when root cause remains unclear
- **Architecture decisions**: Need expert guidance on tradeoffs and patterns
- **Code review assistance**: Second opinion on critical or risky changes
- **Refactoring uncertainty**: Unsure about approach or potential consequences
- **Cross-domain problems**: Issues spanning multiple technologies or systems
- **Performance optimization**: Need analysis of bottlenecks and solutions

## Prerequisites

Requires Oracle CLI: `npm install -g @steipete/oracle`

Or use npx: `npx -y @steipete/oracle ...`

## Workflow

1. **Prepare context**
   - Identify the core question or problem
   - Gather the 3-8 highest-signal files or excerpts (code, config, logs), with precise paths
   - Summarize what you've already tried, your current hypothesis, and the constraints Oracle should respect
   - Prefer a compact curated bundle over broad globs; if a file matters, attach it or quote the relevant excerpt

2. **Bundle and consult**
   ```bash
   # Preview the bundle and per-file token cost before a paid run
   npx -y @steipete/oracle \
     --dry-run summary \
     --files-report \
     -p "Your detailed question here" \
     --file "src/relevant/file.ts" \
     --file "tests/failing_case.ts"

   # API mode (requires OPENAI_API_KEY)
   npx -y @steipete/oracle \
     --engine api \
     --model gpt-5.4 \
     -p "Your detailed question here" \
     --file "src/relevant/file.ts" \
     --file "docs/architecture.md"

   # Or render for manual paste
   npx -y @steipete/oracle \
     --render --copy \
     -p "Your question" \
     --file "src/relevant/file.ts"
   ```

3. **Apply insights**
   - Review the oracle's analysis
   - Validate recommendations against your codebase
   - Implement agreed-upon solutions
   - Document decisions for future reference

## Guidelines

### DO
- Provide specific, focused questions
- Include relevant code files and context
- Summarize prior investigation attempts
- Use `--dry-run summary|full` and `--files-report` to inspect the exact bundle before a paid run
- Treat Oracle as attachment-first: if a file matters, attach it or quote the relevant excerpt instead of asking Oracle to search for it
- Use for complex problems, not trivial tasks
- Verify oracle recommendations before applying

### DO NOT
- Send sensitive data (secrets, PII, credentials)
- Use for simple questions answerable by search
- Blindly apply recommendations without validation
- Rely on browser mode for automated workflows
- Hand Oracle a broad directory or open-ended "look around the repo" task when you can provide the exact files instead

### STOP IF
- The consultation would include sensitive data
- Cost concerns outweigh the problem's impact
- The issue is better resolved through pair programming
- Previous oracle guidance on similar issues was not helpful

## Model Configuration

This subagent uses GPT-5.4 via OpenAI API:
- Model: `gpt-5.4`
- Engine: API (requires `OPENAI_API_KEY` environment variable)

## Example Usage

**Debugging a race condition:**
```bash
npx -y @steipete/oracle \
  --engine api \
  --model gpt-5.4 \
  -p "Analyze this code for race conditions in the payment processing flow. I've observed intermittent test failures in test_payment_flow.py::test_refund. Review the transaction handling and async patterns." \
  --file "src/payments/processor.py" \
  --file "src/payments/transactions.py" \
  --file "tests/test_payment_flow.py"
```

**Architecture guidance:**
```bash
npx -y @steipete/oracle \
  --engine api \
  --model gpt-5.4 \
  -p "We're considering migrating from REST to GraphQL for our API. Review the current API structure and evaluate: 1) Migration complexity, 2) Performance implications, 3) Breaking changes for clients. Recommend approach with tradeoffs." \
  --file "src/api/router.py" \
  --file "src/api/resolvers.py" \
  --file "docs/api-design.md"
```

**Code review assistance:**
```bash
npx -y @steipete/oracle \
  --engine api \
  --model gpt-5.4 \
  -p "Review this authentication refactor for security issues and edge cases. Pay special attention to session handling and token validation." \
  --file "src/auth/session.py" \
  --file "src/auth/tokens.py" \
  --file "src/middleware/auth.py"
```

## Output Format

Oracle returns structured analysis:
- **Assessment**: Summary of the situation
- **Findings**: Specific issues or opportunities identified
- **Recommendations**: Actionable guidance with rationale
- **Tradeoffs**: Pros/cons of different approaches
- **Next Steps**: Prioritized action items

## Integration with Subagent Pattern

When delegating to Oracle from an orchestrator:

```markdown
GOAL: Get expert analysis on [specific problem]

SCOPE BOUNDARIES:
- DO: Bundle pre-synthesized context, attach the exact files or excerpts that matter, ask focused questions, await analysis
- DO NOT: Include sensitive data, ask open-ended research questions, or ask Oracle to search the repo for basic context
- STOP IF: Cost exceeds value, sensitive data would be exposed

CONTEXT: [What you've tried, current hypothesis, relevant architecture, constraints, exact file/log excerpts]

ACCEPTANCE CRITERIA:
- Oracle provides specific findings on the question asked
- Recommendations include rationale and tradeoffs
- Next steps are actionable and prioritized

OUTPUT FORMAT: Return oracle's key findings and your plan for applying them.
```
