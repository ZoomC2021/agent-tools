#!/bin/bash

# set-worker-model.sh — single source of truth for the OpenCode worker model.
#
# Changes the model used by the worker subagents (worker-general, worker-explore)
# everywhere it is referenced, from one command:
#   - prompts/opencode/opencode.json.example  (the canonical "model" fields)
#   - prompts/opencode/agent/worker-*.md       (frontmatter "model:")
#   - README.md                                (subagent table "Model" column)
#
# Scope note: this intentionally touches ONLY the two worker subagents. The
# orchestrators (worker-worker, frontier-worker) and the widereview review-CLI lanes are
# separate model "slots" — change those directly if/when they diverge.
#
# Usage:
#   scripts/set-worker-model.sh <provider/model>
#   scripts/set-worker-model.sh tokenrouter/MiniMax-M4
#
# Idempotent: re-running with the same value is a no-op. Run with no args to
# print the current worker model.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

CONFIG_FILE="$REPO_DIR/prompts/opencode/opencode.json.example"
WORKER_FILES=(
    "$REPO_DIR/prompts/opencode/agent/worker-general.md"
    "$REPO_DIR/prompts/opencode/agent/worker-explore.md"
)
README_FILE="$REPO_DIR/README.md"

# Agents whose "model" field in opencode.json is the worker model.
WORKER_AGENTS=("worker-general" "worker-explore")

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1" >&2; }

require_jq() {
    if ! command -v jq >/dev/null 2>&1; then
        log_error "jq is required but not found on PATH."
        exit 1
    fi
}

current_model() {
    jq -r --arg a "${WORKER_AGENTS[0]}" '.agent[$a].model // empty' "$CONFIG_FILE"
}

main() {
    require_jq

    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Config not found: $CONFIG_FILE"
        exit 1
    fi

    local old_model
    old_model="$(current_model)"

    if [[ $# -eq 0 ]]; then
        log_info "Current worker model: ${old_model:-<unset>}"
        echo "Usage: $(basename "$0") <provider/model>"
        exit 0
    fi

    local new_model="$1"
    local display="${new_model##*/}"   # strip provider prefix for human-facing docs

    if [[ "$new_model" == "$old_model" ]]; then
        log_info "Worker model already set to '$new_model' — nothing to do."
        exit 0
    fi

    log_info "Changing worker model: '${old_model:-<unset>}' -> '$new_model' (display: '$display')"

    # 1) opencode.json.example — the canonical model fields (block-scoped).
    for agent in "${WORKER_AGENTS[@]}"; do
        AGENT="$agent" MODEL="$new_model" perl -0777 -i -pe '
            my ($agent, $model) = ($ENV{AGENT}, $ENV{MODEL});
            s/("\Q$agent\E"\s*:\s*\{.*?"model"\s*:\s*")[^"]*(")/$1$model$2/s;
        ' "$CONFIG_FILE"
    done

    # 2) Worker agent frontmatter "model:" lines.
    for f in "${WORKER_FILES[@]}"; do
        [[ -f "$f" ]] || { log_warn "Skipping missing file: $f"; continue; }
        MODEL="$new_model" perl -i -pe '
            if (!$done && /^model:\s*/) { $_ = "model: $ENV{MODEL}\n"; $done = 1; }
        ' "$f"
    done

    # 3) README subagent table — Model column for the worker rows (display name).
    if [[ -f "$README_FILE" ]]; then
        OLD="${old_model##*/}" NEW="$display" perl -i -pe '
            my ($old, $new) = ($ENV{OLD}, $ENV{NEW});
            if (/^\|\s*\*\*worker-(general|explore)\*\*\s*\|/) {
                s/\Q$old\E/$new/g;
            }
        ' "$README_FILE"
    fi

    # Validate the JSON we just edited.
    if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
        log_error "opencode.json.example is no longer valid JSON after edit — review changes."
        exit 1
    fi

    local confirmed
    confirmed="$(current_model)"
    if [[ "$confirmed" != "$new_model" ]]; then
        log_error "Post-edit verification failed: config still reports '$confirmed'."
        exit 1
    fi

    log_success "Worker model set to '$new_model'."
    log_info "If the provider/model is new, also add its definition to the 'provider' block in $CONFIG_FILE."
    log_info "Then reinstall (scripts/install.sh) to sync installed agent frontmatter."
}

main "$@"
