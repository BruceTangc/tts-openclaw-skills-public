# Decision & Execution Authorization Record

> 研究/解释字段可以保留 Markdown；一旦 Decision 可能触发资本副作用，必须同时落盘一份同 ID 的机器可验证 JSON，供 `runtime/integrity_runtime.py` **重新读取**。Agent 口头声称 PASS 不算授权。

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

# 资本副作用授权字段（PROBE/BUY/ADD/REDUCE/EXIT 必填）
trade_intent_id:
symbol:
max_quantity:
price_policy:
persisted: false
persistence_verified_at:
portfolio_refreshed: false
t_plus_1_passed: false
liquidity_passed: false
risk_passed: false
```

Runtime Gate 的真值来自**已落盘并 read-back 的 Decision JSON**，不是下面的自报 checklist。Gate 必须重新验证：

```text
Opportunity exists/open
→ Decision exists + persisted=true
→ result ∈ {ALLOW, REDUCE_SIZE}
→ action/symbol/quantity 在授权范围
→ portfolio_refreshed=true
→ T+1/liquidity/risk=true
→ trade_intent_id unique
→ no unresolved execution
→ ALLOW
```

任一失败：`EXECUTION_BLOCKED`。

WAIT/BLOCKED/NO_ACTION 永远不能调用资本副作用出口。更改 action/symbol/size 必须产生新的 Decision/authorization，不得复用旧授权。
