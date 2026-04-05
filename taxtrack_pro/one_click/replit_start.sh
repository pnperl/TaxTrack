#!/usr/bin/env bash
set -euo pipefail

# One-click start for Replit (works whether run from repo root or taxtrack_pro/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${APP_DIR}"

PORT="${PORT:-8080}"
python -m pip install --upgrade pip
pip install -r requirements.txt
echo "Starting on 0.0.0.0:${PORT}"
exec gunicorn -w 2 -b 0.0.0.0:${PORT} app:app
