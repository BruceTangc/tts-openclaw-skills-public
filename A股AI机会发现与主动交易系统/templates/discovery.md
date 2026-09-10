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

## first_seen Runtime Integrity

Discovery 第一次成功落盘后必须立即执行 `runtime/integrity_runtime.py verify-first-seen` 创建独立 anchor：

```text
state/runtime/discovery-anchors/<DISC-ID>.json
```

anchor 至少保存：`discovery_id + first_seen + sha256 + anchored_at`。

以后每次读取/更新 Discovery：
1. 先验证 anchor；
2. `first_seen` 不一致 → `FIRST_SEEN_INTEGRITY_VIOLATION`；
3. 该 Discovery 禁止用于 Early Discovery、Discovery Lead Time、Position Lead Time 等成绩计算；
4. 纠错只 append 到 `corrections`，不得改写 first_seen；
5. anchor 本身不得由普通 Discovery 更新流程覆盖。

没有成功持久化并完成 anchor 的 Discovery 不计入 Discovery Lead Time，也不能事后补记为提前发现。
