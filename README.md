# Tradingroom Digest

Mac mini 上的面包群聊汇总项目。LaunchAgent 每天 06:00/18:00 PT 导出 Discord 群聊、ETL、调用 Claude CLI 生成摘要，再通过 OpenClaw transport 投递 Discord，并更新本地网页。

## Run

```bash
./pipeline.sh --no-deliver
./pipeline.sh
```

## Credentials

- `.env` 中的 `DISCORD_TOKEN` 仅供 DiscordChatExporter 读取源群聊；不要输出、记录到文档或提交 Git。
- 最终投递使用 OpenClaw 已配置 Discord account，不从 `.env` 读取发送凭据。
- Claude CLI 使用本机已有登录状态。

## Scheduling and watchdog

- LaunchAgent：`com.vvw.tradingroom-digest`，06:00/18:00 PT；`RunAtLoad` 通过 `startup-check.sh` 只补跑最近已到期的 session。
- heartbeat：`~/.openclaw/task-status/tradingroom-digest.json`。
- 项目内 `watchdog.py` 是旧的专用巡检器；统一管理后由 `/Users/vvw/Automation/manager/supervisor.py` 负责全局状态监控。
- 日志：`logs/launchagent.*.log`。
- 管理：`/Users/vvw/Automation/manager/automationctl status`。
