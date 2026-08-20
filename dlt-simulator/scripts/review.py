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


def load_current_prediction(issue=None):
    """加载预测（默认按期号读取冻结快照）

    Args:
        issue: 期号；None 则读取最近未复盘的一期冻结快照
    """
    predictions_dir = DATA_DIR / "predictions"
    if predictions_dir.exists():
        if issue:
            path = predictions_dir / f"{issue}.json"
            return load_json(path)
        # 无期号：按文件名降序取最新
        files = sorted(predictions_dir.glob("*.json"), reverse=True)
        for f in files:
            pred = load_json(f)
            if pred:
                return pred
    # 回退：旧版 current_prediction.json（兼容）
    return load_json(DATA_DIR / "current_prediction.json")


def load_performance_history():
    """加载各策略版本表现历史（按策略+版本隔离）

    返回 dict：{"strategies": {f"{name}_v{version}": {...}}}
    """
    data = load_json(STRATEGY_DIR / "performance_history.json")
    if isinstance(data, dict) and "strategies" in data:
        return data
    # 兼容旧版 list 结构，迁移为按版本隔离
    if isinstance(data, list):
        migrated = {"strategies": {}}
        for item in data:
            key = f"{item.get('strategy', 'balanced')}_{item.get('version', 1)}"
            migrated["strategies"][key] = {
                "name": item.get("strategy", "balanced"),
                "version": item.get("version", 1),
                "total_runs": item.get("total_runs", 0),
                "success": item.get("success", 0),
                "fail": item.get("fail", 0),
                "tie": item.get("tie", 0),
                "win_count": item.get("win_count", 0),
                "total_wins": item.get("total_wins", 0),
                "best_tier": item.get("best_tier"),
                "best_tier_name": item.get("best_tier_name", ""),
                "first_run": item.get("first_run", ""),
                "last_run": item.get("last_run", ""),
            }
        save_performance_history(migrated)
        return migrated
    return {"strategies": {}}


def save_performance_history(history):
    """保存各策略版本表现历史"""
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

    # 3. 检查预测是否针对本期（硬性条件，防期号错配污染数据）
    pred_issue = prediction.get("issue", "")
    draw_issue = latest.get("issue", "")

    # 数据完整性：预测期号必须与最新开奖期号一致，否则禁止复盘（REVIEW_PENDING），
    # 不对比、不更新策略、不写 win_count/performance —— 防止“拿上期开奖对比本期预测”污染实验数据。
    if pred_issue and draw_issue and str(pred_issue).strip() != str(draw_issue).strip():
        return {
            "error": "期号不匹配，跳过复盘（REVIEW_PENDING）",
            "prediction_issue": pred_issue,
            "draw_issue": draw_issue,
            "status": "REVIEW_PENDING",
            "reason": "预测期号(%s) != 最新开奖期号(%s)，可能因数据源延迟/抓取异常/时机问题"
                       % (pred_issue, draw_issue),
        }

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

    # 计算 Top-2 Selection：SUCCESS / FAIL / TIE
    top2 = _calc_top2_selection(review_result)
    review_result["top2_selection"] = top2  # "SUCCESS" | "FAIL" | "TIE"
    review_result["top2_selection_success"] = top2 == "SUCCESS"

    save_json(filepath, review_result)

    # 8. 更新策略表现（含 SUCCESS/FAIL/TIE + 隔离统计）
    # 无效复盘（空结果）不进入策略统计
    if top2 != "REVIEW_INVALID":
        _update_performance(review_result)

        # 9. 自动策略评估闭环（KEEP / ADJUST / REVERT → 更新 current_strategy.json）
        strategy_result = _run_strategy_loop(review_result)
        review_result["strategy_evaluation"] = strategy_result
    else:
        review_result["strategy_evaluation"] = {
            "action": "SKIP",
            "reason": "复盘结果为空，判定本次无效，不进入策略统计",
        }

    return review_result


