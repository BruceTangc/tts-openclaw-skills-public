# A股投资 Agent V2

本分支从零设计 OpenClaw A 股投资能力，不从旧“大一统交易 Skill”机械拆分。

## V2 自建 Skills
- `A股投资研究与决策/` — 发现、研究、预期差、证伪与投资判断。
- `A股组合管理/` — 资本配置、仓位、风险、再平衡与执行约束。
- `投资复盘与学习/` — 决策质量复盘、错误归因、遗漏机会与经验学习。

## 工作制度
- `A股投资Agent工作制度/AGENTS.fragment.md` — 合并进目标投资 Agent 的 workspace `AGENTS.md`，不要覆盖原文件。
- `ACTIVE.template.md` — 初始化为 workspace 的 `investment/ACTIVE.md`。
- `DAILY-WORKLOG.template.md` — daily memory 中投资工作记录的结构参考。
- `OUTPUT-TEMPLATES.md` — 对用户的固定输出协议。
- `CRON.md` — 全天 Automations/Cron 候选时点与 prompt。
- `MODEL-ROBUSTNESS.md` — 强/弱模型验收。

## 核心架构
Agent 是唯一编排者，Skill 不调用 Skill。

OpenClaw 原生负责 Agent Runtime、Workspace、Memory 和 Automations；东方财富妙想/QVeris 等继续作为 Agent 可选择的既有能力。

每轮统一：
**恢复 ACTIVE/Memory → 处理增量 → 自主选择专业能力/工具 → 输出 → Worklog → 更新 ACTIVE。**

## 安装注意
本仓库仍保留旧的 `A股长期投资组合经理/`、`A股短线交易系统/` 等历史/其他 Skill。**部署 V2 时不要把这些旧 A 股工作流 Skill 与 V2 三个 Skill 同时启用给同一个投资 Agent**，否则可能出现职责重叠和提示冲突。

V2 应安装/启用的自建投资 Skill 只有上面的三个。妙想、QVeris 等既有数据/执行能力不属于这三个 Skill，继续保留。

不要把 `AGENTS.fragment.md` 当成完整 AGENTS.md 直接覆盖现有 workspace；应将其作为投资制度段落合并。

Cron 不应盲目重复创建。先检查现有投资定时任务，删除/停用与旧系统重复的任务，再按 `CRON.md` 建立 V2 唤醒点。

## 文档与验收
- `docs/a-share-v2-architecture.md`
- `docs/a-share-v2-boundary-tests.md`
- `docs/a-share-v2-full-day-simulation.md`

## 当前状态
V2 架构、三项专业能力、连续工作协议、固定用户输出、全天 Cron 设计和模型鲁棒性测试已完成设计审查。下一阶段是 OpenClaw 实机验收。

实机验收重点：实际模型是否先恢复上下文、是否调用真实数据能力、是否更新 Worklog/ACTIVE、账户事实 UNKNOWN 时是否 NO ACTION、ACTIVE 是否膨胀、Cron 是否产生无价值重复工作。


## 市场自适应定位
V2 不预设“长期”或“短线”身份。每个 thesis 的持有/观察周期由 driver、证据有效期、预期差兑现速度和风险收益变化决定，并可随市场变化动态调整。

交易日固定最低巡检建议：`08:45 / 09:27 / 09:40 / 10:30 / 11:15 / 13:30 / 14:30 / 20:30`。这些时间不是固定买卖窗口；若两个 Cron 之间实际获得重大市场变化，应立即重新评估。
