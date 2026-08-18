#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monte_carlo.py — Monte Carlo 模拟模块

基于历史频率分布进行大规模随机模拟，评估策略预期收益
"""
import random
from collections import Counter

from common import load_config

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
FRONT_PICK = cfg["front_pick"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]
BACK_PICK = cfg["back_pick"]
MC_ITERATIONS = cfg["monte_carlo_iterations"]


def frequency_weights(draws, window=None):
    """
    从历史数据计算频率权重

    Returns:
        dict: front_weights, back_weights
    """
    data = draws[:window] if window else draws
    total = len(data)
    if total == 0:
        front_w = {n: 1.0 for n in range(FRONT_MIN, FRONT_MAX + 1)}
        back_w = {n: 1.0 for n in range(BACK_MIN, BACK_MAX + 1)}
        return front_w, back_w

    front_freq = Counter()
    back_freq = Counter()
    for d in data:
        for n in d["front"]:
            front_freq[n] += 1
        for n in d["back"]:
            back_freq[n] += 1

    front_w = {}
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        front_w[n] = (front_freq.get(n, 0) + 1) / (total + 35)  # Laplace平滑
    back_w = {}
    for n in range(BACK_MIN, BACK_MAX + 1):
        back_w[n] = (back_freq.get(n, 0) + 1) / (total + 12)

    return front_w, back_w


def weighted_sample(pool_weights, k):
    """加权不重复抽样"""
    items = list(pool_weights.keys())
    weights = [pool_weights[n] for n in items]
    chosen = []
    remaining_items = list(items)
    remaining_weights = list(weights)
    for _ in range(k):
        total_w = sum(remaining_weights)
        if total_w <= 0:
            idx = random.randrange(len(remaining_items))
        else:
            r = random.uniform(0, total_w)
            cum = 0.0
            idx = 0
            for i, w in enumerate(remaining_weights):
                cum += w
                if cum >= r:
                    idx = i
                    break
        chosen.append(remaining_items[idx])
        remaining_items.pop(idx)
        remaining_weights.pop(idx)
    return sorted(chosen)


def simulate_single(front_weights, back_weights):
    """模拟单期随机组合"""
    front = weighted_sample(front_weights, FRONT_PICK)
    back = weighted_sample(back_weights, BACK_PICK)
    return front, back


def match_numbers(user_front, user_back, draw_front, draw_back):
    """计算命中数"""
    fh = len(set(user_front) & set(draw_front))
    bh = len(set(user_back) & set(draw_back))
    return fh, bh


def monte_carlo_batch(user_front, user_back, draws, iterations=None):
    """
    Monte Carlo 批量模拟

    Args:
        user_front, user_back: 用户选择的号码
        draws: 历史数据（用于构建频率分布）
        iterations: 模拟次数

    Returns:
        dict: 模拟结果统计
    """
    if iterations is None:
        iterations = MC_ITERATIONS

    front_w, back_w = frequency_weights(draws)
    results = {"total": iterations, "prize": 0, "tiers": Counter(), "total_prize": 0}

    for _ in range(iterations):
        df, db = simulate_single(front_w, back_w)
        fh, bh = match_numbers(user_front, user_back, df, db)
        tier = _determine_tier(fh, bh)
        prize = _calc_prize(tier)
        results["tiers"][tier] += 1
        if prize > 0:
            results["prize"] += 1
            results["total_prize"] += prize

    results["tiers"] = dict(results["tiers"])
    results["expected_prize"] = results["total_prize"] / iterations
    results["win_rate"] = results["prize"] / iterations
    return results


def _determine_tier(fh, bh):
    """2026新规奖级判定"""
    tier_map = {
        (5, 2): 1, (5, 1): 2, (5, 0): 3, (4, 2): 3,
        (4, 1): 4, (4, 0): 5, (3, 2): 5,
        (3, 1): 6, (2, 2): 6,
        (3, 0): 7, (2, 1): 7, (1, 2): 7, (0, 2): 7,
    }
    return tier_map.get((fh, bh), None)


def _calc_prize(tier):
    """固定奖奖金"""
    fixed = {3: 5000, 4: 300, 5: 150, 6: 15, 7: 5}
    if tier is None:
        return 0
    if tier <= 2:
        return 0  # 浮动奖，模拟中用固定估计
    return fixed.get(tier, 0)


def simulate_strategy(strategy_func, draws, iterations=None):
    """
    模拟某个策略的长期表现

    Args:
        strategy_func: 策略函数，接收draws返回 (front, back)
        draws: 历史数据
        iterations: 模拟次数

    Returns:
        dict: 策略表现统计
    """
    if iterations is None:
        iterations = MC_ITERATIONS // 10  # 策略模拟用较少次数

    front_w, back_w = frequency_weights(draws)
    results = {"total": iterations, "prize": 0, "total_prize": 0, "tiers": Counter()}

    for _ in range(iterations):
        user_front, user_back = strategy_func(draws)
        df, db = simulate_single(front_w, back_w)
        fh, bh = match_numbers(user_front, user_back, df, db)
        tier = _determine_tier(fh, bh)
        prize = _calc_prize(tier)
        results["tiers"][tier] += 1
        if prize > 0:
            results["prize"] += 1
            results["total_prize"] += prize

    results["tiers"] = dict(results["tiers"])
    results["win_rate"] = results["prize"] / iterations
    results["expected_prize"] = results["total_prize"] / iterations
    return results


def format_monte_carlo(result):
    """格式化输出"""
    lines = ["📊 Monte Carlo 模拟结果"]
    lines.append(f"  模拟次数: {result['total']:,}")
    lines.append(f"  中奖率: {result['win_rate']*100:.4f}%")
    lines.append(f"  预期每注奖金: ¥{result['expected_prize']:.2f}")
    lines.append(f"  投注成本: ¥{result['total']*2:,}")
    lines.append(f"  期望回报: ¥{result['total_prize']:,.0f}")
    if result['total'] * 2 > 0:
        roi = result['total_prize'] / (result['total'] * 2) * 100
        lines.append(f"  回报率: {roi:.2f}%")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from fetch_history import fetch_history

    parser = argparse.ArgumentParser(description="Monte Carlo 模拟")
    parser.add_argument("--front", type=int, nargs=5, required=True)
    parser.add_argument("--back", type=int, nargs=2, required=True)
    parser.add_argument("--iterations", type=int, default=100000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    draws = fetch_history()
    if not draws:
        print("无历史数据")
        exit(1)

    result = monte_carlo_batch(args.front, args.back, draws, args.iterations)
    if args.json:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_monte_carlo(result))
