---
name: dlt-simulator
display_name: 超级大乐透概率统计模拟器
title: 超级大乐透概率统计模拟与策略实验
description: 基于历史开奖数据进行概率统计分析，生成10组模拟候选，选取Top 2作为BUY、其余8组作为WATCH，并在开奖后进行全量复盘、奖级判定和策略迭代。
version: 1.0.0
author: OpenClaw
---

# 超级大乐透概率统计模拟器 v1.0

> ⚠️ **铁律**：SKILL 已封装全部逻辑，agent 只需执行下面列出的命令，零代码、零脚本、零临时文件。
> 禁止 `python3 -c`、禁止 heredoc、禁止写临时 .py、禁止手拼 JSON。
>
> 本 Skill 使用官方中奖规则仅用于判断每组模拟号码的中奖等级，不进行奖金金额预测、理论奖金计算、ROI 或收益模拟。

## 架构概览

本 Skill 采用模块化设计，共 15 个 Python 模块：

| 模块 | 职责 |
|:--|:--|
| `common.py` | 公共工具函数、路径常量 |
| `fetch_history.py` | 从体彩官网抓取历史开奖数据 |
| `validate_data.py` | 数据完整性/格式/逻辑验证 |
| `statistics.py` | 频次统计、遗漏、冷热号、和值、奇偶比、区间分布 |
| `confidence.py` | Wilson 置信区间分析 |
| `chi_square.py` | 卡方检验（均匀分布假设） |
| `monte_carlo.py` | Monte Carlo 大规模模拟 |
| `generator.py` | 候选组合生成 + 多维度评分 |
| `diversify.py` | 组合多样性过滤（区间/奇偶/重叠度） |
| `validator.py` | 历史完整中奖组合硬过滤 |
| `prize_checker.py` | 中奖等级判断（2026新规7奖级） |
| `prediction.py` | 18:00 生成预测（BUY + WATCH） |
| `review.py` | 21:30 复盘（对比开奖 + 更新策略表现） |
| `bootstrap.py` | Walk-forward 回测 + Bootstrap 分析 |
| `strategy_manager.py` | 策略版本管理（KEEP / ADJUST / REVERT） |

## 规则说明

- **前区**: 从 01-35 选 5 个号码（不可重复）
- **后区**: 从 01-12 选 2 个号码（不可重复）
- **基本投注**: 2元/注
- **追加投注**: +1元/注（一二等奖奖金 × 1.8）

### 奖级表（2026新规，7个奖级）

| 奖级 | 中奖条件 | 类型 | 奖金(奖池<8亿) | 奖金(奖池≥8亿) |
|:--|:--|:--|:--|:--|
| 一等奖 | 前区5+后区2 | 浮动 | ≤1000万 | ≤1000万 |
| 二等奖 | 前区5+后区1 | 浮动 | ≤？ | ≤？ |
| 三等奖 | 前区5+后区0 / 前区4+后区2 | 固定 | 5000元 | 6666元 |
| 四等奖 | 前区4+后区1 | 固定 | 300元 | 380元 |
| 五等奖 | 前区4+后区0 / 前区3+后区2 | 固定 | 150元 | 200元 |
| 六等奖 | 前区3+后区1 / 前区2+后区2 | 固定 | 15元 | 18元 |
| 七等奖 | 前区3+后区0 / 前区2+后区1 / 前区1+后区2 / 前区0+后区2 | 固定 | 5元 | 7元 |

中奖条件共 13 条，合并为 7 个奖级。一二等奖浮动，三至七等奖固定。

---

## 所有可用命令

### 分析类

```bash
# 统计分析
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 statistics.py --window 100

# Wilson 置信区间
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 confidence.py --window 100

# 卡方检验
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 chi_square.py --window 100

# 数据验证
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 validate_data.py
```

### 生成类

```bash
# 生成预测（完整流程：抓取→分析→评分→过滤→输出Top 10）
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 prediction.py --save

# 指定策略生成
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 prediction.py --strategy hot --save

# 候选生成（不保存）
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 generator.py --count 10 --strategy balanced

# 使用过滤质数策略生成候选
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 generator.py --count 10 --strategy prime_filter

# 使用尾数过滤策略生成候选
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 generator.py --count 10 --strategy tail_filter
```

### 模拟类

```bash
# Monte Carlo 模拟
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 monte_carlo.py --front 5 12 18 25 33 --back 7 10 --iterations 100000

# Bootstrap 回测
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 bootstrap.py --strategy balanced --iterations 1000

# 策略对比
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 bootstrap.py --compare --iterations 500
```

### 中奖检查

```bash
# 单注检查
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 prize_checker.py --front 5 12 18 25 33 --back 7 10 --draw-front 5 12 18 25 33 --draw-back 7 10
```

### 复盘类

```bash
# 复盘（对比预测与实际开奖）
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 review.py

# 策略表现汇总
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 review.py --performance
```

### 策略管理

