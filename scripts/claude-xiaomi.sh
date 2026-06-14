#!/bin/bash

# Launch Claude Code through Xiaomi MiMo's Anthropic-compatible endpoint.
#
# Usage:
#   export XIAOMI_API_KEY=...
#   scripts/claude-xiaomi.sh
#   scripts/claude-xiaomi.sh -p "Reply with exactly: OK"
#   scripts/claude-xiaomi.sh --model mimo-v2.5-pro
#
# Defaults to mimo-v2.5-pro. Override with ANTHROPIC_MODEL, CLAUDE_MODEL,
# or Claude Code's own --model flag.

set -euo pipefail

MODEL="${ANTHROPIC_MODEL:-${CLAUDE_MODEL:-mimo-v2.5-pro}}"
BASE_URL="${ANTHROPIC_BASE_URL:-https://token-plan-ams.xiaomimimo.com/anthropic}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage:
  export XIAOMI_API_KEY=...
  scripts/claude-xiaomi.sh [claude args...]

Environment:
  XIAOMI_API_KEY         Xiaomi MiMo token. Preferred.
  MIMO_API_KEY           Alternative Xiaomi MiMo token variable.
  ANTHROPIC_API_KEY      Alternative token variable.
  ANTHROPIC_AUTH_TOKEN   Alternative token variable.
  ANTHROPIC_MODEL        Model to use. Default: mimo-v2.5-pro.
  CLAUDE_MODEL           Model fallback when ANTHROPIC_MODEL is unset.
  ANTHROPIC_BASE_URL     Default: https://token-plan-ams.xiaomimimo.com/anthropic

Examples:
  scripts/claude-xiaomi.sh
  scripts/claude-xiaomi.sh -p "Reply with exactly: OK"
  ANTHROPIC_MODEL=mimo-v2.5-pro scripts/claude-xiaomi.sh

Claude Code is launched with --dangerously-skip-permissions.
EOF
    exit 0
fi

if [[ -n "${XIAOMI_API_KEY:-}" ]]; then
    export ANTHROPIC_AUTH_TOKEN="$XIAOMI_API_KEY"
    export ANTHROPIC_API_KEY="$XIAOMI_API_KEY"
elif [[ -n "${MIMO_API_KEY:-}" ]]; then
    export ANTHROPIC_AUTH_TOKEN="$MIMO_API_KEY"
    export ANTHROPIC_API_KEY="$MIMO_API_KEY"
elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    export ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-$ANTHROPIC_API_KEY}"
elif [[ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
    export ANTHROPIC_API_KEY="$ANTHROPIC_AUTH_TOKEN"
else
    echo "error: set XIAOMI_API_KEY, MIMO_API_KEY, ANTHROPIC_API_KEY, or ANTHROPIC_AUTH_TOKEN" >&2
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
