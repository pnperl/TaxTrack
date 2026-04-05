#!/usr/bin/env bash
set -euo pipefail

# Works if current folder is taxtrack_pro OR parent repo
if [[ -f "one_click/replit_start.sh" ]]; then
  exec bash one_click/replit_start.sh
elif [[ -f "taxtrack_pro/one_click/replit_start.sh" ]]; then
  exec bash taxtrack_pro/one_click/replit_start.sh
else
  echo "Could not find one_click/replit_start.sh"
  exit 1
fi
