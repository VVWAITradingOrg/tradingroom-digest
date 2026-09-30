最新流程见 [2026-09-30更新说明](docs/UNIFIED-20260930.md)。

# Tradingroom Digest

Mac mini 上的面包群聊汇总项目。LaunchAgent 每天 06:00/11:00/17:00 PT 导出 Discord 群聊、ETL、调用 Codex CLI `gpt-6.1-sol` 生成摘要（临时容量错误备用 `gpt-6-sol`），再通过 OpenClaw transport 投递 Discord，并更新本地网页。

## Run

```bash
./pipeline.sh --no-deliver
./pipeline.sh
```

## Credentials

- `.env` 中的 `DISCORD_TOKEN` 仅供 DiscordChatExporter 读取源群聊；不要输出、记录到文档或提交 Git。
- 最终投递使用 OpenClaw 已配置 Discord account，不从 `.env` 读取发送凭据。
- Codex CLI 复用本机已有 ChatGPT 登录状态，不在项目中保存凭据。默认模型是 `gpt-6.1-sol`，临时容量错误备用 `gpt-6-sol`；临时测试可用 `TRADINGROOM_MODEL` 环境变量覆盖。

## Analysis contract

- 分析规则位于 `skills/tradingroom-digest/SKILL.md`，由 `pipeline.sh` 显式要求 Codex 读取。
- 群内人物代称、ticker 黑话和交易暗语位于 `docs/chat-glossary.md`；日报模型先读词典，再以当前窗口原文做最终消歧。
- Codex 在 `read-only` sandbox 中运行；CLI 把最终回复先写入临时文件，成功后再原子替换目标 digest。
- Codex stdout/stderr 写入 `logs/codex_<date>_<session>.*.log`，日报仍写入 `exports/daily/digests/`。

## Scheduling and watchdog

2026-09-17 新增：06:00 的 night 日报完成后，追加一份按 ticker/重点人物整理的「早盘开盘交易机会」。
输入仍为昨17:00—今06:00，原文缺失字段留空，计划与已执行动作分开，附逐字引用。
实现和验收见 `/Users/vvw/Automation/tradingroom-digest-v2/docs/OPENING-REPORT.md`。
调用 v2 `opening-addon.sh`，单独投递 Discord，不改变原日报/网站输出。11/17点不追加。
`--no-deliver` 同时禁止该新增项发送。`TRADINGROOM_OPENING_ENABLED=0` 可关闭新增项。
新增项失败会报告失败；原日报完成状态保留，再次运行可单独补机会报告。
日志为 `logs/opening_<夜盘起始日>.log`；没有新增独立LaunchAgent，沿用同一Automation Manager监控。

2026-09-30 修复：网站构建/部署或 Access 检查失败后，仍执行 night 附加报告；整体保留非零退出状态。
Discord 失败同样不再被当成整体成功；本地 `--no-deliver` 不写入已投递 seen 记录。
持仓附加脚本也已预留在同一流程中，但 `TRADINGROOM_POSITIONS_ENABLED` 默认0，尚未首发或启用。

- LaunchAgent：`com.vvw.tradingroom-digest`，06:00/11:00/17:00 PT；`RunAtLoad` 通过 `startup-check.sh` 只补跑最近已到期的 session。
- heartbeat：`~/.openclaw/task-status/tradingroom-digest.json`。
- 项目内 `watchdog.py` 是旧的专用巡检器；统一管理后由 `/Users/vvw/Automation/manager/supervisor.py` 负责全局状态监控。
- 日志：`logs/launchagent.*.log`。
- 管理：`/Users/vvw/Automation/manager/automationctl status`。
