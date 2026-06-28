---
name: oracle
description: Consult the GPT-5.5 oracle subagent for deep reasoning on complex bugs, architecture tradeoffs, risky reviews, or performance problems.
agent: oracle
---

# Oracle Consultation

Use this skill when the user asks to consult an oracle, get a second opinion from a stronger reasoning agent, or escalate a complex engineering question.

## Workflow

1. **Decide whether oracle is appropriate**
   - Use it for complex bugs, architecture tradeoffs, risky reviews, refactoring uncertainty, cross-domain issues, or performance analysis.
   - Do not use it for simple lookups, formatting changes, or questions answerable by reading one obvious file.

2. **Prepare a compact context bundle**
   - Identify the exact question or decision point.
   - Gather the 3-8 highest-signal files or excerpts, with precise paths and why each matters.
   - Include prior attempts, current hypotheses, constraints, logs, failing commands, and validation output when relevant.
   - Exclude secrets, credentials, PII, customer data, and broad unrelated files.

3. **Invoke the custom Devin oracle profile**
   - Use the `oracle` subagent profile.
   - The installed profile is configured with `model: gpt-5.5`, so a Devin session running a different top-level model can still route this consultation to GPT-5.5.
   - Give the oracle a self-contained prompt with sections like:

```markdown
GOAL: [specific question]

CONTEXT:
- [facts]
- [prior attempts]
- [constraints]

FILES / EXCERPTS:
- `path/to/file`: [why it matters]

VALIDATION / LOGS:
- [command output or failure]

REQUESTED OUTPUT:
- Assessment
- Findings
- Recommendations with tradeoffs
- Next steps
```

4. **Apply judgment after the oracle responds**
   - Summarize the oracle's key findings for the user.
   - Validate recommendations against the codebase before applying changes.
   - Do not blindly implement suggestions that conflict with local evidence.

## If the Oracle Profile Is Unavailable

Tell the user to install the Devin assets from this repo:

```bash
./scripts/install.sh devin
```

Or manually copy:

```bash
mkdir -p ~/.config/devin/agents/oracle ~/.config/devin/skills/oracle
cp prompts/devin/agents/oracle/AGENT.md ~/.config/devin/agents/oracle/AGENT.md
cp prompts/devin/skills/oracle/SKILL.md ~/.config/devin/skills/oracle/SKILL.md
```

## Model Configuration Note

The shipped Devin oracle profile uses `model: gpt-5.5`. Devin usage dashboards can show the child subagent model even when ATIF exports only show the parent run model.
