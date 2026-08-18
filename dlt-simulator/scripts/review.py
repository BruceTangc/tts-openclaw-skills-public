#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
review.py — 21:30 复盘

对比预测与实际开奖，更新策略表现数据
"""
import json
from datetime import datetime
from pathlib import Path

from common import (
    load_config, load_json, save_json,
    DATA_DIR, REPORT_DIR, STRATEGY_DIR
)
from fetch_history import fetch_history, get_latest_draw
from prize_checker import check_batch, TIER_NAMES

cfg = load_config()


def load_current_prediction():
    """加载当前预测"""
    return load_json(DATA_DIR / "current_prediction.json")


def load_performance_history():
    """加载策略表现历史"""
    return load_json(STRATEGY_DIR / "performance_history.json") or []


def save_performance_history(history):
    """保存策略表现历史"""
    save_json(STRATEGY_DIR / "performance_history.json", history)


def review():
    """
    执行复盘流程

    Returns:
        dict: 复盘结果
    """
    # 1. 加载当前预测
    prediction = load_current_prediction()
    if not prediction:
        return {"error": "无当前预测数据"}

    # 2. 获取最新开奖
    latest = get_latest_draw()
    if not latest:
        return {"error": "无法获取最新开奖数据"}

    # 3. 检查预测是否针对本期
    pred_issue = prediction.get("issue", "")
    draw_issue = latest.get("issue", "")

    # 4. 合并BUY和WATCH进行检查
    all_predictions = prediction.get("buy", []) + prediction.get("watch", [])

    # 5. 中奖检查（带上号码用于复盘显示）
    check_result = check_batch(
        all_predictions,
        latest["front"],
        latest["back"]
    )
    # 补充号码到结果（check_batch 不返回 front/back）
    for i, r in enumerate(check_result["results"]):
        if i < len(all_predictions):
            r["front"] = all_predictions[i]["front"]
            r["back"] = all_predictions[i]["back"]

    # 6. 组装复盘结果
    review_result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
        "prediction_date": prediction.get("date", ""),
        "prediction_issue": pred_issue,
        "draw_issue": draw_issue,
        "strategy": prediction.get("strategy", "balanced"),
        "draw_front": latest["front"],
        "draw_back": latest["back"],
        "results": check_result["results"],
        "total_prize": check_result["total_prize"],
        "win_count": check_result["win_count"],
        "best_tier": check_result["best_tier"],
        "best_tier_name": check_result["best_tier_name"],
        "total_bet": check_result["total_bet"],
        "buy_count": len(prediction.get("buy", [])),
        "watch_count": len(prediction.get("watch", [])),
        "timestamp": datetime.now().isoformat(),
    }

    # 7. 保存复盘结果
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = REPORT_DIR / "reviews" / f"{date_str}_{draw_issue}.json"
    save_json(filepath, review_result)

    # 8. 更新策略表现
    _update_performance(review_result)

    return review_result


def _update_performance(review_result):
    """更新策略表现数据"""
    strategy = review_result.get("strategy", "balanced")
    history = load_performance_history()

    # 查找现有记录
    existing = None
    for h in history:
        if h.get("strategy") == strategy:
            existing = h
            break

    if existing:
        existing["total_runs"] = existing.get("total_runs", 0) + 1
        existing["total_prize"] = existing.get("total_prize", 0) + review_result.get("total_prize", 0)
        existing["total_bet"] = existing.get("total_bet", 0) + review_result.get("total_bet", 0)
        existing["win_count"] = existing.get("win_count", 0) + review_result.get("win_count", 0)
        existing["total_wins"] = existing.get("total_wins", 0) + (1 if review_result.get("win_count", 0) > 0 else 0)
        existing["last_run"] = review_result.get("date", "")
        # 最佳奖级
        best = review_result.get("best_tier")
        if best and (existing.get("best_tier") is None or best < existing["best_tier"]):
            existing["best_tier"] = best
            existing["best_tier_name"] = review_result.get("best_tier_name", "")
    else:
        history.append({
            "strategy": strategy,
            "total_runs": 1,
            "total_prize": review_result.get("total_prize", 0),
            "total_bet": review_result.get("total_bet", 0),
            "win_count": review_result.get("win_count", 0),
            "total_wins": 1 if review_result.get("win_count", 0) > 0 else 0,
            "best_tier": review_result.get("best_tier"),
            "best_tier_name": review_result.get("best_tier_name", ""),
            "last_run": review_result.get("date", ""),
            "first_run": review_result.get("date", ""),
        })

    save_performance_history(history)


def get_strategy_performance():
    """获取策略表现汇总"""
    history = load_performance_history()
    result = []
    for h in history:
        runs = h.get("total_runs", 0)
        roi = 0.0
        if h.get("total_bet", 0) > 0:
            roi = h.get("total_prize", 0) / h["total_bet"] * 100
        win_rate = h.get("win_count", 0) / runs * 100 if runs > 0 else 0
        result.append({
            "strategy": h["strategy"],
            "total_runs": runs,
            "win_rate": round(win_rate, 2),
            "total_prize": h.get("total_prize", 0),
            "total_bet": h.get("total_bet", 0),
            "roi": round(roi, 2),
            "best_tier": h.get("best_tier"),
            "best_tier_name": h.get("best_tier_name", ""),
            "last_run": h.get("last_run", ""),
        })
    result.sort(key=lambda x: x["roi"], reverse=True)
    return result


def format_review(review_result):
    """格式化输出复盘结果"""
    lines = ["📊 复盘结果"]
    lines.append("=" * 50)
    lines.append(f"日期: {review_result.get('date', '')} {review_result.get('time', '')}")
    lines.append(f"策略: {review_result.get('strategy', '')}")

    # 开奖号码
    front_str = " ".join(f"{n:02d}" for n in review_result.get("draw_front", []))
    back_str = " ".join(f"{n:02d}" for n in review_result.get("draw_back", []))
    lines.append(f"开奖号码: {front_str} + {back_str}")
    lines.append("")

    # 逐注对比
    buy_count = review_result.get("buy_count", 0)
    for i, r in enumerate(review_result.get("results", [])):
        is_buy = i < buy_count
        tag = "BUY" if is_buy else "WATCH"
        front = r.get("front", [])
        back = r.get("back", [])
        if front and back:
            front_str = " ".join(f"{n:02d}" for n in front)
            back_str = " ".join(f"{n:02d}" for n in back)
            lines.append(f"[{tag}] #{i+1}: {front_str} + {back_str}")
        else:
            lines.append(f"[{tag}] #{i+1}:")
        lines.append(f"  前区 {r['front_hit']}/5, 后区 {r['back_hit']}/2")
        if r["tier"]:
            lines.append(f"  🎉 {r['tier_name']} - ¥{r['prize']:,}")
        else:
            lines.append(f"  ❌ 未中奖")
        lines.append("")

    # 汇总
    lines.append(f"总奖金: ¥{review_result.get('total_prize', 0):,}")
    lines.append(f"中奖注数: {review_result.get('win_count', 0)}/{len(review_result.get('results', []))}")
    lines.append(f"投注成本: ¥{review_result.get('total_bet', 0):,}")
    if review_result.get('total_bet', 0) > 0:
        roi = review_result.get('total_prize', 0) / review_result['total_bet'] * 100
        lines.append(f"回报率: {roi:.2f}%")

    if review_result.get("best_tier"):
        lines.append(f"最佳: {review_result['best_tier_name']}")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="大乐透复盘")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--performance", action="store_true", help="显示策略表现")
    args = parser.parse_args()

    if args.performance:
        perf = get_strategy_performance()
        if args.json:
            print(json.dumps(perf, ensure_ascii=False, indent=2))
        else:
            print("📊 策略表现汇总")
            print("=" * 50)
            for p in perf:
                print(f"  {p['strategy']:12s} | 运行 {p['total_runs']:3d} 次 | "
                      f"中奖率 {p['win_rate']:5.1f}% | "
                      f"ROI {p['roi']:+.1f}% | "
                      f"最佳: {p['best_tier_name']}")
    else:
        result = review()
        if "error" in result:
            print(f"错误: {result['error']}")
            exit(1)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_review(result))
