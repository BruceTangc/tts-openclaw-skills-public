#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_strategy_learning_loop.py — 开奖后→策略学习→下一期真实生效的闭环修复测试

覆盖（严格按用户要求，不做架构重构/不新增预测模型/不改 Balanced 算法逻辑本身）：

1. Balanced ADJUST 后真正修改 balanced_* 参数（不再只改 hot_weight）
2. hot 策略 ADJUST 不误改 Balanced 参数
3. prediction 保存 strategy_version + strategy_params
4. review 按 prediction version 记账（不用 current_strategy.version 倒推历史）
5. SUCCESS/FAIL/TIE 中 TIE 不计入 binomial n
6. p=0.20 exact binomial baseline 正确
7. 样本不足不 ADJUST
8. 样本够但不显著不 ADJUST
9. 显著低于 random 才 ADJUST（exact binomial，非固定 <10%）
10. attribution 样本不足不调参
11. 每次最多改 1~2 个 Balanced 参数
12. 参数不越上下限
13. ADJUST→save→next prediction→新参数真实生效（完整闭环）
14. REVERT 可恢复旧版本
15. 历史 prediction 不受 current_strategy 后续变化污染

运行：
    cd scripts && python3 test_strategy_learning_loop.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import random
import tempfile
import shutil
from pathlib import Path

PASS = 0
FAIL = 0
FAILURES = []


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        FAILURES.append(name)
        print(f"  ❌ {name} {detail}")


print("=" * 66)
print("DLT 策略学习闭环修复测试")
print("=" * 66)

# 备份真实策略文件/表现历史，测试结束时恢复（保证测试不污染仓库运行时状态）
_real_strategy_file = None
_real_strategy_content = None
_real_perf_content = None
_strategy_file_path = None
_perf_path = None

def _backup_runtime_state():
    global _real_strategy_file, _real_strategy_content, _real_perf_content, _strategy_file_path, _perf_path
    import common
    _strategy_file_path = common.STRATEGY_DIR / "current_strategy.json"
    _perf_path = common.STRATEGY_DIR / "performance_history.json"
    if _strategy_file_path.exists():
        with open(_strategy_file_path, "r", encoding="utf-8") as f:
            _real_strategy_content = f.read()
    if _perf_path.exists():
        with open(_perf_path, "r", encoding="utf-8") as f:
            _real_perf_content = f.read()


def _restore_runtime_state():
    if _strategy_file_path is None:
        return
    try:
        if _real_strategy_content is None:
            if _strategy_file_path.exists():
                _strategy_file_path.unlink()
        else:
            _strategy_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_strategy_file_path, "w", encoding="utf-8") as f:
                f.write(_real_strategy_content)
        if _real_perf_content is None:
            if _perf_path.exists():
                _perf_path.unlink()
        else:
            _perf_path.parent.mkdir(parents=True, exist_ok=True)
            with open(_perf_path, "w", encoding="utf-8") as f:
                f.write(_real_perf_content)
    except Exception:
        pass


from strategy_manager import (
    MIN_SAMPLE, ADJUST_SAMPLE, CONFIRM_SAMPLE, RANDOM_TOP2_BASELINE,
    default_strategy_params, get_generator_params, adjust_strategy,
    evaluate_strategy, _select_effect_targets, _BALANCED_PARAM_RANGES,
    _BALANCED_PARAM_STEPS, ATTRIBUTION_MIN_SAMPLE, _BALANCED_EFFECT_PARAM,
)
from generator import compute_weights, generate_top_candidates, strategy_effects_for_draws, strategy_effects_for_candidate
from stat_rigor import exact_binomial_pmf, exact_binomial_lower_tail, significance_vs_random


def make_strategy(version=1, name="balanced", params=None):
    p = params or default_strategy_params()
    return {
        "name": name,
        "version": version,
        "created": "t", "updated": "t", "status": "active",
        "params": dict(p),
        "performance": {"top2_accuracy": 0.0, "any_accuracy": 0.0, "total_runs": 0, "win_count": 0},
    }


