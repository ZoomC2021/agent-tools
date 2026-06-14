#!/bin/bash

# Launch Claude Code through AgentRouter's Anthropic-compatible endpoint.
#
# Usage:
#   export AGENT_ROUTER_TOKEN=sk-...
#   scripts/claude-agentrouter.sh
#   scripts/claude-agentrouter.sh -p "Reply with exactly: OK"
#   scripts/claude-agentrouter.sh --model claude-sonnet-4-6
#
# Defaults to claude-sonnet-4-6. Override with ANTHROPIC_MODEL, CLAUDE_MODEL,
# or Claude Code's own --model flag.

set -euo pipefail

MODEL="${ANTHROPIC_MODEL:-${CLAUDE_MODEL:-claude-sonnet-4-6}}"
BASE_URL="${ANTHROPIC_BASE_URL:-https://agentrouter.org/}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage:
  export AGENT_ROUTER_TOKEN=sk-...
  scripts/claude-agentrouter.sh [claude args...]

Environment:
  AGENT_ROUTER_TOKEN     AgentRouter token. Preferred.
  ANTHROPIC_API_KEY      Alternative token variable.
  ANTHROPIC_AUTH_TOKEN   Alternative token variable.
  ANTHROPIC_MODEL        Model to use. Default: claude-sonnet-4-6.
  CLAUDE_MODEL           Model fallback when ANTHROPIC_MODEL is unset.
  ANTHROPIC_BASE_URL     Default: https://agentrouter.org/

Examples:
  scripts/claude-agentrouter.sh
  scripts/claude-agentrouter.sh -p "Reply with exactly: OK"
  ANTHROPIC_MODEL=claude-sonnet-4-6 scripts/claude-agentrouter.sh

Claude Code is launched with --dangerously-skip-permissions.
EOF
    exit 0
fi

if [[ -n "${AGENT_ROUTER_TOKEN:-}" ]]; then
    export ANTHROPIC_AUTH_TOKEN="$AGENT_ROUTER_TOKEN"
    export ANTHROPIC_API_KEY="$AGENT_ROUTER_TOKEN"
elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    export ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-$ANTHROPIC_API_KEY}"
elif [[ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
    export ANTHROPIC_API_KEY="$ANTHROPIC_AUTH_TOKEN"
else
    echo "error: set AGENT_ROUTER_TOKEN, ANTHROPIC_API_KEY, or ANTHROPIC_AUTH_TOKEN" >&2
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
