# Dependencies reference

Runtime and development dependencies for agent-tools.

## Runtime dependencies

### Required

| Tool | Purpose | Version | Used by |
|------|---------|---------|---------|
| `git` | Version control | 2.x+ | All workflows |
| `gh` | GitHub CLI | 2.x+ | PR workflows, review |
| `python3` | Script execution | 3.10+ | Utils, tests, Gemini helper |

### Optional

| Tool | Purpose | Used by |
|------|---------|---------|
| `jq` | JSON validation | Config validation |
| `rg` (ripgrep) | Fast search | Refactor, deslop workflows |
| `gemini` | Gemini CLI review | Ultrareview on Gemini CLI |
| `claude` | Claude CLI | `/cc` command |

## Python dependencies

### Standard library only

The codebase uses only Python standard library modules:

| Module | Purpose |
|--------|---------|
| `datetime` | Date parsing utilities |
| `typing` | Type hints |
| `sys` | System operations, path manipulation |
| `os` | Environment and file operations |
| `tempfile` | Temporary directories |
| `importlib` | Dynamic module loading |
| `pathlib` | Path manipulation |
| `subprocess` | Process execution (Gemini helper) |
| `json` | JSON parsing (Gemini helper) |
| `textwrap` | Text formatting (Gemini helper) |
| `shutil` | Shell utilities (Gemini helper) |
| `time` | Timing and sleeps (Gemini helper) |

### No external packages required

The repository intentionally avoids external dependencies for core utilities.

## Development dependencies

### Testing

| Tool | Purpose | Installation |
|------|---------|--------------|
| `pytest` | Test runner | `pip install pytest` (optional) |

Built-in test runner available via:
```bash
python tests/test_utils.py
```

### Validation

| Tool | Purpose |
|------|---------|
| `jq` | JSON syntax validation |
| `rg` | Pattern search in prompts |

## Agent-specific dependencies

| Agent | Additional requirements |
|-------|------------------------|
| OpenCode | `opencode` CLI installed |
| Claude Code | `claude` CLI installed |
| VSCode Copilot | VSCode with Copilot extension |
| Cursor | Cursor IDE |
| Windsurf | Windsurf IDE |
| Gemini CLI | `gemini` CLI installed |
| Warp | Warp terminal |
| Cline | VSCode with Cline extension |
| Roo Code | VSCode with Roo Code extension |
| Kilo Code | VSCode with Kilo Code extension |
| Pi | pi CLI tool |
| Copilot CLI | `gh copilot` CLI |
| Amp | Amp CLI |
| Codex | `codex` CLI |
| Antigravity | Antigravity CLI |

## Version compatibility

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.10 | 3.12+ |
| Git | 2.40 | 2.50+ |
| GitHub CLI | 2.30 | 2.90+ |

## Installation verification

Check installed versions:

```bash
git --version
gh --version
python3 --version
rg --version
jq --version
```

## See also

- [Configuration](configuration.md) — Configuring providers and models
- [Data models](data-models.md) — Internal data structures
- [Getting started](../overview/getting-started.md) — Installation guide
