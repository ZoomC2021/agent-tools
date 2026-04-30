# Architecture

The agent-tools repository implements a hierarchical orchestration pattern for AI coding agents, with the OpenCode setup being the most sophisticated implementation.

## High-level structure

```
┌─────────────────────────────────────────────────────────────┐
│  Codex53-Kimi Orchestrator (GPT-5.3-Codex)                 │
│  • Plans and sequences work                                  │
│  • Makes routing decisions                                    │
│  • Delegates to specialized subagents                       │
└──────────────────────┬────────────────────────────────────────┘
                       │
   ┌───────────┬──────────────┬──────────────────┬──────────────┐
   │           │              │                  │              │
┌──▼────────┐ ┌▼───────────┐ ┌▼────────────────┐ ┌▼────────────┐
│ kimi-     │ │ kimi-      │ │ github-         │ │ docs-       │
│ general   │ │ explore    │ │ librarian       │ │ research    │
│ execution │ │ local find │ │ remote GitHub   │ │ official    │
└───────────┘ └────────────┘ └─────────────────┘ └─────────────┘
   │               │                 │                  │
┌──▼────────┐ ┌────▼─────┐ ┌────────▼──────┐ ┌─────────▼──────┐
│walkthrough│ │ review   │ │ deslop        │ │ pr-reviewer    │
│ diagrams  │ │ local QA │ │ code quality  │ │ PR fixes       │
└───────────┘ └──────────┘ └───────────────┘ └────────────────┘
                            │                  │
                      ┌─────▼─────┐      ┌────▼────┐
                      │ create-pr │      │ oracle  │
                      │ workflow  │      │ deep    │
                      └───────────┘      │ reasoning│
                                         └─────────┘
```

## Orchestrator routing logic

The `codex53-kimi` agent in `prompts/opencode/agent/codex53-kimi.md` uses deterministic keyword-based routing:

| Trigger | Keywords | Agent Selected |
|---------|----------|----------------|
| PR creation | "create PR", "pull request" | **create-pr** |
| PR feedback | "PR comment", "address PR" | **pr-reviewer** |
| Code audit | "audit", "code quality" | **deslop** |
| Local review | "review changes", "uncommitted" | **review** |
| Remote repo research | GitHub URL, `owner/repo` | **github-librarian** |
| Official docs research | "official docs", "migration guide" | **docs-research** |
| Local walkthrough | "walk me through", "diagram" | **walkthrough** |
| Local discovery | "find", "search", "explore" | **kimi-explore** |
| Implementation | "implement", "fix", "refactor" | **kimi-general** |

## Safety gates

Before routing, the orchestrator applies these checks in order:

1. **Intent Verbalization** — State routing reasoning so users can catch misroutes
2. **Turn-Local Intent Reset** — Reclassify intent from the current message only
3. **Context-Completion Gate** — Block `spec-compiler` until explicit implementation verb + concrete scope
4. **Consecutive Failure Protocol** — After 2 No-Go results, auto-escalate to Oracle; after 3, stop and report

## Mission-aware workflow

For multi-step tasks, the orchestrator uses a phased approach:

```
PHASE 0 (optional): docs-research / github-librarian → Gather external references
PHASE 1: mission-scrutiny → Front-load scrutiny, decompose into milestones
PHASE 2 (loop): spec-compiler → kimi-general → milestone-validator
PHASE 3: quick-validator → Final end-to-end validation
PHASE 4 (optional): change-auditor → Deep audit for high-risk areas
```

## Configuration structure

The `prompts/opencode/opencode.json.example` file defines:

- **Models** — GPT-5.x series for orchestration, Kimi K2.5 Turbo for subagents
- **Agents** — Orchestrator, subagents, and workflow commands with permissions
- **Routing** — Mode-based model selection (plan vs build)

Each agent references a prompt file via `{file:./path/to/prompt.md}` syntax that OpenCode resolves at runtime.
