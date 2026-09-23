# A股投资 Agent V2

本分支从零设计 OpenClaw A股投资能力，不从旧“大一统交易 Skill”机械拆分。

## 自建 Skills
- `A股投资研究与决策/` — 发现、研究、预期差、证伪与投资判断。
- `A股组合管理/` — 资本配置、仓位、风险、再平衡与执行约束。
- `投资复盘与学习/` — 决策质量复盘、错误归因、遗漏机会与经验学习。

## 核心架构
Agent 是唯一编排者。Skill 不调用 Skill。

OpenClaw 原生负责 Agent Runtime、Workspace、Memory 和 Automations；东方财富妙想/QVeris继续作为 Agent 可选择的既有能力。

详细边界见：
- `docs/a-share-v2-architecture.md`
- `docs/a-share-v2-boundary-tests.md`

## 当前阶段
先冻结能力边界，再设计全天 AGENTS.md / Cron。不要把日程、Memory Runtime 或工具包装重新塞回 Skill。
