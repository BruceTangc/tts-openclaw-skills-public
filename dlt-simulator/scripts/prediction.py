#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prediction.py — 18:00 生成预测

完整预测流程：抓取数据 → 统计分析 → 生成候选 → 多样性过滤 → 历史过滤 → 输出Top 10
Top 2 = BUY，其余 = WATCH
"""
import json
from datetime import datetime
from pathlib import Path

from common import (
    load_config, load_json, save_json,
    DATA_DIR, REPORT_DIR, STRATEGY_DIR,
    format_combination
)
from fetch_history import fetch_history
from statistics import full_statistics
from generator import generate_top_candidates
from diversify import full_diversify
from validator import filter_historical, load_history_combos
from strategy_manager import load_current_strategy

cfg = load_config()
PREDICTION_COUNT = cfg["prediction_count"]
BUY_COUNT = cfg["buy_count"]
WATCH_COUNT = cfg["watch_count"]


def generate_prediction(strategy_name=None, prediction_count=None):
    """
    完整预测流程

    Args:
        strategy_name: 策略名称（None则使用当前策略）
        prediction_count: 候选数量

    Returns:
        dict: {
            "date": str,
            "issue": str,
            "strategy": str,
            "buy": [{"front": [...], "back": [...], "rank": int, "score": float}, ...],
            "watch": [...],
            "stats_summary": {...},
            "timestamp": str
        }
    """
    if prediction_count is None:
        prediction_count = PREDICTION_COUNT

    # 1. 抓取历史数据
    draws = fetch_history()
    if not draws:
        return {"error": "无法获取历史数据"}

    # 2. 确定策略
    if strategy_name is None:
        strategy_info = load_current_strategy()
        strategy_name = strategy_info.get("name", "balanced")

    # 3. 统计分析
    stats = full_statistics(draws)

    # 4. 生成候选
    candidates = generate_top_candidates(
        draws, strategy_name, prediction_count, cfg["candidate_pool_size"]
    )

    # 5. 多样性过滤
    diversified = full_diversify(candidates, prediction_count)

    # 6. 历史组合过滤
    history_combos = load_history_combos()
    filtered, rejected = filter_historical(diversified, history_combos)

    # 确保数量足够
    if len(filtered) < prediction_count:
        # 补充生成
        extra = generate_top_candidates(
            draws, strategy_name, prediction_count * 2, cfg["candidate_pool_size"]
        )
        extra_diversified = full_diversify(extra, prediction_count * 2)
        extra_filtered, _ = filter_historical(extra_diversified, history_combos)
        # 合并去重
        seen = set()
        for c in filtered:
            key = (tuple(c["front"]), tuple(c["back"]))
            seen.add(key)
        for c in extra_filtered:
            key = (tuple(c["front"]), tuple(c["back"]))
            if key not in seen:
                filtered.append(c)
                seen.add(key)
                if len(filtered) >= prediction_count:
                    break

    # 7. 分割BUY和WATCH
    buy = filtered[:BUY_COUNT]
    watch = filtered[BUY_COUNT:prediction_count]

    # 8. 获取最新期号
    latest_issue = draws[0].get("issue", "") if draws else ""
    next_issue = str(int(latest_issue) + 1) if latest_issue.isdigit() else ""

    # 9. 组装结果
    result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "issue": next_issue,
        "strategy": strategy_name,
        "buy": [
            {
                "front": c["front"],
                "back": c["back"],
                "rank": c.get("rank", i + 1),
                "score": c.get("score", 0),
                "label": "BUY",
            }
            for i, c in enumerate(buy)
        ],
        "watch": [
            {
                "front": c["front"],
                "back": c["back"],
                "rank": c.get("rank", i + BUY_COUNT + 1),
                "score": c.get("score", 0),
                "label": "WATCH",
            }
            for i, c in enumerate(watch)
        ],
        "historical_filtered": rejected,
        "stats_summary": _stats_summary(stats),
        "timestamp": datetime.now().isoformat(),
    }

    return result


def _stats_summary(stats):
    """提取统计摘要"""
    summary = {}
    for key in ["last_100", "last_50", "last_20"]:
        if key in stats:
            s = stats[key]
            summary[key] = {
                "total": s.get("total", 0),
                "hot_front": s.get("hot_front", [])[:5],
                "cold_front": s.get("cold_front", [])[:5],
                "avg_sum": s.get("avg_sum", 0),
                "avg_odd_ratio": s.get("avg_odd_ratio", 0),
                "rising_front": s.get("rising_front", [])[:5],
            }
    return summary


def save_prediction(prediction):
    """保存预测结果"""
    # 保存到 predictions 目录
    date_str = prediction.get("date", datetime.now().strftime("%Y-%m-%d"))
    issue = prediction.get("issue", "unknown")
    filepath = REPORT_DIR / "predictions" / f"{date_str}_{issue}.json"
    save_json(filepath, prediction)

    # 保存到当前预测文件（供 review 使用）
    current_file = DATA_DIR / "current_prediction.json"
    save_json(current_file, prediction)

    return filepath


def format_prediction(prediction):
    """格式化输出预测结果"""
    lines = []
    lines.append("🎱 超级大乐透预测")
    lines.append("=" * 50)
    lines.append(f"日期: {prediction.get('date', '')} {prediction.get('time', '')}")
    lines.append(f"期号: 第 {prediction.get('issue', '?')} 期")
    lines.append(f"策略: {prediction.get('strategy', 'balanced')}")
    lines.append("")

    # BUY
    lines.append("💰 BUY（推荐购买）:")
    lines.append("-" * 40)
    for c in prediction.get("buy", []):
        front_str = " ".join(f"{n:02d}" for n in c["front"])
        back_str = " ".join(f"{n:02d}" for n in c["back"])
        lines.append(f"  #{c['rank']:2d} [{c['score']:.4f}] {front_str} + {back_str}")
    lines.append("")

    # WATCH
    lines.append("👀 WATCH（观望参考）:")
    lines.append("-" * 40)
    for c in prediction.get("watch", []):
        front_str = " ".join(f"{n:02d}" for n in c["front"])
        back_str = " ".join(f"{n:02d}" for n in c["back"])
        lines.append(f"  #{c['rank']:2d} [{c['score']:.4f}] {front_str} + {back_str}")
    lines.append("")

    if prediction.get("historical_filtered", 0) > 0:
        lines.append(f"⚠️ 已过滤 {prediction['historical_filtered']} 组历史重复组合")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="生成大乐透预测")
    parser.add_argument("--strategy", default=None, help="策略名称")
    parser.add_argument("--count", type=int, default=10, help="候选数量")
    parser.add_argument("--save", action="store_true", help="保存预测结果")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    args = parser.parse_args()

    result = generate_prediction(args.strategy, args.count)
    if "error" in result:
        print(f"错误: {result['error']}")
        exit(1)

    if args.save:
        path = save_prediction(result)
        print(f"已保存到: {path}")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_prediction(result))
