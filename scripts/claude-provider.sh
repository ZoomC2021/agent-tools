#!/bin/bash

# Shared implementation for the provider-specific Claude Code launchers.

set -euo pipefail

PROVIDER="${1:-}"
shift || true

case "$PROVIDER" in
    agentrouter)
        MODEL="${ANTHROPIC_MODEL:-${CLAUDE_MODEL:-claude-sonnet-4-6}}"
        BASE_URL="${ANTHROPIC_BASE_URL:-https://agentrouter.org/}"
        HELP='Usage:
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

Claude Code is launched with --dangerously-skip-permissions.'
        PREFERRED="${AGENT_ROUTER_TOKEN:-}"
        ERROR='error: set AGENT_ROUTER_TOKEN, ANTHROPIC_API_KEY, or ANTHROPIC_AUTH_TOKEN'
        ;;
    bai)
        MODEL="${ANTHROPIC_MODEL:-${CLAUDE_MODEL:-claude-opus-4.8}}"
        BASE_URL="${ANTHROPIC_BASE_URL:-https://api.b.ai}"
        HELP='Usage:
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

Claude Code is launched with --dangerously-skip-permissions.'
        PREFERRED="${BAI_API_KEY:-}"
        ERROR='error: set BAI_API_KEY, ANTHROPIC_API_KEY, or ANTHROPIC_AUTH_TOKEN'
        ;;
    xiaomi)
        MODEL="${ANTHROPIC_MODEL:-${CLAUDE_MODEL:-mimo-v2.5-pro}}"
        BASE_URL="${ANTHROPIC_BASE_URL:-https://token-plan-ams.xiaomimimo.com/anthropic}"
        HELP='Usage:
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

Claude Code is launched with --dangerously-skip-permissions.'
        PREFERRED="${XIAOMI_API_KEY:-${MIMO_API_KEY:-}}"
        ERROR='error: set XIAOMI_API_KEY, MIMO_API_KEY, ANTHROPIC_API_KEY, or ANTHROPIC_AUTH_TOKEN'
        ;;
    *)
        echo "error: unknown Claude provider: $PROVIDER" >&2
        exit 1
        ;;
esac

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    printf '%s\n' "$HELP"
    exit 0
fi

if [[ -n "$PREFERRED" ]]; then
    export ANTHROPIC_AUTH_TOKEN="$PREFERRED"
    export ANTHROPIC_API_KEY="$PREFERRED"
elif [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
    export ANTHROPIC_AUTH_TOKEN="${ANTHROPIC_AUTH_TOKEN:-$ANTHROPIC_API_KEY}"
elif [[ -n "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
    export ANTHROPIC_API_KEY="$ANTHROPIC_AUTH_TOKEN"
else
    echo "$ERROR" >&2
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