def ok_attr(**kw):
    """构造一个样本充足(>=ATTRIBUTION_MIN_SAMPLE)、状态 OK 的归因项，可覆盖 top2_success_rate。"""
    base = {"sample_count": ATTRIBUTION_MIN_SAMPLE + 10, "status": "OK",
            "mean_front_hit": 0.5, "mean_back_hit": 0.3}
    base.update(kw)
    return base


def bad_rates(**rates):
    """按 effect 名传入 top2_success_rate 构造归因（默认全部显著差于随机）。"""
    attr = {}
    for eff in ["hot_effect", "cold_effect", "trend_effect", "omission_effect", "exposure_penalty_effect"]:
        rate = rates.get(eff, 0.05)  # 默认显著低于随机基线
        attr[eff] = ok_attr(top2_success_rate=rate)
    return attr


# ---------------------------------------------------------------------------
print("\n[1] Balanced ADJUST 只改 balanced_* 参数（闭环 bug 修复）")
# ---------------------------------------------------------------------------
_backup_runtime_state()
s = make_strategy(version=1, name="balanced")
attr = bad_rates(hot_effect=0.03, cold_effect=0.03)
adj = adjust_strategy(s, "auto", attribution=attr)
check("Balanced ADJUST 版本+1", adj["version"] == 2, str(adj["version"]))
# 关键：hot_weight 不得被改
check("Balanced ADJUST 不碰 hot_weight", adj["params"]["hot_weight"] == s["params"]["hot_weight"])
# balanced_hot_adjust 应真正变化（数据驱动：hot_effect 显著差）
check("Balanced ADJUST 修改 balanced_hot_adjust",
      adj["params"]["balanced_hot_adjust"] != s["params"]["balanced_hot_adjust"],
      f"{s['params']['balanced_hot_adjust']} -> {adj['params']['balanced_hot_adjust']}")
# 变化量 = -0.01（负向 effect → 小步减弱，单步小调；不再反向加强）
check("hot 步长为 -0.01",
      abs(adj["params"]["balanced_hot_adjust"] - s["params"]["balanced_hot_adjust"] + 0.01) < 1e-9)
check("adjusted params 在上下限内", all(
    _BALANCED_PARAM_RANGES[k][0] <= v <= _BALANCED_PARAM_RANGES[k][1]
    for k, v in adj["params"].items() if k in _BALANCED_PARAM_RANGES))

# ---------------------------------------------------------------------------
print("\n[2] hot 策略 ADJUST 不误改 Balanced 参数")
# ---------------------------------------------------------------------------
h = make_strategy(version=1, name="hot")
h["performance"]["top2_accuracy"] = 0.0
adj_hot = adjust_strategy(h, "auto")
# hot 策略 auto 走旧逻辑（改 hot_weight），不碰 balanced_* 修正
bl_params = [k for k in adj_hot["params"] if k.startswith("balanced") or k == "exposure_penalty_coef"]
check("hot ADJUST 不改任何 balanced_* 参数",
      all(adj_hot["params"][k] == h["params"][k] for k in bl_params))

# ---------------------------------------------------------------------------
print("\n[3] prediction 保存 strategy_version + strategy_params")
# ---------------------------------------------------------------------------
from prediction import generate_prediction
pred = generate_prediction("balanced", 10)
check("prediction 含 strategy_version", pred.get("strategy_version") is not None)
sp = pred.get("strategy_params", {})
check("prediction 含 strategy_params 且含 balanced_*",
      all(k in sp for k in ["balanced_hot_adjust", "balanced_cold_adjust",
                            "balanced_trend_adjust", "balanced_omission_adjust",
                            "balanced_max_total_adjust", "exposure_penalty_coef"]))
check("prediction BUY/WATCH 候选含 components+strategy_effects",
      all({"components", "strategy_effects"}.issubset(c.keys())
          for c in pred.get("buy", []) + pred.get("watch", [])))
check("components 含 sum/odd_even/zone/high_low/frequency/omission",
      all({"sum", "odd_even", "zone", "high_low", "frequency", "omission"}.issubset(
          c["components"].keys()) for c in pred.get("buy", [])))
check("strategy_effects 含 hot/cold/trend/omission/exposure",
      all({"hot_adjust", "cold_adjust", "trend_adjust", "omission_adjust",
           "exposure_penalty_effect"}.issubset(c["strategy_effects"].keys())
          for c in pred.get("buy", []) + pred.get("watch", [])))

