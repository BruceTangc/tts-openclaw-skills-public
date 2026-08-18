#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bootstrap.py — Bootstrap 分析模块

Walk-forward 回测（禁止未来数据泄露），核心指标：Top-2 Selection Accuracy
"""
import random
import json
from collections import Counter
from pathlib import Path

from common import load_config, save_json, DATA_DIR, REPORT_DIR
from fetch_history import fetch_history
from generator import generate_top_candidates, compute_weights, weighted_sample
from diversify import full_diversify
from validator import filter_historical, load_history_combos
from prize_checker import determine_tier

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
FRONT_PICK = cfg["front_pick"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]
BACK_PICK = cfg["back_pick"]
BOOTSTRAP_ITERATIONS = cfg["bootstrap_iterations"]


def walk_forward_backtest(draws, strategy="balanced", train_window=200, test_count=1,
                          top_n=10, buy_count=2):
    """
    Walk-forward 回测

    规则：只用 train_window 之前的数据训练，预测 test_count 期
    禁止未来数据泄露

    Args:
        draws: 按期号降序排列的历史数据
        strategy: 策略名称
        train_window: 训练窗口大小
        test_count: 预测期数
        top_n: 候选数量
        buy_count: BUY数量（用于Accuracy计算）

    Returns:
        dict: 回测结果
    """
    total = len(draws)
    if total < train_window + test_count:
        return {"error": "数据不足", "required": train_window + test_count, "available": total}

    results = []
    for i in range(test_count):
        # 训练数据：只用前 train_window 期（不含未来）
        train_draws = draws[i: i + train_window]
        # 测试目标：第 train_window + i 期
        test_draw = draws[i + train_window]

        # 生成候选（基于训练数据）
        candidates = generate_top_candidates(train_draws, strategy, top_n)
        diversified = full_diversify(candidates, top_n)
        history_combos = load_history_combos()
        filtered, _ = filter_historical(diversified, history_combos)

        if len(filtered) < top_n:
            filtered = diversified[:top_n]

        # 检查BUY组合是否命中
        buy_hits = 0
        for c in filtered[:buy_count]:
            fh = len(set(c["front"]) & set(test_draw["front"]))
            bh = len(set(c["back"]) & set(test_draw["back"]))
            tier = determine_tier(fh, bh)
            if tier is not None:
                buy_hits += 1

        # 检查全部候选是否命中
        any_hit = 0
        best_tier = None
        for c in filtered:
            fh = len(set(c["front"]) & set(test_draw["front"]))
            bh = len(set(c["back"]) & set(test_draw["back"]))
            tier = determine_tier(fh, bh)
            if tier is not None:
                any_hit += 1
                if best_tier is None or tier < best_tier:
                    best_tier = tier

        results.append({
            "test_issue": test_draw.get("issue", ""),
            "draw_front": test_draw["front"],
            "draw_back": test_draw["back"],
            "buy_hit": buy_hits,
            "any_hit": any_hit,
            "best_tier": best_tier,
        })

    # 汇总
    buy_accuracy = sum(1 for r in results if r["buy_hit"] > 0) / len(results) if results else 0
    any_accuracy = sum(1 for r in results if r["any_hit"] > 0) / len(results) if results else 0
    avg_buy_hits = sum(r["buy_hit"] for r in results) / len(results) if results else 0
    avg_any_hits = sum(r["any_hit"] for r in results) / len(results) if results else 0

    return {
        "strategy": strategy,
        "train_window": train_window,
        "test_count": test_count,
        "results": results,
        "top2_accuracy": round(buy_accuracy, 4),
        "any_accuracy": round(any_accuracy, 4),
        "avg_buy_hits": round(avg_buy_hits, 4),
        "avg_any_hits": round(avg_any_hits, 4),
    }


def bootstrap_analysis(draws, strategy="balanced", iterations=None,
                       train_window=200, test_count=1, top_n=10, buy_count=2):
    """
    Bootstrap 分析：多次随机采样回测

    Args:
        draws: 历史数据
        strategy: 策略
        iterations: Bootstrap 次数
        train_window: 训练窗口
        test_count: 每次测试期数
        top_n: 候选数量
        buy_count: BUY数量

    Returns:
        dict: Bootstrap 分析结果
    """
    if iterations is None:
        iterations = BOOTSTRAP_ITERATIONS

    total = len(draws)
    max_start = total - train_window - test_count
    if max_start <= 0:
        return {"error": "数据不足"}

    top2_accuracies = []
    any_accuracies = []
    tier_counts = Counter()

    for _ in iterations:
        # 随机选择起始点（Walk-forward：从随机位置开始，只用历史数据）
        start = random.randint(0, max_start)
        train_draws = draws[start: start + train_window]
        test_draw = draws[start + train_window]

        # 生成候选
        candidates = generate_top_candidates(train_draws, strategy, top_n, cfg["candidate_pool_size"])
        diversified = full_diversify(candidates, top_n)
        history_combos = load_history_combos()
        filtered, _ = filter_historical(diversified, history_combos)
        if len(filtered) < top_n:
            filtered = diversified[:top_n]

        # 检查
        buy_hit = False
        any_hit = False
        best_tier = None
        for i, c in enumerate(filtered):
            fh = len(set(c["front"]) & set(test_draw["front"]))
            bh = len(set(c["back"]) & set(test_draw["back"]))
            tier = determine_tier(fh, bh)
            if tier is not None:
                any_hit = True
                if best_tier is None or tier < best_tier:
                    best_tier = tier
                if i < buy_count:
                    buy_hit = True

        top2_accuracies.append(1 if buy_hit else 0)
        any_accuracies.append(1 if any_hit else 0)
        if best_tier is not None:
            tier_counts[best_tier] += 1

    total_iterations = len(top2_accuracies)
    top2_mean = sum(top2_accuracies) / total_iterations if total_iterations else 0
    any_mean = sum(any_accuracies) / total_iterations if total_iterations else 0

    # 置信区间（Wilson）
    from confidence import wilson_ci
    top2_ci = wilson_ci(sum(top2_accuracies), total_iterations)
    any_ci = wilson_ci(sum(any_accuracies), total_iterations)

    return {
        "strategy": strategy,
        "iterations": total_iterations,
        "train_window": train_window,
        "test_count": test_count,
        "top2_accuracy": round(top2_mean, 4),
        "top2_ci_lower": round(top2_ci[0], 4),
        "top2_ci_upper": round(top2_ci[1], 4),
        "any_accuracy": round(any_mean, 4),
        "any_ci_lower": round(any_ci[0], 4),
        "any_ci_upper": round(any_ci[1], 4),
        "tier_distribution": dict(tier_counts),
    }


def compare_strategies(draws, strategies=None, iterations=None):
    """
    策略对比分析

    Returns:
        list[dict]: 各策略的 Bootstrap 结果
    """
    if strategies is None:
        strategies = ["balanced", "hot", "cold", "trend"]
    if iterations is None:
        iterations = BOOTSTRAP_ITERATIONS // 10  # 策略对比用较少次数

    results = []
    for strat in strategies:
        result = bootstrap_analysis(draws, strat, iterations)
        results.append(result)

    # 按 Top-2 Accuracy 排序
    results.sort(key=lambda x: x.get("top2_accuracy", 0), reverse=True)
    return results


def save_bootstrap_result(result, filename=None):
    """保存 Bootstrap 结果"""
    if filename is None:
        from datetime import datetime
        filename = f"bootstrap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = REPORT_DIR / "statistics" / filename
    save_json(filepath, result)
    return filepath


def format_bootstrap(result):
    """格式化输出"""
    lines = ["📊 Bootstrap 分析结果"]
    lines.append("=" * 50)
    lines.append(f"策略: {result.get('strategy', '')}")
    lines.append(f"迭代次数: {result.get('iterations', 0):,}")
    lines.append(f"训练窗口: {result.get('train_window', 0)}")
    lines.append("")
    lines.append(f"Top-2 Selection Accuracy: {result.get('top2_accuracy', 0)*100:.2f}%")
    lines.append(f"  95% CI: [{result.get('top2_ci_lower', 0)*100:.2f}%, {result.get('top2_ci_upper', 0)*100:.2f}%]")
    lines.append(f"Any Hit Accuracy: {result.get('any_accuracy', 0)*100:.2f}%")
    lines.append(f"  95% CI: [{result.get('any_ci_lower', 0)*100:.2f}%, {result.get('any_ci_upper', 0)*100:.2f}%]")

    tier_dist = result.get("tier_distribution", {})
    if tier_dist:
        lines.append("")
        lines.append("奖级分布:")
        from prize_checker import TIER_NAMES
        for tier in sorted(tier_dist.keys()):
            lines.append(f"  {TIER_NAMES.get(tier, f'第{tier}级')}: {tier_dist[tier]}")

    return "\n".join(lines)


def format_comparison(results):
    """格式化策略对比输出"""
    lines = ["📊 策略对比分析"]
    lines.append("=" * 60)
    lines.append(f"{'策略':<12} {'Top-2 Acc':>10} {'95% CI':>20} {'Any Acc':>10}")
    lines.append("-" * 60)
    for r in results:
        ci = f"[{r.get('top2_ci_lower', 0)*100:.1f}%, {r.get('top2_ci_upper', 0)*100:.1f}%]"
        lines.append(f"{r['strategy']:<12} {r.get('top2_accuracy', 0)*100:>9.2f}% {ci:>20} {r.get('any_accuracy', 0)*100:>9.2f}%")
    lines.append("")
    best = results[0] if results else None
    if best:
        lines.append(f"最佳策略: {best['strategy']} (Top-2 Acc: {best.get('top2_accuracy', 0)*100:.2f}%)")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Bootstrap 分析")
    parser.add_argument("--strategy", default="balanced")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--compare", action="store_true", help="对比多策略")
    parser.add_argument("--save", action="store_true", help="保存结果")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    draws = fetch_history()
    if not draws:
        print("无历史数据")
        exit(1)

    if args.compare:
        results = compare_strategies(draws, iterations=args.iterations)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print(format_comparison(results))
    else:
        result = bootstrap_analysis(draws, args.strategy, args.iterations)
        if args.save:
            path = save_bootstrap_result(result)
            print(f"已保存到: {path}")
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_bootstrap(result))
