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
    DATA_DIR, STRATEGY_DIR,
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

# 大乐透年度末期号（据真实历史 2007-26094 统计）：每年实际期数不同，
# 跨年 = 当年期号达到该年“年末最后一期”的真实期号后，下一期跳到次年 001。
# 例：071503* 年不同 — 07年93期即终（07093→08001），08年154期（08154→09001）。
# 内嵌已观测年份的真实末期号；未观测年份（未来）按年份递增年份+1 期号归001。
_YEAR_END_ISSUE = {
    7: 93, 8: 154, 9: 153, 10: 153, 11: 154, 12: 154, 13: 153, 14: 154,
    15: 153, 16: 154, 17: 153, 18: 154, 19: 150, 20: 134, 21: 150, 22: 150,
    23: 150, 24: 152, 25: 150, 26: 94,
}
# 未观测年份的保守末期号参考值（未来年份，跨年点未知，用 150 兜底）
_DEFAULT_YEAR_END = 150


def compute_next_issue(latest_issue, latest_date=""):
    """计算下一期期号（年度期号 YYNNN，跨年由真实年度末期号决定，不简单 +1）。

    大乐透期号 5 位：YYNNN（年份后两位 + 当年期序号）。跨年规律（据真实数据）：
    当年期号达到该年实际末期号（07年93、08年154、24年152…）时，下一期进位到
    次年 001 —— 如 07093→08001、08154→09001、25150→26001。

    Args:
        latest_issue: 最新一期期号（标准 5 位 YYNNN）
        latest_date: 最新开奖日期（YYYY-MM-DD，可选，年份兜底）

    Returns:
        str: 下一期期号；无法解析返回 ""。
    """
    s = str(latest_issue or "").strip()

    # 标准 5 位年度期号
    if len(s) == 5 and s.isdigit():
        year = int(s[:2])
        num = int(s[2:])
        # 该年实际末期号（历史已知年份）或默认 150（未观测年份）
        year_end = _YEAR_END_ISSUE.get(year, _DEFAULT_YEAR_END)
        # 处于该年末期 → 跨年（年份 +1 取两位、期号归 001）
        if num >= year_end:
            return "%02d001" % ((year + 1) % 100)
        return "%02d%03d" % (year, num + 1)

    # 兜底一：日期提供年份，生成当年期号
    if latest_date:
        d = str(latest_date).strip()
        try:
            from datetime import datetime as _dt
            y = _dt.strptime(d[:10], "%Y-%m-%d").year % 100
            return _try_numeric_next(s, y)
        except Exception:
            pass

    # 兜底二：简单数值 +1
    if s.isdigit():
        return str(int(s) + 1)
    return ""


def _try_numeric_next(issue_str, year):
    """尝试把非 5 位期号按数值 +1，返回年度期号格式；失败则回退。"""
    try:
        num = int(issue_str)
        # 若当前值像“当年期号”（< _YEARLY_MAX_NUM），则包装成年度期号
        if num < _YEARLY_MAX_NUM:
            return "%02d%03d" % (year, num + 1)
        return str(num + 1)
    except (ValueError, TypeError):
        return ""


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

    # 8. 获取最新期号（跨年安全：年度期号 YYNNN 体系，不简单 +1）
    latest_issue = draws[0].get("issue", "") if draws else ""
    latest_date = draws[0].get("date", "") if draws else ""
    next_issue = compute_next_issue(latest_issue, latest_date)

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


PREDICTIONS_DIR = DATA_DIR / "predictions"


def save_prediction(prediction):
    """
    保存预测结果（按期号永久冻结，不可覆盖）

    保存位置：data/predictions/{issue}.json
    同一期号重复生成不会覆盖已有快照，保证 21:30 对比的是 18:00 冻结的 10 组。

    Returns:
        Path: 保存的文件路径
    """
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    issue = prediction.get("issue", "unknown")
    filepath = PREDICTIONS_DIR / f"{issue}.json"

    # 若该期号已有冻结快照，不覆盖（避免 18:00 任务重复执行时破坏不可变性）
    if filepath.exists():
        existing = load_json(filepath)
        if existing and existing.get("issue") == issue:
            return filepath

    save_json(filepath, prediction)

    # 顺带记录最新预测指针（仅用于快速定位，不作为唯一数据源）
    save_json(DATA_DIR / "latest_prediction_issue.json", {"issue": issue})

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
