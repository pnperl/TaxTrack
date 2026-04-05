#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-5000}"
HOST="0.0.0.0"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

LOCAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
if [[ -z "${LOCAL_IP}" ]]; then
  LOCAL_IP="<your-computer-ip>"
fi

echo "Starting TaxTrack Pro for mobile access..."
echo "Open on your phone (same Wi-Fi): http://${LOCAL_IP}:${PORT}"
echo "Press Ctrl+C to stop."

python app.py
