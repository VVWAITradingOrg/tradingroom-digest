#!/usr/bin/env /usr/bin/python3
"""独立心跳监控，每 45 分钟由 LaunchAgent 触发一次。

检查 tradingroom-digest 这个 job：
  1. 是不是卡在 running 状态超过 40 分钟
  2. day/night 两个时段是不是各自按时（留 40 分钟缓冲）产出过成功记录
  3. 每天固定一个时间点（09:00 本地）发一条"巡检正常"，避免沉默被误读

状态文件位置和 report.sh 写的一致：~/.openclaw/task-status/
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

JOB = "tradingroom-digest"
STATUS_DIR = Path.home() / ".openclaw/task-status"
HEARTBEAT = STATUS_DIR / f"{JOB}.json"
LAST_OK = STATUS_DIR / f"{JOB}-last-ok.json"
DAILY_PING_FILE = STATUS_DIR / f"{JOB}-watchdog-last-ping.txt"
MONITOR_CHANNEL = "channel:1476024801415008448"  # cron-monitor

TZ = ZoneInfo("America/Los_Angeles")
STUCK_THRESHOLD_MIN = 40
GRACE_MIN = 40  # 时段该出结果之后再给多久缓冲
DAILY_PING_HOUR = 9  # 09:00 本地固定巡检播报


def load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def parse_utc(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))


def send(text):
    subprocess.run(
        ["openclaw", "message", "send", "--channel", "discord", "-t", MONITOR_CHANNEL, "-m", text],
        check=False,
        capture_output=True,
    )


def check_stuck(now_utc, alerts):
    hb = load_json(HEARTBEAT)
    if not hb or hb.get("status") != "running":
        return
    ts = parse_utc(hb["ts"])
    age_min = (now_utc - ts).total_seconds() / 60
    if age_min > STUCK_THRESHOLD_MIN:
        alerts.append(f"任务卡住：session={hb.get('session') or '?'} step=\"{hb.get('step')}\"，已 {age_min:.0f} 分钟没更新")


def check_missed_sessions(now_local, alerts):
    last_ok = load_json(LAST_OK) or {}

    # 今天 18:40 之后，今天的 day 应该已经成功过
    day_deadline = now_local.replace(hour=18, minute=GRACE_MIN, second=0, microsecond=0)
    if now_local >= day_deadline:
        day_ts = last_ok.get("day", {}).get("ts")
        ok = day_ts and parse_utc(day_ts).astimezone(TZ).date() == now_local.date()
        if not ok:
            alerts.append(f"今天 18:00 的日盘 session 到 {day_deadline.strftime('%H:%M')} 还没有成功记录")

    # 今天 06:40 之后，昨晚的 night 应该已经成功过（追加到昨天的文件）
    night_deadline = now_local.replace(hour=6, minute=GRACE_MIN, second=0, microsecond=0)
    if now_local >= night_deadline:
        night_ts = last_ok.get("night", {}).get("ts")
        yesterday = (now_local - timedelta(days=1)).date()
        ok = night_ts and parse_utc(night_ts).astimezone(TZ).date() >= yesterday
        if not ok:
            alerts.append(f"今早 06:00 的夜盘 session 到 {night_deadline.strftime('%H:%M')} 还没有成功记录")


def main():
    now_utc = datetime.now(ZoneInfo("UTC"))
    now_local = now_utc.astimezone(TZ)

    alerts = []
    check_stuck(now_utc, alerts)
    check_missed_sessions(now_local, alerts)

    if alerts:
        send("⚠️ [tradingroom-watchdog]\n" + "\n".join(f"- {a}" for a in alerts))
        return

    # 没有异常：每天固定一个小时窗口内只播报一次"巡检正常"
    if now_local.hour == DAILY_PING_HOUR:
        today_str = now_local.strftime("%Y-%m-%d")
        last_ping = DAILY_PING_FILE.read_text(encoding="utf-8").strip() if DAILY_PING_FILE.exists() else ""
        if last_ping != today_str:
            send(f"🟢 [tradingroom-watchdog] {today_str} 巡检正常，day/night 均按时完成")
            DAILY_PING_FILE.write_text(today_str, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
