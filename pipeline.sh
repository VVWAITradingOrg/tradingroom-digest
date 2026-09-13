#!/bin/bash
# 面包tradingroom 日报单入口。LaunchAgent 每天 06:00/18:00 (America/Los_Angeles) 调这一个脚本。
#
# 用法:
#   pipeline.sh                          # 按当前时间自动判断该跑 day 还是 night
#   pipeline.sh --session day|night      # 手动指定
#   pipeline.sh --session day   --window "2026-09-11 06:00" "2026-09-11 18:00"   # 手动指定窗口(补跑用)
#   pipeline.sh --no-deliver             # 只生成日报，不发 Discord、不发 vvwbot（backfill.sh 用）
#
# trap EXIT 兜底：无论哪步失败都会走到 report.sh fail。
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

JOB="tradingroom-digest"
CHANNEL_ID="1519516509624598599"
PY=/usr/bin/python3
MODEL="${TRADINGROOM_MODEL:-sonnet}"

SESSION=""
WIN_START=""
WIN_END=""
DELIVER=1
NOTIFY_CHANNEL=""   # --no-deliver 时改成 "none"，让 report.sh 的 ok/fail 也不发 Discord（backfill 批量跑不刷屏）

while [ $# -gt 0 ]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --window) WIN_START="$2"; WIN_END="$3"; shift 3 ;;
    --no-deliver) DELIVER=0; NOTIFY_CHANNEL="none"; shift ;;
    *) echo "未知参数: $1" >&2; exit 1 ;;
  esac
done

# ---- 自动判断 session（没手动指定时）----
NOW_HOUR="$(date +%H)"
if [ -z "$SESSION" ]; then
  if [ "$NOW_HOUR" -lt 12 ]; then SESSION="night"; else SESSION="day"; fi
fi

# ---- 算窗口（没手动指定时）----
if [ -z "$WIN_START" ]; then
  if [ "$SESSION" = "day" ]; then
    TARGET_DATE="$(date +%F)"
    WIN_START="$TARGET_DATE 06:00"
    WIN_END="$TARGET_DATE 18:00"
    FILE_DATE="$TARGET_DATE"
  elif [ "$SESSION" = "night" ]; then
    TARGET_DATE="$(date +%F)"
    YDAY="$(date -v-1d +%F)"
    WIN_START="$YDAY 18:00"
    WIN_END="$TARGET_DATE 06:00"
    FILE_DATE="$YDAY"   # 夜盘追加到"昨天"的文件
  else
    echo "session=full 必须配 --window" >&2
    exit 1
  fi
else
  # 手动指定窗口时，FILE_DATE 取窗口起始那天
  FILE_DATE="$(date -j -f "%Y-%m-%d %H:%M" "$WIN_START" +%F 2>/dev/null || echo "$WIN_START" | cut -d' ' -f1)"
fi

SESSION_LABEL="${SESSION}"
if [ "$SESSION" = "full" ]; then
  # 整天模式：兼容历史 backfill 产物的命名（不带 session 后缀）
  DIGEST_FILE="exports/daily/digests/${FILE_DATE}.md"
  RAW_FILE="exports/raw_${FILE_DATE}_full.json"
else
  DIGEST_FILE="exports/daily/digests/${FILE_DATE}.${SESSION}.md"
  RAW_FILE="exports/raw_${FILE_DATE}_${SESSION}.json"
fi

trap 'ec=$?; if [ $ec -ne 0 ]; then bash report.sh "$JOB" fail "第 ${CUR_STEP:-?} 步异常退出 (exit=$ec)" "$SESSION_LABEL" "$NOTIFY_CHANNEL"; fi' EXIT

bash report.sh "$JOB" start "$SESSION_LABEL"
echo "[pipeline] session=$SESSION 窗口=[$WIN_START, $WIN_END) -> $DIGEST_FILE"

# ---- 1. 抓取 ----
CUR_STEP="1/5 抓取"
bash report.sh "$JOB" step "1/5 抓取 [$WIN_START, $WIN_END)" "$SESSION_LABEL"
./run.sh export -c "$CHANNEL_ID" -f Json --after "$WIN_START" --before "$WIN_END" --utc -o "$RAW_FILE" >/dev/null 2>&1
if [ ! -f "$RAW_FILE" ]; then
  bash report.sh "$JOB" fail "导出失败，没有生成 $RAW_FILE" "$SESSION_LABEL" "$NOTIFY_CHANNEL"
  trap - EXIT
  exit 1
fi
MSG_COUNT="$("$PY" -c "import json;print(len(json.load(open('$RAW_FILE',encoding='utf-8'))['messages']))" 2>/dev/null || echo 0)"

# ---- 2. 幂等判断 ----
CUR_STEP="2/5 幂等判断"
bash report.sh "$JOB" step "2/5 幂等判断 (本次 $MSG_COUNT 条)" "$SESSION_LABEL"
SEEN_FILE="$HOME/.openclaw/task-status/${JOB}-seen.jsonl"
mkdir -p "$(dirname "$SEEN_FILE")"
touch "$SEEN_FILE"
PREV_COUNT="$("$PY" - "$SEEN_FILE" "$FILE_DATE" "$SESSION" <<'EOF'
import json, sys
path, date, session = sys.argv[1], sys.argv[2], sys.argv[3]
last = None
for line in open(path, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    try:
        r = json.loads(line)
    except Exception:
        continue
    if r.get("date") == date and r.get("session") == session:
        last = r
print(last["message_count"] if last else -1)
EOF
)"

