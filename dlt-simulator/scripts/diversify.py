#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diversify.py — 组合多样性过滤

确保候选组合之间有足够的号码差异，避免过于相似的组合
"""
import math
from collections import Counter

from common import load_config

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]


def front_overlap(a_front, b_front):
    """计算两个前区组合的重叠号码数"""
    return len(set(a_front) & set(b_front))


def back_overlap(a_back, b_back):
    """计算两个后区组合的重叠号码数"""
    return len(set(a_back) & set(b_back))


def total_overlap(a_front, a_back, b_front, b_back):
    """计算总重叠（加权：前区权重更高）"""
    return front_overlap(a_front, b_front) * 2 + back_overlap(a_back, b_back)


def diversity_score(candidate, others):
    """
    计算单个候选相对于其他候选的多样性得分

    得分越高表示与其他组合差异越大
    """
    if not others:
        return 1.0

    min_overlap = float('inf')
    total_overlap_sum = 0

    for other in others:
        fo = front_overlap(candidate["front"], other["front"])
        bo = back_overlap(candidate["back"], other["back"])
        total = fo * 2 + bo
        min_overlap = min(min_overlap, total)
        total_overlap_sum += total

    avg_overlap = total_overlap_sum / len(others)

    # 多样性 = 1 - 平均重叠/最大可能重叠
    max_possible = 5 * 2 + 2  # 前区5*2 + 后区2
    diversity = 1.0 - avg_overlap / max_possible
    return round(max(0.0, diversity), 4)


def diversify_candidates(candidates, min_front_overlap=3, min_back_overlap=1):
    """
    多样性过滤：确保候选组合之间有足够的差异

    Args:
        candidates: [{"front": [...], "back": [...], "score": float, "rank": int}, ...]
        min_front_overlap: 前区最小重叠数（低于此值才保留）
        min_back_overlap: 后区最小重叠数

    Returns:
        list: 过滤后的候选列表
    """
    if not candidates:
        return []

    selected = [candidates[0]]

    for cand in candidates[1:]:
        is_diverse = True
        for sel in selected:
            fo = front_overlap(cand["front"], sel["front"])
            bo = back_overlap(cand["back"], sel["back"])
            if fo >= min_front_overlap and bo >= min_back_overlap:
                is_diverse = False
                break
        if is_diverse:
            selected.append(cand)

    return selected


def diversify_by_zone(candidates):
    """
    按区间分布多样性过滤

    确保候选组合覆盖不同的区间模式
    """
    if not candidates:
        return []

    zone_patterns = []
    selected = []

    for cand in candidates:
        zones = [0, 0, 0]
        for n in cand["front"]:
            if n <= 12:
                zones[0] += 1
            elif n <= 24:
                zones[1] += 1
            else:
                zones[2] += 1
        pattern = tuple(zones)

        # 检查是否已有相同区间模式的候选
        if pattern not in zone_patterns:
            zone_patterns.append(pattern)
            selected.append(cand)

    return selected


def diversify_by_odd_even(candidates):
    """
    按奇偶比多样性过滤
    """
    if not candidates:
        return []

    patterns = []
    selected = []

    for cand in candidates:
        odd = sum(1 for n in cand["front"] if n % 2 == 1)
        even = len(cand["front"]) - odd
        pattern = (odd, even)

        if pattern not in patterns:
            patterns.append(pattern)
            selected.append(cand)

    return selected


def full_diversify(candidates, target_count=10, max_front_overlap=3):
    """
    完整多样性过滤流程

    1. 按分数排序（已排好）
    2. 按重叠度过滤（主要手段）
    3. 确保至少返回 target_count 组

    Returns:
        list: 多样化后的候选列表
    """
    if not candidates:
        return []

    # 直接用重叠度过滤，保留得分高的
    selected = [candidates[0]]
    for cand in candidates[1:]:
        ok = True
        for sel in selected:
            fo = front_overlap(cand["front"], sel["front"])
            if fo >= max_front_overlap:
                ok = False
                break
        if ok:
            selected.append(cand)
        if len(selected) >= target_count:
            break

    # 如果不够，放宽条件补充
    if len(selected) < target_count:
        seen = {(tuple(c["front"]), tuple(c["back"])) for c in selected}
        for cand in candidates:
            key = (tuple(cand["front"]), tuple(cand["back"]))
            if key not in seen:
                selected.append(cand)
                seen.add(key)
                if len(selected) >= target_count:
                    break

    return selected[:target_count]


def format_diversity(candidates, filtered):
    """格式化输出"""
    lines = ["🔄 组合多样性过滤"]
    lines.append(f"  原始候选: {len(candidates)}")
    lines.append(f"  过滤后: {len(filtered)}")

    if filtered:
        lines.append("区间分布:")
        for c in filtered:
            zones = [0, 0, 0]
            for n in c["front"]:
                if n <= 12:
                    zones[0] += 1
                elif n <= 24:
                    zones[1] += 1
                else:
                    zones[2] += 1
            front_str = " ".join(f"{n:02d}" for n in c["front"])
            back_str = " ".join(f"{n:02d}" for n in c["back"])
            lines.append(f"  [{c.get('rank', '?')}] {front_str} + {back_str} (区{zones[0]}:{zones[1]}:{zones[2]})")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from generator import generate_top_candidates
    from fetch_history import fetch_history

    parser = argparse.ArgumentParser(description="组合多样性过滤")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--target", type=int, default=10)
    parser.add_argument("--strategy", default="balanced")
    args = parser.parse_args()

    draws = fetch_history()
    if not draws:
        print("无历史数据")
        exit(1)

    candidates = generate_top_candidates(draws, args.strategy, args.count)
    filtered = full_diversify(candidates, args.target)
    print(format_diversity(candidates, filtered))