```bash
# 显示当前策略
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 strategy_manager.py --show

# 调整策略
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 strategy_manager.py --adjust hot_boost

# 回退策略
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 strategy_manager.py --revert

# 保存快照
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 strategy_manager.py --snapshot

# 查看历史
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 strategy_manager.py --history
```

### 数据抓取

```bash
# 抓取历史数据
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 fetch_history.py --force

# 查看最近N期
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 fetch_history.py --recent 10
```

---

## 模拟 cron 标准流程（周一/三/六 18:00）

全部用命令，零代码。

**第1步：生成预测（一条命令完成：抓取+分析+评分+过滤+保存）**
```bash
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 prediction.py --save
```

**第2步：推送**
- 读取 prediction.py 输出的 BUY 和 WATCH 组合
- 纯文字推送给用户（禁用表格）
- Top 2 = BUY，其余 = WATCH

---

## 开奖对比流程（cron 专项，命令驱动版）

开奖对比 cron（周一/三/六 21:30）。**全程只执行下面列出的命令，零代码。**

**第1步：复盘（一条命令完成：拉最新+匹配+更新策略表现）**
```bash
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 review.py --json
```

**第2步：策略评估（如果需要调整）**
```bash
cd ~/.openclaw/workspace-jarvis/skills/dlt-simulator/scripts && python3 strategy_manager.py --show
```

**第3步：推送（纯文字，禁用表格）**
- 附真实开奖 vs 推荐组合逐注对比（命中数+奖级）
- 附策略表现汇总

---

## 关键文件

| 文件 | 用途 |
|:--|:--|
| `strategies/current_strategy.json` | 当前策略配置 |
| `data/history_draws.json` | 历史开奖数据缓存 |
| `data/current_prediction.json` | 当前预测（供 review 使用） |
| `reports/reviews/` | 复盘结果存档 |
| `reports/statistics/` | 统计分析结果 |
| `strategies/strategy_history/` | 策略版本快照 |

## 选号策略

| 策略 | 说明 |
|:--|:--|
| `balanced` | 综合冷热号+遗漏值+段分布+趋势 |
| `hot` | 偏向近期高频出现的热号 |
| `cold` | 偏向长期未出的冷号 |
| `trend` | 偏向近期频率上升的号码 |
| `statistical` | 基于卡方检验和置信区间的统计分析策略 |
| `prime_filter` | 过滤质数号码策略：压低质数权重、提升非质数权重 |
| `tail_filter` | 尾数过滤策略：压低高频尾数权重、提升低频尾数权重 |

## 核心指标

- **Top-2 Selection Accuracy**：模型Top 2是否包含本期10组候选中最佳表现组合（注意：不是命中率，是选优能力）
- **Walk-forward 回测**：禁止未来数据泄露
- **Walk-forward Monte Carlo / Bootstrap-style Stability Analysis**：多次随机取训练窗口的重采样稳定性分析
  （注意：这是随机时间窗口的稳定度实验，不是严格统计学 bootstrap 抽样推断）

---

## 修复记录（2026-08-20）

对 dlt-simulator 做了一轮正确性修复（审计驱动 + 本地实测），未推倒重做：

### 数据源（fetch_history.py）
- **官方历史 API**：改用体彩官方 JSON 接口 `webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry?gameNo=85`
  （原 `lottery.gov.cn/kj/kjlb.html?dlt` 实测返回 HTML 壳、无数据）。分页拉全量 2912 期（07001→26094，非法 0）。
- **数据校验**：新增 `_is_valid_draw()` —— 前区恰 5 个且 1-35、后区 2 个且 1-12、无重复、期号非空。
  **脏数据一律丢弃，绝不写入缓存/历史**（此前 500.com 会产出期号截断、号码>35 的脏数据并污染缓存）。
- 源优先级：官方 API → js-lottery → 500.com（全部过校验）。

### 核心 bug（P0）
- **Bootstrap TypeError**：`bootstrap.py` `for _ in iterations:` → `for _ in range(iterations):`（原为 int 不可迭代，必崩）。
- **未来数据泄露**：Walk-forward 回测历史过滤改用 `build_history_combos(train_draws)`（只用训练窗口），
  不再用 `load_history_combos()`（读全量库含测试点之后）。实测：新逻辑无泄露、旧逻辑会泄露。
- **复盘期号错配**：`review.py` 增加硬性条件 `pred_issue != draw_issue` → 返回 `REVIEW_PENDING`，
  不对比、不更新 win_count/performance/strategy（防拿上期开奖对比本期预测污染数据）。

### 期号与权重（P1）
- **期号跨年**：`prediction.py` `compute_next_issue()` 用真实年度末期号表（07=93、08=154…25=150、26=94）
  判断跨年，当期号达到该年末期跳次年 001。全量 2911 组相邻期号验证 100% 匹配。
- **评分权重**：`generator.py` 删除恒为 0 的 `prize_prob`，5 项重新归一化
  （frequency .278 / omission .222 / sum .167 / odd_even .167 / zone .167，和=1.0）。