# ---------------------------------------------------------------------------
print("\n[4] review 按 prediction version 记账（不污染历史）")
# ---------------------------------------------------------------------------
import review as review_mod
import strategy_manager as sm

# 用临时 STRATEGY_DIR，避免污染真实数据
_real_strategy_dir = sm.STRATEGY_DIR
_real_perf_file = None
tmpdir = Path(tempfile.mkdtemp(prefix="_dlt_loop_"))
try:
    (tmpdir / "strategy_history").mkdir(exist_ok=True)
    sm.STRATEGY_DIR = tmpdir
    review_mod.STRATEGY_DIR = tmpdir
    # 写一份 v3 的历史账户
    hist = {"strategies": {"balanced_v3": {
        "name": "balanced", "version": 3, "total_runs": 5, "success": 1, "fail": 3, "tie": 1,
        "selection_accuracy": 0.25, "win_count": 1, "total_wins": 1,
    }}}
    review_mod.save_performance_history(hist)
    # review_result 携带 prediction 的 version=3
    rv = {
        "strategy": "balanced", "strategy_version": 3, "date": "2026-09-01",
        "total_bet": 200, "total_prize": 30, "win_count": 1,
        "top2_selection": "SUCCESS",
    }
    key = review_mod._update_performance(rv)
    check("_update_performance 按 prediction version=3 记账", key == "balanced_v3", key)
    h2 = review_mod.load_performance_history()["strategies"]["balanced_v3"]
    check("v3 SUCCESS 计数到 2（原1+1）", h2["success"] == 2, str(h2["success"]))
    check("v3 total_runs 到 6", h2["total_runs"] == 6, str(h2["total_runs"]))
finally:
    sm.STRATEGY_DIR = _real_strategy_dir
    review_mod.STRATEGY_DIR = _real_strategy_dir
    shutil.rmtree(tmpdir, ignore_errors=True)

# ---------------------------------------------------------------------------
print("\n[5] TIE 不计入 binomial n（n = SUCCESS + FAIL）")
# ---------------------------------------------------------------------------
sig_tie = significance_vs_random(success=2, fail=8, tie=90)
check("valid_samples = success+fail = 10（TIE 不计入）", sig_tie["valid_samples"] == 10,
      f"{sig_tie['valid_samples']}")
check("observed_top2_accuracy = 2/(2+8)=0.2", abs(sig_tie["observed_top2_accuracy"] - 0.2) < 1e-9)
check("TIE 个数仅记录不参与 n", sig_tie["tie"] == 90)

# ---------------------------------------------------------------------------
print("\n[6] p=0.20 exact binomial 基线正确")
# ---------------------------------------------------------------------------
# P(X<=0 | Bin(1,0.2)) = 0.8
check("1次0成功 p=0.8", abs(exact_binomial_lower_tail(0, 1, 0.20) - 0.8) < 1e-9)
# P(X<=0 | Bin(10,0.2)) = 0.8**10
check("10次0成功 p=0.8^10",
      abs(exact_binomial_lower_tail(0, 10, 0.20) - 0.8 ** 10) < 1e-9)
# P(X<=2 | Bin(5,0.2)) 手算
expected = sum(exact_binomial_pmf(k, 5, 0.20) for k in range(0, 3))
check("5次<=2成功下尾正确", abs(exact_binomial_lower_tail(2, 5, 0.20) - expected) < 1e-12)
check("random_baseline=0.20", significance_vs_random(0, 50)["random_baseline"] == 0.20)

# ---------------------------------------------------------------------------
print("\n[7] 样本不足不 ADJUST")
# ---------------------------------------------------------------------------
r_small = evaluate_strategy(make_strategy(), {"total_runs": 10, "success": 0, "fail": 10, "tie": 0})
check("10次0成功 → KEEP（样本不足）", r_small["action"] == "KEEP", r_small["action"])
check("KEEP 原因含样本不足", "样本不足" in r_small["reason"])

