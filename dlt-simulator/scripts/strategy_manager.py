#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strategy_manager.py — 策略管理模块

策略版本管理：KEEP / ADJUST / REVERT
核心指标：Top-2 Selection Accuracy
"""
import json
from datetime import datetime
from pathlib import Path

from common import load_config, load_json, save_json, STRATEGY_DIR

cfg = load_config()
MIN_SAMPLE = cfg["min_strategy_sample"]
ADJUST_SAMPLE = cfg["adjust_strategy_sample"]
CONFIRM_SAMPLE = cfg["confirm_strategy_sample"]

# 随机基线：Top2(2组) 从 10 组预测里随机选出，命中唯一最佳组合的概率 ≈ buy_count/prediction_count = 2/10 = 0.2
RANDOM_TOP2_BASELINE = 0.2
# 显著差判定容差：top2_acc 低于随机基线的 (1 - SIGNIFICANT_MARGIN) 倍才算"跑不赢随机"
SIGNIFICANT_MARGIN = 0.5

STRATEGY_FILE = STRATEGY_DIR / "current_strategy.json"
HISTORY_DIR = STRATEGY_DIR / "strategy_history"


# balanced 弱修正参数默认值（从 config 回退；策略 params 可覆盖）
_BALANCED_PARAM_DEFAULTS = {
    "balanced_hot_adjust": 0.06,
    "balanced_cold_adjust": 0.08,
    "balanced_trend_adjust": 0.05,
    "balanced_omission_adjust": 0.10,
    "balanced_max_total_adjust": 0.20,
    "exposure_penalty_coef": 0.04,
}


def default_strategy_params():
    """返回默认策略参数（含 balanced 弱修正参数，值从 config 回退）。"""
    params = {
        "hot_weight": 1.5,
        "cold_weight": 1.0,
        "trend_weight": 0.5,
        "omission_bonus": 1.0,
    }
    for k, default in _BALANCED_PARAM_DEFAULTS.items():
        params[k] = cfg.get(k, default)
    return params


def get_generator_params(strategy=None):
    """解析生成器实际使用的策略参数（闭环入口）。

    从当前策略 params 取值，缺失的字段回退到 config 默认值。这样
    hot_weight/cold_weight/trend_weight/omission_bonus 以及 balanced_*_adjust
    都能真正传入 generator.compute_weights / score_candidate，任何 adjust 后
    新参数都会影响后续生成。

    Args:
        strategy: 策略对象（None 则加载当前策略）

    Returns:
        dict: 完整的生成器参数
    """
    if strategy is None:
        strategy = load_current_strategy()
    params = dict(strategy.get("params", {}) or {})
    defaults = default_strategy_params()
    for k, default in defaults.items():
        params.setdefault(k, default)
    return params


def load_current_strategy():
    """加载当前策略"""
    data = load_json(STRATEGY_FILE)
    if data:
        # 补齐缺失的 balanced 弱修正参数（向后兼容旧策略文件）
        data.setdefault("params", {})
        for k, default in default_strategy_params().items():
            data["params"].setdefault(k, default)
        return data
    # 默认策略
    default = {
        "name": "balanced",
        "version": 1,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "status": "active",
        "params": default_strategy_params(),
        "performance": {
            "top2_accuracy": 0.0,
            "any_accuracy": 0.0,
            "total_runs": 0,
            "win_count": 0,
        },
    }
    save_json(STRATEGY_FILE, default)
    return default


def save_current_strategy(strategy):
    """保存当前策略"""
    strategy["updated"] = datetime.now().isoformat()
    save_json(STRATEGY_FILE, strategy)


def save_strategy_snapshot(strategy, reason="snapshot"):
    """保存策略快照（用于历史回溯）"""
    HISTORY_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{strategy['name']}_v{strategy['version']}_{timestamp}.json"
    filepath = HISTORY_DIR / filename
    data = {**strategy, "snapshot_reason": reason, "snapshot_time": datetime.now().isoformat()}
    save_json(filepath, data)
    return filepath


def evaluate_strategy(strategy, performance_data):
    """
    评估策略表现，决定操作：KEEP / ADJUST / REVERT

    Args:
        strategy: 当前策略
        performance_data: 策略表现数据

    Returns:
        dict: {
            "action": "KEEP" | "ADJUST" | "REVERT",
            "reason": str,
            "details": dict
        }
    """
    total_runs = performance_data.get("total_runs", 0)
    top2_acc = performance_data.get("top2_accuracy", 0)
    win_rate = performance_data.get("win_rate", 0)
    roi = performance_data.get("roi", 0)

    # 样本不足，保持（不触发任何调整）
    if total_runs < MIN_SAMPLE:
        return {
            "action": "KEEP",
            "reason": f"样本不足（{total_runs}/{MIN_SAMPLE}），继续观察",
            "details": {"runs": total_runs, "required": MIN_SAMPLE},
        }

    # 显著差阈值：Top-2 准确性严格低于随机基线（含容差）才算"跑不赢随机"
    # 只有在此前提下，跑满阈值次数才可能 ADJUST/REVERT，杜绝"跑满次数就无条件调"
    under_random = top2_acc < RANDOM_TOP2_BASELINE * (1 - SIGNIFICANT_MARGIN)

    # REVERT：达标长期观察且显著低于随机（且绝对水平很低）→ 回退到默认
    if total_runs >= CONFIRM_SAMPLE and under_random and top2_acc < 0.05:
        return {
            "action": "REVERT",
            "reason": (f"长期表现显著低于随机基线：Top-2 Acc={top2_acc*100:.2f}% "
                        f"(随机基线≈{RANDOM_TOP2_BASELINE*100:.0f}%)，ROI={roi:.1f}%，建议回退到默认策略"),
            "details": {
                "top2_accuracy": top2_acc, "roi": roi, "win_rate": win_rate,
                "random_baseline": RANDOM_TOP2_BASELINE, "total_runs": total_runs,
            },
        }

    # ADJUST：达标调整样本且显著低于随机基线 → 才调整（不再"跑满次数就无条件调"）
    if total_runs >= ADJUST_SAMPLE and under_random:
        return {
            "action": "ADJUST",
            "reason": (f"表现显著低于随机基线：Top-2 Acc={top2_acc*100:.2f}% "
                        f"(随机基线≈{RANDOM_TOP2_BASELINE*100:.0f}%)，ROI={roi:.1f}%，建议调整策略"),
            "details": {
                "top2_accuracy": top2_acc, "roi": roi, "win_rate": win_rate,
                "random_baseline": RANDOM_TOP2_BASELINE, "total_runs": total_runs,
            },
        }

    # 默认 KEEP：达标样本但不显著差 / 未达调整阈值，保持观察
    return {
        "action": "KEEP",
        "reason": (f"表现正常/中性：Top-2 Acc={top2_acc*100:.2f}% "
                    f"(随机基线≈{RANDOM_TOP2_BASELINE*100:.0f}%)，ROI={roi:.1f}%，{total_runs}次运行"),
        "details": {
            "top2_accuracy": top2_acc, "roi": roi, "win_rate": win_rate,
            "random_baseline": RANDOM_TOP2_BASELINE, "total_runs": total_runs,
        },
    }


def adjust_strategy(strategy, adjustment_type="auto"):
    """
    调整策略参数

    Args:
        strategy: 当前策略
        adjustment_type: 调整类型

    Returns:
        dict: 调整后的策略
    """
    new_strategy = {**strategy}
    new_strategy["version"] = strategy.get("version", 1) + 1
    new_strategy["params"] = {**strategy.get("params", {})}

    params = new_strategy["params"]

    if adjustment_type == "hot_boost":
        params["hot_weight"] = min(3.0, params.get("hot_weight", 1.5) + 0.3)
        params["cold_weight"] = max(0.5, params.get("cold_weight", 1.0) - 0.2)
    elif adjustment_type == "cold_boost":
        params["cold_weight"] = min(3.0, params.get("cold_weight", 1.0) + 0.3)
        params["hot_weight"] = max(0.5, params.get("hot_weight", 1.5) - 0.2)
    elif adjustment_type == "trend_boost":
        params["trend_weight"] = min(2.0, params.get("trend_weight", 0.5) + 0.3)
    elif adjustment_type == "balance":
        # 重置为默认参数（含 balanced 弱修正参数，从 config 回退）
        for k, v in default_strategy_params().items():
            params[k] = v
    elif adjustment_type == "auto":
        # 自动调整：根据表现数据决定
        perf = strategy.get("performance", {})
        if perf.get("top2_accuracy", 0) < 0.005:
            params["hot_weight"] = min(3.0, params.get("hot_weight", 1.5) + 0.2)

    new_strategy["params"] = params
    new_strategy["status"] = "active"
    return new_strategy


def revert_strategy(target_version=None):
    """
    回退策略到历史版本

    Args:
        target_version: 目标版本号，None则回退到上一版本

    Returns:
        dict: 回退后的策略
    """
    current = load_current_strategy()
    current_version = current.get("version", 1)

    if target_version is None:
        target_version = current_version - 1

    if target_version < 1:
        return current

    # 查找历史快照
    HISTORY_DIR.mkdir(exist_ok=True)
    snapshots = sorted(HISTORY_DIR.glob(f"{current['name']}_v{target_version}_*.json"))
    if not snapshots:
        return current

    # 加载最新的目标版本快照
    snapshot = load_json(snapshots[-1])
    if snapshot:
        snapshot["version"] = current_version + 1
        snapshot["reverted_from"] = current_version
        snapshot["revert_time"] = datetime.now().isoformat()
        snapshot["status"] = "active"
        return snapshot

    return current


def get_strategy_history():
    """获取策略变更历史"""
    HISTORY_DIR.mkdir(exist_ok=True)
    snapshots = sorted(HISTORY_DIR.glob("*.json"))
    history = []
    for s in snapshots:
        data = load_json(s)
        if data:
            history.append({
                "file": s.name,
                "name": data.get("name", ""),
                "version": data.get("version", 0),
                "reason": data.get("snapshot_reason", ""),
                "time": data.get("snapshot_time", ""),
            })
    return history


def format_strategy(strategy):
    """格式化输出策略信息"""
    lines = ["📋 当前策略"]
    lines.append("=" * 40)
    lines.append(f"名称: {strategy.get('name', '')}")
    lines.append(f"版本: v{strategy.get('version', 1)}")
    lines.append(f"状态: {strategy.get('status', '')}")
    lines.append(f"更新: {strategy.get('updated', '')}")
    lines.append("")

    params = strategy.get("params", {})
    lines.append("参数:")
    for k, v in params.items():
        lines.append(f"  {k}: {v}")

    perf = strategy.get("performance", {})
    if perf:
        lines.append("")
        lines.append("表现:")
        lines.append(f"  Top-2 Accuracy: {perf.get('top2_accuracy', 0)*100:.2f}%")
        lines.append(f"  运行次数: {perf.get('total_runs', 0)}")
        lines.append(f"  中奖次数: {perf.get('win_count', 0)}")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="策略管理")
    parser.add_argument("--show", action="store_true", help="显示当前策略")
    parser.add_argument("--adjust", choices=["hot_boost", "cold_boost", "trend_boost", "balance", "auto"])
    parser.add_argument("--revert", type=int, nargs="?", const=0, help="回退到指定版本")
    parser.add_argument("--history", action="store_true", help="显示策略历史")
    parser.add_argument("--snapshot", action="store_true", help="保存当前快照")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    strategy = load_current_strategy()

    if args.show or not any([args.adjust, args.revert, args.history, args.snapshot]):
        if args.json:
            print(json.dumps(strategy, ensure_ascii=False, indent=2))
        else:
            print(format_strategy(strategy))

    if args.adjust:
        save_strategy_snapshot(strategy, reason="before_adjust")
        strategy = adjust_strategy(strategy, args.adjust)
        save_current_strategy(strategy)
        print(f"策略已调整到 v{strategy['version']}")

    if args.revert is not None:
        target = args.revert if args.revert > 0 else None
        save_strategy_snapshot(strategy, reason="before_revert")
        strategy = revert_strategy(target)
        save_current_strategy(strategy)
        print(f"策略已回退到 v{strategy['version']}")

    if args.history:
        history = get_strategy_history()
        if args.json:
            print(json.dumps(history, ensure_ascii=False, indent=2))
        else:
            print("📜 策略历史")
            for h in history:
                print(f"  {h['time'][:19]} | {h['name']} v{h['version']} | {h['reason']}")

    if args.snapshot:
        path = save_strategy_snapshot(strategy, reason="manual")
        print(f"快照已保存: {path}")
