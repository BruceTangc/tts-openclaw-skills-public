# 统计分析策略（Statistical Strategy）

## 概述

新增的 `statistical` 策略基于统计学方法进行号码权重计算，结合卡方检验和置信区间分析，为大乐透号码选择提供数据驱动的决策支持。

## 策略原理

### 1. 卡方检验权重
- 检验号码出现频率是否偏离均匀分布
- 使用卡方统计量判断显著性：
  - χ² > 3.84（95%显著性）：权重 +1.5
  - χ² > 2.71（90%显著性）：权重 +1.0

### 2. 置信区间权重
- 使用Wilson置信区间分析频率偏离
- 频率显著偏高：权重 +1.0
- 频率显著偏低：权重 +0.5（均值回归假设）

### 3. 遗漏值权重
- 长期未出现的号码给予额外权重（均值回归假设）
- 遗漏 > 20期：权重 +0.8
- 遗漏 > 10期：权重 +0.4

## 实现细节

### 文件修改
- `scripts/generator.py`：在 `compute_weights()` 函数中新增 `statistical` 策略分支

### 测试文件
- `scripts/test_statistical.py`：包含4个测试用例
  1. 权重计算测试
  2. 与balanced策略差异测试
  3. 边界情况测试
  4. 与生成器集成测试

## 使用方法

```bash
# 使用统计分析策略生成预测
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 prediction.py --strategy statistical --save

# 使用统计分析策略生成候选
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 generator.py --strategy statistical --count 10

# 策略对比分析
cd ~/.openclaw/workspace/_ref-tts-public/dlt-simulator/scripts && python3 bootstrap.py --compare --iterations 1000
```

## 策略特点

1. **数据驱动**：基于统计检验而非主观判断
2. **多维度分析**：结合频次、置信区间、遗漏值三个维度
3. **风险控制**：对显著偏离的号码给予适当权重，避免极端偏差
4. **均值回归**：对长期未出现的号码给予一定权重，考虑均值回归效应

## 验证结果

- 所有测试通过（7/7）
- 与现有策略（balanced/hot/cold/trend）有显著差异
- 能够正常生成候选组合
- 不破坏现有功能

## 注意事项

1. 统计分析策略基于历史数据，不代表未来预测
2. 大乐透为独立随机开奖，统计策略仅供参考
3. 建议与其他策略结合使用，进行策略对比分析