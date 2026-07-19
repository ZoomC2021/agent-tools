---
name: oracle
description: Consult the read-only GPT-5.6 Sol oracle droid for hard engineering judgments.
---

# Oracle Consultation

Use Oracle when the user requests a second opinion or when a difficult bug,
risky review, architecture decision, migration, or refactor needs deeper
judgment. Do not use it for simple searches, routine edits, or obvious bugs.

## Workflow

1. **Investigate first**
   - Establish the relevant ownership path, current behavior, and exact
     uncertainty.
   - Identify the current diff or exact files and symbols where Oracle should
     begin. Do not gather and paste a broad file bundle.

2. **Invoke the custom droid**
   - Use the Task tool with `subagent_type: oracle`.
   - In non-interactive `droid exec` read-only mode, enable Task when needed,
     for example: `droid exec --enabled-tools Task "..."`.
   - Give Oracle a focused task:

```markdown
INTENT: [behavior or outcome that must be preserved]

DECISION / QUESTION: [exact judgment needed]

RELEVANT FILES:
- @path/to/file: [why it matters]

CURRENT EVIDENCE:
- [observations, reproduction, failures, or prior attempts]

CONSTRAINTS: [compatibility, rollout, performance, and scope limits]

REVIEW INSTRUCTIONS:
- Start with: [current diff or exact path/symbol]
- Focus on: [specific risks]
- Ignore: [non-goals]

OUTPUT: [recommendation, ranked risks, alternatives, smallest fixes, etc.]
```

   Include non-repository logs or facts when needed, but let Oracle inspect
   repository files through its read-only tools. Never include secrets,
   credentials, PII, or customer data.

3. **Apply independent judgment**
   - Validate material claims against the repository.
   - Reject advice that conflicts with local evidence or stated intent.
   - Implement changes in the parent session, never in Oracle, and run the
     narrowest meaningful verification.

## If Oracle Is Unavailable

Install the Droid assets:

```bash
./scripts/install.sh droid
```

Or manually copy:

```bash
mkdir -p ~/.factory/droids ~/.factory/skills/oracle
cp prompts/droid/droids/oracle.md ~/.factory/droids/oracle.md
cp prompts/droid/skills/oracle/SKILL.md ~/.factory/skills/oracle/SKILL.md
```

The shipped profile uses Factory's `gpt-5.6-sol` with high reasoning effort.
If the workspace uses BYOK, configure an equivalent custom model in the droid
profile. A browser subscription is not a CLI/API credential for Droid.
