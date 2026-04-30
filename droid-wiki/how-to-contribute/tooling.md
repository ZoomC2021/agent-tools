# Tooling

Build system, validation tools, and development utilities.

## Repository structure

```
agent-tools/
├── prompts/           # Agent prompts and workflows
│   ├── opencode/     # Primary orchestrator architecture
│   │   ├── agent/    # Agent definitions
│   │   ├── commands/ # Workflow prompts
│   │   ├── bin/      # Helper scripts
│   │   └── evals/    # Eval harness
│   └── <agent>/      # Other agent targets
├── scripts/          # Installer scripts
│   ├── install.sh    # macOS/Linux installer
│   └── install.ps1   # Windows installer
├── tests/            # Test files
│   └── test_utils.py # Python utility tests
├── utils.py          # Shared Python utilities
├── README.md         # User documentation
└── AGENTS.md         # Contributor guidelines
```

## Installer scripts

### install.sh (macOS/Linux)

- Detects OS (macOS vs Linux)
- Installs to platform-appropriate paths
- Supports selective agent installation
- Color-coded logging

Usage:

```bash
# Install all agents
./scripts/install.sh

# Install specific agents
./scripts/install.sh claude codex opencode
```

### install.ps1 (Windows)

PowerShell equivalent with similar functionality.

## Helper scripts

### opencode-gemini-review

Located at `prompts/opencode/bin/opencode-gemini-review`. Python script for:
- Building deterministic review bundles
- Chunking large diffs for Gemini CLI
- Managing retries and partial failures
- Writing structured summary output

### opencode-eval

Located at `prompts/opencode/bin/opencode-eval`. Test harness for:
- Listing configured eval scenarios
- Running scenarios with fixtures
- Dry-run mode for validation

### opencode_review_utils.py

Helper module with:
- Git operations (diff, untracked files)
- Failure classification
- Summary writing

## Python utilities

### utils.py

- `parse_date()` — Multi-format date parsing
- Used by helper scripts and potentially other tools

## Validation commands

### JSON validation

```bash
jq -e . prompts/opencode/opencode.json.example
```

### File reference check

```bash
jq -r '.. | strings | select(test("^\\{file:[^}]+\\}$")) | capture("^\\{file:(?<p>[^}]+)\\}$").p' \
  prompts/opencode/opencode.json.example | sort -u | while read ref; do
    [ -f "prompts/opencode/${ref#./}" ] || echo "MISS $ref"
  done
```

### Python tests

```bash
python tests/test_utils.py
```

### OpenCode eval

```bash
prompts/opencode/bin/opencode-eval list
prompts/opencode/bin/opencode-eval run --dry-run
```

## Dependencies

Runtime dependencies (user machines):
- Git
- GitHub CLI (`gh`)
- OpenCode
- Bash or PowerShell

Development dependencies:
- Python 3
- jq (for JSON validation)
- pytest (optional, for running tests)

## Adding new tools

When adding new helper scripts:
1. Place in `prompts/opencode/bin/` (for OpenCode-specific) or appropriate location
2. Add tests in `tests/test_utils.py` if applicable
3. Update installer if the tool needs distribution
4. Document in relevant prompts that use the tool
