# 尾数过滤策略（Tail Filter Strategy）

## 概述

`tail_filter` 策略基于号码个位数（尾数，n%10，取值 0-9）进行差异化权重处理。自动检测历史数据中最近高频出现的尾数并压低其权重，试图避开尾数过度集中的号码组合。

## 策略原理

1. **前区**：统计所有前区号码的尾数频次（`Counter(n%10 for n in front)`），取 `most_common(3)` 得到 top-3 高频尾数。命中高频尾数的号码权重压低至 0.05；非命中号码保留基础权重 1.0，并叠加热度（+1.5）、遗漏>15（+1.0）、趋势rising（+0.5）加成。
2. **后区**：同理取 `most_common(2)` 得到 top-2 高频尾数。命中权重 0.05，非命中权重 1.0 + 后区热号 top-4（+1.5）加成。
3. **注意**：后区号码范围 1-12，尾数实际只覆盖 0-2（即个位数 0、1、2）。

## 与其他策略的对比

| 对比维度 | prime_filter | tail_filter |
|:--|:--|:--|
| 过滤维度 | 质数/非质数 | 高频尾数/非高频尾数 |
| 前区压低目标 | 固定质数集 | 动态 top-3 高频尾数 |
| 后区压低目标 | 固定质数集 | 动态 top-2 高频尾数 |
| 非命中加权 | 热度+遗漏+趋势 | 热度+遗漏+趋势（前区）/ 热号 top-4（后区） |

## 实现细节

### 文件修改
- `scripts/generator.py`：在 `compute_weights()` 的前区和后区 if/elif 链中各新增 `tail_filter` 策略分支。

### 测试文件
- `scripts/test_tail_filter.py`：包含权重计算、高频尾数压低、策略差异、边界情况、集成测试、后区权重测试共 6 个测试用例。

## 使用方法

```bash
# 使用 tail_filter 策略生成候选
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 generator.py --strategy tail_filter --count 10

# 使用 tail_filter 策略生成预测
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 prediction.py --strategy tail_filter --save

# 运行 tail_filter 策略测试
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 -m pytest test_tail_filter.py -v
```

## 注意事项

1. 尾数过滤策略为实验性策略，用于探索尾数分布对候选组合的影响。
2. 大乐透为独立随机开奖，策略结果仅供参考，不构成任何预测保证。
3. 后区号码范围仅 1-12，尾数分布天然受限（仅 0/1/2），策略效果可能不如前区明显。
4. 请结合其他策略进行对比分析，以评估其在不同数据窗口下的表现。
