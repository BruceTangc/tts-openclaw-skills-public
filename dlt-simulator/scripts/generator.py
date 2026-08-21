#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generator.py — 候选生成+评分模块

生成候选组合池，对每组进行多维度评分
"""
import random
import math
import warnings
from collections import Counter

from common import load_config, combination_key, mean, std

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
FRONT_PICK = cfg["front_pick"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]
BACK_PICK = cfg["back_pick"]
POOL_SIZE = cfg["candidate_pool_size"]
MAX_FRONT_OVERLAP = cfg["max_front_overlap"]

_KNOWN_STRATEGIES = frozenset({
    "balanced", "hot", "cold", "trend", "even_filter",
    "statistical", "prime_filter", "tail_filter",
    "odd_even_balance_filter", "sum_filter", "zone_filter",
    "repeat_filter", "span_filter",
})


def weighted_sample(pool_weights, k):
    """加权不重复抽样"""
    items = list(pool_weights.keys())
    weights = [pool_weights[n] for n in items]
    chosen = []
    rem_items = list(items)
    rem_weights = list(weights)
    for _ in range(k):
        total_w = sum(rem_weights)
        if total_w <= 0:
            idx = random.randrange(len(rem_items))
        else:
            r = random.uniform(0, total_w)
            cum = 0.0
            idx = 0
            for i, w in enumerate(rem_weights):
                cum += w
                if cum >= r:
                    idx = i
                    break
        chosen.append(rem_items[idx])
        rem_items.pop(idx)
        rem_weights.pop(idx)
    return sorted(chosen)


def _parse_strategies(strategy):
    """解析 "+" 分隔的策略表达式 → 去重保序的已知策略名列表。"""
    if strategy is None:
        strategy = ""
    else:
        strategy = str(strategy).strip()
    names, seen = [], set()
    for part in strategy.split("+"):
        p = part.strip()
        if not p:
            continue
        if p not in _KNOWN_STRATEGIES:
            warnings.warn(f"未知策略 '{p}'，已跳过", UserWarning, stacklevel=2)
            continue
        if p in seen:
            continue
        seen.add(p)
        names.append(p)
    return names if names else ["balanced"]


def compute_weights(draws, strategy="balanced", window=None):
    """
    根据策略计算号码权重，支持多策略 "+" 组合（逐号相乘融合，不归一化）。

    Args:
        draws: 历史开奖数据列表（含 "front"/"back" 键的字典）。
        strategy: 策略名。单个名称（如 "hot"）或用 "+" 组合多个
                  （如 "hot+tail_filter"）。多策略时前后区独立、
                  各策略权重逐号相乘（product）融合，不归一化。
                  未知策略名自动跳过并告警；空表达式回退 "balanced"。
        window: 可选，仅用最近 window 期数据。

    Returns:
        tuple: (front_weights, back_weights)，均为 {号码: 权重} 字典。

    组合语义：
        - 多策略融合 = 各单策略权重逐号相乘（product），不做归一化
          （如 "hot+cold" 同时给热号、冷号高权重，等权叠加后整体更均衡）。
        - trend / even_filter 只作用于前区（后区无对应分支，按 balanced
          计算），故 "hot+trend" 的后区权重等价于 "hot+balanced" 的后区权重。
    """
    names = _parse_strategies(strategy)
    if len(names) == 1:
        return _compute_weights_single(draws, names[0], window)
    front_w = {n: 1.0 for n in range(FRONT_MIN, FRONT_MAX + 1)}
    back_w = {n: 1.0 for n in range(BACK_MIN, BACK_MAX + 1)}
    for nm in names:
        fw, bw = _compute_weights_single(draws, nm, window)
        for n in range(FRONT_MIN, FRONT_MAX + 1):
            front_w[n] *= fw.get(n, 1.0)
        for n in range(BACK_MIN, BACK_MAX + 1):
            back_w[n] *= bw.get(n, 1.0)
    return front_w, back_w


def _compute_weights_single(draws, name, window=None):
    """单策略权重计算（内部）。name 为单一策略名"""
    data = draws[:window] if window else draws
    total = len(data)
    if total == 0:
        front_w = {n: 1.0 for n in range(FRONT_MIN, FRONT_MAX + 1)}
        back_w = {n: 1.0 for n in range(BACK_MIN, BACK_MAX + 1)}
        return front_w, back_w

    # 统计
    front_freq = Counter()
    back_freq = Counter()
    front_last_seen = {}
    back_last_seen = {}

    for i, d in enumerate(data):
        for n in d["front"]:
            front_freq[n] += 1
            if n not in front_last_seen:
                front_last_seen[n] = i
        for n in d["back"]:
            back_freq[n] += 1
            if n not in back_last_seen:
                back_last_seen[n] = i

    # 趋势分析
    recent_n = min(20, total)
    recent = data[:recent_n]
    older = data[recent_n:]
    recent_freq = Counter()
    older_freq = Counter()
    for d in recent:
        for n in d["front"]:
            recent_freq[n] += 1
    for d in older:
        for n in d["front"]:
            older_freq[n] += 1

    rising = set()
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        r = recent_freq.get(n, 0) / max(1, recent_n)
        o = older_freq.get(n, 0) / max(1, len(older))
        if r > o * 1.3 and r > 0.02:
            rising.add(n)

    # 热号/冷号
    sorted_front = sorted(range(FRONT_MIN, FRONT_MAX + 1),
                          key=lambda n: front_freq.get(n, 0), reverse=True)
    hot_front = set(sorted_front[:10])
    cold_front = set(sorted_front[-10:])

    # 构建权重
    front_w = {}
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if name == "hot":
            w = front_freq.get(n, 0) + 1
        elif name == "cold":
            w = front_last_seen.get(n, total) + 1
        elif name == "trend":
            w = 3.0 if n in rising else 1.0
        elif name == "even_filter":
            # 过滤偶数策略：前区偏向奇数，偶数权重极低
            if n % 2 == 0:
                w = 0.05  # 偶数几乎不选
            else:
                w = 1.0
                if n in hot_front:
                    w += 1.5
                miss = front_last_seen.get(n, total)
                if miss > 15:
                    w += 1.0
                if n in rising:
                    w += 0.5
        elif name == "statistical":
            # 统计分析策略：基于卡方检验和置信区间
            w = 1.0
            # 1. 卡方检验权重：偏离均匀分布的号码加权
            observed = front_freq.get(n, 0)
            expected = total * 5 / 35  # 期望频次
            chi2_contrib = (observed - expected) ** 2 / expected if expected > 0 else 0
            if chi2_contrib > 3.84:  # 95%显著性阈值
                w += 1.5  # 显著偏离
            elif chi2_contrib > 2.71:  # 90%显著性阈值
                w += 1.0  # 边缘显著
            
            # 2. 置信区间权重：频率偏离置信区间
            if total > 0:
                from confidence import wilson_ci
                ci_low, ci_high = wilson_ci(observed, total)
                p_hat = observed / total
                expected_freq = 5 / 35
                if p_hat > ci_high:  # 频率显著偏高
                    w += 1.0
                elif p_hat < ci_low:  # 频率显著偏低
                    w += 0.5  # 低频号码也给一定权重（均值回归假设）
            
            # 3. 遗漏值权重：长期未出现的号码（均值回归假设）
            miss = front_last_seen.get(n, total)
            if miss > 20:  # 遗漏超过20期
                w += 0.8
            elif miss > 10:  # 遗漏超过10期
                w += 0.4
        elif name == "prime_filter":
            # 过滤质数策略：前区压低质数权重，提升非质数权重
            _front_primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31}
            if n in _front_primes:
                w = 0.05
            else:
                # 非质数：常规加权（热度+遗漏+趋势）
                w = 1.0
                if n in hot_front:
                    w += 1.5
                miss = front_last_seen.get(n, total)
                if miss > 15:
                    w += 1.0
                if n in rising:
                    w += 0.5
        elif name == "tail_filter":
            # 尾数过滤策略：前区按号码个位数差异化权重
            _front_tail_freq = Counter(n % 10 for d in data for n in d["front"])
            _top3_tails = {t for t, _ in _front_tail_freq.most_common(3)}
            if n % 10 in _top3_tails:
                w = 0.05
            else:
                w = 1.0
                if n in hot_front:
                    w += 1.5
                miss = front_last_seen.get(n, total)
                if miss > 15:
                    w += 1.0
                if n in rising:
                    w += 0.5
        elif name == "odd_even_balance_filter":
            # 奇偶平衡过滤策略：压低过热的一类号码（奇数或偶数）
            # 统计前区奇偶频次
            _front_odd_freq = sum(1 for d in data for nn in d["front"] if nn % 2 == 1)
            _front_even_freq = sum(1 for d in data for nn in d["front"] if nn % 2 == 0)
            if _front_odd_freq > _front_even_freq:
                suppress = (n % 2 == 1)   # 奇数过热，压低奇数
            elif _front_even_freq > _front_odd_freq:
                suppress = (n % 2 == 0)   # 偶数过热，压低偶数
            else:
                suppress = False          # tie，不压低任何一方
            if suppress:
                w = 0.05
            else:
                w = 1.0
                if n in hot_front:
                    w += 1.5
                miss = front_last_seen.get(n, total)
                if miss > 15:
                    w += 1.0
                if n in rising:
                    w += 0.5
        elif name == "sum_filter":
            # 和值过滤策略：基于和值偏离理论中心的 z-score 压制大号或小号
            _FRONT_THEORY_CENTER = 90.0
            front_sums = [sum(d["front"]) for d in data]
            suppress_front_large = False
            suppress_front_small = False
            if len(front_sums) >= 2 and std(front_sums) > 0:
                _mean_sum = mean(front_sums)
                _std_sum = std(front_sums)
                _z = (_mean_sum - _FRONT_THEORY_CENTER) / _std_sum
                if _z > 1.0:
                    suppress_front_large = True
                elif _z < -1.0:
                    suppress_front_small = True
            w = 1.0
            if suppress_front_large and n >= 19:
                w *= 0.5
            elif suppress_front_small and n <= 18:
                w *= 0.5
            if w == 1.0:
                if n in hot_front:
                    w += 1.5
                miss = front_last_seen.get(n, total)
                if miss > 15:
                    w += 1.0
                if n in rising:
                    w += 0.5
        elif name == "zone_filter":
            # 区间段平衡过滤策略：前区 1-35 分 7 段（每段 5 号），段号=(n-1)//5
            # 段0={1..5}、段1={6..10}、...、段6={31..35}。统计最近 window 期
            # 各段累计出号频次，压制"过热段"（显著高于均匀期望）内所有号码权重到 0.5，
            # 实现段位平衡回归。
            _FRONT_ZONE_NUM = 7     # 前区段数
            _FRONT_ZONE_SIZE = 5    # 每段号码数
            _ZONE_HOT_RATIO = 1.5   # 比值阈值：段出号 ≥ 期望的 1.5 倍才算过热（经济显著性）
            _ZONE_MIN_GAP = 2.0     # 绝对下限：至少比期望多出 2 次（防小窗口单次波动误触发）
            _ZONE_MIN_Z = 1.0       # 跨段 z-score 下限（统计显著性，需段间有离散度）
            _front_zone_freq = [0] * _FRONT_ZONE_NUM
            for d in data:
                for nn in d["front"]:
                    if FRONT_MIN <= nn <= FRONT_MAX:  # 越界号码是脏数据：跳过，不参与段统计
                        _front_zone_freq[(nn - 1) // _FRONT_ZONE_SIZE] += 1
            _front_zone_exp = FRONT_PICK * total / _FRONT_ZONE_NUM  # 均匀期望 = 5*window/7
            _front_zone_std = std(_front_zone_freq)                 # 样本标准差（common.std）
            _front_hot_zones = set()
            # 退化：window<2 → 不压制（balanced 风格，全 1.0 起算）
            if total >= 2:
                for _z_i, _f in enumerate(_front_zone_freq):
                    _gap = _f - _front_zone_exp
                    if _f >= _front_zone_exp * _ZONE_HOT_RATIO and _gap >= _ZONE_MIN_GAP:
                        # std<=0（各段全相等）时 z 无意义 → 退化为仅用比值+下限判定；
                        # 此时各段必恰等于期望（5w 总和 / 7 段），比值条件自然不成立 → 无压制。
                        if _front_zone_std <= 0 or _gap / _front_zone_std >= _ZONE_MIN_Z:
                            _front_hot_zones.add(_z_i)
            if (n - 1) // _FRONT_ZONE_SIZE in _front_hot_zones:
                w = 0.5  # 过热段：段内所有号码权重压到 0.5（段位平衡回归）
            else:
                w = 1.0
                if n in hot_front:
                    w += 1.5
                miss = front_last_seen.get(n, total)
                if miss > 15:
                    w += 1.0
                if n in rising:
                    w += 0.5
        elif name == "repeat_filter":
            # 重号过滤策略：前区压制「上期（最近一期 data[0]）已开出的号码」
            # 权重到 0.5，体现彩票「重号概率低」规律；未开出的号码按 balanced
            # 基础权重（1.0 + hot 加成 1.5 + miss>15 加成 1.0 + rising 加成 0.5）。
            # 空数据退化由上方 total==0 提前返回处理；data[0] 即最近一期，
            # 与 window 无关（window 只截取统计期数范围）。前后区独立统计。
            if n in data[0]["front"]:
                w = 0.5
            else:
                w = 1.0
                if n in hot_front:
                    w += 1.5
                miss = front_last_seen.get(n, total)
                if miss > 15:
                    w += 1.0
                if n in rising:
                    w += 0.5
        elif name == "span_filter":
            # 跨度过滤策略：压制「跨度偏离历史均值」的号码，实现跨度回归。
            # 前区（1-35，取5）：统计 window 期每期跨度 max(front)-min(front)
            # 的均值 μ_f，理论跨度中心 = 24。μ_f > 24（历史偏分散）→ 压制
            # 「极端号」（n≤10 或 n≥26）到 0.5，让跨度收敛；μ_f < 24（历史偏
            # 集中）→ 压制「中心号」（11≤n≤25）到 0.5，让跨度发散。其余号码
            # 按 balanced 基础权重（1.0 + hot 1.5 + miss>15 1.0 + rising 0.5）。
            # 边界：空数据走 total==0 提前返回；跨度样本 <2（如单期）无法判断
            # 偏离 → 退化 balanced 不压制；越界号码忽略不参与跨度统计；
            # window 只截取统计期数范围；前后区独立统计。
            _FRONT_SPAN_CENTER = 24.0  # 前区理论跨度中心（彩票经验值）
            _front_spans = []
            for d in data:
                _vals = [nn for nn in d["front"] if FRONT_MIN <= nn <= FRONT_MAX]
                if len(_vals) >= 2:  # 越界号/脏数据导致有效号码不足2个 → 跳过该期
                    _front_spans.append(max(_vals) - min(_vals))
            _suppress_front_extremes = False
            _suppress_front_center = False
            if len(_front_spans) >= 2:  # 单期（1 个跨度样本）无法判断偏离 → 不压制
                _mu_f = mean(_front_spans)
                if _mu_f > _FRONT_SPAN_CENTER:
                    _suppress_front_extremes = True
                elif _mu_f < _FRONT_SPAN_CENTER:
                    _suppress_front_center = True
            if _suppress_front_extremes and (n <= 10 or n >= 26):
                w = 0.5  # μ_f>24：压制极端号，跨度回归
            elif _suppress_front_center and 11 <= n <= 25:
                w = 0.5  # μ_f<24：压制中心号，跨度回归
            else:
                w = 1.0
                if n in hot_front:
                    w += 1.5
                miss = front_last_seen.get(n, total)
                if miss > 15:
                    w += 1.0
                if n in rising:
                    w += 0.5
        else:  # balanced
            w = 1.0
            if n in hot_front:
                w += 1.5
            miss = front_last_seen.get(n, total)
            if miss > 15:
                w += 1.0
            if n in rising:
                w += 0.5
        front_w[n] = w

    back_w = {}
    for n in range(BACK_MIN, BACK_MAX + 1):
        if name == "hot":
            w = back_freq.get(n, 0) + 1
        elif name == "cold":
            w = back_last_seen.get(n, total) + 1
        elif name == "statistical":
            # 统计分析策略：基于卡方检验和置信区间
            w = 1.0
            # 1. 卡方检验权重
            observed = back_freq.get(n, 0)
            expected = total * 2 / 12  # 期望频次
            chi2_contrib = (observed - expected) ** 2 / expected if expected > 0 else 0
            if chi2_contrib > 3.84:  # 95%显著性阈值
                w += 1.5  # 显著偏离
            elif chi2_contrib > 2.71:  # 90%显著性阈值
                w += 1.0  # 边缘显著
            
            # 2. 置信区间权重
            if total > 0:
                from confidence import wilson_ci
                ci_low, ci_high = wilson_ci(observed, total)
                p_hat = observed / total
                expected_freq = 2 / 12
                if p_hat > ci_high:  # 频率显著偏高
                    w += 1.0
                elif p_hat < ci_low:  # 频率显著偏低
                    w += 0.5  # 低频号码也给一定权重
            
            # 3. 遗漏值权重
            miss = back_last_seen.get(n, total)
            if miss > 15:  # 遗漏超过15期
                w += 0.8
            elif miss > 8:  # 遗漏超过8期
                w += 0.4
        elif name == "prime_filter":
            # 过滤质数策略：后区压低质数权重，提升非质数权重
            _back_primes = {2, 3, 5, 7, 11}
            if n in _back_primes:
                w = 0.05
            else:
                # 非质数：保持热度加权逻辑（与平衡策略一致）
                w = 1.0
                if n in [x for x, _ in Counter({k: back_freq.get(k, 0) for k in range(BACK_MIN, BACK_MAX + 1)}).most_common(4)]:
                    w += 1.5
        elif name == "tail_filter":
            # 尾数过滤策略：后区按号码个位数差异化权重
            _back_tail_freq = Counter(n % 10 for d in data for n in d["back"])
            _top2_tails = {t for t, _ in _back_tail_freq.most_common(2)}
            if n % 10 in _top2_tails:
                w = 0.05
            else:
                w = 1.0
                if n in [x for x, _ in Counter({k: back_freq.get(k, 0) for k in range(BACK_MIN, BACK_MAX + 1)}).most_common(4)]:
                    w += 1.5
        elif name == "odd_even_balance_filter":
            # 奇偶平衡过滤策略：压低过热的一类号码（奇数或偶数），前后区独立统计
            _back_odd_freq = sum(1 for d in data for nn in d["back"] if nn % 2 == 1)
            _back_even_freq = sum(1 for d in data for nn in d["back"] if nn % 2 == 0)
            if _back_odd_freq > _back_even_freq:
                suppress = (n % 2 == 1)   # 奇数过热，压低奇数
            elif _back_even_freq > _back_odd_freq:
                suppress = (n % 2 == 0)   # 偶数过热，压低偶数
            else:
                suppress = False          # tie，不压低任何一方
            if suppress:
                w = 0.05
            else:
                w = 1.0
                if n in [x for x, _ in Counter({k: back_freq.get(k, 0) for k in range(BACK_MIN, BACK_MAX + 1)}).most_common(4)]:
                    w += 1.5
        elif name == "sum_filter":
            # 和值过滤策略：基于和值偏离理论中心的 z-score 压制大号或小号
            _BACK_THEORY_CENTER = 13.0
            back_sums = [sum(d["back"]) for d in data]
            suppress_back_large = False
            suppress_back_small = False
            if len(back_sums) >= 2 and std(back_sums) > 0:
                _mean_sum = mean(back_sums)
                _std_sum = std(back_sums)
                _z = (_mean_sum - _BACK_THEORY_CENTER) / _std_sum
                if _z > 1.0:
                    suppress_back_large = True
                elif _z < -1.0:
                    suppress_back_small = True
            _back_hot = [x for x, _ in Counter({k: back_freq.get(k, 0) for k in range(BACK_MIN, BACK_MAX + 1)}).most_common(4)]
            w = 1.0
            if suppress_back_large and n >= 7:
                w *= 0.5
            elif suppress_back_small and n <= 6:
                w *= 0.5
            if w == 1.0:
                if n in _back_hot:
                    w += 1.5
        elif name == "zone_filter":
            # 区间段平衡过滤策略：后区 1-12 分 4 段（每段 3 号），段号=(n-1)//3
            # 段0={1..3}、段1={4..6}、段2={7..9}、段3={10..12}，与前区独立统计、对称设计。
            # 阈值与前区共用同一套（比值/绝对下限/z-score）：三者均为无量纲量
            # （相对比值 + 标准差归一化），前区 7 段 vs 后区 4 段的段数差异和
            # 单期出号率差异（5/7 vs 2/4）已被期望与 std 归一化吸收，无需分设阈值；
            # 段数少时 std 更不稳，但三重条件（比值+下限+z）在两侧都偏保守。
            _BACK_ZONE_NUM = 4     # 后区段数
            _BACK_ZONE_SIZE = 3    # 每段号码数
            # 共享阈值（与前区同一套，无量纲化设计，见前区注释）
            _ZONE_HOT_RATIO = 1.5
            _ZONE_MIN_GAP = 2.0
            _ZONE_MIN_Z = 1.0
            _back_zone_freq = [0] * _BACK_ZONE_NUM
            for d in data:
                for nn in d["back"]:
                    if BACK_MIN <= nn <= BACK_MAX:  # 越界号码是脏数据：跳过，不参与段统计
                        _back_zone_freq[(nn - 1) // _BACK_ZONE_SIZE] += 1
            _back_zone_exp = BACK_PICK * total / _BACK_ZONE_NUM  # 均匀期望 = 2*window/4 = window/2
            _back_zone_std = std(_back_zone_freq)
            _back_hot_zones = set()
            if total >= 2:  # 退化：window<2 → 不压制
                for _z_i, _f in enumerate(_back_zone_freq):
                    _gap = _f - _back_zone_exp
                    if _f >= _back_zone_exp * _ZONE_HOT_RATIO and _gap >= _ZONE_MIN_GAP:
                        if _back_zone_std <= 0 or _gap / _back_zone_std >= _ZONE_MIN_Z:
                            _back_hot_zones.add(_z_i)
            _back_hot = [x for x, _ in Counter({k: back_freq.get(k, 0) for k in range(BACK_MIN, BACK_MAX + 1)}).most_common(4)]
            if (n - 1) // _BACK_ZONE_SIZE in _back_hot_zones:
                w = 0.5  # 过热段：段内所有号码权重压到 0.5
            else:
                w = 1.0
                if n in _back_hot:
                    w += 1.5
        elif name == "repeat_filter":
            # 重号过滤策略：后区独立统计，压制「上期（最近一期 data[0]）已开出
            # 的号码」权重到 0.5；未开出的号码按 balanced 基础权重。
            if n in data[0]["back"]:
                w = 0.5
            else:
                w = 1.0
                if n in [x for x, _ in Counter({k: back_freq.get(k, 0) for k in range(BACK_MIN, BACK_MAX + 1)}).most_common(4)]:
                    w += 1.5
        elif name == "span_filter":
            # 跨度过滤策略（后区，与前区独立统计、对称设计）：统计 window 期
            # 每期后区跨度 max(back)-min(back) 的均值 μ_b，理论跨度中心 = 6。
            # μ_b > 6（历史偏分散）→ 压制「极端号」（n≤2 或 n≥11）到 0.5；
            # μ_b < 6（历史偏集中）→ 压制「中心号」（3≤n≤10）到 0.5。
            # 其余按 balanced（1.0 + hot 加成 1.5）。边界同前区：空数据走
            # total==0 提前返回；跨度样本 <2（如单期）→ 退化 balanced 不压制；
            # 越界号码忽略不参与统计；window 只截取统计期数范围。
            _BACK_SPAN_CENTER = 6.0  # 后区理论跨度中心（彩票经验值）
            _back_spans = []
            for d in data:
                _vals = [nn for nn in d["back"] if BACK_MIN <= nn <= BACK_MAX]
                if len(_vals) >= 2:  # 有效号码不足2个 → 跳过该期
                    _back_spans.append(max(_vals) - min(_vals))
            _suppress_back_extremes = False
            _suppress_back_center = False
            if len(_back_spans) >= 2:  # 单期无法判断偏离 → 不压制
                _mu_b = mean(_back_spans)
                if _mu_b > _BACK_SPAN_CENTER:
                    _suppress_back_extremes = True
                elif _mu_b < _BACK_SPAN_CENTER:
                    _suppress_back_center = True
            _back_hot = [x for x, _ in Counter({k: back_freq.get(k, 0) for k in range(BACK_MIN, BACK_MAX + 1)}).most_common(4)]
            if _suppress_back_extremes and (n <= 2 or n >= 11):
                w = 0.5  # μ_b>6：压制极端号，跨度回归
            elif _suppress_back_center and 3 <= n <= 10:
                w = 0.5  # μ_b<6：压制中心号，跨度回归
            else:
                w = 1.0
                if n in _back_hot:
                    w += 1.5
        else:
            w = 1.0
            if n in [x for x, _ in Counter({k: back_freq.get(k, 0) for k in range(BACK_MIN, BACK_MAX + 1)}).most_common(4)]:
                w += 1.5
        back_w[n] = w

    return front_w, back_w


def generate_candidate(front_w, back_w, max_retries=50):
    """生成单个候选组合"""
    for _ in range(max_retries):
        front = weighted_sample(front_w, FRONT_PICK)
        back = weighted_sample(back_w, BACK_PICK)

        # 验证合理性
        front_sum = sum(front)
        if front_sum < 50 or front_sum > 140:
            continue
        odd_count = sum(1 for n in front if n % 2 == 1)
        if odd_count < 1 or odd_count > 4:
            continue
        # 区间覆盖
        zones = set()
        for n in front:
            if n <= 12:
                zones.add(0)
            elif n <= 24:
                zones.add(1)
            else:
                zones.add(2)
        if len(zones) < 2:
            continue
        return front, back

    # 退回纯随机
    front = sorted(random.sample(range(FRONT_MIN, FRONT_MAX + 1), FRONT_PICK))
    back = sorted(random.sample(range(BACK_MIN, BACK_MAX + 1), BACK_PICK))
    return front, back


def generate_pool(draws, strategy="balanced", count=None):
    """
    生成候选组合池

    Returns:
        list[tuple]: [(front, back), ...]
    """
    if count is None:
        count = POOL_SIZE
    front_w, back_w = compute_weights(draws, strategy)
    pool = set()
    for _ in range(count * 3):  # 多生成一些去重
        front, back = generate_candidate(front_w, back_w)
        key = combination_key(front, back)
        pool.add(key)
        if len(pool) >= count:
            break
    return [(list(k[0]), list(k[1])) for k in pool]


def _build_freq(data):
    """一次构建号码频次与末次出现（供 rank_candidates 复用，避免每个候选重复扫描）。

    返回 (front_freq, back_freq, front_last, back_last)。front_last[n] 为号码 n
    最近一次出现的索引（data 升序，索引小 = 更早；absent 用 total 兜底）。
    """
    front_freq = Counter()
    back_freq = Counter()
    front_last = {}
    back_last = {}
    total = len(data)
    for i, d in enumerate(data):
        for n in d["front"]:
            front_freq[n] += 1
            front_last[n] = i
        for n in d["back"]:
            back_freq[n] += 1
            back_last[n] = i
    return front_freq, back_freq, front_last, back_last, total


def score_candidate(front, back, draws, window=None, freq=None):
    """
    多维度评分

    Args:
        freq: 可选预计算 (front_freq, back_freq, front_last, back_last, total)，
              由 rank_candidates 一次构建传入，避免每个候选重复 O(期数) 扫描。

    Returns:
        dict: 各维度分数及总分
    """
    if freq is not None:
        front_freq, back_freq, front_last, back_last, total = freq
        data = draws[:window] if window else draws  # 仅用于 total/len 一致性
    else:
        data = draws[:window] if window else draws
        total = len(data)
        if total == 0:
            return {"total": 0}
        front_freq, back_freq, front_last, back_last, total = _build_freq(data)

    if total == 0:
        return {"total": 0}

    scores = {}

    # 1. 频率得分（号码在历史中出现的频率，适度偏高更好）
    front_freq_score = sum(front_freq.get(n, 0) for n in front) / (total * 5)
    back_freq_score = sum(back_freq.get(n, 0) for n in back) / (total * 2)
    scores["frequency"] = round((front_freq_score + back_freq_score) / 2, 4)

    # 2. 遗漏值得分（遗漏适中的号码）
    #    freq 已预计算时 front_last/back_last 已就绪；否则现场构建（一次性）
    if freq is None:
        front_last = {}
        back_last = {}
        for i, d in enumerate(draws[:window] if window else draws):
            for n in d["front"]:
                if n not in front_last:
                    front_last[n] = i
            for n in d["back"]:
                if n not in back_last:
                    back_last[n] = i
    front_miss = [front_last.get(n, total) for n in front]
    back_miss = [back_last.get(n, total) for n in back]
    avg_front_miss = sum(front_miss) / len(front_miss) if front_miss else 0
    avg_back_miss = sum(back_miss) / len(back_miss) if back_miss else 0
    # 遗漏10-30期为佳
    scores["omission"] = round(
        max(0, 1.0 - abs(avg_front_miss - 20) / 30) * 0.5 +
        max(0, 1.0 - abs(avg_back_miss - 10) / 15) * 0.5, 4)

    # 3. 和值得分（70-130为佳）
    front_sum = sum(front)
    if 70 <= front_sum <= 130:
        scores["sum"] = 1.0
    elif 50 <= front_sum < 70 or 130 < front_sum <= 140:
        scores["sum"] = 0.5
    else:
        scores["sum"] = 0.1
    scores["sum"] = round(scores["sum"], 4)

    # 4. 奇偶得分（2:3 或 3:2 为佳）
    odd = sum(1 for n in front if n % 2 == 1)
    if odd in (2, 3):
        scores["odd_even"] = 1.0
    elif odd in (1, 4):
        scores["odd_even"] = 0.5
    else:
        scores["odd_even"] = 0.1
    scores["odd_even"] = round(scores["odd_even"], 4)

    # 5. 区间分布得分
    zones = [0, 0, 0]
    for n in front:
        if n <= 12:
            zones[0] += 1
        elif n <= 24:
            zones[1] += 1
        else:
            zones[2] += 1
    if all(z >= 1 for z in zones):
        scores["zone"] = 1.0
    elif sum(1 for z in zones if z >= 1) >= 2:
        scores["zone"] = 0.6
    else:
        scores["zone"] = 0.2
    scores["zone"] = round(scores["zone"], 4)

    # 6. 奖级概率得分已移除：大乐透为独立随机开奖，无可靠概率预测，
    #    避免“伪评分”误导。权重在下方 5 项归一化为 100%。

    # 加权总分（5 项归一化）
    weights = {
        "frequency": 0.278,
        "omission": 0.222,
        "sum": 0.167,
        "odd_even": 0.167,
        "zone": 0.167,
    }
    total_score = sum(scores[k] * weights[k] for k in weights)
    scores["total"] = round(total_score, 4)
    scores["components"] = {k: v for k, v in scores.items() if k != "total"}

    return scores


def rank_candidates(pool, draws, window=None):
    """
    对候选池评分并排序（预计算频次，避免每个候选重复 O(期数) 扫描）

    Returns:
        list[tuple]: [(front, back, score), ...] 按总分降序
    """
    data = draws[:window] if window else draws
    if not data:
        return []
    freq = _build_freq(data)  # 一次构建，全部候选复用
    scored = []
    for front, back in pool:
        scores = score_candidate(front, back, draws, window, freq=freq)
        scored.append((front, back, scores["total"]))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored


def _mask(front):
    """把 5 个前区号码编码成整数位掩码（1..35 映射到位 0..34）。

    O(n) 过滤用：两组合前区重叠数 = popcount(mask_a & mask_b)，
    避免每次重建 set + 交集（原 O(n^2) set 计算是性能瓶颈，88% 耗时）。
    """
    m = 0
    for n in front:
        m |= 1 << (int(n) - 1)
    return m


def _popcount(x):
    return x.bit_count()  # Python 3.10+ 内置 C 级人口计数，比 bin().count() 快两个数量级


def filter_overlap(ranked, max_overlap=None):
    """
    过滤过度重叠的组合（前区重叠过高的候选舍去，保证候选多样性）。

    Args:
        ranked: [(front, back, score), ...]
        max_overlap: 前区最大重叠号码数

    Returns:
        list: 过滤后的排序组合
    """
    if max_overlap is None:
        max_overlap = MAX_FRONT_OVERLAP

    filtered = []
    filtered_masks = []
    for front, back, score in ranked:
        m = _mask(front)
        ok = True
        # 位掩码 O(1) 判重：与已选组合按位与后，数出重叠号码数
        for fm in filtered_masks:
            if _popcount(m & fm) > max_overlap:
                ok = False
                break
        if ok:
            filtered.append((front, back, score))
            filtered_masks.append(m)
    return filtered


def generate_top_candidates(draws, strategy="balanced", top_n=10, pool_size=None):
    """
    完整流程：生成候选池 → 评分 → 过滤 → 取Top N

    Returns:
        list[dict]: [{"front": [...], "back": [...], "score": float, "rank": int}, ...]
    """
    if pool_size is None:
        pool_size = max(POOL_SIZE, top_n * 100)

    pool = generate_pool(draws, strategy, pool_size)
    ranked = rank_candidates(pool, draws)
    filtered = filter_overlap(ranked)
    top = filtered[:top_n]

    return [
        {"front": f, "back": b, "score": s, "rank": i + 1}
        for i, (f, b, s) in enumerate(top)
    ]


if __name__ == "__main__":
    import argparse
    from fetch_history import fetch_history

    parser = argparse.ArgumentParser(description="候选生成与评分")
    parser.add_argument("--count", type=int, default=10, help="候选数量")
    parser.add_argument("--strategy", default="balanced", help="策略：单个名称或用 + 组合多个（如 hot+tail_filter），未知策略名自动跳过")
    parser.add_argument("--pool-size", type=int, default=10000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    draws = fetch_history()
    if not draws:
        print("无历史数据")
        exit(1)

    results = generate_top_candidates(draws, args.strategy, args.count, args.pool_size)
    if args.json:
        import json
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for r in results:
            front_str = " ".join(f"{n:02d}" for n in r["front"])
            back_str = " ".join(f"{n:02d}" for n in r["back"])
            print(f"#{r['rank']:2d} [{r['score']:.4f}] {front_str} + {back_str}")
