# Lore

The history and evolution of the agent-tools repository.

## Eras

### Foundation (Mar–Apr 2025)

The repository emerged to solve a specific problem: inconsistent workflows across AI coding agents. Early commits established the core OpenCode architecture with the Codex53-MiMo orchestrator pattern.

Key events:
- Initial OpenCode agent definitions and routing logic
- Establishment of deterministic routing with safety gates
- Creation of core workflow prompts: review, refactor, create-pr, pr-reviewer

### Multi-Agent Expansion (Apr 2025)

Rapid expansion to support the most popular AI coding agents. Each agent target required adapting prompts to platform-specific formats (SKILL.md for Windsurf/Amp/Gemini, .agent.md for VSCode Copilot, YAML for Warp).

Key events:
- Added Claude Code, Codex, Cursor, Cline support
- Added VSCode Copilot and Copilot CLI
- Added Windsurf and Amp skill formats
- Added Gemini CLI skill format

### Advanced Workflows (Apr 2025)

Introduction of sophisticated multi-agent and multi-model workflows.

Key events:
- **Apr 16**: Ultrareview — parallel dual-model review with GPT 5.5 + Gemini 3.1 Pro Preview
- **Apr 16**: Mission-scrutiny workflow for long-running tasks with milestone validation
- **Apr 25**: Handoff command for session continuity
- **Apr 25**: Ultrareview-lite — lower-cost dual-model variant
- **Apr 25**: Change-auditor for deep security and breaking-change analysis

### Hardening and Coverage (Apr–May 2025)

Focus on reliability, eval infrastructure, and remaining agent targets.

Key events:
- **Apr 25**: OpenCode eval harness with scenario testing
- **Apr 25**: Plan-review subagent for binary Execution Contract validation
- **Apr 29**: Pi agent support
- **Apr 29**: Warp support with predict-issues command
- **Apr 29**: Predict-issues workflow for proactive problem detection

## Longest-standing features

| Feature | Introduced | Notes |
|---------|------------|-------|
| Review workflow | Early Apr 2025 | Core workflow, present from initial releases |
| Refactor workflow | Early Apr 2025 | Core workflow with churn detection |
| Create-pr workflow | Early Apr 2025 | Branch creation and PR automation |
| PR-reviewer | Early Apr 2025 | PR feedback integration |
| Deterministic routing | Foundation era | Keyword-based routing system |
| Safety gates | Foundation era | Intent verbalization and context-completion |

## Deprecated features

None yet — the codebase is young and actively evolving.

## Growth trajectory

```
Mar 2025: ~5 agent targets, 4 workflows
Apr 2025: 14 agent targets, 8+ workflows
May 2025: Continued refinement, eval infrastructure
```

The repository grew from a single OpenCode-focused project to a comprehensive multi-agent workflow library in approximately 6 weeks.

## Notable patterns

**Model selection philosophy**: Use highest-reasoning models (GPT-5.x) for planning and orchestration, fast capable models (MiMo v2.5 Pro) for execution and research.

**Safety-first design**: Every workflow includes multiple safety gates before destructive actions. The orchestrator verbalizes intent, checks context completion, and escalates after consecutive failures.

**Format proliferation**: Supporting 14 agents means maintaining prompts in ~5 different formats (Markdown with frontmatter, SKILL.md, .agent.md, YAML, plain Markdown).
