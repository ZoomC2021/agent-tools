# Gemini

Active contributors: zmang

## Purpose

Gemini CLI support provides AI workflows using SKILL.md format organized in subdirectories.

## Directory layout

```
prompts/gemini/
├── create-pr/
│   └── SKILL.md
├── deslop/
│   └── SKILL.md
├── pr-reviewer/
│   └── SKILL.md
├── pr-reviewer-only/
│   └── SKILL.md
├── refactor/
│   └── SKILL.md
└── review/
    └── SKILL.md
```

## Workflows supported

| Workflow | Path |
|----------|------|
| create-pr | `create-pr/SKILL.md` |
| deslop | `deslop/SKILL.md` |
| pr-reviewer | `pr-reviewer/SKILL.md` |
| pr-reviewer-only | `pr-reviewer-only/SKILL.md` |
| refactor | `refactor/SKILL.md` |
| review | `review/SKILL.md` |

## Installation path

```
~/.gemini/
```

## Usage

In Gemini CLI, skills are available as workflow commands.

## Related pages

- [Agent targets overview](index.md)
- [Feature workflows](../features/index.md)
