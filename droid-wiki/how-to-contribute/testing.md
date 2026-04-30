# Testing

How to run and validate changes in the agent-tools repository.

## Test structure

Tests are in `tests/test_utils.py`. They cover:
- `utils.py` — date parsing functions
- `prompts/opencode/bin/opencode-gemini-review` — chunking, failure classification, git operations

## Running tests

### Basic test run

```bash
python tests/test_utils.py
```

### With pytest (if available)

```bash
pytest tests/test_utils.py -v
```

## What the tests cover

### Date parsing (`utils.py`)

- Multiple formats: YYYY-MM-DD, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY
- Default value handling for None/empty/whitespace
- Invalid date handling (ValueError)
- Leap year handling
- Whitespace stripping

### Gemini review helper (`opencode-gemini-review`)

- **Chunk building** — Large files get their own chunk; small files group together
- **Failure classification** — Maps error messages to stable failure reasons (auth, rate_limited, missing_cli, timeout, etc.)
- **Git operations** — Handles missing git command gracefully
- **Gemini execution** — Uses subprocess timeout correctly (no unsupported CLI flags)

## Adding new tests

When modifying `utils.py` or the helper scripts, add corresponding tests:

```python
def test_new_function_case():
    """Test description."""
    result = new_function(input_value)
    assert result == expected_value
```

Add the test function to the `tests` list at the bottom of `test_utils.py`:

```python
tests = [
    # ... existing tests ...
    test_new_function_case,
]
```

## Validating prompt changes

### Broken link check

For prompt/doc-only changes:
- Check for broken internal references
- Ensure command examples match real files

### OpenCode eval (for opencode changes)

```bash
# List configured scenarios
prompts/opencode/bin/opencode-eval list

# Dry run without executing
prompts/opencode/bin/opencode-eval run --dry-run

# Run specific scenario
prompts/opencode/bin/opencode-eval run --scenario review-simple
```

### Config file check (for opencode.json.example changes)

```bash
# Validate JSON parses
jq -e . prompts/opencode/opencode.json.example

# Verify all {file:...} references resolve
jq -r '.. | strings | select(test("^\\{file:[^}]+\\}$")) | capture("^\\{file:(?<p>[^}]+)\\}$").p' \
  prompts/opencode/opencode.json.example | sort -u | while read ref; do
    [ -f "prompts/opencode/${ref#./}" ] || echo "MISS $ref"
  done
```

## CI considerations

The repository does not have CI configured. Manual validation is required before PR submission. Run the smallest relevant validation set for your changes.
