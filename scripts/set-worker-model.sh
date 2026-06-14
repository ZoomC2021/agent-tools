#!/bin/bash

# set-worker-model.sh — backwards-compatible shim.
#
# The worker subagents are no longer a special case: model swapping is now
# handled for ANY skill/subagent by scripts/set-model.sh. This shim preserves
# the old entry point by forwarding to set-model.sh for the two worker agents.
#
# Usage:
#   scripts/set-worker-model.sh                 # show the worker models
#   scripts/set-worker-model.sh <provider/model>  # set both worker agents
#
# Prefer calling set-model.sh directly:
#   scripts/set-model.sh worker-general worker-explore <provider/model>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
    exec "$SCRIPT_DIR/set-model.sh" worker-general worker-explore
fi

exec "$SCRIPT_DIR/set-model.sh" worker-general worker-explore "$1"