# ---------------------------------------------------------------------------
print("\n[8] 样本够但不显著不 ADJUST")
# ---------------------------------------------------------------------------
r_nosig = evaluate_strategy(make_strategy(), {"total_runs": ADJUST_SAMPLE, "success": 10, "fail": ADJUST_SAMPLE - 10, "tie": 0})
# 50 次中 10 成功 = acc 0.20 == 随机基线，p 接近 1，不显著
check("50次acc=0.20 → KEEP（等于随机基线不显著）", r_nosig["action"] == "KEEP", r_nosig["action"])
check("p_value >= 0.05", r_nosig["significance"]["p_value"] >= 0.05, f"{r_nosig['significance']['p_value']:.4f}")

# ---------------------------------------------------------------------------
print("\n[9] 显著低于 random 才 ADJUST（exact binomial）")
# ---------------------------------------------------------------------------
r_sig = evaluate_strategy(make_strategy(), {"total_runs": ADJUST_SAMPLE, "success": 0, "fail": ADJUST_SAMPLE, "tie": 0})
check("50次0成功(acc=0) → ADJUST", r_sig["action"] == "ADJUST", r_sig["action"])
check("significance 输出块齐全", all(
    k in r_sig["significance"] for k in
    ["random_baseline", "success", "fail", "tie", "valid_samples",
     "observed_top2_accuracy", "p_value", "alpha", "significantly_below_random"]))
check("significance 含 alpha=0.05", r_sig["significance"]["alpha"] == 0.05)
check("significantly_below_random=true", r_sig["significance"]["significantly_below_random"] is True)
# p 值来自 exact binomial（0.8**50 级）
check("0.2^50 < 0.05 显著", r_sig["significance"]["p_value"] < 0.05,
      f"p={r_sig['significance']['p_value']:.2e}")

# ---------------------------------------------------------------------------
print("\n[10] attribution 样本不足不调参")
# ---------------------------------------------------------------------------
s10 = make_strategy(version=1, name="balanced")
insuff = {"hot_effect": {"sample_count": 5, "status": "INSUFFICIENT_DATA", "top2_success_rate": 0.0}}
check("样本<%d 的 effect 不入选调参目标" % ATTRIBUTION_MIN_SAMPLE,
      _select_effect_targets(insuff, s10) == [])
adj10 = adjust_strategy(s10, "auto", attribution=insuff)
check("attribution 不足时无参数变化",
      adj10["params"]["balanced_hot_adjust"] == s10["params"]["balanced_hot_adjust"])

# ---------------------------------------------------------------------------
print("\n[11] 每次最多改 1~2 个 Balanced 参数")
# ---------------------------------------------------------------------------
s11 = make_strategy(version=1, name="balanced")
attr5 = bad_rates(hot_effect=0.02, cold_effect=0.02, trend_effect=0.02,
                  omission_effect=0.02, exposure_penalty_effect=0.02)
adj11 = adjust_strategy(s11, "auto", attribution=attr5)
changed = [k for k in adj11["params"] if adj11["params"][k] != s11["params"][k]]
bal_changed = [k for k in changed if k.startswith("balanced") or k == "exposure_penalty_coef"]
check("即使5个effect全显著差，最多改2个参数", 0 < len(bal_changed) <= 2, f"changed={bal_changed}")

# ---------------------------------------------------------------------------
print("\n[12] 参数不越上下限")
# ---------------------------------------------------------------------------
# 把 hot 顶到上限，再调应仍在上限内
s12 = make_strategy(version=1, name="balanced")
s12["params"]["balanced_hot_adjust"] = _BALANCED_PARAM_RANGES["balanced_hot_adjust"][1]
adj12 = adjust_strategy(s12, "auto", attribution=bad_rates(hot_effect=0.0))
hi = _BALANCED_PARAM_RANGES["balanced_hot_adjust"][1]
check("hot 已在上限时 ADJUST 不越界", adj12["params"]["balanced_hot_adjust"] <= hi,
      f"{adj12['params']['balanced_hot_adjust']}")
# 全部参数检查
check("全部 balanced 参数均在配置区间",
      all(_BALANCED_PARAM_RANGES[k][0] <= adj12["params"][k] <= _BALANCED_PARAM_RANGES[k][1]
          for k in _BALANCED_PARAM_RANGES))

