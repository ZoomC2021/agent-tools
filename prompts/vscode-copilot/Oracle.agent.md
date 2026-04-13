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
   - Gather relevant files (code, config, logs)
   - Summarize what you've already tried

2. **Bundle and consult**
   - Use terminal to run oracle with API mode
   - Or use `--render --copy` for manual paste into ChatGPT

3. **Apply insights**
   - Review the oracle's analysis
   - Validate recommendations against your codebase
   - Implement agreed-upon solutions

## Example Commands

```bash
# API mode (requires OPENAI_API_KEY)
npx -y @steipete/oracle \
  --engine api \
  --model gpt-5.4 \
  -p "Your detailed question here" \
  --file "src/**/*.ts" \
  --file "docs/architecture.md"

# Render for manual paste
npx -y @steipete/oracle \
  --render --copy \
  -p "Your question" \
  --file "src/relevant/file.ts"
```

## Guidelines

### DO
- Provide specific, focused questions
- Include relevant code files and context
- Summarize prior investigation attempts
- Use for complex problems, not trivial tasks
- Verify oracle recommendations before applying

### DO NOT
- Send sensitive data (secrets, PII, credentials)
- Use for simple questions answerable by search
- Blindly apply recommendations without validation

## Model Configuration

- Model: `gpt-5.4`
- Engine: API (requires `OPENAI_API_KEY`)
