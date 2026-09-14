#!/bin/bash
# Recover the most recently due session after login without running a future slot early.
# 三段：06:00 触发 -> night(昨晚18:00-今早06:00)；12:00 触发 -> morning(今早06:00-12:00)；
# 18:00 触发 -> afternoon(今天12:00-18:00)。
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOUR="$(date +%H)"
if [ "$HOUR" -lt 6 ]; then
  echo "startup check: no session due"
  exit 0
fi
if [ "$HOUR" -lt 12 ]; then
  exec "$DIR/pipeline.sh" --session night
fi
if [ "$HOUR" -lt 18 ]; then
  exec "$DIR/pipeline.sh" --session morning
fi
exec "$DIR/pipeline.sh" --session afternoon
