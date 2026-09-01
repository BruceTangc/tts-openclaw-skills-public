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

# Balanced 自动调参约束（保守区间 + 单步长）。
# 只改 Balanced.compute_weights() 实际读取的参数；balanced_max_total_adjust
# 原则上不自动频繁改（除非有充分统计证据），故默认步长 0。
_BALANCED_PARAM_STEPS = {
    "balanced_hot_adjust": 0.01,
    "balanced_cold_adjust": 0.01,
    "balanced_trend_adjust": 0.01,
    "balanced_omission_adjust": 0.01,
    "balanced_max_total_adjust": 0.0,   # 默认不动，需显式证据
    "exposure_penalty_coef": 0.005,
}
# 保守参数范围（可配置不散落硬编码）
_BALANCED_PARAM_RANGES = {
    "balanced_hot_adjust": (0.00, 0.12),
    "balanced_cold_adjust": (0.00, 0.15),
    "balanced_trend_adjust": (0.00, 0.10),
    "balanced_omission_adjust": (0.00, 0.15),
    "balanced_max_total_adjust": (0.00, 0.25),  # 界上限，但默认步长0避免频繁改
    "exposure_penalty_coef": (0.00, 0.08),
}

# 归因样本阈值：样本 < 此值时禁止据此自动调参（标注 INSUFFICIENT_DATA）
ATTRIBUTION_MIN_SAMPLE = 30

