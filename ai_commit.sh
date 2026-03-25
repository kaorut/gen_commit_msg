#!/usr/bin/env sh

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_PYTHON="$SCRIPT_DIR/venv_linux/bin/python3"
TARGET_SCRIPT="$SCRIPT_DIR/ai_commit.py"

# Try to use venv Python first.
if [ -x "$VENV_PYTHON" ]; then
    PYTHON_CMD="$VENV_PYTHON"
else
    # Fallback to system Python if venv is not available.
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD=$(command -v python3)
    elif command -v python >/dev/null 2>&1; then
        PYTHON_CMD=$(command -v python)
    else
        echo "[ERROR] Python is required but not found." >&2
        echo "Expected either:" >&2
        echo "  1. Virtual environment at: $VENV_PYTHON" >&2
        echo "  2. python3 or python in PATH (system installation)" >&2
        exit 1
    fi
fi

if [ ! -f "$TARGET_SCRIPT" ]; then
    echo "[ERROR] Script not found: $TARGET_SCRIPT" >&2
    exit 1
fi

exec "$PYTHON_CMD" "$TARGET_SCRIPT" "$@"
