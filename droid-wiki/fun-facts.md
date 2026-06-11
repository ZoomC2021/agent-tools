# Fun facts

## Oldest surviving code

The `utils.py` file contains the oldest continuously-used code. The `parse_date()` function has remained largely unchanged since early repository history, providing consistent date parsing across multiple formats (YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY).

## TODO/FIXME archaeology

The codebase has relatively few accumulated TODOs because:
- Prompts are self-contained and specify complete workflows
- The AGENTS.md explicitly discourages leaving TODOs in prompts
- Fast iteration cycles mean issues are resolved quickly

## File count champion

The `prompts/opencode/opencode.json.example` is the largest single file by line count (~800 lines). It serves as the authoritative configuration source for the entire OpenCode agent architecture.

## Format diversity

Supporting 14 different AI agents means the repository speaks multiple "dialects":
- Markdown with YAML frontmatter (most agents)
- SKILL.md format (Windsurf, Amp, Gemini CLI)
- .agent.md suffix (VSCode Copilot)
- YAML (Warp workflows)

## Naming origins

- **Deslop**: Named after the open-source deslop utility for code quality audits
- **Ultrareview**: The "ultra" signifies the dual-model parallel execution
- **Codex53-MiMo**: GPT 5.5 (the orchestrator model) + MiMo (the subagent model)
- **Oracle**: The name for the deep-reasoning GPT-5.5 agent you consult for wisdom

## Skill location trivia

The installer supports 14 agents but needs to know 14+ different config directory paths:
- macOS: `~/Library/Application Support/...`
- Linux: `~/.config/...` or `~/.local/share/...`
- XDG paths, APPDATA on Windows

The `scripts/install.sh` and `scripts/install.ps1` abstract all of this.
