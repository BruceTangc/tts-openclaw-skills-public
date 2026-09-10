# System State

```yaml
as_of:
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
next_priority:
```

规则：每次会话/定时工作先恢复本状态，再读取 active Opportunity 与 Research Agenda；完成工作后更新。`next_priority` 只保留一个最高优先事项。
