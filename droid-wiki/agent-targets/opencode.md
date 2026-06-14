# OpenCode

Active contributors: zmang

## Purpose

OpenCode is the primary agent target for agent-tools, featuring the sophisticated GPT-5.5 worker orchestration architecture. It uses GPT-5.5 for planning and routing, with model-swappable worker subagents for execution and discovery.

## Directory layout

```
prompts/opencode/
├── agent/                    # Agent definitions
│   ├── frontier-worker.md      # Primary orchestrator (GPT-5.5)
│   ├── worker-general.md      # Implementation execution
│   ├── worker-explore.md      # Read-only local discovery
│   ├── github-librarian.md  # Remote GitHub research
│   ├── docs-research.md     # Official documentation research
│   ├── walkthrough.md       # Architecture walkthroughs
│   └── oracle.md            # Deep reasoning (GPT-5.5)
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
| `agent/frontier-worker.md` | Orchestrator with deterministic routing and safety gates |
| `opencode.json.example` | Complete agent and model configuration |
| `bin/opencode-gemini-review` | Helper for dual-model reviews |

## Orchestrator routing

The frontier-worker agent implements deterministic routing:

```
"create PR" / "pull request" → create-pr
"PR comment" / "address PR" → pr-reviewer
"audit" / "code quality" → deslop
"review changes" → review
GitHub URL / "owner/repo" → github-librarian
"official docs" → docs-research
"walk me through" → walkthrough
"find" / "search" → worker-explore
"implement" / "fix" → spec-compiler → worker-general
```

## Safety gates

1. **Intent Verbalization** — State routing reasoning aloud
2. **Turn-Local Intent Reset** — Reclassify from current message only
3. **Context-Completion Gate** — Block spec-compiler until ready
4. **Consecutive Failure Protocol** — Escalate to Oracle after 2 failures

## Configuration

The `opencode.json.example` defines:
- Models (GPT-5.x series, MiMo v2.5 Pro, Gemini)
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
