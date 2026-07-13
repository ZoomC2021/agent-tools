# AGENTS.md

Guidance for coding agents working in this repository.

## Project Scope

- This repository stores prompt, skill, and workflow content for multiple coding agents.
- Most changes are Markdown updates under `prompts/` and shell/PowerShell installer updates under `scripts/`.
- A small Python utility and tests live in `utils.py` and `tests/test_utils.py`.

## Important Paths

- `prompts/`: Agent prompts, workflows, and eval fixtures.
- `prompts/aliases.json`: Exact-byte duplicate paths mapped to canonical retained files. Edit canonical files, run `python scripts/render-prompts.py refresh` to update alias metadata, then run `python scripts/render-prompts.py check`.
- `prompts/opencode/evals/`: OpenCode eval harness (`scenarios.json`, `variants.json`, fixtures, and run outputs under `out/`).
- `scripts/install.sh` and `scripts/install.ps1`: Installer logic for all supported agent targets.
- `prompts/opencode/bin/zenmux-throttle-proxy`: Streaming reverse proxy that enforces a hard requests-per-minute cap in front of a rate-limited OpenAI-compatible provider (e.g. ZenMux). See the "Rate-Limited Providers" section in `README.md`.
- `README.md`: Source of truth for supported workflows and installation instructions.
- `tests/test_utils.py`: Regression tests for `utils.py`.
- `tests/test_devin_token_usage.py`: Tests for `scripts/devin-token-usage.py` (Devin token usage counter).
- `tests/test_codex_token_usage.py`: Tests for `scripts/codex-token-usage.py` (ChatGPT/Codex token usage counter).
- `tests/zenmux-throttle-proxy.test.js`: Node test for the throttle proxy (pacing, concurrency cap, queue-not-fail, SSE passthrough); runs fully locally with no network or API key.
- `scripts/devin-token-usage.py`: Counts Devin token usage from CLI transcripts (`~/.local/share/devin/cli/transcripts/`) and Desktop ACP events (`~/Library/Application Support/Devin/User/acp-events/`), merges them, and estimates API cost from per-model pricing. Run with `python scripts/devin-token-usage.py` (use `--json` for machine-readable output, `--no-acp` for CLI-only).
- `scripts/codex-token-usage.py`: Counts ChatGPT/Codex subscription token usage from Codex CLI session rollouts (`~/.codex/sessions/`) and Hermes agent state (`~/.hermes/state.db`, filtered to `billing_provider = 'openai-codex'`), merges them, and estimates API cost from OpenAI per-model pricing. Run with `python scripts/codex-token-usage.py` (use `--json` for machine-readable output, `--no-codex`/`--no-hermes` for single-source, `--all-providers` to include non-Codex Hermes providers).

## Editing Rules

- Keep docs and prompts concise and deterministic; avoid contradictory instructions across agents.
- Preserve existing frontmatter and heading structure in prompt files unless a migration requires updates.
- Prefer minimal, targeted edits over broad rewrites.
- Installers render aliases into a temporary complete physical `prompts/` tree before copying files to agent targets.
- When changing install behavior, keep Linux and macOS paths aligned where applicable.
- Never commit real secrets or API keys (for example in `opencode.json`-style config files).
- `prompts/opencode/opencode.json.example` is the authoritative shipped OpenCode config. Any change to agents, commands, plugins, providers, models, permissions, or `{file:...}` references under `prompts/opencode/` must be reflected in the example in the same commit — the installer uses it as the source of truth to sync existing user configs.

## Changing a Skill or Subagent's Model

Do not hand-edit model fields. The model for any OpenCode skill/subagent lives in three places that must stay in sync: the canonical `.agent[NAME].model` in `opencode.json.example`, the `model:` frontmatter in the matching `prompts/opencode/{agent,commands}/NAME.md`, and the "Model" column in the README "Subagent Reference" table. Use `scripts/set-model.sh`, which updates all three and validates the result:

```bash
scripts/set-model.sh                                  # list every agent and its model
scripts/set-model.sh plan-review                      # show one agent's current model
scripts/set-model.sh plan-review xiaomi/mimo-v2.5-pro # set one skill
scripts/set-model.sh review change-auditor openai/gpt-5.5  # set several at once
scripts/set-model.sh all xiaomi/mimo-v2.5-pro         # set every agent
```

- The model is the last argument containing a `/`; everything before it is a target name (or `all`).
- `scripts/set-worker-model.sh` is a backwards-compatible shim that forwards to `set-model.sh` for `worker-general` and `worker-explore`.
- When introducing a new `provider/model`, also add its definition to the `provider` block in `opencode.json.example`, and add a display-name mapping in `set-model.sh` (`display_name()`) so the README column renders the human-facing name. Then run `scripts/install.sh` to sync installed agent frontmatter.

## Validation

Pytest configuration lives in `pyproject.toml` (`pythonpath = ["."]`) so root-level
modules like `utils.py` are importable without manual `sys.path` hacks.

Run the smallest relevant validation set after changes:

```bash
# All Python tests (preferred)
make test

# Or directly:
python -m pytest tests/ -q

# JS tests (zenmux-throttle-proxy, no network/API key required)
make test-js
# Or: node tests/zenmux-throttle-proxy.test.js
```

For prompt/doc-only changes:

- Check for broken links/references and mismatched file names.
- Ensure command examples match real files in this repo.

For OpenCode workflow/routing changes (under `prompts/opencode`):

```bash
# Inspect configured eval matrix
prompts/opencode/bin/opencode-eval list

# Fast sanity check without running full cases
prompts/opencode/bin/opencode-eval run --dry-run
```

When editing `prompts/opencode/opencode.json.example`, verify it parses and all `{file:...}` references resolve:

```bash
jq -e . prompts/opencode/opencode.json.example >/dev/null
jq -r '.. | strings | select(test("^\\{file:[^}]+\\}$")) | capture("^\\{file:(?<p>[^}]+)\\}$").p' \
  prompts/opencode/opencode.json.example | sort -u | while read ref; do
    [ -f "prompts/opencode/${ref#./}" ] || echo "MISS $ref"
  done
```

## Commit and PR Expectations

- Keep commits focused by workflow/agent area (for example `prompts/claude`, `prompts/opencode`, or `scripts/`).
- In PR descriptions, explain why behavior changed, not only what text changed.
- Include validation evidence (commands run or rationale when tests are not applicable).
