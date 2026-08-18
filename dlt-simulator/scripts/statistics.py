#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
statistics.py — 统计分析模块

频次统计、遗漏值、冷热号、和值分析、奇偶比、区间分布、趋势分析
"""
import json
import math
from collections import Counter
from pathlib import Path

from common import load_config, load_json, save_json, DATA_DIR, mean, variance, std

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
FRONT_PICK = cfg["front_pick"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]
BACK_PICK = cfg["back_pick"]
WINDOWS = cfg["statistics_windows"]


def frequency_analysis(draws, window=None):
    """
    频次统计分析

    Args:
        draws: 按期号降序排列的开奖数据列表
        window: 分析窗口（最近N期），None表示全部

    Returns:
        dict: front_freq, back_freq, total
    """
    data = draws[:window] if window else draws
    total = len(data)
    front_freq = Counter()
    back_freq = Counter()
    for d in data:
        for n in d["front"]:
            front_freq[n] += 1
        for n in d["back"]:
            back_freq[n] += 1
    return {
        "front_freq": dict(front_freq),
        "back_freq": dict(back_freq),
        "total": total,
    }


def omission_analysis(draws):
    """
    遗漏值分析（每个号码距上次出现的期数）

    Returns:
        dict: front_omission, back_omission
    """
    front_last_seen = {}
    back_last_seen = {}
    for i, d in enumerate(draws):
        for n in d["front"]:
            if n not in front_last_seen:
                front_last_seen[n] = i
        for n in d["back"]:
            if n not in back_last_seen:
                back_last_seen[n] = i

    total = len(draws)
    front_omission = {n: front_last_seen.get(n, total) for n in range(FRONT_MIN, FRONT_MAX + 1)}
    back_omission = {n: back_last_seen.get(n, total) for n in range(BACK_MIN, BACK_MAX + 1)}
    return {"front_omission": front_omission, "back_omission": back_omission}


def hot_cold_analysis(draws, window=None, hot_ratio=0.3, cold_ratio=0.3):
    """
    冷热号分析

    Returns:
        dict: hot_front, cold_front, hot_back, cold_back
    """
    data = draws[:window] if window else draws
    front_freq = Counter()
    back_freq = Counter()
    for d in data:
        for n in d["front"]:
            front_freq[n] += 1
        for n in d["back"]:
            back_freq[n] += 1

    total_front = len(data)
    total_back = len(data)

    # 前区冷热
    sorted_front = sorted(range(FRONT_MIN, FRONT_MAX + 1),
                          key=lambda n: front_freq.get(n, 0), reverse=True)
    n_hot_f = max(1, int(FRONT_MAX * hot_ratio))
    n_cold_f = max(1, int(FRONT_MAX * cold_ratio))
    hot_front = sorted_front[:n_hot_f]
    cold_front = sorted_front[-n_cold_f:]

    # 后区冷热
    sorted_back = sorted(range(BACK_MIN, BACK_MAX + 1),
                         key=lambda n: back_freq.get(n, 0), reverse=True)
    n_hot_b = max(1, int(BACK_MAX * hot_ratio))
    n_cold_b = max(1, int(BACK_MAX * cold_ratio))
    hot_back = sorted_back[:n_hot_b]
    cold_back = sorted_back[-n_cold_b:]

    return {
        "hot_front": hot_front,
        "cold_front": cold_front,
        "hot_back": hot_back,
        "cold_back": cold_back,
    }


def sum_analysis(draws, window=None):
    """
    和值分析（前区5个号码之和）

    Returns:
        dict: avg_sum, std_sum, min_sum, max_sum, sum_distribution
    """
    data = draws[:window] if window else draws
    sums = [sum(d["front"]) for d in data]
    return {
        "avg_sum": mean(sums),
        "std_sum": std(sums),
        "min_sum": min(sums) if sums else 0,
        "max_sum": max(sums) if sums else 0,
        "sums": sums,
    }


def odd_even_analysis(draws, window=None):
    """
    奇偶比分析

    Returns:
        dict: avg_odd_ratio, odd_even_distribution
    """
    data = draws[:window] if window else draws
    ratios = []
    distribution = Counter()
    for d in data:
        odd = sum(1 for n in d["front"] if n % 2 == 1)
        even = FRONT_PICK - odd
        ratios.append(odd / FRONT_PICK)
        distribution[f"{odd}:{even}"] += 1
    return {
        "avg_odd_ratio": mean(ratios),
        "distribution": dict(distribution),
    }


def zone_analysis(draws, window=None):
    """
    区间分布分析（前区1-12/13-24/25-35）

    Returns:
        dict: avg_zones, distribution
    """
    data = draws[:window] if window else draws
    distribution = Counter()
    for d in data:
        z1 = sum(1 for n in d["front"] if 1 <= n <= 12)
        z2 = sum(1 for n in d["front"] if 13 <= n <= 24)
        z3 = sum(1 for n in d["front"] if 25 <= n <= 35)
        distribution[f"{z1}:{z2}:{z3}"] += 1
    return {"distribution": dict(distribution)}


def trend_analysis(draws, recent_n=20):
    """
    趋势分析（近期 vs 历史）

    Returns:
        dict: rising_front, falling_front, rising_back, falling_back
    """
    recent = draws[:recent_n]
    older = draws[recent_n:]

    recent_front = Counter()
    older_front = Counter()
    recent_back = Counter()
    older_back = Counter()

    for d in recent:
        for n in d["front"]:
            recent_front[n] += 1
        for n in d["back"]:
            recent_back[n] += 1
    for d in older:
        for n in d["front"]:
            older_front[n] += 1
        for n in d["back"]:
            older_back[n] += 1

    rising = []
    falling = []
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        r = recent_front.get(n, 0) / max(1, len(recent))
        o = older_front.get(n, 0) / max(1, len(older))
        if r > o * 1.3 and r > 0.02:
            rising.append(n)
        elif o > r * 1.3 and o > 0.02:
            falling.append(n)

    rising_back = []
    falling_back = []
    for n in range(BACK_MIN, BACK_MAX + 1):
        r = recent_back.get(n, 0) / max(1, len(recent))
        o = older_back.get(n, 0) / max(1, len(older))
        if r > o * 1.3 and r > 0.02:
            rising_back.append(n)
        elif o > r * 1.3 and o > 0.02:
            falling_back.append(n)

    return {
        "rising_front": rising,
        "falling_front": falling,
        "rising_back": rising_back,
        "falling_back": falling_back,
    }


def full_statistics(draws):
    """
    完整统计分析，返回各窗口下的统计结果

    Returns:
        dict: window -> statistics
    """
    result = {}
    for w in [None] + WINDOWS:
        key = f"all" if w is None else f"last_{w}"
        data = draws[:w] if w else draws
        freq = frequency_analysis(data)
        hot_cold = hot_cold_analysis(data)
        sum_stat = sum_analysis(data)
        odd_even = odd_even_analysis(data)
        zone = zone_analysis(data)
        trend = trend_analysis(data) if w and w >= 50 else trend_analysis(draws, recent_n=20)
        omit = omission_analysis(draws)

        result[key] = {
            "total": len(data),
            "front_freq": freq["front_freq"],
            "back_freq": freq["back_freq"],
            "hot_front": hot_cold["hot_front"],
            "cold_front": hot_cold["cold_front"],
            "hot_back": hot_cold["hot_back"],
            "cold_back": hot_cold["cold_back"],
            "front_omission": omit["front_omission"],
            "back_omission": omit["back_omission"],
            "avg_sum": sum_stat["avg_sum"],
            "std_sum": sum_stat["std_sum"],
            "avg_odd_ratio": odd_even["avg_odd_ratio"],
            "odd_even_distribution": odd_even["distribution"],
            "zone_distribution": zone["distribution"],
            "rising_front": trend["rising_front"],
            "falling_front": trend["falling_front"],
        }
    return result


def format_statistics(stats, label=""):
    """格式化输出统计结果"""
    lines = []
    if label:
        lines.append(f"📊 统计分析 — {label}")
        lines.append("=" * 50)

    lines.append(f"分析期数: {stats.get('total', 0)}")

    if "hot_front" in stats:
        lines.append(f"🔥 前区热号: {' '.join(f'{n:02d}' for n in stats['hot_front'])}")
        lines.append(f"❄️  前区冷号: {' '.join(f'{n:02d}' for n in stats['cold_front'])}")
    if "hot_back" in stats:
        lines.append(f"🔥 后区热号: {' '.join(f'{n:02d}' for n in stats['hot_back'])}")
        lines.append(f"❄️  后区冷号: {' '.join(f'{n:02d}' for n in stats['cold_back'])}")
    if "avg_sum" in stats:
        lines.append(f"📐 前区和值: 平均 {stats['avg_sum']:.1f} ± {stats.get('std_sum', 0):.1f}")
    if "avg_odd_ratio" in stats:
        lines.append(f"🔢 奇偶比: 平均奇数占比 {stats['avg_odd_ratio']*100:.1f}%")
    if "rising_front" in stats and stats["rising_front"]:
        lines.append(f"📈 趋势上升: {' '.join(f'{n:02d}' for n in stats['rising_front'])}")
    if "falling_front" in stats and stats["falling_front"]:
        lines.append(f"📉 趋势下降: {' '.join(f'{n:02d}' for n in stats['falling_front'])}")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from fetch_history import fetch_history

    parser = argparse.ArgumentParser(description="大乐透统计分析")
    parser.add_argument("--window", type=int, default=100, help="分析窗口")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    args = parser.parse_args()

    draws = fetch_history()
    if not draws:
        print("无历史数据")
        exit(1)

    stats = full_statistics(draws)
    key = f"last_{args.window}" if args.window else "all"
    result = stats.get(key, {})

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_statistics(result, f"最近 {args.window} 期"))
