# A股 AI 机会发现与主动交易系统 V1.1 — Final Acceptance

Status: **ARCHITECTURE_FROZEN / SPEC_FINAL**

本文件定义最终运行验收。文档设计完成不等于真实 OpenClaw 环境已经通过；必须在安装后以真实工具与持久化环境逐项验证。

## Static Acceptance — PASS

- [x] Discovery 是 Alpha 源，主线/龙头不是顶层发现入口。
- [x] Radar 无交易权限。
- [x] Anomaly → Cluster → Cause → Industry → A-share Map，禁止直接跳 Stock。
- [x] Reality / Expectation / Pricing 独立。
- [x] immutable first_seen + no hindsight discovery。
- [x] Opportunity lifecycle + mandatory Transition Record。
- [x] Evidence / Hypothesis / Invalidation / Opposing View。
- [x] Required Fact criticality + approved Tool Routing + fail-closed。
- [x] State Recovery + ordered Commit + persistence verification。
- [x] Decision Gate + Execution Authorization Contract。
- [x] trade_intent_id idempotency + UNKNOWN execution reconciliation。
- [x] T+1 / liquidity / cost / portfolio risk。
- [x] Missed Opportunity + Discovery/Trade Attribution + anti-future-leakage。
- [x] Discovery Lead Time / False Discovery / Missed Opportunity 等 KPI。

## Runtime Acceptance — MUST PASS IN OPENCLAW

1. 首次启动可初始化 System State；第二次运行能恢复。
2. 删除/破坏非首次 State 后系统进入 STATE_RECOVERY_FAILED，禁止 BUY/ADD。
3. 创建 Discovery 后 first_seen 持久化；后续更新不覆盖。
4. Radar 异常只生成/更新 Discovery/Opportunity，不调用 mx-moni。
5. Stage 更新前存在已持久化 Transition Record。
6. REQUIRED fact 的主工具失败且无可靠替代时，Decision 为 WAIT/BLOCKED。
7. 禁止使用 Python/requests/curl/临时爬虫替代 REQUIRED 数据。
8. Decision 未持久化或 result 非 ALLOW/REDUCE_SIZE 时 mx-moni 不被调用。
9. BUY/ADD 前持仓/现金/T+1/流动性已刷新。
10. 重复 trade_intent_id 不产生第二笔订单。
11. 模拟一次交易工具 timeout/UNKNOWN；系统进入 UNRESOLVED_EXECUTION，先对账再允许后续等价交易。
12. mx-moni REJECTED/UNKNOWN 不被写成 FILLED。
13. material state change 的对象记录先写，system-state 最后写，并可重新读取验证。
14. 当天形成重大主题但无事前 Discovery 时产生 MISSED_OPPORTUNITY，不回填 first_seen。
15. CLOSED Opportunity 产生 Attribution。
16. 无重要变化返回 NO_MATERIAL_CHANGE / NO_ACTION。

只有上述 Runtime Acceptance 全部通过，才允许标记：

`FINAL_ACCEPTED = true`

在此之前，Skill 可以用于研究/模拟验证，但不得把“文档静态验收通过”表述成“真实运行已验证通过”。
