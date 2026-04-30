# OpenCode

Active contributors: zmang

## Purpose

OpenCode is the primary agent target for agent-tools, featuring the sophisticated Codex53-Kimi orchestration architecture. It uses GPT-5.3-Codex for planning and routing, with Fireworks Kimi K2.5 Turbo subagents for execution.

## Directory layout

```
prompts/opencode/
├── agent/                    # Agent definitions
│   ├── codex53-kimi.md      # Primary orchestrator (GPT-5.3-Codex)
│   ├── codex53-kimi-turbo.md # Alternative orchestrator (Kimi)
│   ├── kimi-general.md      # Implementation execution
│   ├── kimi-explore.md      # Read-only local discovery
│   ├── github-librarian.md  # Remote GitHub research
│   ├── docs-research.md     # Official documentation research
│   ├── walkthrough.md       # Architecture walkthroughs
│   └── oracle.md            # Deep reasoning (GPT-5.4)
├── commands/                 # Workflow prompts
│   ├── review.md
│   ├── refactor.md
│   ├── deslop.md
│   ├── create-pr.md
│   ├── pr-reviewer.md
│   ├── pr-reviewer-only.md
│   ├── ultrareview.md
│   ├── ultrareview-lite.md
│   ├── spec-compiler.md
│   ├── quick-validator.md
│   ├── change-auditor.md
│   ├── mission-scrutiny.md
│   ├── milestone-validator.md
│   ├── plan-review.md
│   ├── handoff.md
│   └── cc.md                # Claude CLI integration
├── bin/                      # Helper scripts
│   ├── opencode-eval        # Eval harness
│   ├── opencode-gemini-review  # Gemini review helper
│   └── opencode_review_utils.py  # Shared utilities
├── evals/                    # Evaluation fixtures
│   ├── scenarios.json
│   ├── variants.json
│   └── fixtures/
└── opencode.json.example     # Authoritative configuration
```

## Key abstractions

| File | Purpose |
|------|---------|
| `agent/codex53-kimi.md` | Orchestrator with deterministic routing and safety gates |
| `opencode.json.example` | Complete agent and model configuration |
| `bin/opencode-gemini-review` | Helper for dual-model reviews |

## Orchestrator routing

The codex53-kimi agent implements deterministic routing:

```
"create PR" / "pull request" → create-pr
"PR comment" / "address PR" → pr-reviewer
"audit" / "code quality" → deslop
"review changes" → review
GitHub URL / "owner/repo" → github-librarian
"official docs" → docs-research
"walk me through" → walkthrough
"find" / "search" → kimi-explore
"implement" / "fix" → spec-compiler → kimi-general
```

## Safety gates

1. **Intent Verbalization** — State routing reasoning aloud
2. **Turn-Local Intent Reset** — Reclassify from current message only
3. **Context-Completion Gate** — Block spec-compiler until ready
4. **Consecutive Failure Protocol** — Escalate to Oracle after 2 failures

## Configuration

The `opencode.json.example` defines:
- Models (GPT-5.x series, Kimi K2.5 Turbo, Gemini)
- Agents with permissions and prompts
- Mode-based routing (plan vs build)

## Installation path

```
~/.config/opencode/
├── opencode.json
├── commands/
├── agent/
└── bin/
```

## Related pages

- [Architecture](../overview/architecture.md) — System overview
- [Features](../features/index.md) — Available workflows
- [Getting started](../overview/getting-started.md) — Setup instructions
