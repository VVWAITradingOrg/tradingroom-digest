#!/bin/bash
# Recover the most recently due session after login without running a future slot early.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOUR="$(date +%H)"
if [ "$HOUR" -lt 6 ]; then
  echo "startup check: no session due"
  exit 0
fi
if [ "$HOUR" -lt 18 ]; then
  exec "$DIR/pipeline.sh" --session night
fi
exec "$DIR/pipeline.sh" --session day
