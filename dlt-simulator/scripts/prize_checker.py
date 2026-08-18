#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prize_checker.py — 中奖等级判断（2026新规7奖级）

13个中奖条件 → 7个奖级
"""
import json
from common import load_config

cfg = load_config()

# 2026新规：13个中奖条件 → 7个奖级
# (front_hit, back_hit) → tier
TIER_MAP = {
    (5, 2): 1,
    (5, 1): 2,
    (5, 0): 3,
    (4, 2): 3,
    (4, 1): 4,
    (4, 0): 5,
    (3, 2): 5,
    (3, 1): 6,
    (2, 2): 6,
    (3, 0): 7,
    (2, 1): 7,
    (1, 2): 7,
    (0, 2): 7,
}

TIER_NAMES = {
    1: "一等奖",
    2: "二等奖",
    3: "三等奖",
    4: "四等奖",
    5: "五等奖",
    6: "六等奖",
    7: "七等奖",
}

# 统一组合表现等级（用于 Top-2 Selection 等跨模块排序）
# 一等奖=7 ... 七等奖=1，未中奖=0
TIER_RANK = {
    1: 7,
    2: 6,
    3: 5,
    4: 4,
    5: 3,
    6: 2,
    7: 1,
}


def performance_key(tier, front_hit, back_hit):
    """
    统一的组合表现排序键：奖级优先，其次前区命中，再后区命中

    Returns:
        tuple: (prize_rank, front_hit, back_hit)
    """
    prize_rank = TIER_RANK.get(tier, 0)  # 未中奖 = 0
    return (prize_rank, front_hit, back_hit)

# 固定奖奖金（元）：tier → (pool<8亿, pool>=8亿)
PRIZE_RULES = {
    3: (5000, 6666),
    4: (300, 380),
    5: (150, 200),
    6: (15, 18),
    7: (5, 7),
}


def match_numbers(user_front, user_back, draw_front, draw_back):
    """
    对比号码，返回前区命中数、后区命中数

    Returns:
        tuple: (front_hit, back_hit)
    """
    fh = len(set(user_front) & set(draw_front))
    bh = len(set(user_back) & set(draw_back))
    return fh, bh


def determine_tier(front_hit, back_hit):
    """
    根据命中数返回奖级

    Returns:
        int or None: 奖级(1-7)，未中奖返回None
    """
    return TIER_MAP.get((front_hit, back_hit))


def calc_prize(tier, pool_billion=None, add_bet=False):
    """
    计算单注奖金

    Args:
        tier: 奖级(1-7)
        pool_billion: 奖池金额（亿）
        add_bet: 是否追加投注

    Returns:
        int: 奖金（元）
    """
    if tier is None:
        return 0
    if tier <= 2:
        # 浮动奖，简化估计
        if tier == 1:
            base = 5000000  # 500万
        else:
            base = 300000   # 30万
        if add_bet:
            base = int(base * 1.8)
        return base
    # 固定奖
    use_over = pool_billion is not None and pool_billion >= 8
    return PRIZE_RULES[tier][1 if use_over else 0]


def check_prize(user_front, user_back, draw_front, draw_back, pool_billion=None, add_bet=False):
    """
    完整中奖检查

    Returns:
        dict: {
            front_hit, back_hit, tier, tier_name,
            prize, is_add, is_floating
        }
    """
    fh, bh = match_numbers(user_front, user_back, draw_front, draw_back)
    tier = determine_tier(fh, bh)
    prize = calc_prize(tier, pool_billion, add_bet)
    tier_name = TIER_NAMES.get(tier, "未中奖") if tier else "未中奖"

    return {
        "front_hit": fh,
        "back_hit": bh,
        "tier": tier,
        "tier_name": tier_name,
        "prize": prize,
        "is_add": add_bet,
        "is_floating": tier is not None and tier <= 2,
    }


def check_batch(predictions, draw_front, draw_back, pool_billion=None, add_bet=False):
    """
    批量检查多注预测的中奖情况

    Args:
        predictions: [{"front": [...], "back": [...], ...}, ...]
        draw_front, draw_back: 实际开奖号码

    Returns:
        dict: {
            results: [check_prize结果...],
            total_prize: 总奖金,
            best_tier: 最佳奖级,
            win_count: 中奖注数
        }
    """
    results = []
    total_prize = 0
    best_tier = None
    win_count = 0

    for pred in predictions:
        result = check_prize(
            pred["front"], pred["back"],
            draw_front, draw_back,
            pool_billion, add_bet
        )
        results.append(result)
        total_prize += result["prize"]
        if result["tier"] is not None:
            win_count += 1
            if best_tier is None or result["tier"] < best_tier:
                best_tier = result["tier"]

    return {
        "results": results,
        "total_prize": total_prize,
        "best_tier": best_tier,
        "best_tier_name": TIER_NAMES.get(best_tier, "未中奖") if best_tier else "未中奖",
        "win_count": win_count,
        "total_bet": len(predictions) * (3 if add_bet else 2),
    }


def format_check(results, draw_front=None, draw_back=None):
    """格式化输出中奖检查结果"""
    lines = ["🎯 中奖检查结果"]
    lines.append("=" * 50)

    if draw_front and draw_back:
        front_str = " ".join(f"{n:02d}" for n in draw_front)
        back_str = " ".join(f"{n:02d}" for n in draw_back)
        lines.append(f"开奖号码: {front_str} + {back_str}")
        lines.append("")

    for i, r in enumerate(results.get("results", []), 1):
        front_str = " ".join(f"{n:02d}" for n in r.get("front", []))
        back_str = " ".join(f"{n:02d}" for n in r.get("back", []))
        lines.append(f"第{i}注: {front_str} + {back_str}")
        lines.append(f"  前区命中 {r['front_hit']}/5, 后区命中 {r['back_hit']}/2")
        if r["tier"]:
            lines.append(f"  🎉 {r['tier_name']} - ¥{r['prize']:,}")
        else:
            lines.append(f"  ❌ 未中奖")

    lines.append("")
    lines.append(f"总奖金: ¥{results.get('total_prize', 0):,}")
    lines.append(f"中奖注数: {results.get('win_count', 0)}/{len(results.get('results', []))}")
    lines.append(f"投注成本: ¥{results.get('total_bet', 0):,}")
    if results.get('total_bet', 0) > 0:
        roi = results.get('total_prize', 0) / results['total_bet'] * 100
        lines.append(f"回报率: {roi:.2f}%")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="中奖等级判断")
    parser.add_argument("--front", type=int, nargs=5, required=True, help="用户前区")
    parser.add_argument("--back", type=int, nargs=2, required=True, help="用户后区")
    parser.add_argument("--draw-front", type=int, nargs=5, required=True, help="开奖前区")
    parser.add_argument("--draw-back", type=int, nargs=2, required=True, help="开奖后区")
    parser.add_argument("--pool", type=float, default=None, help="奖池(亿)")
    parser.add_argument("--add", action="store_true", help="追加投注")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = check_prize(args.front, args.back, args.draw_front, args.draw_back, args.pool, args.add)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"前区命中: {result['front_hit']}/5, 后区命中: {result['back_hit']}/2")
        print(f"奖级: {result['tier_name']}")
        print(f"奖金: ¥{result['prize']:,}")
