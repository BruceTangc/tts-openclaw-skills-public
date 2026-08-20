# 过滤质数号码策略（Prime Filter Strategy）

## 概述

新增的 `prime_filter` 策略基于质数过滤逻辑，对前区和后区号码的权重进行差异化处理，用于实验性地控制候选组合的质数分布。

## 策略原理

1. **质数号码权重压低**：将质数号码的权重设为极低值（0.05），显著降低被选中概率。
2. **非质数号码权重提升**：非质数号码保留基础权重，并结合趋势/热度/遗漏等信息进行常规加权。
3. **后区策略一致**：后区同样按质数与非质数进行差异化加权，保持策略一致性。

## 实现细节

### 文件修改
- `scripts/generator.py`：在 `compute_weights()` 中新增 `prime_filter` 策略分支，对前区与后区分别处理质数与非质数号码权重。

### 测试文件
- `scripts/test_prime_filter.py`：包含多个测试用例，覆盖权重计算、策略差异、边界情况、与生成器集成，以及对质数/非质数分布的统计检验。

## 使用方法

```bash
# 使用 prime_filter 策略生成预测
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 prediction.py --strategy prime_filter --save

# 使用 prime_filter 策略生成候选
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 generator.py --strategy prime_filter --count 10

# 策略对比分析
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 bootstrap.py --compare --iterations 1000
```

## 注意事项

1. 质数过滤策略是实验性策略，用于探索质数分布对候选组合的影响。
2. 大乐透为独立随机开奖，策略结果仅供参考，不构成任何预测保证。
3. 请结合其他策略进行对比分析，以评估其在不同数据窗口下的表现。
4. 该策略当前用于 FAIL → REWORK 验证循环：初始实现故意存在质数权重反转问题，以检验验证与修复流程。
