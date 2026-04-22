# AGENTS.md

Guidance for coding agents working in this repository.

## Project Scope

- This repository stores prompt, skill, and workflow content for multiple coding agents.
- Most changes are Markdown updates under `prompts/` and shell/PowerShell installer updates under `scripts/`.
- A small Python utility and tests live in `utils.py` and `tests/test_utils.py`.

## Important Paths

- `prompts/`: Agent prompts, workflows, and eval fixtures.
- `prompts/opencode/evals/`: OpenCode eval harness (`scenarios.json`, `variants.json`, fixtures, and run outputs under `out/`).
- `scripts/install.sh` and `scripts/install.ps1`: Installer logic for all supported agent targets.
- `README.md`: Source of truth for supported workflows and installation instructions.
- `tests/test_utils.py`: Regression tests for `utils.py`.

## Editing Rules

- Keep docs and prompts concise and deterministic; avoid contradictory instructions across agents.
- Preserve existing frontmatter and heading structure in prompt files unless a migration requires updates.
- Prefer minimal, targeted edits over broad rewrites.
- When changing install behavior, keep Linux and macOS paths aligned where applicable.
- Never commit real secrets or API keys (for example in `opencode.json`-style config files).

## Validation

Run the smallest relevant validation set after changes:

```bash
# Python utility tests
python tests/test_utils.py

# Optional, if pytest is available
pytest tests/test_utils.py
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

## Commit and PR Expectations

- Keep commits focused by workflow/agent area (for example `prompts/claude`, `prompts/opencode`, or `scripts/`).
- In PR descriptions, explain why behavior changed, not only what text changed.
- Include validation evidence (commands run or rationale when tests are not applicable).