if [ "$PREV_COUNT" = "$MSG_COUNT" ] && [ -f "$DIGEST_FILE" ]; then
  bash report.sh "$JOB" ok "无新增，跳过 ($FILE_DATE/$SESSION, $MSG_COUNT 条)" "$SESSION_LABEL" "$NOTIFY_CHANNEL"
  trap - EXIT
  exit 0
elif [ "$PREV_COUNT" != "-1" ]; then
  bash report.sh "$JOB" step "检测到消息数变化 ($PREV_COUNT -> $MSG_COUNT)，重新生成" "$SESSION_LABEL"
fi

# ---- 3. 切分 ----
CUR_STEP="3/5 切分"
bash report.sh "$JOB" step "3/5 切分" "$SESSION_LABEL"
if [ "$SESSION" = "full" ]; then
  # 整天模式：复用老的按日切分脚本（产出 exports/daily/<date>.txt 等，兼容历史格式）
  "$PY" etl.py "$RAW_FILE"
  CHAPTER_TXT="exports/daily/${FILE_DATE}.txt"
  PROMPT="用 tradingroom-digest skill（整天模式）分析 exports/daily/${FILE_DATE}.txt，把日报写到 ${DIGEST_FILE}。"
else
  CHAPTER_TXT="exports/daily/chapters/${FILE_DATE}.${SESSION}.txt"
  mkdir -p exports/daily/chapters
  "$PY" etl_chapter.py "$RAW_FILE" "$CHAPTER_TXT"
  PROMPT="用 tradingroom-digest skill（章节模式）分析 ${CHAPTER_TXT}（这是 $FILE_DATE 的${SESSION}盘，窗口 [$WIN_START, $WIN_END)），把日报写到 ${DIGEST_FILE}。"
fi

# ---- 4. 分析（唯一值钱的一步）----
CUR_STEP="4/5 分析"
bash report.sh "$JOB" step "4/5 claude -p 分析中" "$SESSION_LABEL"
CLAUDE_OUT="$(claude -p "$PROMPT" \
  --allowedTools "Read" "Write" "Glob" "Grep" \
  --permission-mode bypassPermissions \
  --model "$MODEL" \
  --add-dir "$DIR" 2>&1)"

if echo "$CLAUDE_OUT" | grep -qi "session limit\|rate limit"; then
  bash report.sh "$JOB" fail "claude -p 撞到用量限制，本次不计入已完成，留给下次重试。输出: $(echo "$CLAUDE_OUT" | tail -c 300)" "$SESSION_LABEL" "$NOTIFY_CHANNEL"
  trap - EXIT
  exit 1
fi
if [ ! -s "$DIGEST_FILE" ]; then
  bash report.sh "$JOB" fail "分析没有产出文件 ${DIGEST_FILE}。输出: $(echo "$CLAUDE_OUT" | tail -c 300)" "$SESSION_LABEL" "$NOTIFY_CHANNEL"
  trap - EXIT
  exit 1
fi

# ---- 5. 交付 ----
CUR_STEP="5/5 交付"
bash report.sh "$JOB" step "5/5 交付" "$SESSION_LABEL"

"$PY" build_view.py >/dev/null 2>&1 || echo "[pipeline] 本地看板生成失败，不影响主流程" >&2

DIGEST_SUMMARY="$(sed -n '2,4p' "$DIGEST_FILE" | grep '^>' | head -1 | sed 's/^> //')"

if [ "$DELIVER" = "1" ]; then
  openclaw message send --channel discord -t "channel:1548152579844743228" \
    -m "📋 ${FILE_DATE} ${SESSION}盘\n${DIGEST_SUMMARY}" \
    --media "$DIR/$DIGEST_FILE" >/dev/null 2>&1 \
    || echo "[pipeline] Discord 投递失败，见下方 vvwbot 步骤是否仍继续" >&2

  bash report.sh "$JOB" step "5/5 交付 vvwbot" "$SESSION_LABEL"
  ( cd ~/Desktop/vvwbot-site && venv/bin/python build.py >/dev/null && wrangler deploy >/dev/null 2>&1 )
  ACCESS_CHECK="$(curl -sS -o /dev/null -w '%{http_code}' https://vvwbot.com/research/tradingroom/ 2>/dev/null || echo "000")"
  if [ "$ACCESS_CHECK" != "302" ]; then
    bash report.sh "$JOB" fail "vvwbot 发布后 Access 校验失败：/research/tradingroom/ 返回 ${ACCESS_CHECK}（应为302），可能是 Access 保护失效或部署出错，不能当成功处理" "$SESSION_LABEL"
    trap - EXIT
    exit 1
  fi
fi

# ---- 全部成功：落 seen 记录 ----
"$PY" - "$SEEN_FILE" "$FILE_DATE" "$SESSION" "$MSG_COUNT" <<'EOF'
import json, sys
from datetime import datetime, timezone
path, date, session, count = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
rec = {"date": date, "session": session, "message_count": count,
       "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
EOF

bash report.sh "$JOB" ok "$FILE_DATE ${SESSION}盘 完成 ($MSG_COUNT 条)" "$SESSION_LABEL" "$NOTIFY_CHANNEL"
trap - EXIT
exit 0
