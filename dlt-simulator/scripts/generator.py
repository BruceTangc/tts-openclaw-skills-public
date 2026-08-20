#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generator.py — 候选生成+评分模块

生成候选组合池，对每组进行多维度评分
"""
import random
import math
from collections import Counter

from common import load_config, combination_key

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
FRONT_PICK = cfg["front_pick"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]
BACK_PICK = cfg["back_pick"]
POOL_SIZE = cfg["candidate_pool_size"]
MAX_FRONT_OVERLAP = cfg["max_front_overlap"]


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


def compute_weights(draws, strategy="balanced", window=None):
    """
    根据策略计算号码权重

    Returns:
        dict: front_weights, back_weights
    """
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
        if strategy == "hot":
            w = front_freq.get(n, 0) + 1
        elif strategy == "cold":
            w = front_last_seen.get(n, total) + 1
        elif strategy == "trend":
            w = 3.0 if n in rising else 1.0
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
        if strategy == "hot":
            w = back_freq.get(n, 0) + 1
        elif strategy == "cold":
            w = back_last_seen.get(n, total) + 1
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


def score_candidate(front, back, draws, window=None):
    """
    多维度评分

    Returns:
        dict: 各维度分数及总分
    """
    data = draws[:window] if window else draws
    total = len(data)
    if total == 0:
        return {"total": 0}

    front_freq = Counter()
    back_freq = Counter()
    for d in data:
        for n in d["front"]:
            front_freq[n] += 1
        for n in d["back"]:
            back_freq[n] += 1

    scores = {}

    # 1. 频率得分（号码在历史中出现的频率，适度偏高更好）
    front_freq_score = sum(front_freq.get(n, 0) for n in front) / (total * 5)
    back_freq_score = sum(back_freq.get(n, 0) for n in back) / (total * 2)
    scores["frequency"] = round((front_freq_score + back_freq_score) / 2, 4)

    # 2. 遗漏值得分（遗漏适中的号码）
    front_last = {}
    back_last = {}
    for i, d in enumerate(data):
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
    对候选池评分并排序

    Returns:
        list[tuple]: [(front, back, score), ...] 按总分降序
    """
    scored = []
    for front, back in pool:
        scores = score_candidate(front, back, draws, window)
        scored.append((front, back, scores["total"]))
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored


def filter_overlap(ranked, max_overlap=None):
    """
    过滤过度重叠的组合

    Args:
        ranked: [(front, back, score), ...]
        max_overlap: 前区最大重叠号码数

    Returns:
        list: 过滤后的排序组合
    """
    if max_overlap is None:
        max_overlap = MAX_FRONT_OVERLAP

    filtered = []
    for front, back, score in ranked:
        front_set = set(front)
        ok = True
        for f_front, _, _ in filtered:
            overlap = len(front_set & set(f_front))
            if overlap > max_overlap:
                ok = False
                break
        if ok:
            filtered.append((front, back, score))
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
            print(f"#{r['rank']:2d} [{r['score']:.4f}] {front_str} + {back_str}")
