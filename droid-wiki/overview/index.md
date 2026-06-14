# Agent Tools

Agent-tools provides custom prompts, skills, and workflows for AI coding agents. It enables consistent developer workflows across 14+ coding assistants including OpenCode, Claude Code, Codex, Cursor, Pi, Warp, and others.

The repository centers around the **OpenCode GPT-5.5 worker architecture** — a sophisticated orchestrator pattern using GPT-5.5 for planning and routing, with model-swappable worker subagents for execution and research tasks.

## What it provides

- **Workflow prompts** for common development tasks: code review, refactoring, PR management, quality audits
- **Agent definitions** with deterministic routing logic and safety gates
- **Installation scripts** for macOS and Linux that sync prompts to agent config directories
- **Helper utilities** for date parsing and dual-model review coordination

## Quick links

- [Getting started](getting-started.md) — install and configure
- [Architecture](architecture.md) — how the OpenCode orchestration works
- [Workflow reference](../features/index.md) — available commands by agent
- [Glossary](glossary.md) — terms and concepts
