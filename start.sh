#!/bin/bash
# Thin wrapper — forwards to scripts/start.sh
exec "$(dirname "$0")/scripts/start.sh" "$@"

# Use the following to start the project:
# cd "Projects /Agent Forge" && ./start.sh
