#!/usr/bin/env bash
set -euo pipefail

# One-click start for Termux (Android)
if command -v pkg >/dev/null 2>&1; then
  pkg update -y
  pkg install -y python git
fi

python -m venv .venv || true
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
exec python app.py
