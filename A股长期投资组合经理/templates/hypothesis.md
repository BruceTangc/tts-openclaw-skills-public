# Investment Hypothesis — {股票代码} {股票名称}

> 回答：**为什么投资这家公司？** 假设卡是决策框架，不是推荐列表。
> V3.4 协议：所有新数据都必须产生 Evidence 并反向追踪；假设状态变化须引用 Evidence ID；禁止单数据点推翻长期 Thesis（按 Evidence→短期→中期→长期→Hypothesis Impact 判断）。
> 所有新数据都必须问：这条数据加强还是削弱本假设？
> 反方思维：始终给出 Bull / Base / Bear + 空头反驳。市场价隐含哪种情景？

## 核心投资假设
（一句话：未来 X 年利润 CAGR Y%，由什么驱动）

## 价值驱动
1. 行业增长
2. 市占率提升
3. 毛利率改善
4. ...

## 关键验证数据
| 指标 | 数值 | 所属日期 | 来源 | 是否验证 | 口径 |
|:----|:----|:----|:----|:----|:----|
| 营收增速 | | | | | |
| 净利润增速 | | | | | |
| 毛利率 | | | | | |
| ROE | | | | | |
| ROIC | | | | | |
| 经营现金流 | | | | | |
| 自由现金流 | | | | | |
| 现金流/净利润 | | | | | |
| 负债 | | | | | |
| 市占率 | | | | | |

## 估值
- **估值带**：PE_low / PE_fair / PE_high（方法）
- **当前估值**：___（历史分位 %）
- **同行对比**：

## Bull / Base / Bear
- **Bull**：利润 CAGR ___%
- **Base**：利润 CAGR ___%
- **Bear**：利润停止增长 / 下降
- **市场价隐含哪种情景**：___
- **空头会怎么反驳我**：___

## 证伪条件（falsifiers）
| 指标 | 触发条件 | 动作 |
|:----|:----|:----|
|  |  | **ACTIVE→WEAKENING**（重要负面，未达失效）→ **INVALIDATED**（满足失效条件）→ **ARCHIVED**（历史） |
> 动作与正文 7.0 六态完全对应：满足 Invalidation Conditions 必须→INVALIDATED（不得赖在 WEAKENING）；INVALIDATED/ARCHIVED 不得作 BUY/ADD 依据。

## 生命周期（V3.4：统一六态 IDEA→VALIDATING→ACTIVE→WEAKENING→INVALIDATED→ARCHIVED）
> 状态推进必须有 Evidence 或明确规则驱动，不得仅凭主观标状态；状态变化写原因 + 引用 Evidence ID。
- **lifecycle_status**：`IDEA / VALIDATING / ACTIVE / WEAKENING / INVALIDATED / ARCHIVED`（新假设默认 VALIDATING；INVALIDATED/ARCHIVED 属历史，不得作 BUY/ADD 依据。）
- **invalidation_conditions**：什么发生就推翻此假设（与下方「证伪条件」一致，供主动监测）
- **confidence**：当前置信度（0~1 或 %，见文件末尾）
- **last_verified**：上次验证日期
- **next_verification**：下次验证日期
- **freshness**：核心证据时效 FRESH / AGING / STALE（同 9.6；STALE 不得作唯一关键依据，须重查/降 Confidence/入 Agenda）

- **目标仓位 %**：___   **最大仓位 %**：___
- **上次审查**：____   **审查周期**：____

## 证据日志（append-only，V3.4：每行必须带 Evidence ID）
| 日期 | Evidence ID | 来源 | 证据/发现/判断 | 短期/中期/长期影响 | 置信度影响 |
|:----|:----|:----|:----|:----|:----|

## 当前置信度：___%   上次验证：____   下次验证：____
> lifecycle_status：___    freshness（核心证据）：___   （STALE 须重查/降 Confidence/入 Agenda）
