# 当前状态 · 2026-10-15

关注人 position 每日跟踪已接入原06:00 night流程，在早盘机会之后整理前一个完整美西自然日，并投递独立「关注人position跟踪」频道。每人summary、同标的前日披露对照、原文和链接；不做周度对比。默认启用，可设置 `TRADINGROOM_POSITION_TRACKING_ENABLED=0` 关闭。

9/1–10/14共44份历史日档已通过Manager补发，44条摘要与44个附件逐一读回、字节哈希一致，增量重跑为already_up_to_date且0新增发送。分析质量仍有42日partial、1日unresolved，不代表完整仓位账；图片未做视觉解析。

父流程新增进度心跳，Manager的night完成告警阈值为07:15；原06/11/17启动时间、精简/详细摘要、开盘机会及其目标频道保持原有流程。旧positions快照默认关闭，避免重复输出。未新增cron/LaunchAgent。

最终212项共享测试（含12项生产pipeline隔离测试）通过，shell语法及独立审查通过。实现、真实投递及v1.3.0发布证据见[日跟踪状态](../tradingroom-digest-v2/STATUS.md)。与本次无关的未跟踪文件保留。
