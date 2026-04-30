# Development workflow

The standard branch, code, test, and PR cycle for agent-tools.

## Branch strategy

The repository uses a simple main-branch workflow:

1. **Create feature branch** from `main`
2. **Make focused commits** by agent/workflow area
3. **Open PR** against `main`
4. **Merge** via squash or merge commit

## Making changes

### Prompt changes

```bash
# Edit the prompt file
vim prompts/opencode/commands/review.md

# If it's an OpenCode change, sync the example config
# Check if file references need updating in opencode.json.example
```

### Adding new agent support

1. Create directory: `mkdir prompts/newagent`
2. Add workflow prompts (review.md, refactor.md, etc.)
3. Update `scripts/install.sh` with install logic
4. Update `scripts/install.ps1` with Windows install logic
5. Add to README.md agent table
6. Test installer: `./scripts/install.sh newagent`

### Installer changes

Keep macOS and Linux paths aligned. Test both:

```bash
# macOS
./scripts/install.sh

# Linux (if available)
./scripts/install.sh
```

## Testing before PR

### Python tests

```bash
python tests/test_utils.py
```

### OpenCode validation (if applicable)

```bash
# Inspect eval matrix
prompts/opencode/bin/opencode-eval list

# Dry run
prompts/opencode/bin/opencode-eval run --dry-run
```

### Config validation (if opencode.json.example changed)

```bash
jq -e . prompts/opencode/opencode.json.example

# Check file references resolve
jq -r '.. | strings | select(test("^\\{file:[^}]+\\}$")) | capture("^\\{file:(?<p>[^}]+)\\}$").p' \
  prompts/opencode/opencode.json.example | sort -u | while read ref; do
    [ -f "prompts/opencode/${ref#./}" ] || echo "MISS $ref"
  done
```

## PR structure

A good PR:

1. **Focused scope** — One agent or workflow per PR
2. **Clear title** — `feat(opencode): add handoff command`
3. **Explains "why"** — What problem does this solve?
4. **Validation evidence** — "Tested with `python tests/test_utils.py`"

Example PR description:

```
Add handoff command to all agent harnesses

The handoff command generates context for continuing work in a new
session. This is useful for long-running tasks that span multiple
conversations.

Changes:
- Added handoff.md to prompts/opencode/commands/
- Added handoff/SKILL.md to prompts/windsurf/
- Updated installer scripts to copy handoff files
- Updated README with handoff documentation

Validation:
- Ran `python tests/test_utils.py` — all passed
- Verified installer with `./scripts/install.sh opencode windsurf`
```
