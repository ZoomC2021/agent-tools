#!/bin/bash

# Launch Codex through ccapi.us's OpenAI-compatible endpoint.
#
# Usage:
#   export CCAPI_API_KEY=sk-...
#   scripts/codex-ccapi.sh
#   scripts/codex-ccapi.sh "Reply with exactly: OK"
#   scripts/codex-ccapi.sh --model gpt-5.5
#
# Defaults to gpt-5.5. Override with OPENAI_MODEL, CODEX_MODEL,
# or Codex's own --model flag.

set -euo pipefail

MODEL="${OPENAI_MODEL:-${CODEX_MODEL:-gpt-5.5}}"
BASE_URL="${OPENAI_BASE_URL:-https://api-direct.ccapi.us/v1}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage:
  export CCAPI_API_KEY=sk-...
  scripts/codex-ccapi.sh [codex args...]

Environment:
  CCAPI_API_KEY       ccapi.us API key. Preferred.
  OPENAI_API_KEY      Alternative ccapi.us API key variable.
  OPENAI_MODEL        Model to use. Default: gpt-5.5.
  CODEX_MODEL         Model fallback when OPENAI_MODEL is unset.
  OPENAI_BASE_URL     Default: https://api-direct.ccapi.us/v1

Examples:
  scripts/codex-ccapi.sh
  scripts/codex-ccapi.sh "Reply with exactly: OK"
  OPENAI_MODEL=gpt-5.5 scripts/codex-ccapi.sh

Codex is launched with --dangerously-bypass-approvals-and-sandbox.
EOF
    exit 0
fi

if [[ -n "${CCAPI_API_KEY:-}" ]]; then
    export OPENAI_API_KEY="$CCAPI_API_KEY"
elif [[ -n "${OPENAI_API_KEY:-}" ]]; then
    export OPENAI_API_KEY="$OPENAI_API_KEY"
else
    echo "error: set CCAPI_API_KEY or OPENAI_API_KEY" >&2
    exit 1
fi

if [[ -x /opt/homebrew/bin/codex ]]; then
    CODEX_BIN="/opt/homebrew/bin/codex"
elif command -v codex >/dev/null 2>&1; then
    CODEX_BIN="$(command -v codex)"
else
    echo "error: codex not found on PATH" >&2
    exit 1
fi

exec "$CODEX_BIN" \
    -c 'model_provider="ccapi"' \
    -c "model_providers.ccapi={name=\"ccapi\",base_url=\"$BASE_URL\",env_key=\"OPENAI_API_KEY\",wire_api=\"responses\"}" \
    --dangerously-bypass-approvals-and-sandbox \
    --model "$MODEL" \
    "$@"
