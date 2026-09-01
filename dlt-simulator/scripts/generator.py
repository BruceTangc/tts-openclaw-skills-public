#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generator.py — 候选生成+评分模块

生成候选组合池，对每组进行多维度评分
"""
import random
import math
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
# 遗漏目标参数（可配置，默认值保持 20/10，与 3519810 行为一致）
FRONT_OMISSION_TARGET = cfg.get("front_omission_target", 20)
BACK_OMISSION_TARGET = cfg.get("back_omission_target", 10)
# balanced 弱修正参数默认值（可从 config / strategy params 覆盖）
BALANCED_HOT_ADJUST = cfg.get("balanced_hot_adjust", 0.06)
BALANCED_COLD_ADJUST = cfg.get("balanced_cold_adjust", 0.08)
BALANCED_TREND_ADJUST = cfg.get("balanced_trend_adjust", 0.05)
BALANCED_OMISSION_ADJUST = cfg.get("balanced_omission_adjust", 0.10)
BALANCED_MAX_TOTAL_ADJUST = cfg.get("balanced_max_total_adjust", 0.20)
EXPOSURE_PENALTY_COEF = cfg.get("exposure_penalty_coef", 0.04)


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


def compute_weights(draws, strategy="balanced", window=None, params=None):
    """
    根据策略计算号码权重。

    设计原则（Balanced 重构）：
      - hot/cold/trend 独立策略保留明显倾向（强权重重构，不再写死 1.5/1.0/0.5）。
      - balanced = 均匀随机基线(base=1.0) + 弱统计修正，最大单项调整受
        ±0.05~±0.20 限制；只有统计证据可信时才弱修正：
          热号奖励 = 全局卡方显著 且 单号偏差超 Wilson CI(abnormal_high)
          冷号奖励 = 单号偏差超 Wilson CI(abnormal_low)
          趋势/遗漏 = 很弱 heuristic（不声称概率）

    Args:
        draws: 按期号降序的开奖数据
        strategy: balanced | hot | cold | trend
        window: 分析窗口（None=全部）
        params: 生成器参数（由 strategy_manager.get_generator_params() 提供；
                None 时回退到 config 默认值）

    Returns:
        (front_weights, back_weights)
    """
    params = params or {}
    data = draws[:window] if window else draws
    total = len(data)
    if total == 0:
        front_w = {n: 1.0 for n in range(FRONT_MIN, FRONT_MAX + 1)}
        back_w = {n: 1.0 for n in range(BACK_MIN, BACK_MAX + 1)}
        return front_w, back_w

    # ---- 策略参数（闭环：从 strategy params / config 取值，不写死）----
    hot_weight = float(params.get("hot_weight", 1.5))
    cold_weight = float(params.get("cold_weight", 1.0))
    trend_weight = float(params.get("trend_weight", 0.5))
    b_hot = float(params.get("balanced_hot_adjust", BALANCED_HOT_ADJUST))
    b_cold = float(params.get("balanced_cold_adjust", BALANCED_COLD_ADJUST))
    b_trend = float(params.get("balanced_trend_adjust", BALANCED_TREND_ADJUST))
    b_omit = float(params.get("balanced_omission_adjust", BALANCED_OMISSION_ADJUST))
    max_total_adjust = float(params.get("balanced_max_total_adjust", BALANCED_MAX_TOTAL_ADJUST))

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

    # 趋势分析（前区+后区）
    recent_n = min(20, total)
    recent = data[:recent_n]
    older = data[recent_n:]
    recent_freq = Counter()
    older_freq = Counter()
    recent_back_freq = Counter()
    older_back_freq = Counter()
    for d in recent:
        for n in d["front"]:
            recent_freq[n] += 1
        for n in d["back"]:
            recent_back_freq[n] += 1
    for d in older:
        for n in d["front"]:
            older_freq[n] += 1
        for n in d["back"]:
            older_back_freq[n] += 1

    rising = set()
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        r = recent_freq.get(n, 0) / max(1, recent_n)
        o = older_freq.get(n, 0) / max(1, len(older))
        if r > o * 1.3 and r > 0.02:
            rising.add(n)
    rising_back = set()
    for n in range(BACK_MIN, BACK_MAX + 1):
        r = recent_back_freq.get(n, 0) / max(1, recent_n)
        o = older_back_freq.get(n, 0) / max(1, len(older))
        if r > o * 1.3 and r > 0.02:
            rising_back.add(n)

    # 统计证据（仅 balanced 弱修正用；卡方/Wilson 只描述分布偏置，不声称某号概率更高）
    front_ci = None
    back_ci = None
    front_chi = None
    back_chi = None
    if strategy == "balanced" and total >= 20:
        try:
            from chi_square import front_chi_square, back_chi_square
            from confidence import frequency_ci
            front_chi = front_chi_square(data)
            back_chi = back_chi_square(data)
            ci = frequency_ci(data)
            front_ci = ci.get("front", {})
            back_ci = ci.get("back", {})
        except Exception:
            front_chi = back_chi = None
            front_ci = back_ci = None

    def _clamp_adjust(adj):
        return max(-max_total_adjust, min(max_total_adjust, adj))

    # 构建权重
    front_w = {}
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if strategy == "hot":
            w = 1.0 + hot_weight * front_freq.get(n, 0)
        elif strategy == "cold":
            w = 1.0 + cold_weight * front_last_seen.get(n, total)
        elif strategy == "trend":
            w = (1.0 + trend_weight * 3.0) if n in rising else 1.0
        else:  # balanced：均匀基线 + 弱统计修正
            adj = 0.0
            info = front_ci.get(n) if front_ci else None
            # 热号奖励：全局卡方显著 且 单号偏差超 CI(abnormal_high)
            if front_chi and front_chi.get("is_reject") and info \
                    and info.get("abnormal_direction") == "high":
                adj += b_hot
            # 冷号奖励：单号偏差超 CI(abnormal_low)
            if info and info.get("abnormal_direction") == "low":
                adj += b_cold
            # 趋势：很弱 heuristic
            if n in rising:
                adj += b_trend
            # 遗漏：很弱 heuristic
            miss = front_last_seen.get(n, total)
            if miss > FRONT_OMISSION_TARGET:
                adj += b_omit
            w = 1.0 + _clamp_adjust(adj)
        front_w[n] = max(0.01, w)

    back_w = {}
    for n in range(BACK_MIN, BACK_MAX + 1):
        if strategy == "hot":
            w = 1.0 + hot_weight * back_freq.get(n, 0)
        elif strategy == "cold":
            w = 1.0 + cold_weight * back_last_seen.get(n, total)
        elif strategy == "trend":
            w = (1.0 + trend_weight * 3.0) if n in rising_back else 1.0
        else:  # balanced
            adj = 0.0
            info = back_ci.get(n) if back_ci else None
            if back_chi and back_chi.get("is_reject") and info \
                    and info.get("abnormal_direction") == "high":
                adj += b_hot
            if info and info.get("abnormal_direction") == "low":
                adj += b_cold
            if n in rising_back:
                adj += b_trend
            miss = back_last_seen.get(n, total)
            if miss > BACK_OMISSION_TARGET:
                adj += b_omit
            w = 1.0 + _clamp_adjust(adj)
        back_w[n] = max(0.01, w)

    return front_w, back_w


def generate_candidate(front_w, back_w, max_retries=50):
    """生成单个候选组合。

    仅保证合法范围/无重复（由 weighted_sample 保证 5 个不同前区 + 2 个不同后区）。
    和值/奇偶/三区的硬过滤已移除 —— 不再 reject 极端和值或高低聚集，改为
    score_candidate 层的连续/分级 soft 评分（符合“全部允许生成、不硬杀号”原则）。
    """
    front = weighted_sample(front_w, FRONT_PICK)
    back = weighted_sample(back_w, BACK_PICK)
    return front, back


def generate_pool(draws, strategy="balanced", count=None, params=None):
    """
    生成候选组合池

    Returns:
        list[tuple]: [(front, back), ...]
    """
    if count is None:
        count = POOL_SIZE
    front_w, back_w = compute_weights(draws, strategy, params=params)
    pool = set()
    for _ in range(count * 3):  # 多生成一些去重
        front, back = generate_candidate(front_w, back_w)
        key = combination_key(front, back)
        pool.add(key)
        if len(pool) >= count:
            break
    return [(list(k[0]), list(k[1])) for k in pool]


def _build_freq(data):
    """一次构建号码频次与最近一次出现位置（供 rank_candidates 复用）。

    返回 (front_freq, back_freq, front_last, back_last, total)。
    *front_last[n] 为号码 n 最近一次出现的位置*（data 降序：位置 0 = 最新一期，
    1 = 距今 1 期，…），即为 omission 值（距上次出现的期数）。
    / 注意与 statistics.omission_analysis 保持同一语义：
      仅记录“最近/首次遇到”的位置，不得被后续更老的出现覆盖。
    """
    front_freq = Counter()
    back_freq = Counter()
    front_last = {}
    back_last = {}
    total = len(data)
    for i, d in enumerate(data):
        for n in d["front"]:
            front_freq[n] += 1
            # 只记录最近一次（首次遇到=位置最小=最新），不覆盖成更老位置
            if n not in front_last:
                front_last[n] = i
        for n in d["back"]:
            back_freq[n] += 1
            if n not in back_last:
                back_last[n] = i
    return front_freq, back_freq, front_last, back_last, total


def _theoretical_sum_stats():
    """前区和值的理论分布均值/标准差（1..35 无放回取 5 个）。

    单号均值 18，和值均值 5*18=90；有限总体无放回修正：
      Var(sum) = pick * pop_var * (N - pick) / (N - 1)
    其中 pop_var = (N^2 - 1) / 12（离散均匀 1..N）。
    """
    n_pop = FRONT_MAX - FRONT_MIN + 1
    pop_var = (n_pop * n_pop - 1) / 12.0
    mean_sum = FRONT_PICK * (FRONT_MIN + FRONT_MAX) / 2.0
    var_sum = FRONT_PICK * pop_var * (n_pop - FRONT_PICK) / (n_pop - 1)
    return mean_sum, math.sqrt(var_sum)


def _sum_score(front_sum, data):
    """和值 z-score 连续评分：随偏离历史 mean/std 平滑下降，不禁止极端和值。

    历史样本充足(>=20)用历史 mean_sum/std_sum；否则用理论分布 fallback。
    评分 = exp(-0.5 * z^2)，位于 (0, 1]，均值处=1.0，不硬杀号。
    """
    if len(data) >= 20:
        sums = [sum(d["front"]) for d in data]
        mean_sum = mean(sums)
        std_sum = std(sums)
    else:
        mean_sum, std_sum = _theoretical_sum_stats()
    if std_sum <= 0:
        return 1.0
    z = (front_sum - mean_sum) / std_sum
    return math.exp(-0.5 * z * z)


def _hypergeom_pmf(k, pick, k_high, n_pop):
    """超几何概率 P(X=k)：从 n_pop 中无放回取 pick 个，命中 k 个“高区”。"""
    if k < 0 or k > pick or k > k_high or (pick - k) > (n_pop - k_high):
        return 0.0
    return math.comb(k_high, k) * math.comb(n_pop - k_high, pick - k) / math.comb(n_pop, pick)


def _high_low_score(front, back):
    """前区高区(18-35)/后区高区(7-12) 连续分布评分。

    基于理论超几何分布中该 high/low 划分的常见度（除以最大概率归一化到 (0,1]）。
    2:3/3:2 接近 1.0，1:4/4:1 次之，0:5/5:0 更低但非 0 —— 全部允许生成，不硬限。
    """
    front_high = sum(1 for n in front if n >= 18)
    front_k_high = FRONT_MAX - 18 + 1  # 18..35 = 18 个高区
    front_probs = [_hypergeom_pmf(x, FRONT_PICK, front_k_high, FRONT_MAX - FRONT_MIN + 1)
                   for x in range(FRONT_PICK + 1)]
    front_score = _hypergeom_pmf(front_high, FRONT_PICK, front_k_high, FRONT_MAX - FRONT_MIN + 1) / max(front_probs)

    back_high = sum(1 for n in back if n >= 7)
    back_k_high = BACK_MAX - 7 + 1  # 7..12 = 6 个高区
    back_probs = [_hypergeom_pmf(x, BACK_PICK, back_k_high, BACK_MAX - BACK_MIN + 1)
                  for x in range(BACK_PICK + 1)]
    back_score = _hypergeom_pmf(back_high, BACK_PICK, back_k_high, BACK_MAX - BACK_MIN + 1) / max(back_probs)

    return (front_score + back_score) / 2.0


_LEGACY_WEIGHTS = {
    "frequency": 0.25,
    "omission": 0.20,
    "sum": 0.15,
    "odd_even": 0.15,
    "zone": 0.10,
    "high_low": 0.15,
}
# Balanced 独立评分路径：结构分维度（非历史，只描述组合本身形态）
_STRUCTURAL_DIMS = ("sum", "odd_even", "zone", "high_low")
# 历史统计修正维度（balanced 下只作弱 correction，受上限约束）
_STATISTICAL_DIMS = ("frequency", "omission")
# Balanced 排名层：历史统计 correction 对最终分的最大贡献比例（10%~15%）
# 取 0.15：即便 frequency+omission 全部打满，也不会超过结构分的主导地位，
# 避免历史噪声经 ranking 层回流造成高位塌缩。
BALANCED_STAT_CAP = cfg.get("balanced_stat_cap", 0.15)


def _score_dimensions(front, back, draws, window=None, freq=None, params=None):
    """计算各维度原始分（不合并）。

    Returns:
        (scores, data): scores 为各维度分数 dict，data 为用于总分长度一致性的一次样本窗口。
    """
    params = params or {}
    omission_bonus = float(params.get("omission_bonus", 1.0))

    if freq is not None:
        front_freq, back_freq, front_last, back_last, total = freq
        data = draws[:window] if window else draws
    else:
        data = draws[:window] if window else draws
        total = len(data)
        if total == 0:
            return {k: 0.0 for k in _STRUCTURAL_DIMS + _STATISTICAL_DIMS}, data
        front_freq, back_freq, front_last, back_last, total = _build_freq(data)

    if total == 0:
        return {k: 0.0 for k in _STRUCTURAL_DIMS + _STATISTICAL_DIMS}, data

    scores = {}
    # 1. 频率（历史）
    front_freq_score = sum(front_freq.get(n, 0) for n in front) / (total * 5)
    back_freq_score = sum(back_freq.get(n, 0) for n in back) / (total * 2)
    scores["frequency"] = round((front_freq_score + back_freq_score) / 2, 4)
    # 2. 遗漏（历史）
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
    scores["omission"] = round(omission_bonus * (
        max(0, 1.0 - abs(avg_front_miss - FRONT_OMISSION_TARGET) / (FRONT_OMISSION_TARGET + 10)) * 0.5 +
        max(0, 1.0 - abs(avg_back_miss - BACK_OMISSION_TARGET) / (BACK_OMISSION_TARGET + 5)) * 0.5), 4)
    # 3. 和值（结构）
    scores["sum"] = round(_sum_score(sum(front), data), 4)
    # 4. 奇偶（结构）
    odd = sum(1 for n in front if n % 2 == 1)
    if odd in (2, 3):
        scores["odd_even"] = 1.0
    elif odd in (1, 4):
        scores["odd_even"] = 0.5
    else:
        scores["odd_even"] = 0.1
    scores["odd_even"] = round(scores["odd_even"], 4)
    # 5. 区间分布（结构）
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
    # 6. high/low（结构）
    scores["high_low"] = round(_high_low_score(front, back), 4)
    return scores, data


def _combine_legacy(scores):
    """hot/cold/trend：沿用原加权（历史维度可占主导）。"""
    return round(sum(scores[k] * _LEGACY_WEIGHTS[k] for k in _LEGACY_WEIGHTS), 4)


def _combine_balanced(scores, cap=None):
    """balanced：结构分为主 + 统计修正为辅（历史贡献封顶）。

    结构分各维均分 1.0 权重（4 项结构维取均值，范围 [0,1]）；
    统计修正分（frequency/omission 均值，范围 [0,1]）乘以封顶比例作为增量。
    """
    if cap is None:
        cap = BALANCED_STAT_CAP
    struct = sum(scores[k] for k in _STRUCTURAL_DIMS) / len(_STRUCTURAL_DIMS)
    stats = sum(scores[k] for k in _STATISTICAL_DIMS) / len(_STATISTICAL_DIMS)
    # 统计修正最多贡献 cap * 结构分；未获统计证据支持的历史频率无法形成强排名优势
    correction = min(stats, cap * struct) if struct > 0 else 0.0
    return round(struct + correction, 4)


def score_candidate(front, back, draws, window=None, freq=None, params=None):
    """
    多维度评分（legacy 入口，hot/cold/trend 沿用原加权；balanced 请走 rank_candidates）。

    保持既有返回契约：包含 frequency/omission/sum/odd_even/zone/high_low/total/components。
    """
    scores, _ = _score_dimensions(front, back, draws, window, freq, params)
    scores["total"] = _combine_legacy(scores)
    scores["components"] = {k: v for k, v in scores.items() if k != "total"}
    return scores


def rank_candidates(pool, draws, window=None, params=None, strategy="balanced"):
    """
    对候选池评分并排序（预计算频次，避免每个候选重复 O(期数) 扫描）

    balanced 走独立评分路径：结构分为主 + 统计修正为辅（历史贡献封顶）；
    hot/cold/trend 沿用原加权（历史维度可占主导）。

    Returns:
        list[tuple]: [(front, back, score), ...] 按总分降序
    """
    data = draws[:window] if window else draws
    if not data:
        return []
    freq = _build_freq(data)  # 一次构建，全部候选复用
    scored = []
    for front, back in pool:
        scores, _ = _score_dimensions(front, back, draws, window, freq=freq, params=params)
        if strategy == "balanced":
            total = _combine_balanced(scores, cap=(params or {}).get("balanced_stat_cap"))
        else:
            total = _combine_legacy(scores)
        scored.append((front, back, total))
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


def calibrate_portfolio(ranked, top_n, penalty_coef=None):
    """Top10 Portfolio Exposure 校准（仅 balanced 用）。

    对排名后的候选做贪婪选取，当一个号码已在已选组合中出现过时，对含该号码的
    候选施加 soft 曝光惩罚（惩罚随曝光次数连续增强：penalty = coef * 已出现次数），
    防止某些号码过度占据候选池。不硬限单号出现次数，不 reject，只降排序优先级。

    关键修正：曝光惩罚会改变“最终排序”的评分（score - penalty），因此必须把
    原始质量分(raw_score)与校准后的排序分(adjusted_score)分开暴露，避免旧实现里
    “按 adjusted 排序但返回 raw score”导致 score 不再单调、破坏 Top2 排序不变量。

    Args:
        ranked: [(front, back, score), ...] 按总分降序
        top_n: 选取数量
        penalty_coef: 曝光惩罚系数（None 用 config 默认）

    Returns:
        list[tuple]: 校准后的 top_n 组合，元素为
            (front, back, raw_score, adjusted_score, exposure_penalty)
    """
    if penalty_coef is None:
        penalty_coef = EXPOSURE_PENALTY_COEF
    penalty_coef = float(penalty_coef)
    # 仅当“候选数多于需求”时，贪婪选择才有意义；但即便 len(ranked) <= top_n，
    # 若 len(ranked) > 1 仍应跑一遍软惩罚重排序（修复收口#2：最终 Top10 即便恰好凑满，
    # 也要对重叠号码施加曝光降权，避免重复号霸占 BUY/WATCH 高位，而非直接 append）。
    if penalty_coef <= 0:
        return [(f, b, s, s, 0.0) for f, b, s in ranked[:top_n]]

    remaining = list(ranked)
    selected = []
    front_counts = Counter()
    back_counts = Counter()
    while len(selected) < top_n and remaining:
        best_idx = -1
        best_adj = float("-inf")
        best_pen = 0.0
        for i, (front, back, score) in enumerate(remaining):
            pen = 0.0
            for n in front:
                c = front_counts.get(n, 0)
                if c >= 1:
                    pen += penalty_coef * c
            for n in back:
                c = back_counts.get(n, 0)
                if c >= 1:
                    pen += penalty_coef * c
            adj = score - pen
            if adj > best_adj:
                best_adj = adj
                best_idx = i
                best_pen = pen
        front, back, score = remaining.pop(best_idx)
        selected.append((front, back, score, round(score - best_pen, 4), round(best_pen, 4)))
        for n in front:
            front_counts[n] += 1
        for n in back:
            back_counts[n] += 1
    return selected


def finalize_portfolio(candidates, prediction_count, backend_calibrate=True, penalty_coef=None):
    """对“最终实际输出”候选集合做一次收尾 portfolio exposure 校准。

    背景（收口修复#2）：原先流程在历史过滤+补充生成+去重之后，直接用 append 顺序
    分割 BUY/WATCH，最终 Top10 没有再作为一个完整组合集做一次曝光检查；若补充候选
    里某个号码高度重复，那些组会被原样 append 进最终集，破坏曝光均匀性。

    本函数在**所有步骤之后**（生成→diversify→历史过滤→不足补充→去重）对最终候选集：
      - soft penalty 重排序（不硬限单号出现次数，不 reject，不重引入历史完整过滤）
      - 只调排序，保证最终仍返回 prediction_count 组
      - 重算 adjusted_score / exposure_penalty，并重编号 rank（与 adjusted_score 排序一致）

    Args:
        candidates: list[dict]，每个含 front/back/score（原始质量分）；
                    可选已有 adjusted_score/exposure_penalty
        prediction_count: 最终目标组数
        backend_calibrate: 是否对最终集执行曝光校准（balanced 传 True）
        penalty_coef: 曝光惩罚系数（None 用 config 默认）

    Returns:
        list[dict]: 重校准并按 adjusted_score 降序、rank 重编号后的最终候选集
    """
    out = []
    # 1. 按原始质量分降序作为入校准的初始顺序
    scored = [(c["front"], c["back"], float(c.get("score", c.get("adjusted_score", 0.0))))
              for c in candidates]
    if backend_calibrate:
        calibrated = calibrate_portfolio(scored, prediction_count, penalty_coef=penalty_coef)
    else:
        calibrated = [(f, b, s, s, 0.0) for (f, b, s) in scored[:prediction_count]]
    # 2. 校准结果与原始候选信息合并（按 front/back 匹配，保留原始元数据）
    by_key = {(tuple(c["front"]), tuple(c["back"])): c for c in candidates}
    for front, back, raw, adj, pen in calibrated:
        info = by_key.get((tuple(front), tuple(back)), {})
        out.append({
            "front": front,
            "back": back,
            "score": round(raw, 4),
            "adjusted_score": round(adj, 4),
            "exposure_penalty": round(pen, 4),
            **({k: v for k, v in info.items()
                if k not in ("front", "back", "score", "adjusted_score", "exposure_penalty", "rank")}),
        })
    # 3. 按 adjusted_score 降序重排并重编号 rank
    out.sort(key=lambda x: x["adjusted_score"], reverse=True)
    for i, c in enumerate(out):
        c["rank"] = i + 1
    return out[:prediction_count]


def generate_top_candidates(draws, strategy="balanced", top_n=10, pool_size=None, params=None):
    """
    完整流程：生成候选池 → 评分 → 过滤 → (balanced)曝光校准 → 取Top N

    Args:
        params: 生成器参数（由 strategy_manager.get_generator_params() 提供）

    Returns:
        list[dict]: [{"front": [...], "back": [...], "score": float, "rank": int}, ...]
    """
    if pool_size is None:
        pool_size = max(POOL_SIZE, top_n * 100)

    pool = generate_pool(draws, strategy, pool_size, params=params)
    ranked = rank_candidates(pool, draws, params=params, strategy=strategy)
    filtered = filter_overlap(ranked)
    if strategy == "balanced":
        # 曝光校准：返回 (front, back, raw_score, adjusted_score, penalty)
        filtered = calibrate_portfolio(filtered, top_n,
                                       penalty_coef=(params or {}).get("exposure_penalty_coef"))
    else:
        # 非 balanced 无曝光惩罚：adjusted_score == raw_score, penalty == 0
        filtered = [(f, b, s, s, 0.0) for (f, b, s) in filtered]
    top = filtered[:top_n]

    return [
        {
            "front": f,
            "back": b,
            "score": raw,
            "adjusted_score": adj,
            "exposure_penalty": pen,
            "rank": i + 1,
        }
        for i, (f, b, raw, adj, pen) in enumerate(top)
    ]


if __name__ == "__main__":
    import argparse
    from fetch_history import fetch_history

    parser = argparse.ArgumentParser(description="候选生成与评分")
    parser.add_argument("--count", type=int, default=10, help="候选数量")
    parser.add_argument("--strategy", default="balanced")
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
            print(f"#{r['rank']:2d} [raw {r['score']:.4f} / adj {r['adjusted_score']:.4f}] {front_str} + {back_str}")
