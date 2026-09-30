#!/bin/bash
# Recover the most recently due session after login without running a future slot early.
# 三段：06:00 触发 -> night(昨晚17:00-今早06:00)；11:00 触发 -> morning(今早06:00-11:00)；
# 17:00 触发 -> afternoon(今天11:00-17:00)。
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOUR="$(date +%H)"
if [ "$HOUR" -lt 6 ]; then
  echo "startup check: no session due"
  exit 0
fi
if [ "$HOUR" -lt 11 ]; then
  exec /usr/bin/python3 "$DIR/runtime.py" --session night
fi
if [ "$HOUR" -lt 17 ]; then
  exec /usr/bin/python3 "$DIR/runtime.py" --session morning
fi
exec /usr/bin/python3 "$DIR/runtime.py" --session afternoon
