#!/usr/bin/env bash
set -euo pipefail
if [[ -f "one_click/cloud_start.sh" ]]; then
  exec bash one_click/cloud_start.sh
elif [[ -f "taxtrack_pro/one_click/cloud_start.sh" ]]; then
  exec bash taxtrack_pro/one_click/cloud_start.sh
else
  echo "Could not find one_click/cloud_start.sh"
  exit 1
fi
