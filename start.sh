#!/bin/bash
# Thin wrapper — forwards to scripts/start.sh
exec "$(dirname "$0")/scripts/start.sh" "$@"
