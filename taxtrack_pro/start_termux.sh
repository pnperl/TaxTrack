#!/usr/bin/env bash
set -euo pipefail
if [[ -f "one_click/termux_start.sh" ]]; then
  exec bash one_click/termux_start.sh
elif [[ -f "taxtrack_pro/one_click/termux_start.sh" ]]; then
  exec bash taxtrack_pro/one_click/termux_start.sh
else
  echo "Could not find one_click/termux_start.sh"
  exit 1
fi
