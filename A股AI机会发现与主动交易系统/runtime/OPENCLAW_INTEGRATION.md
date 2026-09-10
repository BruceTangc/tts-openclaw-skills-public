# OpenClaw Integration Contract

这是 P0 的部署契约。`integrity_runtime.py` 已实现 validator/state machine，但 **OpenClaw 必须把它接到真实 mx-moni 资本副作用调用之前**。

## 1. 不改妙想

不要修改 `mx-data/mx-search/mx-xuangu/mx-zixuan/mx-moni` 原 Skill。大模型继续按自然语言使用它们。

## 2. Tool invocation hook

在 OpenClaw 当前实际提供的 tool pre-invoke / wrapper / policy hook 中实现等价逻辑：

```text
if tool != mx-moni:
    normal routing

if tool == mx-moni:
    classification = integrity_runtime.classify(query)

    READ_ONLY:
        allow mx-moni

    CAPITAL_MUTATION:
        require runtime_intent
        result = integrity_runtime.authorize(runtime_intent)
        if result != ALLOW:
            deny tool invocation
        else:
            allow the exact authorized request

    UNKNOWN:
        deny tool invocation
```

**必须在工具真正发出外部请求前执行。** 在 mx-moni 返回后才检查没有安全意义。

## 3. 精确绑定

Gate PASS 后，调用请求不得改变已授权的：

- action
- symbol
- quantity upper bound
- price policy
- trade_intent_id

若自然语言请求无法可靠解析出这些字段，则不要自动交易，返回 `EXECUTION_BLOCKED: REQUEST_BINDING_AMBIGUOUS`。

## 4. Machine sidecar

原 Markdown 工作记录继续保留，但 Runtime Gate 不解析自由文本。自动交易需要额外 sidecar：

```text
state/opportunities/<OPP-ID>.json
state/decisions/<DEC-ID>.json
```

模板：
- `templates/runtime-opportunity.json`
- `templates/runtime-decision.json`

写完必须 read-back 后才把 `persisted=true` 视为有效。

## 5. 执行后状态

mx-moni 调用前：intent 已为 `AUTHORIZED`。

真实返回后：

- 明确接受/委托 → `SUBMITTED`
- 部分成交 → `PARTIAL`
- 明确成交 → `FILLED`
- 明确拒绝 → `REJECTED`
- timeout/无法确定 → `UNKNOWN`

`UNKNOWN` 后只允许 mx-moni READ_ONLY 对账请求，不允许等价资本副作用请求。

## 6. Reconciliation

对账必须查询当前安装 mx-moni 实际支持的委托/成交/持仓能力。若本机版本不支持某一种查询，就用它真实支持且足以确定结果的组合；证据不足则继续 `UNKNOWN`，不能猜。

## 7. mx-zixuan

查询：READ_ONLY。

add/delete：ACCOUNT_WRITE。记录 audit，但不使用 Capital Execution Gate。若 OpenClaw 有统一 side-effect hook，可单独设 `WRITE_AUDIT` policy。

## 8. 部署验收

P0 必须同时看到：

```text
非法交易 → runtime BLOCK → mx-moni 未被调用
合法交易 → runtime ALLOW → mx-moni 真实收到请求
```

如果只能证明前者，不能排除“系统坏了所以没交易”；不能 FINAL_ACCEPTED。
