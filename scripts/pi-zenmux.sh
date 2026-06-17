#!/bin/bash

# Launch Pi through the local ZenMux throttle proxy.
#
# Usage:
#   scripts/pi-zenmux.sh
#   scripts/pi-zenmux.sh -p "Reply with exactly: OK"
#   PI_ZENMUX_MODEL=moonshotai/kimi-k2.7-code-free scripts/pi-zenmux.sh
#
# The script starts prompts/opencode/bin/zenmux-throttle-proxy when needed,
# creates a temporary Pi agent config whose zenmux provider points at the proxy,
# then launches pi with provider=zenmux. Your real ~/.pi/agent/models.json is
# left untouched.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROXY_BIN="$REPO_DIR/prompts/opencode/bin/zenmux-throttle-proxy"

HOST="${ZENMUX_PROXY_HOST:-127.0.0.1}"
PORT="${ZENMUX_PROXY_PORT:-8787}"
PROXY_BASE_URL="http://$HOST:$PORT/zenmux"
MODEL="${PI_ZENMUX_MODEL:-z-ai/glm-5.2-free}"
REAL_AGENT_DIR="${PI_CODING_AGENT_SOURCE_DIR:-$HOME/.pi/agent}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat <<'EOF'
Usage:
  scripts/pi-zenmux.sh [pi args...]

Environment:
  PI_ZENMUX_MODEL              ZenMux model to use. Default: z-ai/glm-5.2-free.
  PI_CODING_AGENT_SOURCE_DIR   Source Pi config dir. Default: ~/.pi/agent.
  ZENMUX_PROXY_HOST            Proxy host. Default: 127.0.0.1.
  ZENMUX_PROXY_PORT            Proxy port. Default: 8787.
  ZENMUX_RPM                   Proxy ZenMux RPM cap. Default: 9.
  ZENMUX_API_KEY               Used only if your models.json has no zenmux provider.

Examples:
  scripts/pi-zenmux.sh
  scripts/pi-zenmux.sh -p "Reply with exactly: OK"
  PI_ZENMUX_MODEL=moonshotai/kimi-k2.7-code-free scripts/pi-zenmux.sh

The wrapper launches pi with --provider zenmux and --model PI_ZENMUX_MODEL
unless you pass your own --provider or --model arguments.
EOF
    exit 0
fi

if [[ ! -x "$PROXY_BIN" ]]; then
    echo "error: throttle proxy not found or not executable: $PROXY_BIN" >&2
    exit 1
fi

if [[ -x /opt/homebrew/bin/pi ]]; then
    PI_BIN="/opt/homebrew/bin/pi"
elif command -v pi >/dev/null 2>&1; then
    PI_BIN="$(command -v pi)"
else
    echo "error: pi not found on PATH" >&2
    exit 1
fi

if [[ ! -f "$REAL_AGENT_DIR/models.json" ]]; then
    echo "error: Pi models config not found: $REAL_AGENT_DIR/models.json" >&2
    exit 1
fi

if ! command -v node >/dev/null 2>&1; then
    echo "error: node not found on PATH; required for zenmux-throttle-proxy" >&2
    exit 1
fi

proxy_started=0
proxy_pid=""
temp_agent_dir=""

cleanup() {
    local status=$?
    if [[ -n "$proxy_pid" ]] && kill -0 "$proxy_pid" >/dev/null 2>&1; then
        kill "$proxy_pid" >/dev/null 2>&1 || true
    fi
    if [[ -n "$temp_agent_dir" ]]; then
        rm -rf "$temp_agent_dir"
    fi
    exit "$status"
}
trap cleanup EXIT INT TERM

health_url="http://$HOST:$PORT/healthz"
if ! curl -fsS --max-time 1 "$health_url" >/dev/null 2>&1; then
    "$PROXY_BIN" >/tmp/pi-zenmux-throttle-proxy.log 2>&1 &
    proxy_pid=$!
    proxy_started=1
    for _ in {1..50}; do
        if curl -fsS --max-time 1 "$health_url" >/dev/null 2>&1; then
            break
        fi
        if ! kill -0 "$proxy_pid" >/dev/null 2>&1; then
            echo "error: throttle proxy exited early; see /tmp/pi-zenmux-throttle-proxy.log" >&2
            exit 1
        fi
        sleep 0.1
    done
fi

if ! curl -fsS --max-time 1 "$health_url" >/dev/null 2>&1; then
    echo "error: throttle proxy did not become healthy at $health_url" >&2
    exit 1
fi

temp_agent_dir="$(mktemp -d "${TMPDIR:-/tmp}/pi-zenmux-agent.XXXXXX")"
chmod 700 "$temp_agent_dir"

cp "$REAL_AGENT_DIR/models.json" "$temp_agent_dir/models.json"
for entry in auth.json settings.json trust.json prompts skills tools bin themes sessions; do
    if [[ -e "$REAL_AGENT_DIR/$entry" ]]; then
        ln -s "$REAL_AGENT_DIR/$entry" "$temp_agent_dir/$entry"
    fi
done

PI_ZENMUX_PROXY_BASE_URL="$PROXY_BASE_URL" PI_ZENMUX_MODEL_ID="$MODEL" python3 - <<'PY' "$temp_agent_dir/models.json"
import json
import os
import sys

path = sys.argv[1]
proxy_base_url = os.environ["PI_ZENMUX_PROXY_BASE_URL"]
model_id = os.environ["PI_ZENMUX_MODEL_ID"]

with open(path) as f:
    data = json.load(f)

providers = data.setdefault("providers", {})
zenmux = providers.setdefault("zenmux", {
    "baseUrl": "https://zenmux.ai/api/v1",
    "api": "openai-completions",
    "apiKey": "!printenv ZENMUX_API_KEY",
    "authHeader": True,
    "models": [],
})
zenmux["baseUrl"] = proxy_base_url
zenmux.setdefault("api", "openai-completions")
zenmux.setdefault("authHeader", True)
models = zenmux.setdefault("models", [])

if model_id == "z-ai/glm-5.2-free" and not any(m.get("id") == model_id for m in models):
    models.append({
        "id": "z-ai/glm-5.2-free",
        "name": "GLM-5.2 Free (ZenMux)",
        "reasoning": True,
        "input": ["text"],
        "contextWindow": 1000000,
        "maxTokens": 128000,
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
    })

with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY

has_provider=0
has_model=0
for arg in "$@"; do
    case "$arg" in
        --provider|--provider=*) has_provider=1 ;;
        --model|--model=*) has_model=1 ;;
    esac
done

pi_args=()
if [[ "$has_provider" -eq 0 ]]; then
    pi_args+=(--provider zenmux)
fi
if [[ "$has_model" -eq 0 ]]; then
    pi_args+=(--model "$MODEL")
fi

if [[ "$proxy_started" -eq 1 ]]; then
    echo "started ZenMux throttle proxy at $PROXY_BASE_URL" >&2
else
    echo "using existing ZenMux throttle proxy at $PROXY_BASE_URL" >&2
fi

PI_CODING_AGENT_DIR="$temp_agent_dir" "$PI_BIN" "${pi_args[@]}" "$@"
