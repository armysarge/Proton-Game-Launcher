#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
if [ ! -f "$VENV/bin/pytest" ]; then
    echo "Run run.sh first to set up the environment." >&2
    exit 1
fi
exec "$VENV/bin/pytest" "$SCRIPT_DIR/tests/" -v "$@"
