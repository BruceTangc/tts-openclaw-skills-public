# 奇偶平衡过滤策略（odd_even_balance_filter）

## 策略说明

基于历史开奖数据的奇偶频次统计，动态调整号码权重，实现候选组合的奇偶平衡。

## 核心逻辑

### 前区（1-35 选 5）
- 统计最近 `window` 期历史开奖中，前区奇数号码（n % 2 == 1）与偶数号码（n % 2 == 0）的出现总频次
- 若奇数过热（odd_freq > even_freq），则压低奇数号码权重至 0.05
- 反之压低偶数号码权重至 0.05
- 另一类保持 1.0 + 热度(+1.5) + 遗漏>15(+1.0) + 趋势rising(+0.5)

### 后区（1-12 选 2）
- 同理独立统计、独立平衡
- 前后区奇偶频次统计完全独立，互不影响

## 权重计算公式

被压低的一类号码：
```
w = 0.05
```

另一类号码：
```
w = 1.0
if n in hot_front:  # 热号加权
    w += 1.5
if miss > 15:       # 遗漏>15期加权
    w += 1.0
if n in rising:     # 趋势上升加权
    w += 0.5
```

## 边界处理

- **空数据边界**：data 为空（[]）或 window 内无历史数据时，返回默认均匀权重（所有号码 w=1.0）
- **奇偶相等**：当 odd_freq == even_freq 时，不压低任何一类

## 使用方法

```bash
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 generator.py --count 10 --strategy odd_even_balance_filter
```

## 与其他策略对比

| 策略 | 策略类型 | 前区逻辑 | 后区逻辑 |
|:--|:--|:--|:--|
| balanced | 综合 | 冷热+遗漏+趋势 | 冷热 |
| even_filter | 过滤 | 偶数权重0.05 | 无 |
| prime_filter | 过滤 | 质数权重0.05 | 质数权重0.05 |
| tail_filter | 过滤 | 高频尾数权重0.05 | 高频尾数权重0.05 |
| odd_even_balance_filter | 动态平衡 | 压低过热奇/偶数 | 压低过热奇/偶数 |

## 测试

```bash
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 -m pytest test_odd_even_balance_filter.py -v
```
