#!/bin/bash

# set-model.sh — single source of truth for swapping the model used by any
# OpenCode skill/subagent in this repo.
#
# Generalizes the old set-worker-model.sh (which only handled the two worker
# subagents) to any agent/skill by name. It keeps the three places a model is
# referenced in sync, from one command:
#   - prompts/opencode/opencode.json.example  (the canonical .agent[NAME].model)
#   - prompts/opencode/{agent,commands}/NAME.md  (frontmatter "model:")
#   - README.md                                (Subagent Reference "Model" column)
#
# The canonical source of truth is opencode.json.example. install.sh re-syncs
# the .md frontmatter from it on install; this script edits the repo copies too
# so the working tree stays coherent before an install.
#
# Usage:
#   scripts/set-model.sh                         # list every agent and its model
#   scripts/set-model.sh <name> [<name>...]      # show the model for these agents
#   scripts/set-model.sh <name> [<name>...] <provider/model>
#   scripts/set-model.sh all <provider/model>    # set every agent at once
#
# Examples:
#   scripts/set-model.sh plan-review xiaomi/mimo-v2.5-pro
#   scripts/set-model.sh review change-auditor openai/gpt-5.5
#   scripts/set-model.sh worker-general worker-explore tokenrouter/MiniMax-M4
#
# The model argument is recognized as the LAST argument that contains a "/".
# Anything before it is treated as a target name. "all" expands to every key
# under .agent in the config.
#
# Idempotent: re-running with the same value is a no-op. If a provider/model is
# new, add its definition to the "provider" block in opencode.json.example, then
# reinstall (scripts/install.sh) to sync installed agent frontmatter.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

CONFIG_FILE="$REPO_DIR/prompts/opencode/opencode.json.example"
CONFIG_DIR="$(dirname "$CONFIG_FILE")"
README_FILE="$REPO_DIR/README.md"

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

# Map a provider/model id to the human-facing display name used in the README
# "Model" column. Unknown models fall back to the bare model id (provider
# prefix stripped) and trigger a warning so the README can be reviewed by hand.
display_name() {
    case "$1" in
        tokenrouter/MiniMax-M3)            echo "MiniMax-M3" ;;
        tokenrouter/MiniMax-M4)            echo "MiniMax-M4" ;;
        xiaomi/mimo-v2.5-pro)              echo "MiMo v2.5 Pro" ;;
        openai/gpt-5.5)                    echo "GPT-5.5" ;;
        xai/grok-imagine-image-quality)    echo "xAI Grok Imagine Image Quality" ;;
        google/gemini-3-pro-image-preview) echo "Gemini 3 Pro Image Preview" ;;
        zenmux/z-ai/glm-5.2-free)          echo "GLM-5.2 Free (ZenMux)" ;;
        zenmux/moonshotai/kimi-k2.7-code-free) echo "Kimi K2.7 Code Free (ZenMux)" ;;
        *)                                 echo "" ;;  # signal: unknown
    esac
}

agent_exists() {
    jq -e --arg n "$1" '.agent | has($n)' "$CONFIG_FILE" >/dev/null 2>&1
}

agent_model() {
    jq -r --arg n "$1" '.agent[$n].model // empty' "$CONFIG_FILE"
}

all_agents() {
    jq -r '.agent | keys[]' "$CONFIG_FILE"
}

list_all() {
    log_info "Agents and their models (from $(basename "$CONFIG_FILE")):"
    jq -r '.agent | to_entries[] | "  \(.key)\t\(.value.model // "<inherits parent>")"' "$CONFIG_FILE" \
        | column -t -s $'\t'
}

