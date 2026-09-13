#!/bin/bash
# 批量补历史日报（整天模式，old 格式，不发 Discord/vvwbot）。复用 pipeline.sh。
#
# 用法: backfill.sh              （跑 exports/daily 下所有还没生成 digest 的历史日期）
#      backfill.sh --one 日期   （单天，内部用，也可以手动调）
set -uo pipefail
DIR="$HOME/Desktop/tradingroom-digest"
cd "$DIR"
mkdir -p exports/daily/digests logs

if [ "${1:-}" = "--one" ]; then
  d="$2"
  next="$(date -j -v+1d -f %Y-%m-%d "$d" +%F)"
  bash pipeline.sh --session full --window "$d 00:00" "$next 00:00" --no-deliver \
    > "logs/digest_$d.log" 2>&1
  if [ -s "exports/daily/digests/$d.md" ]; then echo "OK   $d"; else echo "FAIL $d (见 logs/digest_$d.log)"; fi
  exit 0
fi

DAYS=$(ls exports/daily/*.txt 2>/dev/null | sed 's|.*/||; s|\.txt$||' | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | sort)
if [ -z "$DAYS" ]; then
  echo "exports/daily/ 下没有整天格式的历史 txt，先用 pipeline.sh --session full --window ... 抓一天再跑本脚本" >&2
  exit 1
fi
TODO=$(comm -23 <(echo "$DAYS") <(ls exports/daily/digests/*.md 2>/dev/null | sed 's|.*/||; s|\.md$||' | grep -vE '\.(day|night)$' | sort))
echo "待处理: $(echo "$TODO" | grep -c .) 天"
echo "$TODO" | xargs -P 1 -I{} bash "$DIR/backfill.sh" --one {}
echo "全部结束，生成 $(ls exports/daily/digests/*.md 2>/dev/null | grep -cvE '\.(day|night)\.md$') 份整天日报"
