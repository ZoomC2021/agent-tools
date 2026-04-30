# Warp

Active contributors: zmang

## Purpose

Warp terminal support provides AI command workflows for the Warp terminal app, using YAML format for workflow definitions.

## Directory layout

```
prompts/warp/
├── create-pr.yaml
├── deslop.yaml
├── handoff.yaml
├── pr-reviewer-only.yaml
├── pr-reviewer.yaml
├── refactor.yaml
├── review.yaml
└── ultrareview.yaml
```

## Workflows supported

| Workflow | File |
|----------|------|
| create-pr | `create-pr.yaml` |
| deslop | `deslop.yaml` |
| handoff | `handoff.yaml` |
| pr-reviewer-only | `pr-reviewer-only.yaml` |
| pr-reviewer | `pr-reviewer.yaml` |
| refactor | `refactor.yaml` |
| review | `review.yaml` |
| ultrareview | `ultrareview.yaml` |

## Installation path

```
~/.warp/workflows/
```

## Usage

In Warp, workflows appear in the command palette. Access them via the AI button or command palette shortcuts.

## Related pages

- [Agent targets overview](index.md)
- [Feature workflows](../features/index.md)