# ---------------------------------------------------------------------------
print("\n[13] ADJUST→save→next prediction→新参数真实生效（完整闭环）")
# ---------------------------------------------------------------------------
# 用真实 fetch_history 数据验证：改 balanced_* 参数后，同一 seed 下生成结果变化
from fetch_history import fetch_history
draws = fetch_history()
check("历史数据加载", len(draws) > 0)

s13 = make_strategy(version=1, name="balanced")
adj13 = adjust_strategy(s13, "auto", attribution=bad_rates(hot_effect=0.02, cold_effect=0.02))
new_params = get_generator_params(adj13)
# old params
old_params = get_generator_params(s13)

check("ADJUST 后 get_generator_params 读到变化后的 balanced_*",
      new_params["balanced_hot_adjust"] != old_params["balanced_hot_adjust"])

# 固定 seed：old vs new 参数下生成结果不同（参数真实进入生成器）
random.seed(101)
t_old = generate_top_candidates(draws, "balanced", top_n=10, pool_size=200, params=old_params)
random.seed(101)
t_new = generate_top_candidates(draws, "balanced", top_n=10, pool_size=200, params=new_params)
old_keys = [tuple(c["front"]) + tuple(c["back"]) for c in t_old]
new_keys = [tuple(c["front"]) + tuple(c["back"]) for c in t_new]
check("新参数真实改变下一期生成结果（闭环生效）", old_keys != new_keys,
      f"old={old_keys[:2]} new={new_keys[:2]}")
# compute_weights 也随参数变化（更底层证明参数真正进权重）
fw_old, _ = compute_weights(draws, "balanced", window=200, params=old_params)
fw_new, _ = compute_weights(draws, "balanced", window=200, params=new_params)
check("compute_weights 读取到新 balanced_* 参数", fw_old != fw_new)

# ---------------------------------------------------------------------------
print("\n[14] REVERT 可恢复旧版本")
# ---------------------------------------------------------------------------
# 临时目录测 revert
_real_sf = sm.STRATEGY_FILE
_real_hd = sm.HISTORY_DIR
tmp2 = Path(tempfile.mkdtemp(prefix="_dlt_revert_"))
try:
    (tmp2 / "strategy_history").mkdir(exist_ok=True)
    sm.STRATEGY_FILE = tmp2 / "current_strategy.json"
    sm.HISTORY_DIR = tmp2 / "strategy_history"
    # 先落一个 v1 基线
    v1 = make_strategy(version=1, name="balanced")
    sm.save_json(sm.STRATEGY_FILE, v1)
    sm.save_strategy_snapshot(v1, reason="baseline_v1")
    # ADJUST 到 v2 并存快照
    v2 = adjust_strategy(v1, "auto", attribution=bad_rates(hot_effect=0.02))
    sm.save_json(sm.STRATEGY_FILE, v2)
    sm.save_strategy_snapshot(v2, reason="before_revert")
    # REVERT 回 v1 参数
    from strategy_manager import revert_strategy
    reverted = revert_strategy(target_version=1)
    check("REVERT 版本号递增", reverted["version"] > v2["version"])
    check("REVERT 恢复 balanced_hot_adjust 到 v1 值",
          reverted["params"]["balanced_hot_adjust"] == v1["params"]["balanced_hot_adjust"])
    check("REVERT 标记 reverted_from", reverted.get("reverted_from") == v2["version"])
finally:
    sm.STRATEGY_FILE = _real_sf
    sm.HISTORY_DIR = _real_hd
    shutil.rmtree(tmp2, ignore_errors=True)


