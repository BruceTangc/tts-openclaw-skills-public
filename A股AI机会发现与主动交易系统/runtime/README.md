# Runtime Integrity Layer

本目录只负责**不可依赖 Agent 自律的安全不变量**，不重写妙想，不实现行情/资讯/选股 API。

## 边界

妙想仍按其原生 Skill 方式由大模型使用自然语言调用：

- `mx-data / mx-search / mx-xuangu`：研究与数据能力；
- `mx-zixuan`：自选查询/维护；
- `mx-moni`：模拟组合查询与当前安装版本实际暴露的资本副作用能力。

**实际能力以 OpenClaw 当前安装版本为准。** 不因公开文档存在某功能就假设本机一定存在。

`integrity_runtime.py` 不调用东方财富 API，也不猜测 mx-moni 内部 schema。它只做：

1. 交易意图分类（只读 / 资本副作用 / 未知）；
2. Execution Authorization fail-closed；
3. `trade_intent_id` 持久化与等价意图去重；
4. UNKNOWN execution 阻塞与 reconciliation 状态机；
5. Discovery `first_seen` 锚定与篡改检测；
6. append-only authorization audit。

## 关键要求：必须接在真正的交易入口前

仅把本文件放进 Skill **不能**阻止 Agent 直接绕过它调用 mx-moni。

OpenClaw 部署时必须满足以下不变量：

```text
Agent
  ├─ mx-moni READ_ONLY query ───────────────→ mx-moni
  └─ mx-moni CAPITAL_MUTATION
           ↓
      integrity_runtime authorize
           ├─ BLOCK → 禁止调用 mx-moni
           └─ ALLOW → 才允许调用 mx-moni
                         ↓
                    写 Execution Result
                         ↓
              update-intent / reconcile
```

如果当前 OpenClaw 无法在 tool invocation 前插入此 Gate，则本模块只能作为 validator，不能宣称 `FINAL_ACCEPTED`。

## 状态目录

运行时新增：

```text
state/runtime/trade-intents.json
state/runtime/authorization-audit.jsonl
state/runtime/discovery-anchors/<DISC-ID>.json
```

所有关键 JSON 使用 temp + fsync + atomic replace 写入，并立即 read-back 验证。

## Decision 的机器可验证字段

用于自动交易的 Decision 必须同时提供机器可验证字段：

```json
{
  "decision_id": "DEC-...",
  "opportunity_id": "OPP-...",
  "action": "BUY",
  "result": "ALLOW",
  "trade_intent_id": "INTENT-...",
  "symbol": "600000",
  "max_quantity": 100,
  "persisted": true,
  "portfolio_refreshed": true,
  "t_plus_1_passed": true,
  "liquidity_passed": true,
  "risk_passed": true
}
```

这些字段不是让 Agent 自己口头声称通过；生成 Decision 后必须落盘并 read-back，Gate 从落盘文件重新读取。

## 使用示例

### 1. 判断 mx-moni 自然语言请求是否有资本副作用

```bash
python runtime/integrity_runtime.py classify "查询我的持仓"
python runtime/integrity_runtime.py classify "买入 600000 100股"
```

返回 `READ_ONLY / CAPITAL_MUTATION / UNKNOWN`。`UNKNOWN` 对资本工具默认 fail-closed。

### 2. 授权交易

```bash
python runtime/integrity_runtime.py --root . authorize \
'{"trade_intent_id":"INTENT-001","opportunity_id":"OPP-001","decision_id":"DEC-001","action":"BUY","symbol":"600000","quantity":100,"price_policy":"LIMIT"}'
```

只有返回 `result=ALLOW` 才允许把对应自然语言交易请求交给 mx-moni。

### 3. 记录执行结果

明确提交：

```bash
python runtime/integrity_runtime.py --root . update-intent INTENT-001 SUBMITTED \
'{"mx_moni_evidence":"真实返回摘要/引用"}'
```

结果不确定：

```bash
python runtime/integrity_runtime.py --root . update-intent INTENT-001 UNKNOWN \
'{"reason":"timeout"}'
```

此时同标的等价新交易被阻塞。必须先自然语言调用 mx-moni 查询真实委托/成交/持仓，再：

```bash
python runtime/integrity_runtime.py --root . update-intent INTENT-001 RECONCILED \
'{"verified_by_mx_moni":true,"reconciliation_evidence":"委托/成交/持仓真实查询证据"}'
```

不得用模型推测或行情走势代替对账。

### 4. first_seen 完整性

Discovery 首次落盘后：

```bash
python runtime/integrity_runtime.py --root . verify-first-seen state/discoveries/DISC-001.json
```

第一次生成不可变 anchor；后续每次读取/更新 Discovery 再校验。若 `first_seen` 被 sed/编辑器改写，返回 `FIRST_SEEN_INTEGRITY_VIOLATION`，该记录不得用于计算 Early Discovery/Lead Time。

## mx-zixuan

`mx-zixuan` 添加/删除自选属于账户写操作，但不改变资本。它不进入 Capital Execution Gate；应记录 Write Audit。查询为 READ_ONLY。

## 不做的事

- 不重写妙想脚本；
- 不直接请求东方财富 API；
- 不写死妙想内部 endpoint/schema；
- 不让 Radar/Research 获得交易权限；
- 不把工具调用失败当成 Gate PASS；
- 不把“模块缺失导致交易失败”当安全证明。