def _calc_top2_selection(review_result):
    """
    计算 Top-2 Selection 三态结果

    定义（沿用统一 performance_rank）：模型 Top 2（BUY）是否包含本期 10 组中最佳表现组合。

    Returns:
        str: "SUCCESS"（Top2 含唯一/并列最佳）| "FAIL"（Top2 无最佳）| "TIE"（10 组表现完全相同）
    """
    from prize_checker import performance_key
    results = review_result.get("results")
    buy_count = review_result.get("buy_count", 2)

    # 空结果 / 结果数不足 → 无效复盘，不进入 TIE/SUCCESS/FAIL 判定（避免污染实验数据）
    if not results or len(results) < buy_count:
        return "REVIEW_INVALID"

    # 每组统一表现键（奖级优先 → 前区命中 → 后区命中）
    keys = [performance_key(r["tier"], r["front_hit"], r["back_hit"]) for r in results]

    # 若 10 组表现完全相同 → TIE（模型没有选错，本期无差异）
    if len(set(keys)) == 1:
        return "TIE"

    # 最佳表现键
    best_key = max(keys)
    # Top 2（BUY）是否包含任一最佳组合
    if any(keys[i] == best_key for i in range(buy_count)):
        return "SUCCESS"
    return "FAIL"


def _run_strategy_loop(review_result):
    """
    自动策略闭环：根据复盘表现评估策略，KEEP/ADJUST/REVERT 并更新 current_strategy.json
    """
    try:
        from strategy_manager import (
            load_current_strategy, save_current_strategy,
            save_strategy_snapshot, evaluate_strategy, adjust_strategy
        )
        strategy = load_current_strategy()

        # 累计各策略表现（含 Top-2 指标）由 _update_performance 更新，这里评估当前策略
        history = load_performance_history()
        current_strategy_name = review_result.get("strategy", strategy.get("name", "balanced"))
        current_version = strategy.get("version", 1)
        key = f"{current_strategy_name}_v{current_version}"
        perf = history["strategies"].get(key, {})

        s = perf.get("success", 0)
        f = perf.get("fail", 0)
        sel_acc = perf.get("selection_accuracy", 0)
        perf_data = {
            "total_runs": perf.get("total_runs", 0),
            "win_rate": (perf.get("total_wins", 0) / perf.get("total_runs", 1)) * 100 if perf.get("total_runs", 0) > 0 else 0,
        }
        eval_result = evaluate_strategy(strategy, perf_data)
        action = eval_result.get("action", "KEEP")

        if action == "KEEP":
            # 更新当前策略表现（含 Selection Accuracy 累计）
            perf_out = {
                "top2_accuracy": sel_acc,
                "any_accuracy": 0.0,
                "total_runs": perf.get("total_runs", 0),
                "win_count": perf.get("win_count", 0),
                "success": s,
                "fail": f,
                "tie": perf.get("tie", 0),
            }
            strategy["performance"] = perf_out
            save_current_strategy(strategy)
        elif action == "ADJUST":
            save_strategy_snapshot(strategy, reason="auto_adjust_before")
            new_strategy = adjust_strategy(strategy, "auto")
            save_current_strategy(new_strategy)
            eval_result["new_version"] = new_strategy.get("version")
        elif action == "REVERT":
            save_strategy_snapshot(strategy, reason="auto_revert_before")
            from strategy_manager import revert_strategy
            reverted = revert_strategy()
            save_current_strategy(reverted)
            eval_result["new_version"] = reverted.get("version")

        return eval_result
    except Exception as e:
        return {"action": "ERROR", "reason": str(e)}


