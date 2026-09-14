import json
import sys
import re
import os
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from chat_clean import build_id_to_name, clean_content as _clean_content

SRC = sys.argv[1] if len(sys.argv) > 1 else "exports/bread_tradingroom_week.json"
OUT_DIR = "exports/daily"
TZ = ZoneInfo("America/Los_Angeles")

os.makedirs(OUT_DIR, exist_ok=True)

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

msgs = data["messages"]

id_to_name = build_id_to_name(msgs)


def clean_content(m):
    return _clean_content(m, id_to_name)

FOCUS_USERS = ["himself65", "solo_leveling116", "frank_hou._87743", "sunrunlong1727"]

by_day = defaultdict(list)
focus_by_day = {u: defaultdict(list) for u in FOCUS_USERS}

for m in msgs:
    ts = m["timestamp"]  # e.g. 2026-08-19T07:00:53.197+00:00
    ts_norm = re.sub(r"\.\d+", "", ts, count=1)
    dt_utc = datetime.fromisoformat(ts_norm)
    dt_local = dt_utc.astimezone(TZ)
    day = dt_local.strftime("%Y-%m-%d")
    sort_key = dt_local.isoformat()
    author = m["author"]
    display = author.get("nickname") or author["name"]
    username = author["name"]
    content = clean_content(m)
    if not content.strip():
        continue
    hh_mm = dt_local.strftime("%H:%M")
    line = f"[{hh_mm}] {display}({username}): {content}"
    by_day[day].append((sort_key, line))
    if username in focus_by_day:
        focus_by_day[username][day].append((sort_key, line))

summary = {}
for day, lines in sorted(by_day.items()):
    lines.sort(key=lambda x: x[0])
    path = os.path.join(OUT_DIR, f"{day}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# 时间均为美西时间 America/Los_Angeles ({day})\n")
        f.write("\n".join(l for _, l in lines))
    summary[day] = len(lines)

for user, days in focus_by_day.items():
    for day, lines in sorted(days.items()):
        lines.sort(key=lambda x: x[0])
        path = os.path.join(OUT_DIR, f"{day}.{user}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(l for _, l in lines))

print("Days:", len(by_day))
for day, cnt in sorted(summary.items()):
    counts = " ".join(f"{u}={len(focus_by_day[u].get(day, []))}" for u in FOCUS_USERS)
    print(f"  {day}: {cnt} messages ({counts})")
