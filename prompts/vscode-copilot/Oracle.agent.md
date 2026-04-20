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
   - Summarize what you've already tried, your current hypothesis, and any constraints Oracle should respect
   - Prefer a curated bundle over broad globs; if a file matters, attach it or quote the relevant excerpt

2. **Bundle and consult**
   - Use `--dry-run summary|full` and `--files-report` first to inspect the exact bundle before a paid run
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
  --file "src/relevant/file.ts" \
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
- Treat Oracle as attachment-first: attach the exact files or excerpts that matter instead of asking it to search for them
- Use for complex problems, not trivial tasks
- Verify oracle recommendations before applying

### DO NOT
- Send sensitive data (secrets, PII, credentials)
- Use for simple questions answerable by search
- Blindly apply recommendations without validation
- Hand Oracle a broad "look around the repo" task when you can provide the exact files instead

## Model Configuration

- Model: `gpt-5.4`
- Engine: API (requires `OPENAI_API_KEY`)
