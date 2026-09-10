# Execution & Reconciliation Record

```yaml
execution_id: EXE-YYYYMMDD-NNN
trade_intent_id:
decision_id:
opportunity_id:
request_time:
requested_action:
requested_symbol:
requested_qty:
requested_price_or_type:
tool: mx-moni
tool_result:
order_id:
fill_status: NOT_SENT | SUBMITTED | PARTIAL | FILLED | REJECTED | UNKNOWN
filled_qty:
avg_fill_price:
fees:
reconciled_at:
reconciliation_status: VERIFIED | UNRESOLVED
```

若交易调用超时、返回不完整或成交状态未知，必须记录 `UNKNOWN + UNRESOLVED` 并加入 System State 的 `unresolved_executions`。下一轮先查询订单/持仓对账；在确认前禁止同一 trade_intent_id 或等价重复意图再次执行。