# ---------------------------------------------------------------------------
print("\n[15] 历史 prediction 不受 current_strategy 后续变化污染")
# ---------------------------------------------------------------------------
# v3 快照已存 strategy_version=3 与 strategy_params；若策略后来变成 v7，读取该快照
# 仍应回原 v3（key = balanced_v3，不因 current_strategy.version=7 变成 v7）
tmp3 = Path(tempfile.mkdtemp(prefix="_dlt_immutable_"))
try:
    (tmp3 / "strategy_history").mkdir(parents=True, exist_ok=True)
    sm.STRATEGY_DIR = tmp3
    review_mod.STRATEGY_DIR = tmp3
    # 构造一个带 v3 版本信息的历史预测快照 + 账户
    hist = {"strategies": {"balanced_v3": {
        "name": "balanced", "version": 3, "total_runs": 5, "success": 2, "fail": 3, "tie": 0,
        "selection_accuracy": 0.4, "win_count": 1, "total_wins": 1,
    }}}
    review_mod.save_performance_history(hist)
    # 当前策略升到 v7
    v7 = make_strategy(version=7, name="balanced")
    sm.save_json(sm.STRATEGY_FILE, v7)
    # review 用 prediction 的 v3 记账 → 应记到 balanced_v3，而非 v7
    rv15 = {"strategy": "balanced", "strategy_version": 3, "date": "2026-09-01",
            "total_bet": 200, "total_prize": 0, "win_count": 0, "top2_selection": "FAIL"}
    key15 = review_mod._update_performance(rv15)
    check("历史预测(v3)在 current_strategy=v7 时仍记到 v3", key15 == "balanced_v3", key15)
    h15 = review_mod.load_performance_history()["strategies"]["balanced_v3"]
    check("v3 fail 计数到 4（原3+1，未被 v7 污染）", h15["fail"] == 4, str(h15["fail"]))
finally:
    sm.STRATEGY_DIR = _real_strategy_dir
    review_mod.STRATEGY_DIR = _real_strategy_dir
    shutil.rmtree(tmp3, ignore_errors=True)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
print("\n[16] 2个闭环bug回归：ADJUST调参方向 + 前后区attribution串区")
# ---------------------------------------------------------------------------
# --- 16.1 ADJUST 调参方向：负向 effect → 小步减弱（direction=-1），绝不调大 ---
# omission_effect 负向 → balanced_omission_adjust 必须下降 (0.10 -> 0.09)
s_om = make_strategy(version=2, params={
    **default_strategy_params(), "balanced_omission_adjust": 0.10})
attr_om = {"omission_effect": ok_attr(top2_success_rate=0.08)}
r_om = adjust_strategy(dict(s_om), "auto", attribution=attr_om)
_om_v = r_om["params"].get("balanced_omission_adjust")
check("omission_effect 负向 → balanced_omission_adjust 下降(0.10->0.09)", _om_v == 0.09, f"got={_om_v}")
check("omission 负向 绝不升到 0.11", _om_v < 0.10 and _om_v <= 0.11, f"got={_om_v}")

# hot_effect 负向 → balanced_hot_adjust 下降
s_hot = make_strategy(version=2, params={
    **default_strategy_params(), "balanced_hot_adjust": 0.06})
attr_hot = {"hot_effect": ok_attr(top2_success_rate=0.04)}
r_hot = adjust_strategy(dict(s_hot), "auto", attribution=attr_hot)
_hv = r_hot["params"].get("balanced_hot_adjust")
check("hot_effect 负向 → balanced_hot_adjust 下降(0.06->0.05)", _hv == 0.05, f"got={_hv}")

# cold_effect / trend_effect / exposure 负向同理只能减弱
s_cold = make_strategy(version=2, params={
    **default_strategy_params(), "balanced_cold_adjust": 0.08})
r_cold = adjust_strategy(dict(s_cold), "auto", attribution={"cold_effect": ok_attr(top2_success_rate=0.07)})
_cv = r_cold["params"].get("balanced_cold_adjust")
check("cold_effect 负向 → balanced_cold_adjust 下降(0.08->0.07)", _cv == 0.07, f"got={_cv}")
s_tr = make_strategy(version=2, params={
    **default_strategy_params(), "balanced_trend_adjust": 0.05})
r_tr = adjust_strategy(dict(s_tr), "auto", attribution={"trend_effect": ok_attr(top2_success_rate=0.06)})
_tv = r_tr["params"].get("balanced_trend_adjust")
check("trend_effect 负向 → balanced_trend_adjust 下降(0.05->0.04)", _tv == 0.04, f"got={_tv}")
s_ex = make_strategy(version=2, params={
    **default_strategy_params(), "exposure_penalty_coef": 0.04})
