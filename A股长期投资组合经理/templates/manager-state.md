# Manager State — 经理认知状态

> 回答：**我目前对整个投资系统的认知状态**——我持仓了什么、相信什么假设、在验证什么问题、最大的风险在哪、下一步先做什么。
>
> **Manager State ≠ 日报**。它不是每日流水账，而是经理"当前认知状态"的**大脑缓存**，跨时段（Cron 阶段 / 当天 / 跨天）连续工作的锚。当日流水（Worklog）在 `state/daily/YYYY-MM-DD.md`，**两者分离、不混为一谈**。
>
> **更新规则**：
> - 起于 08:45 晨会，止于 20:30 日终固化；跨天继承（次日恢复，不从零开始）。
> - **每个阶段 / 重大变化后更新**（行情/公告/组合/假设/决策/研究推进后，凡认知状态有变即写回）。
> - 更新必须附 Evidence 依据 / 判断理由，**不写空占位**。
> - `next_priority` 同一时刻只有一个明确优先项，写入下一阶段 INPUT。
> **每日启动先读**：任何工作阶段（尤其首个 Cron 唤醒）前，先读本文件恢复认知，**未读 Manager State 禁止进入研究或交易**（〇.1 启动门第 1 步，违反即从零开始，触发全局禁止 #20）。

---

```yaml
timestamp:                 YYYY-MM-DD HH:MM        # 本状态最后固化时刻

# -------- market_state --------
market_state:
  regime:                  风险偏好升 / 中 / 降
  liquidity:               流动性环境描述
  valuation_environment:   整体估值环境（高/中/低，风险收益比）
  major_events:            近期重大事件清单
  major_risks:             市场级主要风险

# -------- portfolio_state --------
portfolio_state:
  positions:               持仓清单（标的/数量/成本/市值/占比）
  cash:                    现金及现金比例
  concentration:           单股集中度 + 行业集中度
  sector_exposure:         行业/板块敞口
  factor_exposure:         风格/因子暴露（成长/价值/周期等）
  portfolio_risk:          组合波动/相关性/Beta/最大潜在回撤
  max_drawdown_estimate:   组合回撤估算（自近期高点）
  dist_to_drawdown_hardline: 距最大回撤硬线的距离   # A-4：回撤硬线 15.5（单票>20%/组合>10% 触发强制重评估），记录"当前距离"使触发检查主动化；不改硬线本身

# -------- active_hypotheses --------
active_hypotheses:         # 只列当前有效（VALIDATING/ACTIVE/WEAKENING）
  - id:                    HYP-YYYYMMDD-xx
    thesis:                一句话核心假设
    confidence:            0~1 或 %
    status:                VALIDATING / ACTIVE / WEAKENING
    invalidation:          失效条件
    latest_evidence:       最新 Evidence ID + 关键结论

# -------- watchlist --------
watchlist:
  candidates:              观察池候选（引用 mx-zixuan 状态）
  priority:                每候选优先级/下一步

# -------- research_agenda --------
research_agenda:
  - id:                    RQ-YYYYMMDD-xx
    question:              待回答问题
    priority:              高/中/低
    reason:                为什么要答
    required_evidence:     需要什么证据
    status:                进行中 / 待验证 / 闭合

# -------- open_questions --------
open_questions:            未决问题（跨时段延续，若影响决策重大则入 agenda）

# -------- key_risks --------
key_risks:                 # 关键风险 + 监控方式
  - risk:                  具体风险
    monitor:               如何监控 / 触发上报条件
    dist_to_drawdown_hardline:  （组合级）当前距回撤硬线距离   # A-4：同上，主动化触发检查

# -------- opportunity_cost --------
opportunity_cost:
  best_alternative:        当前最佳替代（标的/现金/降险）
  reason:                  为何替代更优（收益/风险/确定性/估值比较）
  comparison:              本组合 vs 替代的预期对比

# -------- recent_decisions --------
recent_decisions:          最近决策 + 结果（Decision 记忆摘要，引用 DEC-{id}）

# -------- experience --------
experience:                已沉淀可复用经验（引用 state/experience.md，多案例验证后）

# -------- mistakes --------
mistakes:                  当前在防的错误 / 已记录（引用 state/mistake-book.md）

# -------- next_priority --------
next_priority:             下一步唯一优先项（写入下一阶段 INPUT）
```
