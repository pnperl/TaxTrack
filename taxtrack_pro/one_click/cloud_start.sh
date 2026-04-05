#!/usr/bin/env bash
set -euo pipefail

# One-click start for Render/Railway shell
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${APP_DIR}"

PORT="${PORT:-8080}"
python -m pip install --upgrade pip
pip install -r requirements.txt
exec gunicorn -w 2 -b 0.0.0.0:${PORT} app:app
