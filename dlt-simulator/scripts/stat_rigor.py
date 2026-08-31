#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stat_rigor.py — 统计严谨性增强模块（基于 3519810 设计基准新增，不改动选号核心）

本模块为现有策略体系【增加】统计验证能力，明确区分三个概念：

1. theoretical probability  — 大乐透理论概率（静态，不随时间变化）
2. historical frequency    — 历史实际观察频率（只能描述历史，不能称下一期概率）
3. heuristic score         — 现有选号评分（frequency/omission/sum/odd_even/zone）
                            ⚠️ 必须明确 heuristic score ≠ probability

核心新增：
- RANDOM_BASELINE：严格的大乐透均匀随机模型（不用历史、不用冷热、不用权重）
- 统一评价指标：平均前区/后区命中、前区≥3/≥4/5命中率、任意中奖概率、Top2/Top10
- Strategy vs Random：delta = strategy_metric - random_metric（描述样本表现差异）
"""
import random
import math
from collections import Counter

from common import mean, std


# ---------------------------------------------------------------------------
# 一、理论概率（theoretical probability）
# ---------------------------------------------------------------------------
def front_single_pick_prob(players=1, pool=35, pick=5):
    """前区单号被选中概率：本注 5 个位置都在，单号命中概率 = 5/35。

    说明：大乐透从 1..35 均匀无放回取 5 个，单个给定号码被抽中概率恒为 5/35=14.2857%。
    这是理论概率，与任何历史数据无关。
    """
    return pick / pool


def back_single_pick_prob(players=1, pool=12, pick=2):
    """后区单号被选中概率：2/12 = 16.6667%。"""
    return pick / pool


def full_combo_prob(front_pool=35, front_pick=5, back_pool=12, back_pick=2):
    """完整单注中一等奖理论概率：1 / C(35,5) × C(12,2) = 1 / 21,425,712。"""
    def nCr(n, r):
        if r > n:
            return 0
        return math.comb(n, r)
    total = nCr(front_pool, front_pick) * nCr(back_pool, back_pick)
    return 1.0 / total, total


def theoretical_prob_report(front_pool=35, front_pick=5, back_pool=12, back_pick=2):
    """返回理论概率说明文本/结构。

    大乐透理论上每个完整组合等概率；理论概率不随期数变化。
    """
    fp = front_single_pick_prob(pool=front_pool, pick=front_pick)
    bp = back_single_pick_prob(pool=back_pool, pick=back_pick)
    combo_p, combo_total = full_combo_prob(front_pool, front_pick, back_pool, back_pick)
    return {
        "front_single": round(fp * 100, 4),   # %
        "back_single": round(bp * 100, 4),    # %
        "full_combo_p": combo_p,
        "full_combo_total": combo_total,
        "note": "大乐透理论上每个完整组合等概率；此概率为静态理论值，不随历史数据变化，不代表任何号码更可能开出。",
    }


# ---------------------------------------------------------------------------
# 二、Random Baseline（严格均匀随机模型）
# ---------------------------------------------------------------------------
def random_front_back(seed=None, front_min=1, front_max=35, front_pick=5,
                      back_min=1, back_max=12, back_pick=2):
    """严格均匀随机生成一注大乐透组合。

    规则：
      - 前区从 [front_min, front_max] 均匀无放回取 front_pick 个
      - 后区从 [back_min, back_max] 均匀无放回取 back_pick 个
      - 不使用历史频率 / 冷热 / 趋势 / 遗漏 / 任何 heuristic weight
      - 不使用和值 / 奇偶 / 三区过滤
      - 种子可选（可复现，默认 None=系统随机）

    这就是真正的大乐透均匀随机模型。现有 Balanced 不是 Random Baseline。
    """
    rng = random.Random(seed)
    front = sorted(rng.sample(range(front_min, front_max + 1), front_pick))
    back = sorted(rng.sample(range(back_min, back_max + 1), back_pick))
    return front, back


def random_baseline_pool(count=10, seed=None):
    """生成 count 组严格随机组合（不评分、不过滤）。

    Returns:
        list[dict]: [{"front": [...], "back": [...]}, ...]
    """
    rng = random.Random(seed)
    pool = []
    seen = set()
    while len(pool) < count:
        front = sorted(rng.sample(range(1, 36), 5))
        back = sorted(rng.sample(range(1, 13), 2))
        key = (tuple(front), tuple(back))
        if key in seen:
            continue
        seen.add(key)
        pool.append({"front": front, "back": back})
    return pool


# ---------------------------------------------------------------------------
# 三、统一评价指标（所有策略共用同一评价函数）
# ---------------------------------------------------------------------------
def evaluate_candidates(candidates, draws):
    """对一组候选在历史开奖数据上的统一表现做评价。

    注意：draws 提供多期开奖（walk-forward 场景逐期调用，或最后一期评估）。

    Args:
        candidates: [{"front": [...], "back": [...], ...}, ...]
        draws: 开奖期列表 [{"front": [...], "back": [...]}, ...]

    Returns:
        dict: 见下方字段，所有策略同口径
    """
    # 若 draws 为多期，逐期累计命中数后求平均
    n_periods = len(draws)
    if n_periods == 0:
        return _empty_metrics()

    # 简单聚合：把候选每期都比一遍，累计平均
    total_front_hits = 0.0
    total_back_hits = 0.0
    front_ge3 = 0
    front_ge4 = 0
    front_5 = 0
    any_win = 0

    # 对每个候选、每期统计
    candidate_front_hits = []   # 每注平均前区命中
    candidate_back_hits = []
    candidate_fge3 = 0
    candidate_fge4 = 0
    candidate_f5 = 0
    candidate_any = 0

    for cand in candidates:
        cf = cand["front"]
        cb = cand["back"]
        # 统计每期命中，取最佳命中（同一注只需中一次即算中奖）
        best_fh = 0
        best_bh = 0
        fge3 = 0
        fge4 = 0
        f5 = 0
        anyt = 0
        for d in draws:
            fh = len(set(cf) & set(d["front"]))
            bh = len(set(cb) & set(d["back"]))
            best_fh = max(best_fh, fh)
            best_bh = max(best_bh, bh)
            if fh >= 3:
                fge3 += 1
            if fh >= 4:
                fge4 += 1
            if fh == 5:
                f5 += 1
            # 任意中奖：命中组合能构成任一奖级（至少 front>=3 或 back==2 且有前区配合）
            if _is_win(fh, bh):
                anyt += 1
        # 取该候选的整体表现（用最佳命中 + 命中率）
        candidate_front_hits.append(best_fh)
        candidate_back_hits.append(best_bh)
        candidate_fge3 += 1 if fge3 > 0 else 0
        candidate_fge4 += 1 if fge4 > 0 else 0
        candidate_f5 += 1 if f5 > 0 else 0
        candidate_any += 1 if anyt > 0 else 0

    n_cand = len(candidates)
    metrics = {
        "strategy": None,  # 调用处填充
        "count": n_cand,
        "mean_front_hits": round(sum(candidate_front_hits) / n_cand, 4) if n_cand else 0.0,
        "mean_back_hits": round(sum(candidate_back_hits) / n_cand, 4) if n_cand else 0.0,
        "front_ge3_hit_rate": round(candidate_fge3 / n_cand, 4) if n_cand else 0.0,
        "front_ge4_hit_rate": round(candidate_fge4 / n_cand, 4) if n_cand else 0.0,
        "front_5_hit_rate": round(candidate_f5 / n_cand, 4) if n_cand else 0.0,
        "any_win_rate": round(candidate_any / n_cand, 4) if n_cand else 0.0,
        "periods_evaluated": n_periods,
    }
    return metrics


def _is_win(fh, bh):
    """判断 (front_hit, back_hit) 是否构成任一奖级（覆盖 2026 新规 7 奖级）。"""
    # 逻辑：后区0命需要前区3+；后区1命需前区2+；后区2命需前区1+
    if bh == 2:
        return fh >= 1
    if bh == 1:
        return fh >= 2
    # bh == 0
    return fh >= 3


def _empty_metrics():
    return {
        "strategy": None,
        "count": 0,
        "mean_front_hits": 0.0,
        "mean_back_hits": 0.0,
        "front_ge3_hit_rate": 0.0,
        "front_ge4_hit_rate": 0.0,
        "front_5_hit_rate": 0.0,
        "any_win_rate": 0.0,
        "periods_evaluated": 0,
    }


# ---------------------------------------------------------------------------
# 四、Strategy vs Random 比较
# ---------------------------------------------------------------------------
def compare_to_random(strategy_metrics, random_metrics):
    """对每个策略指标计算相对随机基线的差异。

    delta = strategy_metric - random_metric

    输出必须明确：这是相对于随机基线的历史样本表现差异，不代表未来中奖概率提高。
    """
    keys = [
        "mean_front_hits",
        "mean_back_hits",
        "front_ge3_hit_rate",
        "front_ge4_hit_rate",
        "front_5_hit_rate",
        "any_win_rate",
    ]
    deltas = {}
    for k in keys:
        deltas[k] = round(
            (strategy_metrics.get(k, 0.0) or 0.0) - (random_metrics.get(k, 0.0) or 0.0),
            4,
        )
    return {
        "deltas": deltas,
        "disclaimer": "这是相对于随机基线的历史样本表现差异，不代表未来中奖概率提高。",
    }


# ---------------------------------------------------------------------------
# 六、分布诊断（distribution diagnostics）
# ---------------------------------------------------------------------------
def portfolio_distribution(candidates):
    """对一个候选组合集合做分布诊断。

    只描述“候选组合池”的号码曝光/结构特征（是否均匀、有无曝光塌缩、和值/高低比例），
    用于检验算法偏置 —— 绝不预测任何号码下一期的中奖概率。

    Args:
        candidates: [{"front": [...], "back": [...]}, ...]

    Returns:
        dict: 分布诊断指标
    """
    n = len(candidates)
    if n == 0:
        return {"n_candidates": 0}

    front_exposure = Counter()
    back_exposure = Counter()
    sums = []
    front_high = 0
    back_high = 0
    all_front = []
    for c in candidates:
        f = c["front"]
        b = c["back"]
        for x in f:
            front_exposure[x] += 1
            all_front.append(x)
            if x >= 18:
                front_high += 1
        for x in b:
            back_exposure[x] += 1
            if x >= 7:
                back_high += 1
        sums.append(sum(f))

    # 卡方均匀性检验（用于检验曝光是否均匀，非概率预测）
    from chi_square import chi_square_test
    front_obs = [front_exposure.get(i, 0) for i in range(1, 36)]
    front_exp = [n * 5 / 35] * 35
    back_obs = [back_exposure.get(i, 0) for i in range(1, 13)]
    back_exp = [n * 2 / 12] * 12
    front_chi = chi_square_test(front_obs, front_exp)
    back_chi = chi_square_test(back_obs, back_exp)

    return {
        "n_candidates": n,
        "front_exposure": dict(front_exposure),
        "back_exposure": dict(back_exposure),
        "front_mean": round(mean(all_front), 4),
        "front_sum_mean": round(mean(sums), 4),
        "front_sum_std": round(std(sums), 4),
        "front_high_ratio": round(front_high / (n * 5), 4),
        "back_high_ratio": round(back_high / (n * 2), 4),
        "max_front_exposure_ratio": round(max(front_exposure.values()) / n, 4),
        "max_back_exposure_ratio": round(max(back_exposure.values()) / n, 4),
        "chi2_front_p": front_chi["p_value"],
        "chi2_back_p": back_chi["p_value"],
    }


def distribution_diagnostics(candidates, seed=42):
    """对候选组合池做分布诊断，并附带严格均匀 Random Baseline 对照。

    Args:
        candidates: 候选组合列表（通常为 generate_top_candidates 输出）
        seed: Random Baseline 的固定种子（仅诊断对照用，不影响生产）

    Returns:
        dict: {"portfolio": ..., "random_baseline": ..., "note": ...}
    """
    random_pool = random_baseline_pool(len(candidates), seed=seed)
    return {
        "portfolio": portfolio_distribution(candidates),
        "random_baseline": portfolio_distribution(random_pool),
        "note": ("分布诊断只描述候选组合池的号码曝光/结构特征（是否均匀、有无曝光塌缩、"
                  "和值/高低比例），用于算法偏置检验，不预测任何号码下一期的中奖概率。"),
    }


# ---------------------------------------------------------------------------
# 五、CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="DLT 统计严谨性增强（理论概率/Random Baseline）")
    parser.add_argument("--theory", action="store_true", help="输出理论概率")
    parser.add_argument("--random", type=int, default=0, help="生成 N 组严格随机组合")
    parser.add_argument("--seed", type=int, default=None, help="随机种子")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.theory:
        report = theoretical_prob_report()
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print("📐 大乐透理论概率")
            print(f"  前区单号: 5/35 = {report['front_single']}%")
            print(f"  后区单号: 2/12 = {report['back_single']}%")
            print(f"  完整组合(一等): 1/{report['full_combo_total']:,} = {report['full_combo_p']:.10f}")
            print(f"  {report['note']}")
    elif args.random > 0:
        pool = random_baseline_pool(args.random, args.seed)
        if args.json:
            print(json.dumps(pool, ensure_ascii=False, indent=2))
        else:
            print(f"⚪ Random Baseline: {args.random} 组严格均匀随机组合")
            for i, c in enumerate(pool, 1):
                fs = " ".join(f"{n:02d}" for n in c["front"])
                bs = " ".join(f"{n:02d}" for n in c["back"])
                print(f"  #{i:2d} {fs} + {bs}")
            print("  注：不使用历史频率/冷热/趋势/遗漏/heuristic weight/过滤（真正均匀随机）。")
    else:
        parser.print_help()
