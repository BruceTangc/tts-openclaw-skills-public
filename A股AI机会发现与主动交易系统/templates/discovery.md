# Discovery Record

```yaml
discovery_id: DISC-YYYYMMDD-NNN
first_seen: IMMUTABLE_TIMESTAMP
created_at:
source_domain: POLICY | INDUSTRY | COMPANY | GLOBAL | INFORMATION | MARKET
signal_type: DELTA_LEVEL | DELTA_RATE | DELTA_TREND | DELTA_RELATIONSHIP
known_facts: []
baseline:
current:
delta:
anomaly:
possible_cluster:
market_reaction:
attention_level:
known_unknowns: []
next_research: []

gates:
  materiality: PASS | FAIL | UNKNOWN
  persistence: NOISE | EVENT | TREND | STRUCTURAL | UNKNOWN
  mispricing_potential: PASS | KNOWN_PRICED | CROWDED | UNKNOWN

status: DISCOVERY_CANDIDATE
corrections: []
persisted: false
```

`first_seen` 创建后不可修改。纠错只追加到 `corrections`，不得覆盖原始发现时间、原始事实或原始 Gate 判断。没有成功持久化的 Discovery 不计入 Discovery Lead Time，也不能事后补记为提前发现。
