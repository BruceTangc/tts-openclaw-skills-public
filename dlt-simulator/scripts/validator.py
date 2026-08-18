#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validator.py — 历史组合硬过滤

拒绝与历史完整中奖组合完全一致的候选组合
规则：7个号码全部一致才拒绝（前区5个+后区2个完全匹配）
"""
from pathlib import Path

from common import DATA_DIR, load_json, combination_key


HISTORY_FILE = DATA_DIR / "history_draws.json"


def load_history_combos():
    """加载历史开奖组合集合"""
    draws = load_json(HISTORY_FILE)
    if not draws:
        return set()
    combos = set()
    for d in draws:
        front = tuple(sorted(d["front"]))
        back = tuple(sorted(d["back"]))
        combos.add((front, back))
    return combos


def is_historical(front, back, history_combos=None):
    """
    检查组合是否与历史完整中奖组合完全一致

    规则：7个号码全部一致才拒绝

    Args:
        front: 前区号码列表
        back: 后区号码列表
        history_combos: 历史组合集合（可选，避免重复加载）

    Returns:
        tuple: (is_rejected, match_issue or None)
    """
    if history_combos is None:
        history_combos = load_history_combos()

    key = (tuple(sorted(front)), tuple(sorted(back)))
    if key in history_combos:
        return True, "历史完整中奖组合"
    return False, None


def filter_historical(candidates, history_combos=None):
    """
    批量过滤历史组合

    Args:
        candidates: [{"front": [...], "back": [...], ...}, ...]
        history_combos: 历史组合集合

    Returns:
        tuple: (filtered, rejected_count)
    """
    if history_combos is None:
        history_combos = load_history_combos()

    filtered = []
    rejected = 0
    for c in candidates:
        is_hist, _ = is_historical(c["front"], c["back"], history_combos)
        if is_hist:
            rejected += 1
        else:
            filtered.append(c)

    return filtered, rejected


def format_validator(filtered, rejected):
    """格式化输出"""
    lines = ["✅ 历史组合过滤"]
    lines.append(f"  通过: {len(filtered)}")
    lines.append(f"  拒绝（完整历史重复）: {rejected}")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from generator import generate_top_candidates
    from fetch_history import fetch_history

    parser = argparse.ArgumentParser(description="历史组合过滤")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--strategy", default="balanced")
    args = parser.parse_args()

    draws = fetch_history()
    if not draws:
        print("无历史数据")
        exit(1)

    candidates = generate_top_candidates(draws, args.strategy, args.count)
    history_combos = load_history_combos()
    filtered, rejected = filter_historical(candidates, history_combos)
    print(format_validator(filtered, rejected))
