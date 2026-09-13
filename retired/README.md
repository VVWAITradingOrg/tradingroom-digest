# 已退役：standalone watchdog

2026-09-13: tradingroom-digest 的巡检职责已并入 `~/Automation/manager`
统一 supervisor 框架（`supervisor.py` 每 5 分钟跑一次，registry.json 里
`tradingroom-digest` 条目已配 heartbeat/last_ok/day-night deadlines/
stuck_minutes=40）。

这个目录下的 watchdog.py.retired 和 com.vvw.tradingroom-watchdog.plist
是原来独立的 LaunchAgent 巡检（45 分钟一次），已 `launchctl unload`，
仅保留备份，不再运行。如果以后要恢复：
  cp com.vvw.tradingroom-watchdog.plist ~/Library/LaunchAgents/
  mv watchdog.py.retired ../watchdog.py
  launchctl load ~/Library/LaunchAgents/com.vvw.tradingroom-watchdog.plist
但那样会和 automation-supervisor 对同一个 job 重复报警，一般不需要恢复。