def _update_performance(review_result):
    """更新各策略版本表现数据（按策略+版本隔离，累计 SUCCESS/FAIL/TIE）"""
    strategy = review_result.get("strategy", "balanced")
    # 策略版本：从 strategy_evaluation 或 current_strategy 读取当前版本
    version = review_result.get("strategy_version", None) or _current_strategy_version(strategy)
    key = f"{strategy}_v{version}"

    history = load_performance_history()
    strategies = history["strategies"]
    existing = strategies.get(key)

    sel = review_result.get("top2_selection", "TIE")
    if existing:
        existing["total_runs"] = existing.get("total_runs", 0) + 1
        existing["success"] = existing.get("success", 0) + (1 if sel == "SUCCESS" else 0)
        existing["fail"] = existing.get("fail", 0) + (1 if sel == "FAIL" else 0)
        existing["tie"] = existing.get("tie", 0) + (1 if sel == "TIE" else 0)
        s = existing.get("success", 0)
        f = existing.get("fail", 0)
        existing["selection_accuracy"] = round(s / (s + f), 4) if (s + f) > 0 else 0.0
        existing["win_count"] = existing.get("win_count", 0) + review_result.get("win_count", 0)
        existing["total_wins"] = existing.get("total_wins", 0) + (1 if review_result.get("win_count", 0) > 0 else 0)
        existing["last_run"] = review_result.get("date", "")
        best = review_result.get("best_tier")
        if best and (existing.get("best_tier") is None or best < existing["best_tier"]):
            existing["best_tier"] = best
            existing["best_tier_name"] = review_result.get("best_tier_name", "")
    else:
        strategies[key] = {
            "name": strategy,
            "version": version,
            "total_runs": 1,
            "success": 1 if sel == "SUCCESS" else 0,
            "fail": 1 if sel == "FAIL" else 0,
            "tie": 1 if sel == "TIE" else 0,
            "selection_accuracy": 1.0 if sel == "SUCCESS" else 0.0,
            "win_count": review_result.get("win_count", 0),
            "total_wins": 1 if review_result.get("win_count", 0) > 0 else 0,
            "best_tier": review_result.get("best_tier"),
            "best_tier_name": review_result.get("best_tier_name", ""),
            "first_run": review_result.get("date", ""),
            "last_run": review_result.get("date", ""),
        }

    save_performance_history(history)
    return key


def _current_strategy_version(strategy_name):
    """读取当前运行策略的版本号（用于隔离统计）"""
    try:
        from strategy_manager import load_current_strategy
        st = load_current_strategy()
        if st.get("name") == strategy_name:
            return st.get("version", 1)
    except Exception:
        pass
    return 1


def get_strategy_performance():
    """获取各策略版本表现汇总（按版本隔离）"""
    history = load_performance_history()
    result = []
    for key, h in history["strategies"].items():
        runs = h.get("total_runs", 0)
        s = h.get("success", 0)
        f = h.get("fail", 0)
        sel_acc = h.get("selection_accuracy", 0)
        win_rate = h.get("total_wins", 0) / runs * 100 if runs > 0 else 0
        result.append({
            "strategy": h.get("name", key),
            "version": h.get("version", 1),
            "total_runs": runs,
            "success": s,
            "fail": f,
            "tie": h.get("tie", 0),
            "selection_accuracy": round(sel_acc * 100, 2) if sel_acc else 0.0,
            "win_rate": round(win_rate, 2),
            "best_tier": h.get("best_tier"),
            "best_tier_name": h.get("best_tier_name", ""),
            "first_run": h.get("first_run", ""),
            "last_run": h.get("last_run", ""),
        })
    result.sort(key=lambda x: x["selection_accuracy"], reverse=True)
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

    if review_result.get("best_tier"):
        lines.append(f"最佳: {review_result['best_tier_name']}")

    # Top-2 Selection 三态
    sel = review_result.get("top2_selection")
    if sel:
        lines.append(f"Top-2 Selection: {sel}")

    # 策略自动评估
    se = review_result.get("strategy_evaluation")
    if se:
        action = se.get("action", "?")
        lines.append(f"策略评估: {action} | {se.get('reason', '')}")

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
                print(f"  {p['strategy']} v{p['version']:2d} | 运行 {p['total_runs']:3d} 次 | "
                      f"S/F/T  {p['success']}/{p['fail']}/{p['tie']} | "
                      f"Sel-Acc {p['selection_accuracy']:5.1f}% | "
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