r_ex = adjust_strategy(dict(s_ex), "auto", attribution={"exposure_penalty_effect": ok_attr(top2_success_rate=0.05)})
_ev = r_ex["params"].get("exposure_penalty_coef")
check("exposure_effect 负向 → exposure_penalty_coef 下降(0.04->0.035)", abs(_ev - 0.035) < 1e-9, f"got={_ev}")

# 无充分 attribution 样本 → 参数不变
s_ns = make_strategy(version=2, params={
    **default_strategy_params(), "balanced_omission_adjust": 0.10})
attr_ns = {"omission_effect": {"sample_count": 5, "status": "INSUFFICIENT_DATA", "top2_success_rate": 0.02}}
r_ns = adjust_strategy(dict(s_ns), "auto", attribution=attr_ns)
_ns_v = r_ns["params"].get("balanced_omission_adjust")
check("无充分样本 → 参数不变(仍0.10)", _ns_v == 0.10, f"got={_ns_v}")
check("无充分样本 → changed 为空", r_ns["last_adjustment"]["changed"] == [], str(r_ns["last_adjustment"]["changed"]))

# 参数仍不得越下限：0.005-0.01 被 clamp 到 0.0
s_lo2 = make_strategy(version=2, params={
    **default_strategy_params(), "balanced_cold_adjust": 0.005})
r_lo2 = adjust_strategy(dict(s_lo2), "auto", attribution={"cold_effect": ok_attr(top2_success_rate=0.03)})
_lo2_v = r_lo2["params"].get("balanced_cold_adjust")
check("参数不低于下限(clamp到0.0)", _lo2_v >= 0.0, f"got={_lo2_v}")

# --- 16.2 前后区 attribution 串区修复 ---
# 构造 front 8 与 back 8 effect 不同的 flags：
#   front[8] = hot + trend；back[8] = omission（后区无 hot）
_ef = {
    "front": {8: {"hot": True, "cold": False, "trend": True, "omission": False},
              1: {"hot": False, "cold": False, "trend": False, "omission": False}},
    "back": {8: {"hot": False, "cold": False, "trend": False, "omission": True},
             9: {"hot": False, "cold": False, "trend": False, "omission": False}},
}
# 仅前区含8：应只读 front_flags[8] → hot/trend，无 omission
_r_f_only = strategy_effects_for_candidate([8, 1, 2, 3, 4], [9, 10], _ef)
check("前区含8 → 命中 hot(不走后区flag)", _r_f_only["hot_adjust"] is True and _r_f_only["omission_adjust"] is False,
      str(_r_f_only))
check("前区含8 → trend 命中", _r_f_only["trend_adjust"] is True, str(_r_f_only))
# 仅后区含8：应只读 back_flags[8] → omission，不得误读 front hot
_r_b_only = strategy_effects_for_candidate([1, 2, 3, 4, 5], [8, 9], _ef)
check("后区含8 → 命中 omission(读back_flags[8])", _r_b_only["omission_adjust"] is True, str(_r_b_only))
check("后区含8 → 不误读 front hot(串区修复)", _r_b_only["hot_adjust"] is False, str(_r_b_only))
check("后区含8 → 不误读 trend(串区修复)", _r_b_only["trend_adjust"] is False, str(_r_b_only))
# 前后都含8：两者各自 flag 都累计
_r_both = strategy_effects_for_candidate([8, 1, 2, 3, 4], [8, 9], _ef)
check("前后区均含8 → hot(前)+omission(后)都命中", _r_both["hot_adjust"] is True and _r_both["omission_adjust"] is True,
      str(_r_both))

# --- 16.3 原 15 段语义保持：负向不再反向加强的完整核对 ---
# 若去掉 direction 修复前，omission 负向会变成 0.11；现在必须在区间内且下降
check("omission 负向结果仍在配置区间[0,0.15]",
      0.0 <= _om_v <= _BALANCED_PARAM_RANGES["balanced_omission_adjust"][1], f"got={_om_v}")


_restore_runtime_state()
print("\n" + "=" * 66)
print(f"结果: PASS={PASS} FAIL={FAIL}")
if FAILURES:
    print("失败项:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("全部通过 ✅")
    sys.exit(0)
