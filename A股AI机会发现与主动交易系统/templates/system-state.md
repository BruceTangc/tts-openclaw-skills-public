# System State

```yaml
schema_version: 1
as_of:
last_successful_run:
last_successful_persist:
market_regime:
portfolio_state:
  positions: []
  cash:
  concentration:
  sector_exposure:
  portfolio_risk:
active_opportunities: []
discovery_candidates: []
research_agenda: []
open_questions: []
key_risks: []
stale_evidence: []
recent_decisions: []
unresolved_executions: []
next_priority:
```

## Recovery Contract

每次运行先读取 System State，再读取 active Opportunity、Discovery Candidate、Research Agenda 和当日 worklog，之后才允许进入工具调用。

非首次运行若状态缺失/损坏：`STATE_RECOVERY_FAILED`。允许只读 Discovery，但禁止 BUY/ADD，直到恢复或人工确认。

## Commit Contract

material change 的写入顺序：原子对象记录 → daily worklog → research agenda → system-state（最后）→ 重新读取关键记录验证。只有全部成功才是 `RUN_COMMITTED`。

写失败：`PERSISTENCE_FAILED`。若交易工具已返回订单/成交而本地写失败，加入 `unresolved_executions`，下一轮必须先对账，禁止重复下单。

`next_priority` 只保留一个最高优先事项。
