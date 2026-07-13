#!/bin/bash

exec /bin/bash "$(dirname "$0")/claude-provider.sh" bai "$@"
