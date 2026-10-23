# Investment Active Context

> 当前投资工作的交接面。只保留下一轮继续工作所需的最新状态；历史过程写入 daily memory。
> **本文件有硬性大小上限：见文末「Retention 规则」。超过上限必须先清理再更新。**

- date:
- last_updated:
- last_trigger:
- market_status:
- data_freshness:

## Active Opportunities

> 上限 5 条。超限时按「status 优先级 + 距今天数」淘汰。

### OP-001
- subject:
- status: DISCOVERED | RESEARCHING | VALIDATING | ACTIONABLE | WATCH | INVALIDATED | CLOSED
- first_seen:
- current_view:
- why_it_matters:
- key_evidence:
- strongest_counterevidence:
- unknowns:
- invalidation:
- next_check:

## Active Theses

> 上限 5 条，且必须是**有持仓或正在交易**的 thesis。已平仓的 thesis 移到 daily memory，不留在本文件。

### TH-001
- subject:
- linked_opportunity:
- status:
- thesis:
- confidence: LOW | MEDIUM | HIGH
- horizon: intraday | 3-10d | 1-3m | 6-12m | open-ended
- driver:
- evidence_changed_since_last_run:
- expectation_pricing:
- last_material_change:
- invalidation:
- next_check:

## Portfolio Attention

> 只写**当前需要盯**的持仓。没有需要特别关注的就写「无」，不要罗列全部持仓。

- symbol / subject:
  - reason:
  - current_issue:
  - required_check:

## Open Questions

> 上限 3 条。只保留会影响下一轮判断的问题。超过 3 条说明应先在 20:30 集中处理。

- Q-001:
  - question:
  - why_material:
  - status:
  - next_source_or_check:

## Next Actions

> 上限 3 条。必须是**可验证动作**（查什么、验证什么），不是「继续关注」。

1.
2.
3.

## Handoff Note

> **只写一句话**。上一轮的「What changed this run」在下一轮读完即失效，更新时直接覆盖，不要累积。

- 下一轮最优先：
- 上一轮变更（一句话，会被覆盖）：

---

## Retention 规则（硬性）

本文件是**交接面，不是档案**。以下规则每轮更新时必须执行。

### 大小上限

| 部分 | 上限 | 超限处置 |
|:--|:--|:--|
| 全文 | **不超过 150 行 / 6000 字符** | 按下方淘汰顺序清理后再写 |
| Active Opportunities | 5 条 | 淘汰 status 最低、first_seen 最早的 |
| Active Theses | 5 条 | 淘汰已 CLOSED 的，再淘汰 confidence 最低且无持仓的 |
| Portfolio Attention | 只写需盯的 | 无则写「无」，不列全持仓 |
| Open Questions | 3 条 | 超出的移到 daily memory 的待处理区 |
| Next Actions | 3 条 | 超出说明分不清优先级，需重排 |

### 淘汰顺序（超限时按此顺序删）

1. 已 `CLOSED` / `INVALIDATED` 的 Opportunities（可保留结论一句到 daily）
2. 已平仓的 Theses
3. `WATCH` 状态超过 **10 个交易日**无新证据的 Opportunities
4. `next_check` 已过期超过 5 个交易日的条目
5. 已被解决的 Open Questions
6. Handoff Note 中的历史残留（永远只留最新）

### 归档动作

被淘汰的条目**不是直接删掉**，而是在 daily memory 当天段落追加一行摘要：

```
[ACTIVE 归档] OP-x <subject> <status> — <一句话结论>
```

这样历史可追溯，但 ACTIVE 保持精简。

### 自检

每轮更新完 ACTIVE 后，**必须数一下行数**。超过 150 行 → 立即执行淘汰，不得留到下一轮。
