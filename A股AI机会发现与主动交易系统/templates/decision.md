# Decision & Execution Authorization Record

```yaml
decision_id: DEC-YYYYMMDD-NNN
timestamp:
opportunity_id:
action: PROBE | BUY | ADD | HOLD | REDUCE | EXIT | NO_ACTION | WAIT | BLOCKED
current_stage:
thesis_status:
new_evidence: []
evidence_freshness:
expectation_gap:
market_validation:
crowding:
portfolio_impact:
risk_budget:
liquidity_and_cost:
T_plus_1_constraints:
invalidation:
expected_upside_downside:
opposing_view:
unknowns: []
result: ALLOW | REDUCE_SIZE | WAIT | BLOCKED | NO_ACTION
trade_intent_id:
persisted: false
persistence_verified_at:

authorization:
  opportunity_exists: false
  opportunity_open: false
  decision_persisted: false
  result_allows_execution: false
  action_matches: false
  trade_intent_unique: false
  portfolio_refreshed: false
  t_plus_1_passed: false
  liquidity_risk_passed: false
  unresolved_execution_clear: false
  execution_authorized: false
```

`execution_authorized` 只有所有必要条件均通过时才能为 true。WAIT/BLOCKED/NO_ACTION 永远不能调用交易出口。更改 action/size 必须产生新的 Decision/authorization，不得复用旧授权。