# 归因 effect 与可调 Balanced 参数的映射（effect 名 → 参数名）
_BALANCED_EFFECT_PARAM = {
    "hot_effect": "balanced_hot_adjust",
    "cold_effect": "balanced_cold_adjust",
    "trend_effect": "balanced_trend_adjust",
    "omission_effect": "balanced_omission_adjust",
    "exposure_penalty_effect": "exposure_penalty_coef",
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


def _significance_block(success, fail, tie):
    """对 SUCCESS/FAIL（TIE 不计入 n）做 p0=0.20 的 exact binomial 检验。

    替代旧的固定阈值：RANDOM_TOP2_BASELINE / SIGNIFICANT_MARGIN / under_random=top2_acc<0.1。
    """
    from stat_rigor import significance_vs_random
    return significance_vs_random(success, fail, p0=RANDOM_TOP2_BASELINE, tie=tie)


def evaluate_strategy(strategy, performance_data):
    """
    评估策略表现，决定操作：KEEP / ADJUST / REVERT（exact binomial vs p=0.20）

    Args:
        strategy: 当前策略
        performance_data: 策略表现数据（含 success/fail/tie 或由 total_runs/top2_accuracy 折算）

    Returns:
        dict: {
            "action": "KEEP" | "ADJUST" | "REVERT",
            "reason": str,
            "details": dict,
            "significance": dict,   # exact binomial 检验结果
        }
    """
    total_runs = performance_data.get("total_runs", 0)
    top2_acc = performance_data.get("top2_accuracy", 0)
    win_rate = performance_data.get("win_rate", 0)
    roi = performance_data.get("roi", 0)

    # 从 performance_data 中优先取 SUCCESS/FAIL/TIE（评审按 prediction version 记账后可直接提供）
    success = performance_data.get("success", None)
    fail = performance_data.get("fail", None)
    tie = performance_data.get("tie", 0)

    if success is not None and fail is not None:
        sig = _significance_block(success, fail, tie)
        n_valid = sig["valid_samples"]
    else:
        # 兼容旧调用方（仅给 total_runs/top2_accuracy）：把 top2_acc 折算成 success
        n_valid = int(total_runs)
        est_success = int(round(top2_acc * n_valid))
        est_fail = n_valid - est_success
        sig = _significance_block(est_success, est_fail, 0)
        # 真实 SUCCESS/FAIL 仅在 review 提供时可用
        sig["success"] = est_success
        sig["fail"] = est_fail
        sig["tie"] = tie

    observed = sig["observed_top2_accuracy"]
    p_value = sig["p_value"]
    alpha = 0.05

    # 样本不足，保持（不触发任何调整）
    if n_valid < MIN_SAMPLE:
        return {
            "action": "KEEP",
            "reason": f"样本不足（{n_valid}/{MIN_SAMPLE}），继续观察",
            "details": {"valid_samples": n_valid, "required": MIN_SAMPLE},
            "significance": sig,
        }

    significantly_below = sig["significantly_below_random"]

    # REVERT：达标长期观察 且 显著低于随机（p<0.01）且绝对水平很低
    if n_valid >= CONFIRM_SAMPLE and p_value < 0.01 and observed < RANDOM_TOP2_BASELINE * 0.5:
        return {
            "action": "REVERT",
            "reason": (f"exact binomial 判定长期显著低于随机基线：Top-2 Acc={observed*100:.2f}% "
                        f"(随机基线≈{RANDOM_TOP2_BASELINE*100:.0f}%, p={p_value:.4f}<0.01)，建议回退"),
            "details": {
                "top2_accuracy": observed, "roi": roi, "win_rate": win_rate,
                "random_baseline": RANDOM_TOP2_BASELINE, "valid_samples": n_valid,
            },
            "significance": sig,
        }

    # ADJUST：达标调整样本 且 显著低于随机（p<0.05）
    if n_valid >= ADJUST_SAMPLE and p_value < alpha and significantly_below:
        return {
            "action": "ADJUST",
            "reason": (f"exact binomial 判定显著低于随机基线：Top-2 Acc={observed*100:.2f}% "
                        f"(随机基线≈{RANDOM_TOP2_BASELINE*100:.0f}%, p={p_value:.4f}<{alpha})"),
            "details": {
                "top2_accuracy": observed, "roi": roi, "win_rate": win_rate,
                "random_baseline": RANDOM_TOP2_BASELINE, "valid_samples": n_valid,
            },
            "significance": sig,
        }

    # 默认 KEEP：达标样本但不显著差 / 未达调整阈值
    return {
        "action": "KEEP",
        "reason": (f"表现正常/中性或不显著：Top-2 Acc={observed*100:.2f}% "
                    f"(随机基线≈{RANDOM_TOP2_BASELINE*100:.0f}%, p={p_value:.4f})，{n_valid}次运行"),
        "details": {
            "top2_accuracy": observed, "roi": roi, "win_rate": win_rate,
            "random_baseline": RANDOM_TOP2_BASELINE, "valid_samples": n_valid,
        },
        "significance": sig,
    }


def _clamp_param(value, pmin, pmax):
    return max(pmin, min(pmax, value))


def _select_effect_targets(attribution, strategy):
    """从归因结果选出本次最多改 1~2 个 Balanced 参数（数据驱动，不拍脑袋）。

    规则：
      - 只有 sample_count >= ATTRIBUTION_MIN_SAMPLE 且非 INSUFFICIENT_DATA 的 effect 可入选。
      - 按“表现差于随机”的方向性（负向 effect）排序，优先调负向最重的 effect。
      - 负向 effect → 小步减弱（direction = -1）；无充分证据 → 不动。绝不因表现差而调大参数。
      - 每个 effect 对应一个 balanced_* 参数；balanced_max_total_adjust 默认步长0且
        除非有充分统计证据否则不选。
      - 多个 effect 同现标记 confounded=True（不假装完全分离因果）。

    Args:
        attribution: dict，形如 {"hot_effect": {...}, ...}，每项含
                     sample_count / top2_success_rate（或 mean_front_hit/mean_back_hit）
        strategy: 当前策略（用于读现状参数）

    Returns:
        list[(param_name, direction)]：direction in (+1, -1)，升序列出候选
    """
    candidates = []
    for effect, param in _BALANCED_EFFECT_PARAM.items():
        info = (attribution or {}).get(effect) or {}
        if not info:
            continue
        if info.get("status") == "INSUFFICIENT_DATA" or info.get("sample_count", 0) < ATTRIBUTION_MIN_SAMPLE:
            continue
        # 仅当该 effect 有实际样本时才考虑；这里不做复杂因果，只用方向性：
        # top2_success_rate 明显低于随机基线(0.20)时，对应的参数需要调整。
        rate = info.get("top2_success_rate")
        if rate is None:
            continue
        if rate < RANDOM_TOP2_BASELINE * 0.7:  # 明显跑不赢随机才触发方向
            # 负向 effect → 小步减弱（减弱对应 heuristic 修正的权重），绝不要调大。
            # 若要未来支持正向加强，必须另立独立的正向统计证据规则；本轮不加。
            candidates.append((param, -1))
    # 最多选 2 个：按 effect 顺序去重，避免一次全面漂移
    selected = []
    seen = set()
    for param, direction in candidates:
        if param in seen:
            continue
        seen.add(param)
        selected.append((param, direction))
        if len(selected) >= 2:
            break
    return selected


def adjust_strategy(strategy, adjustment_type="auto", attribution=None):
    """
    调整策略参数（按 strategy.name 分支，Balanced 只改 Balanced 真正使用的参数）

    - hot/cold/trend + hot_boost/cold_boost/trend_boost/balance：沿用旧逻辑。
    - strategy.name == balanced + "auto"：**不得只改 hot_weight**。必须只调整
      compute_weights() 实际读取的 balanced_* / exposure_penalty_coef，且由数据驱动
      （attribution result → 选 effect → 小步 patch），小步/带上下限/可回退/最多1~2个。

    Args:
        strategy: 当前策略
        adjustment_type: "auto" | "hot_boost" | "cold_boost" | "trend_boost" | "balance"
        attribution: 归因汇总（仅 balanced auto 用）。若为空/样本不足则退化为稳定化
                     (nudge 到更保守区间)而非乱调。

    Returns:
        dict: 调整后的策略
    """
    new_strategy = {**strategy}
    name = new_strategy.get("name", "balanced")
    new_strategy["version"] = strategy.get("version", 1) + 1
    new_strategy["params"] = {**strategy.get("params", {})}

    params = new_strategy["params"]

    # Balanced 的分支：auto 只调 Balanced 真正使用的参数，不碰 hot_weight
    if name == "balanced" and adjustment_type == "auto":
        patches = _select_effect_targets(attribution, strategy)
        changed = []
        adjustments = []
        for param, direction in patches:
            lo, hi = _BALANCED_PARAM_RANGES.get(param, (0.0, 1.0))
            step = _BALANCED_PARAM_STEPS.get(param, 0.01)
            if step <= 0:
                continue  # 默认不动 balanced_max_total_adjust
            cur = float(params.get(param, _BALANCED_PARAM_DEFAULTS.get(param, 0.0)))
            new_val = _clamp_param(cur + direction * step, lo, hi)
            if abs(new_val - cur) > 1e-12:
                params[param] = round(new_val, 4)
                changed.append(param)
                adjustments.append({"param": param, "from": round(cur, 4), "to": new_val})
        new_strategy["params"] = params
        new_strategy["status"] = "active"
        new_strategy["last_adjustment"] = {
            "reason": "balanced auto adjust (exact binomial 显著低于随机 + 归因驱动)",
            "changed": changed,
            "adjustments": adjustments,
            "timestamp": datetime.now().isoformat(),
        }
        new_strategy["adjustment_log"] = new_strategy.get("adjustment_log", []) + [adjustments]
        return new_strategy

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
        # 非 balanced 的 auto（hot/cold/trend）：沿用旧逻辑（只改 legacy 权重）
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
