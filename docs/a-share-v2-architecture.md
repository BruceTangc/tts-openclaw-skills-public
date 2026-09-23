# A股投资 Agent V2 — 能力架构与边界

## 目标

不是把旧系统拆成多个 Skill，而是只为 OpenClaw Agent 补充通用模型不容易长期稳定做好的专业投资能力。

最高原则：

> Agent is the sole orchestrator. Skills do not orchestrate Skills.

Skill 提供专业方法、判断纪律和工具使用指导。Agent 根据目标、上下文、Memory 和工具结果决定下一步。

## 三个自建 Skill

### 1. A股投资研究与决策
核心问题：**我应该相信什么？是否存在值得投资的机会？**

覆盖主动发现、研究、因果链、A股映射、Reality/Expectation/Pricing、反方论证、证伪和投资吸引力判断。

不决定组合仓位。

### 2. A股组合管理
核心问题：**资本应该如何配置？**

覆盖已有组合、仓位、集中度、相关暴露、风险预算、建仓/加减仓/退出、再平衡和真实执行约束。

不重新做完整证券研究。

### 3. 投资复盘与学习
核心问题：**过去应该学到什么？**

覆盖当时信息集、Decision Quality vs Outcome、错误归因、行为偏误、Missed Opportunity 和经验分级。

不直接修改其他 Skill。

## 非 Skill 职责

### AGENTS.md
长期工作制度：Agent 身份、全天工作原则、跨日连续性、什么时候主动工作、记录纪律、如何选择能力。

### OpenClaw Automations/Cron
只负责在需要的时间唤醒 Agent，并给出当前任务目标。Cron 不复制投资方法。

### OpenClaw Memory
负责跨日连续性和长期记忆。日常事实进入 daily memory；经复盘确认的稳定经验才适合长期记忆。

### Workspace
保存需要长期引用的研究材料、投资 thesis、组合工作资料。不要为了 Skill 自己另造 Runtime/数据库。

### 东方财富妙想 / QVeris
它们是 Agent 已有能力。三个自建 Skill 不包装、不复制、不硬编码它们的内部 API。Agent 根据当前问题自主选择实际可用能力。

## Skill 边界判定

一个任务按“当前主要决策问题”选能力，而不是按固定流水线：

- “最近有什么没充分交易的新变化？” → 研究与决策
- “研究一下某公司现在有没有投资价值” → 研究与决策
- “这个利好是不是已经 price in？” → 研究与决策
- “我有 20% 仓位了还要不要加？” → 组合管理
- “我的 AI 持仓是不是太集中？” → 组合管理
- “今天这些持仓怎么调整？” → 组合管理；若某 thesis 缺关键事实，Agent 可另行使用研究能力
- “复盘这笔亏损” → 复盘与学习
- “为什么上个月总是追高？” → 复盘与学习
- “错过某次行情该学什么？” → 复盘与学习

多个能力可能在同一 Agent turn 中先后有价值，但切换由 Agent 决定，Skill 不指定下一个 Skill。

## 不新增 Skill 的默认规则

只有同时满足以下条件才考虑新增：
1. 高频重复出现；
2. 有独立专业方法；
3. 现有 Skill + 通用模型无法稳定做好；
4. 能独立完成一类真实任务；
5. 独立后明显减少错误，而不是仅让目录更整齐。

因此 Opportunity Discovery、Expectation Assessment、Risk、Execution 暂不单独拆 Skill：前两者属于研究判断；风险属于组合管理；执行已有妙想/工具能力。

## 全天工作制度

全天流程不是 Skill。它属于 AGENTS.md + Automations + Memory 的组合：
- Automation：什么时候唤醒；
- AGENTS.md：这个时点应该关注什么类型的问题和连续性要求；
- Agent：判断当前需要哪个 Skill/工具；
- Memory：承接昨天与今天之前的上下文；
- Skill：提供专业做法。

这避免把 Skill 重新做成 Agent Runtime。
