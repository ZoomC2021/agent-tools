# Opencode Workflow Eval Harness

This harness runs repeatable A/B evaluations for your Opencode workflow definitions, Codex CLI runs, and Devin CLI runs.

It is designed for model-swap experiments like:

- current `frontier-worker` orchestrator on `openai/gpt-5.5`
- candidate `frontier-worker` orchestrator on `openai/gpt-5.5`

It also supports direct subagent evaluation by defining scenarios that target a hidden subagent with `"agent": "<subagent-name>"`.

## What It Does

- Creates isolated Opencode config variants from `opencode.json`
- Runs a scenario matrix with `opencode run --format json`, `codex exec --json`, or `devin -p`
- Captures JSON event streams, stderr, and exported session transcripts
- Scores each run against explicit expectations
- Produces a machine-readable JSON summary plus a human-readable Markdown report

## Files

- `bin/opencode-eval` — runner CLI
- `evals/variants.json` — model/config variants
- `evals/scenarios.json` — scenarios and checks
- `evals/fixtures/tiny-js-app` — isolated implementation sandbox fixture

## Prerequisites

1. Copy `opencode.json.example` to `opencode.json` and fill in your API keys
2. Ensure `opencode` CLI is installed and on your `PATH` for OpenCode variants
3. Ensure `codex` CLI is installed and authenticated for Codex variants
4. Ensure `devin` CLI is installed and authenticated for Devin variants
5. Ensure `antigravity-accounts.json` exists if using Antigravity-proxied models

## Quick Start

List the configured variants and scenarios:

```bash
bin/opencode-eval list
```

Dry-run the default starter matrix:

```bash
bin/opencode-eval run --dry-run
```

Run the default starter suite:

```bash
bin/opencode-eval run
```

Run a Codex model against a task-outcome scenario:

```bash
bin/opencode-eval run --runner codex --variants codex-spark-high --scenarios implementation-sandbox-task-outcome
```

Run Devin GLM-5.2 against the suite using only portable outcome checks:

```bash
bin/opencode-eval run --runner devin --variants devin-glm52 --outcome-only
```

Run Devin Kimi K2.7 the same way:

```bash
bin/opencode-eval run --runner devin --variants devin-kimi27 --outcome-only
```

Run the end-to-end primary workflow result suite with the current GPT 5.5 orchestrator:

```bash
bin/opencode-eval run --variants baseline-gpt55-primary --tags workflow-results
```

Run only the GPT 5.5 primary variant against the sandbox implementation scenario:

```bash
bin/opencode-eval run --variants gpt55-primary --scenarios implementation-sandbox
```

Run mission-scrutiny subagent evals on GPT-5.5 (current default) only:

```bash
bin/opencode-eval run --variants mission-scrutiny-gpt55 --tags mission-scrutiny
```

Run plan-review subagent evals on GPT-5.5:

```bash
bin/opencode-eval run --variants plan-review-gpt55 --tags plan-review
```

Run only the adversarial plan-review subset (anti-perfectionism, hidden blockers, format discipline, STOP IF triggers):

```bash
bin/opencode-eval run --variants plan-review-gpt55 --tags plan-review-adversarial
```

Rebuild the summary for an existing run directory:

```bash
bin/opencode-eval report evals/out/<run-id>
```

By default, `run` executes scenarios tagged `starter`. Use `--tags extended` or `--scenarios <id>` for additional cases.

The `workflow-results` tag focuses on end-to-end task outcomes through the primary `spec-compiler` -> `worker-general` -> `quick-validator` path rather than routing-only checks. It intentionally evaluates final receipts, resulting file state, and executable behavior, not brittle internal assertions about exact subagent hop order or delegated prompt wording.

## Variant Format

Each variant can override:

- `runner` — optional runner, either `opencode`, `codex`, or `devin` (`opencode` by default)
- `codexModel` — model passed to `codex exec --model`
- `codexReasoningEffort` — value passed through Codex config as `model_reasoning_effort`
- `devinModel` — model passed to `devin --model`
- `devinPermissionMode` — value passed to `devin --permission-mode` (`dangerous` is required for non-interactive evals that need tool execution, and evals run inside isolated fixture copies)
- `configOverrides` — dotted paths in `opencode.json`
- `promptFrontmatterOverrides` — frontmatter keys in prompt files copied into the variant workspace

That means you can test:

- orchestrator model swaps
- plan-mode model swaps
- subagent model swaps for `mission-scrutiny`, `quick-validator`, `review`, and similar roles
- Codex and Devin model swaps for task outcome scenarios

Use Codex and Devin variants with expectations based on final text, files, exit codes, and workspace commands. OpenCode-specific expectations such as `requiredSubagents`, `forbiddenSubagents`, `taskPromptIncludes`, and `transcriptRegex` depend on OpenCode session export internals. Use `--outcome-only` to score a run on exit status, file assertions, workspace commands, and token limits while ignoring OpenCode telemetry and receipt-format assertions.

In `--outcome-only` mode, a timed-out process can still pass when the scenario has concrete file or workspace-command checks and those checks pass after the workspace is preserved. Prompt-only timeouts still fail because there is no durable outcome to verify.

## Scenario Format

Each scenario can define:

- `agent` — the agent to invoke
- `prompt` — the exact message to send to Opencode
- `tags` — for filtering suites
- `workingDirectory` — target directory for the run
- `sandbox.copyFrom` — optional fixture copied into a per-run workspace
- `setupCommands` — optional shell setup commands executed before the run
- `expectations` — pass/fail checks

Supported expectations include:

- `exitCode`
- `finalIncludes`
- `finalExcludes`
- `finalRegex`
- `transcriptIncludes`
- `transcriptRegex`
- `requiredSubagents`
- `forbiddenSubagents`
- `requiredAssistantModel`
- `maxTotalTokens`
- `fileContains`

## Recommended Use For Your Primary-Model Test

The built-in variants already cover the exact comparison you asked for:

- `baseline-gpt55-primary`
- `gpt55-primary`

Run the starter suite first to compare:

1. routing fidelity
2. delegation behavior
3. implementation-path behavior in the sandbox fixture
4. token and duration differences

If you want broader coverage, add scenarios that target:

1. `mission-scrutiny`
2. `milestone-validator`
3. `change-auditor`
4. `review`
5. `docs-research`
6. `github-librarian`

## Output Layout

Each run writes to `evals/out/<timestamp>/` and includes:

- `manifest.json`
- `summary.json`
- `summary.md`
- `variants/<variant>/...` isolated config copies
- `cases/<variant>__<scenario>/events.jsonl`
- `cases/<variant>__<scenario>/session.json`
- `cases/<variant>__<scenario>/result.json`

This makes it easy to diff runs, inspect transcripts, and build a higher-level judge later if you want to add model-based scoring.
