# How to contribute

Guidelines for making changes to the agent-tools repository.

## Project scope

This repository stores prompt, skill, and workflow content for multiple coding agents. Most changes are:
- Markdown updates under `prompts/`
- Shell/PowerShell installer updates under `scripts/`
- Small Python utility changes in `utils.py`

## Work pickup process

1. **Read AGENTS.md** — The project guidelines live at `/Users/zmang/Repos/agent-tools/AGENTS.md`
2. **Identify the scope** — Which agent target(s) are affected?
3. **Check existing patterns** — Look at similar prompts for the same agent
4. **Make minimal, targeted edits** — Avoid broad rewrites
5. **Preserve frontmatter** — Keep existing heading structure unless migrating
6. **Keep Linux and macOS paths aligned** — When changing install behavior

## Definition of done

- [ ] Changes match existing style in the target agent directory
- [ ] OpenCode changes reflected in `opencode.json.example` if applicable
- [ ] Installer scripts updated if new files or paths are added
- [ ] Tests pass (`python tests/test_utils.py`)
- [ ] For OpenCode eval changes: `opencode-eval run --dry-run` passes
- [ ] For `opencode.json.example` changes: file references resolve

## PR process

1. Keep commits focused by workflow/agent area (e.g., `prompts/claude`, `prompts/opencode`, `scripts/`)
2. Explain **why** behavior changed, not just what changed
3. Include validation evidence (commands run or rationale)
4. Never commit real secrets or API keys in config files

## Related pages

- [Development workflow](development-workflow.md) — branch, code, test, PR cycle
- [Testing](testing.md) — how to run and write tests
- [Patterns and conventions](patterns-and-conventions.md) — coding style and structure
- [Tooling](tooling.md) — build system and validation
