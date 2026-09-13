#!/bin/bash
# 状态上报 + Discord 通知。给 pipeline.sh 用，也可以给以后别的 pipeline 复用。
#
# 用法:
#   report.sh <job> start [session]
#   report.sh <job> step  <message> [session]
#   report.sh <job> ok    <message> [session] [channel]
#   report.sh <job> fail  <message> [session] [channel]
#
# 心跳文件: ~/.openclaw/task-status/<job>.json          {status, session, step, message, ts}
# 最近成功: ~/.openclaw/task-status/<job>-last-ok.json  {day: {...}, night: {...}}  (仅 ok 时更新)
#
# start/step 只落本地心跳文件；ok/fail 才发 Discord。
set -uo pipefail

JOB="${1:?用法: report.sh <job> start|step|ok|fail ...}"
EVENT="${2:?缺少事件类型: start|step|ok|fail}"
MSG="${3:-}"
SESSION="${4:-}"
CHANNEL="${5:-}"

STATUS_DIR="$HOME/.openclaw/task-status"
mkdir -p "$STATUS_DIR"
HEARTBEAT="$STATUS_DIR/$JOB.json"
LAST_OK="$STATUS_DIR/$JOB-last-ok.json"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 默认投递频道：日报走"面包群聊汇总"，失败/报警走"cron-monitor"
DIGEST_CHANNEL="channel:1548152579844743228"
MONITOR_CHANNEL="channel:1476024801415008448"

json_escape() {
  /usr/bin/python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

write_heartbeat() {
  local status="$1" step="$2"
  local msg_json step_json session_json
  msg_json="$(json_escape "$step")"
  session_json="$(json_escape "$SESSION")"
  cat > "$HEARTBEAT" <<EOF
{"job":"$JOB","status":"$status","session":$session_json,"step":$msg_json,"ts":"$NOW"}
EOF
}

update_last_ok() {
  local sess="${SESSION:-unknown}"
  /usr/bin/python3 - "$LAST_OK" "$sess" "$NOW" <<'EOF'
import json, sys, os
path, sess, ts = sys.argv[1], sys.argv[2], sys.argv[3]
data = {}
if os.path.exists(path):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        data = {}
data[sess] = {"ts": ts}
json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False)
EOF
}

send_discord() {
  local channel="$1" text="$2"
  if [ "$channel" = "none" ]; then
    return 0  # 调用方明确要求不投递（比如 backfill 批量补历史，不刷屏）
  fi
  local target="${channel:-$MONITOR_CHANNEL}"
  # 同步发送：失败也不让 pipeline 崩，但要在本地日志留痕方便排查
  if ! openclaw message send --channel discord -t "$target" -m "$text" >/dev/null 2>>"$STATUS_DIR/$JOB-send-errors.log"; then
    echo "[report.sh] 警告: 发送到 $target 失败，见 $STATUS_DIR/$JOB-send-errors.log" >&2
  fi
}

case "$EVENT" in
  start)
    write_heartbeat "running" "start"
    ;;
  step)
    write_heartbeat "running" "$MSG"
    ;;
  ok)
    write_heartbeat "ok" "$MSG"
    update_last_ok
    send_discord "${CHANNEL:-$DIGEST_CHANNEL}" "✅ [$JOB${SESSION:+/$SESSION}] $MSG"
    ;;
  fail)
    write_heartbeat "fail" "$MSG"
    send_discord "${CHANNEL:-$MONITOR_CHANNEL}" "🔴 [$JOB${SESSION:+/$SESSION}] 失败: $MSG"
    ;;
  *)
    echo "未知事件: $EVENT (应为 start|step|ok|fail)" >&2
    exit 1
    ;;
esac
