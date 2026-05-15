#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PROTON_DIR="$SCRIPT_DIR/proton"

# --- Python venv setup ---
if [ ! -f "$VENV/bin/python" ]; then
    echo "Setting up Python environment (first run)..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet PyQt5 requests pytest
fi

# --- Proton-GE download ---
if [ ! -d "$PROTON_DIR" ]; then
    echo "Downloading Proton-GE (first run, ~500 MB)..."
    RELEASE_JSON=$(curl -sf https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest)
    if [ -z "$RELEASE_JSON" ]; then
        echo "ERROR: Could not reach GitHub API. Check your internet connection." >&2
        echo "To install manually: download a Proton-GE .tar.gz from" >&2
        echo "https://github.com/GloriousEggroll/proton-ge-custom/releases" >&2
        echo "and extract it to $PROTON_DIR" >&2
        exit 1
    fi
    TARBALL_URL=$(echo "$RELEASE_JSON" | "$VENV/bin/python" -c \
        "import sys,json; d=json.load(sys.stdin); print(next(a['browser_download_url'] for a in d['assets'] if a['name'].endswith('.tar.gz')))")
    TARBALL_NAME=$(basename "$TARBALL_URL")
    echo "  Downloading $TARBALL_NAME..."
    curl -L --progress-bar -o "/tmp/$TARBALL_NAME" "$TARBALL_URL"
    echo "  Extracting..."
    mkdir -p "$PROTON_DIR"
    tar -xzf "/tmp/$TARBALL_NAME" -C "$PROTON_DIR" --strip-components=1
    rm "/tmp/$TARBALL_NAME"
    echo "  Proton-GE ready."
fi

exec "$VENV/bin/python" "$SCRIPT_DIR/launcher.py"
