#!/bin/bash
set -e
VENV="$HOME/.venvs/banseok3d"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -r "$(dirname "$0")/requirements.txt"
echo "ready: source $VENV/bin/activate"
