#!/usr/bin/env /usr/bin/python3
"""把一个已经精确到小时的 12 小时窗口导出（raw json）转成单一章节文本文件。

跟 etl.py 的区别：etl.py 假设输入跨越完整自然日、需要按 Pacific 日期拆成多份；
这里的输入本身就已经是恰好一个 day/night 章节的窗口，不需要再拆，直接整体转成一份文本
（同时单独抽出重点人物的发言，供 skill 快速定位）。

用法: etl_chapter.py <raw.json> <输出.txt>
"""
import json
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from chat_clean import build_id_to_name, clean_content

TZ = ZoneInfo("America/Los_Angeles")
FOCUS_USERS = ["himself65", "solo_leveling116", "frank_hou._87743"]


def main():
    src, out = sys.argv[1], sys.argv[2]
    data = json.load(open(src, encoding="utf-8"))
    msgs = data["messages"]
    id_to_name = build_id_to_name(msgs)

    lines = []
    focus_lines = {u: [] for u in FOCUS_USERS}

    for m in msgs:
        ts_norm = re.sub(r"\.\d+", "", m["timestamp"], count=1)
        dt_local = datetime.fromisoformat(ts_norm).astimezone(TZ)
        author = m["author"]
        display = author.get("nickname") or author["name"]
        username = author["name"]
        content = clean_content(m, id_to_name)
        if not content.strip():
            continue
        line = f"[{dt_local.strftime('%H:%M')}] {display}({username}): {content}"
        lines.append(line)
        if username in focus_lines:
            focus_lines[username].append(line)

    header = f"# 时间均为美西时间 America/Los_Angeles（本文件为单一章节，非完整自然日）\n"
    with open(out, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines))

    base = out.rsplit(".", 1)[0]
    for user in FOCUS_USERS:
        with open(f"{base}.{user}.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(focus_lines[user]))

    print(f"{len(lines)} lines -> {out} "
          + " ".join(f"{u}={len(focus_lines[u])}" for u in FOCUS_USERS))


if __name__ == "__main__":
    main()
