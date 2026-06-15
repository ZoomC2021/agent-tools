#!/bin/bash

# Launch Claude Code through b.ai's Anthropic-compatible endpoint.
#
# Usage:
#   export BAI_API_KEY=sk-...
#   scripts/claude-bai.sh
#   scripts/claude-bai.sh -p "Reply with exactly: OK"
#   scripts/claude-bai.sh --model claude-opus-4.8
#
# Defaults to claude-opus-4.8. Override with ANTHROPIC_MODEL, CLAUDE_MODEL,
# or Claude Code's own --model flag.

set -euo pipefail

MODEL="${ANTHROPIC_MODEL:-${CLAUDE_MODEL:-claude-opus-4.8}}"
BASE_URL="${ANTHROPIC_BASE_URL:-https://api.b.ai}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage:
  export BAI_API_KEY=sk-...
  scripts/claude-bai.sh [claude args...]

Environment:
  BAI_API_KEY            b.ai API key. Preferred.
  ANTHROPIC_API_KEY      Alternative b.ai API key variable.
  ANTHROPIC_AUTH_TOKEN   Alternative b.ai API key variable.
  ANTHROPIC_MODEL        Model to use. Default: claude-opus-4.8.
  CLAUDE_MODEL           Model fallback when ANTHROPIC_MODEL is unset.
  ANTHROPIC_BASE_URL     Default: https://api.b.ai

Examples:
  scripts/claude-bai.sh
  scripts/claude-bai.sh -p "Reply with exactly: OK"
  ANTHROPIC_MODEL=claude-opus-4.8 scripts/claude-bai.sh

Claude Code is launched with --dangerously-skip-permissions.
EOF
    exit 0
fi

if [[ -n "${BAI_API_KEY:-}" ]]; then
    export ANTHROPIC_API_KEY="$BAI_API_KEY"
    export ANTHROPIC_AUTH_TOKEN="$BAI_API_KEY"
elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    export ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
    export ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-$ANTHROPIC_API_KEY}"
elif [[ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
    export ANTHROPIC_API_KEY="$ANTHROPIC_AUTH_TOKEN"
else
    echo "error: set BAI_API_KEY, ANTHROPIC_API_KEY, or ANTHROPIC_AUTH_TOKEN" >&2
    exit 1
fi

export ANTHROPIC_BASE_URL="$BASE_URL"
export ANTHROPIC_MODEL="$MODEL"

if [[ -x /opt/homebrew/bin/claude ]]; then
    CLAUDE_BIN="/opt/homebrew/bin/claude"
elif command -v claude >/dev/null 2>&1; then
    CLAUDE_BIN="$(command -v claude)"
else
    echo "error: claude not found on PATH" >&2
    exit 1
fi

exec "$CLAUDE_BIN" --dangerously-skip-permissions --model "$MODEL" "$@"
