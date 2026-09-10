# Opportunity Record

```yaml
opportunity_id: OPP-YYYYMMDD-NNN
created_at:
first_seen: IMMUTABLE_TIMESTAMP
source_discoveries: []
cluster:
stage: DISCOVERED
last_transition_id:

research:
  facts: []
  causal_chain: []
  profit_transmission: []
  a_share_mapping: []
  opposing_view: []
  unknowns: []

expectation:
  reality:
  market_expectation:
  pricing:
  gap_direction: UNKNOWN
  gap_magnitude: UNKNOWN
  crowding:
  confidence:

hypothesis:
  thesis:
  lifecycle: IDEA
  confidence: LOW
  confirmation_conditions: []
  invalidation_conditions: []
  expected_window:

validation:
  reality:
  causal:
  market:
  expectation:
  latest_change: UNKNOWN

candidates: []
position:
  state: FLAT
  size: 0
  avg_cost:
  risk_budget:

next_evidence: []
next_action:
closed_reason:
```

## Stage Transition Record

```yaml
transition_id: TRN-YYYYMMDD-NNN
opportunity_id:
timestamp:
from_stage:
to_stage:
trigger:
new_material_evidence: []
reality_change:
expectation_gap_change:
market_validation_change:
crowding_change:
gate_result: ALLOW | BLOCK
reason:
persisted: false
```

禁止直接覆盖 `stage`。Transition Record 必须先成功写入，随后才更新 Opportunity 的 `stage` 与 `last_transition_id`。若写入失败，原 stage 保持不变。
