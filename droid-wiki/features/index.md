# Features

Cross-cutting capabilities and workflows available across agent platforms.

## Workflow overview

| Workflow | Purpose | Availability |
|----------|---------|--------------|
| [review](review.md) | Review uncommitted changes for bugs and regressions | All 14 agents |
| [refactor](refactor.md) | Analyze and prioritize refactoring opportunities | All 14 agents |
| [create-pr](create-pr.md) | Create PR with auto-generated title and description | All 14 agents |
| [pr-reviewer](pr-reviewer.md) | Address PR review feedback | All 14 agents |
| [pr-reviewer-only](pr-reviewer-only.md) | Fetch PR comments, generate fix prompts without auto-fixing | All 14 agents |
| [deslop](deslop.md) | Code quality audit against engineering principles | 13 agents |
| [ultrareview](ultrareview.md) | Parallel dual-model review (GPT 5.4 + Gemini) | 9 agents |
| [handoff](handoff.md) | Generate context for continuing work | 8 agents |
| [predict-issues](predict-issues.md) | Proactive issue detection | 3 agents |
| [mission-scrutiny](mission-scrutiny.md) | Front-load planning for long-running multi-step tasks | OpenCode |

## OpenCode-specific features

Beyond standard workflows, OpenCode provides:

- **Deterministic routing** — Keyword-based agent selection with safety gates
- **Mission-aware workflows** — Long-running task decomposition with milestone validation
- **Multi-model orchestration** — GPT-5.x for planning, Kimi for execution
- **Research agents** — GitHub librarian, docs research, architecture walkthroughs
- **Execution contracts** — Structured specs before implementation work

## How workflows map to agents

Each workflow is adapted to platform-specific formats:

- **OpenCode**: Markdown with frontmatter in `commands/`
- **VSCode Copilot**: `.agent.md` files
- **Windsurf/Amp/Gemini**: `SKILL.md` format
- **Warp**: YAML workflow files
- **Others**: Plain Markdown

## Related pages

- [Review workflow](review.md)
- [Refactor workflow](refactor.md)
- [Create PR workflow](create-pr.md)
- [PR reviewer workflow](pr-reviewer.md)
- [Deslop workflow](deslop.md)
- [Ultrareview workflow](ultrareview.md)