# Resolve the prompt .md file for an agent from its {file:...} prompt field.
prompt_file_for() {
    local name="$1" prompt rel
    prompt="$(jq -r --arg n "$name" '.agent[$n].prompt // empty' "$CONFIG_FILE")"
    [[ "$prompt" =~ ^\{file:(.+)\}$ ]] || return 1
    rel="${BASH_REMATCH[1]}"
    if [[ "$rel" = /* ]]; then
        echo "$rel"
    else
        echo "$CONFIG_DIR/${rel#./}"
    fi
}

# Rewrite the first frontmatter "model:" line of a .md file in place.
update_frontmatter() {
    local file="$1" model="$2" tmp
    [[ -f "$file" ]] || return 1
    tmp="$(mktemp)"
    awk -v new_model="$model" '
        NR==1 && $0=="---" { in_fm=1; print; next }
        in_fm && !replaced && $0 ~ /^model:[[:space:]]*/ {
            print "model: " new_model; replaced=1; next
        }
        in_fm && $0=="---" { in_fm=0; print; next }
        { print }
        END { exit (replaced ? 0 : 2) }
    ' "$file" > "$tmp"
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        rm -f "$tmp"
        return $rc
    fi
    mv "$tmp" "$file"
}

# Replace the "Model" (3rd) column of the README table row for an agent.
update_readme_row() {
    local name="$1" display="$2"
    [[ -f "$README_FILE" ]] || return 1
    NAME="$name" DISPLAY="$display" perl -i -pe '
        my ($name, $display) = ($ENV{NAME}, $ENV{DISPLAY});
        if (/^\|\s*\*\*\Q$name\E\*\*\s*\|/) {
            my @f = split /\|/, $_, -1;
            # fields: [0]="" [1]=name [2]=purpose [3]=model [4]=effort [5]=trailing
            if (@f >= 5) { $f[3] = " $display "; $_ = join("|", @f); }
        }
    ' "$README_FILE"
}

main() {
    require_jq

    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Config not found: $CONFIG_FILE"
        exit 1
    fi

    # No args: list everything.
    if [[ $# -eq 0 ]]; then
        list_all
        echo
        echo "Usage: $(basename "$0") <name> [<name>...] <provider/model>"
        exit 0
    fi

    # Determine whether a model was supplied: the last arg contains a "/".
    local last="${*: -1}"
    local new_model="" targets=()

    if [[ "$last" == */* ]]; then
        new_model="$last"
        targets=("${@:1:$#-1}")
        if [[ ${#targets[@]} -eq 0 ]]; then
            log_error "No target agent given. Usage: $(basename "$0") <name> [<name>...] <provider/model>"
            exit 1
        fi
    else
        # Query mode: print the model for each named agent.
        local missing=0
        for t in "$@"; do
            if agent_exists "$t"; then
                log_info "$t -> $(agent_model "$t" || echo '<inherits parent>')"
            else
                log_error "Unknown agent: $t"
                missing=1
            fi
        done
        exit $missing
    fi

    # Expand "all" and validate every target up front.
    local expanded=()
    for t in "${targets[@]}"; do
        if [[ "$t" == "all" ]]; then
            while IFS= read -r a; do expanded+=("$a"); done < <(all_agents)
        else
            expanded+=("$t")
        fi
    done

    local unknown=()
    for t in "${expanded[@]}"; do
        agent_exists "$t" || unknown+=("$t")
    done
    if [[ ${#unknown[@]} -gt 0 ]]; then
        log_error "Unknown agent(s): ${unknown[*]}"
        log_info "Run with no args to list valid names."
        exit 1
    fi

    local display
    display="$(display_name "$new_model")"
    if [[ -z "$display" ]]; then
        log_warn "Unknown model '$new_model' has no README display name; using bare id."
        display="${new_model##*/}"
    fi

    local changed=0
    for t in "${expanded[@]}"; do
        local old
        old="$(agent_model "$t")"
        if [[ "$old" == "$new_model" ]]; then
            log_info "$t already '$new_model' — skipping."
            continue
        fi
        changed=1
        log_info "$t: '${old:-<unset>}' -> '$new_model'"

        # 1) Canonical config model.
        local tmp
        tmp="$(mktemp)"
        jq --arg n "$t" --arg m "$new_model" '.agent[$n].model = $m' "$CONFIG_FILE" > "$tmp"
        mv "$tmp" "$CONFIG_FILE"

        # 2) Repo .md frontmatter (skip built-in agents with no prompt file).
        local pf
        if pf="$(prompt_file_for "$t")" && [[ -f "$pf" ]]; then
            if ! update_frontmatter "$pf" "$new_model"; then
                log_warn "  no frontmatter 'model:' line in $pf — left unchanged"
            fi
        fi

        # 3) README Model column (skip agents with no table row).
        update_readme_row "$t" "$display"
    done

    if [[ $changed -eq 0 ]]; then
        log_info "Nothing to change."
        exit 0
    fi

    # Validate the JSON we just edited.
    if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
        log_error "opencode.json.example is no longer valid JSON after edit — review changes."
        exit 1
    fi

    # Verify each target now reports the new model.
    for t in "${expanded[@]}"; do
        local got
        got="$(agent_model "$t")"
        if [[ "$got" != "$new_model" ]]; then
            log_error "Post-edit verification failed for '$t': config reports '$got'."
            exit 1
        fi
    done

    log_success "Set ${#expanded[@]} agent(s) to '$new_model'."
    log_info "If the provider/model is new, add its definition to the 'provider' block in $CONFIG_FILE."
    log_info "Then reinstall (scripts/install.sh) to sync installed agent frontmatter."
}

main "$@"
