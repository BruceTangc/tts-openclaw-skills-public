# A股 AI 机会发现与主动交易系统 V1.2 — Runtime Hardening Acceptance

Status: **ARCHITECTURE_FROZEN / RUNTIME_HARDENING**

文档设计完成不等于真实 OpenClaw 环境已经通过。尤其是资本副作用安全：必须证明 Gate 真正在 tool invocation 前执行，不能用“模块缺失导致交易失败”冒充安全。

## Static Acceptance — PASS

- [x] Discovery 是 Alpha 源，主线/龙头不是顶层发现入口。
- [x] Radar 无交易权限。
- [x] Anomaly → Cluster → Cause → Industry → A-share Map。
- [x] Reality / Expectation / Pricing 独立。
- [x] Opportunity lifecycle + Transition Record。
- [x] Evidence / Hypothesis / Invalidation / Opposing View。
- [x] State Recovery + ordered Commit。
- [x] Decision / Execution contract。
- [x] Runtime integrity module 已加入仓库。
- [x] trade_intent ledger / UNKNOWN reconciliation 状态机已加入。
- [x] first_seen independent anchor 已加入。

## 妙想 Runtime 原则

妙想由大模型按其原生 Skill 方式使用自然语言调用；本系统不写死底层 API/schema。当前 OpenClaw 实际安装版本暴露什么能力，就只使用什么能力。

- READ_ONLY 数据/查询：按 Tool Routing 使用；
- `mx-zixuan` add/delete：账户写操作，记录 Write Audit，但不等同资本交易；
- `mx-moni` 当前实际支持的任何资本副作用意图：必须先过 Execution Gate；
- UNKNOWN mx-moni intent：fail-closed，先确认意图/能力。

## P0 Runtime Acceptance — MUST PASS

### A. Gate interception

1. 证明 OpenClaw 的真实 `mx-moni` 资本副作用调用路径在 tool invocation **之前**经过 `runtime/integrity_runtime.py authorize` 或等价强制 hook。
2. 直接让 Agent 尝试绕过 Gate 调用资本副作用操作，必须被 runtime 拒绝；仅“Agent遵守SKILL所以没调用”不算 PASS。
3. `mx-moni` 只读查询仍可正常执行。

### B. Negative authorization

4. No Opportunity → BLOCK。
5. CLOSED/INVALIDATED Opportunity → BLOCK。
6. No Decision → BLOCK。
7. Decision 未 read-back 验证持久化 → BLOCK。
8. Decision=WAIT/BLOCKED/NO_ACTION → BLOCK。
9. action/symbol/quantity 超出授权 → BLOCK。
10. portfolio/T+1/liquidity/risk 任一未通过 → BLOCK。
11. duplicate trade_intent_id → BLOCK。
12. 同标的存在 UNKNOWN unresolved execution → BLOCK 等价新交易。

### C. Positive authorization

13. Valid Opportunity + Valid persisted Decision + ALLOW + unique intent + risk checks 全通过 → Gate 必须真实返回 ALLOW。
14. ALLOW 后真实 mx-moni 请求必须可到达工具；不能因为 integrity module/调用链损坏而失败。
15. mx-moni 明确返回的真实状态按原样进入 Execution Record；REJECTED/UNKNOWN 不得写成 FILLED。

### D. Idempotency / Reconciliation

16. intent 从 AUTHORIZED → SUBMITTED/PARTIAL/FILLED/REJECTED/UNKNOWN 有持久状态。
17. UNKNOWN 后不得直接 retry。
18. 必须自然语言调用 mx-moni 查询真实委托/成交/持仓进行 reconciliation。
19. 没有 mx-moni 对账证据，runtime 不允许标 RECONCILED。
20. 对账完成后如仍需交易，使用新的 trade_intent_id；不得复用旧 ID。

### E. first_seen integrity

21. Discovery 第一次持久化后生成独立 anchor。
22. 正常更新不改变 first_seen，verify PASS。
23. 用 sed/编辑器篡改 first_seen 后 verify 必须返回 FIRST_SEEN_INTEGRITY_VIOLATION。
24. 被篡改记录不得进入 Early Discovery/Lead Time 成绩。

### F. Existing system invariants

25. State Recovery 失败禁止 BUY/ADD。
26. Radar 不能直接交易。
27. Stage 更新前存在 Transition Record。
28. REQUIRED fact 缺失 → WAIT/BLOCKED。
29. material state change 遵守对象先写、system-state 最后写并 read-back。
30. MISSED_OPPORTUNITY 不允许事后回填 first_seen。
31. CLOSED Opportunity 产生 Attribution。

## 最终裁决

只有 P0 A-E 全部真实 PASS，且 F 无回归，才允许：

`FINAL_ACCEPTED = true`

以下情况一律不能 FINAL_ACCEPTED：
- Gate 只是文档约定；
- Agent 可以直接调用资本副作用工具绕过 Gate；
- 合法授权也无法真实到达 mx-moni；
- UNKNOWN 可重复提交；
- first_seen 篡改检测无效。
