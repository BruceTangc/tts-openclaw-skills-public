# Discovery Record

```yaml
discovery_id: DISC-YYYYMMDD-NNN
first_seen: IMMUTABLE_TIMESTAMP
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
```

`first_seen` 创建后不可修改。后续纠错必须追加 correction 记录，不得覆盖原始发现时间与原始事实。
