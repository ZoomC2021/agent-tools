---
name: oracle
description: Consult the oracle droid for deep reasoning on complex bugs, architecture tradeoffs, risky reviews, or performance problems.
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

3. **Invoke the custom droid**
   - Use the Task tool with `subagent_type: oracle`.
   - In non-interactive `droid exec` read-only mode, enable the Task tool when needed, for example `droid exec --enabled-tools Task "..."`.
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

## If the Oracle Droid Is Unavailable

Tell the user to install the Droid assets from this repo:

```bash
./scripts/install.sh droid
```

Or manually copy:

```bash
mkdir -p ~/.factory/droids ~/.factory/skills/oracle
cp prompts/droid/droids/oracle.md ~/.factory/droids/oracle.md
cp prompts/droid/skills/oracle/SKILL.md ~/.factory/skills/oracle/SKILL.md
```

## Model Configuration Note

The shipped oracle droid inherits the parent Droid's configured model and uses `reasoningEffort: low`, so it should work with the user's available Factory plan, credits, or BYOK configuration. If the user specifically wants Factory's built-in `gpt-5.5` and their workspace can access it, they can edit `~/.factory/droids/oracle.md` to use `model: gpt-5.5`; for BYOK use a configured model such as `model: custom:<configured-model-name>`. A ChatGPT Plus/Pro browser subscription is not an API credential for Droid.
