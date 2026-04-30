# Maintainers

Subsystem ownership and recent contributor information.

## Subsystem ownership

Based on git history analysis (no CODEOWNERS file exists).

| Subsystem | Primary contributor | Recent activity |
|-----------|---------------------|-----------------|
| `prompts/opencode/` | ZoomC2021 | 40 commits |
| `prompts/claude/` | ZoomC2021 | 11 commits |
| `scripts/` | ZoomC2021 | 17 commits + 7 (alt env) |
| `utils.py` | ZoomC2021 | 1 commit |
| `tests/` | ZoomC2021 | 2 commits |

## All recent contributors

| Contributor | Total commits | Primary areas |
|-------------|---------------|---------------|
| ZoomC2021 (UbuntuDesktop) | 46 | All subsystems |
| ZoomC2021 | 7 | prompts/claude, scripts |
| ZMAng | 3 | scripts, prompts/opencode, prompts/claude |
| K8-Plus | 3 | prompts/opencode, scripts |
| Ang Zhuu Ming | 1 | scripts |

> Note: Bot accounts (ending in `[bot]`) are filtered from this list.

## Contribution patterns

### prompts/opencode/

- **Most active area** — 40+ commits
- **Focus**: Agent definitions, command prompts, subagent workflows
- **Key files**: `opencode.json.example`, commands/*.md, agent/*.md

### prompts/claude/

- **Secondary focus** — 11 commits
- **Focus**: Slash commands, agent prompts
- **Key files**: commands/*.md, agent/*.md

### scripts/

- **Installer maintenance** — 24 commits total
- **Focus**: `install.sh`, `install.ps1`
- **Contributors**: Most diverse contributor set

### utils.py / tests/

- **Minimal churn** — Utility functions are stable
- **Focus**: Date parsing, Gemini helper scripts
- **Pattern**: Small, focused changes

## How to find current maintainers

To update this information:

```bash
# Get contributors for a specific path
git log --format="%an" -- "prompts/opencode/" | sort | uniq -c | sort -rn

# Get contributors excluding bots
git log --format="%an" -- "path/" | grep -v '\[bot\]$' | sort | uniq -c | sort -rn
```

## Contributing

See [How to contribute](how-to-contribute/index.md) for guidelines on:
- Development workflow
- Testing requirements
- Code patterns and conventions

## Related

- [How to contribute](how-to-contribute/index.md) — Contribution guidelines
- [Development workflow](how-to-contribute/development-workflow.md) — Git workflow
- [Patterns and conventions](how-to-contribute/patterns-and-conventions.md) — Coding standards
