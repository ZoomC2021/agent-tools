# VSCode Copilot

Active contributors: zmang

## Purpose

VSCode Copilot support provides agent workflows for GitHub Copilot in VS Code, using `.agent.md` file suffix.

## Directory layout

```
prompts/vscode-copilot/
├── Create-PR.agent.md
├── Deslop.agent.md
├── Handoff.agent.md
├── Oracle.agent.md
├── PR-Reviewer.agent.md
├── PR-Reviewer-Only.agent.md
├── Refactor.agent.md
├── Review.agent.md
└── ultrareview.md
```

## Workflows supported

| Workflow | File |
|----------|------|
| create-pr | `Create-PR.agent.md` |
| deslop | `Deslop.agent.md` |
| handoff | `Handoff.agent.md` |
| oracle | `Oracle.agent.md` |
| pr-reviewer | `PR-Reviewer.agent.md` |
| pr-reviewer-only | `PR-Reviewer-Only.agent.md` |
| refactor | `Refactor.agent.md` |
| review | `Review.agent.md` |
| ultrareview | `ultrareview.md` |

## Installation path

```
~/.github/copilot/
```

## Usage

In VSCode with Copilot, agents are available through the Copilot chat interface.

## Related pages

- [Agent targets overview](index.md)
- [Feature workflows](../features/index.md)
