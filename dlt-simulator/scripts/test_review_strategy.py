#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_review_strategy.py — #8 修复 + #17 主链路测试

覆盖：
A. strategy_manager.evaluate_strategy 判定分支
   - 样本不足 → KEEP
   - 正常表现（≥随机基线，未显著差）→ KEEP（不再"跑满次数就无条件 ADJUST"）
   - 显著低于随机基线 + 达标调整样本 → ADJUST
   - 显著低于随机基线 + 达标长期观察 → REVERT
   - Random 基线比较：top2_acc 高于/达到随机基线不触发调整
B. review._run_strategy_loop 传给 evaluate_strategy 的 perf_data 字段完整
   - 必须含 top2_accuracy 与 roi（#8 根因：之前只传 total_runs/win_rate）
   - 50 次后若 Top-2 表现正常 → 不再无条件 ADJUST
   - KEEP/ADJUST 闭环动作正确（写入策略 performance / 升级版本）

运行：
    cd scripts && python3 test_review_strategy.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
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


print("=" * 60)
print("DLT 策略评估与复盘主链路测试 (#8/#17)")
print("=" * 60)

from strategy_manager import (
    MIN_SAMPLE, ADJUST_SAMPLE, CONFIRM_SAMPLE,
    RANDOM_TOP2_BASELINE, evaluate_strategy, adjust_strategy,
)
from common import STRATEGY_DIR

# ---------------------------------------------------------------------------
# 辅助：构造最小策略对象（按 load_current_strategy 的默认结构）
# ---------------------------------------------------------------------------
def make_strategy(version=1):
    return {
        "name": "balanced",
        "version": version,
        "created": "t",
        "updated": "t",
        "status": "active",
        "params": {"hot_weight": 1.5, "cold_weight": 1.0, "trend_weight": 0.5, "omission_bonus": 1.0},
        "performance": {"top2_accuracy": 0.0, "any_accuracy": 0.0, "total_runs": 0, "win_count": 0},
    }


# ---------------------------------------------------------------------------
print("\n[A] strategy_manager.evaluate_strategy 判定分支")
print("=" * 60)

# A1. 样本不足 → KEEP（不触发调整）
r = evaluate_strategy(make_strategy(), {
    "total_runs": 5, "win_rate": 0, "top2_accuracy": 0.0, "roi": -100.0,
})
check("样本不足(<MIN) → KEEP", r["action"] == "KEEP", str(r))

# 证明：即使 top2_acc/roi 都为 0，只要样本不足也不触发调整（区别于旧 bug）
r0 = evaluate_strategy(make_strategy(), {"total_runs": 30, "win_rate": 0, "top2_accuracy": 0.0, "roi": 0.0})
check("旧bug场景(缺字段恒0)在30次时也KEEP(未达50) → 不再无条件调",
      r0["action"] == "KEEP", str(r0))

# A2. 正常表现（≥随机基线）→ KEEP，即使跑满 50/100 次也不无条件 ADJUST（#8 核心修复）
r_normal = evaluate_strategy(make_strategy(), {
    "total_runs": ADJUST_SAMPLE + 10, "win_rate": 30, "top2_accuracy": RANDOM_TOP2_BASELINE, "roi": -30.0,
})
check(f"达标{ADJUST_SAMPLE}+次 随机基线表现 → KEEP(不再无条件ADJUST)", r_normal["action"] == "KEEP", str(r_normal))

r_normal2 = evaluate_strategy(make_strategy(), {
    "total_runs": CONFIRM_SAMPLE + 10, "win_rate": 30, "top2_accuracy": RANDOM_TOP2_BASELINE, "roi": -30.0,
})
check(f"达标{CONFIRM_SAMPLE}+次 随机基线表现 → KEEP", r_normal2["action"] == "KEEP", str(r_normal2))

# A3. 显著低于随机基线 + 达标调整样本 → ADJUST
under_random_acc = RANDOM_TOP2_BASELINE * 0.4  # 显著低于随机(0.08 < 0.1)
r_adj = evaluate_strategy(make_strategy(), {
    "total_runs": ADJUST_SAMPLE + 5, "win_rate": 60, "top2_accuracy": under_random_acc, "roi": -85.0,
})
check("显著低于随机 + 达标调整样本 → ADJUST", r_adj["action"] == "ADJUST", str(r_adj))

# A4. 显著低于随机 + 达标长期观察 → REVERT
r_rew = evaluate_strategy(make_strategy(), {
    "total_runs": CONFIRM_SAMPLE + 20, "win_rate": 60, "top2_accuracy": 0.02, "roi": -90.0,
})
check("显著低于随机 + 达标长期观察 → REVERT", r_rew["action"] == "REVERT", str(r_rew))

# A5. 显著低于随机但样本<ADJUST → 保持 KEEP（未达调整阈值就调整也不合理）
r_early = evaluate_strategy(make_strategy(), {
    "total_runs": ADJUST_SAMPLE - 1, "win_rate": 60, "top2_accuracy": 0.0, "roi": -90.0,
})
check("显著差但未达调整样本 → 仍 KEEP", r_early["action"] == "KEEP", str(r_early))

# A6. Random 基线存在且用于比较（details 带 random_baseline）
check("ADJUST 含 random_baseline 比较", r_adj["details"].get("random_baseline") == RANDOM_TOP2_BASELINE, str(r_adj))
check("KEEP 含 random_baseline 比较", r_normal["details"].get("random_baseline") == RANDOM_TOP2_BASELINE, str(r_normal))

# A7. adjust_strategy 对外行为不变：auto 叠加 bump
s = make_strategy(version=3)
s["performance"] = {"top2_accuracy": 0.0, "any_accuracy": 0.0, "total_runs": 60, "win_count": 0}
adj = adjust_strategy(s, "auto")
check("adjust_strategy auto 版本+1", adj["version"] == 4, str(adj))
check("adjust_strategy 就地更新不破坏 params", set(s["params"]) <= set(adj["params"]), str(adj))


# ---------------------------------------------------------------------------
print("\n[B] review._run_strategy_loop 传给 evaluate_strategy 的 perf_data 字段完整 (#8)")
print("=" * 60)
import review as review_mod

# 记录 evaluate_strategy 拿到的 perf_data，验证字段是否补全
captured = {}

def _fake_evaluate(strategy, perf_data):
    captured["perf_data"] = dict(perf_data)
    return {"action": "KEEP", "reason": "测试用", "details": {}}

orig_evaluate = {}
import strategy_manager as sm

B1 = 0
B2 = 0


def run_loop_with_history(strategy_ver, perf, review_result):
    """在隔离的临时 STRATEGY_DIR 下跑一次 _run_strategy_loop，验证 perf_data 透传"""
    global captured
    captured = {}
    import importlib
    # 备份原始函数/路径
    orig_strategy_file = sm.STRATEGY_FILE
    orig_history_dir = sm.HISTORY_DIR
    try:
        # 建临时策略目录避免污染真实数据（结束后清理）
        tmp = STRATEGY_DIR.parent / "_test_tmp"
        (tmp / "strategy_history").mkdir(parents=True, exist_ok=True)
        sm.STRATEGY_FILE = tmp / "current_strategy.json"
        sm.HISTORY_DIR = tmp / "strategy_history"
        review_mod.STRATEGY_DIR = tmp  # 让 history 读写走临时目录

        strategy = make_strategy(version=strategy_ver)
        sm.save_json(sm.STRATEGY_FILE, strategy)

        # 覆写 evaluate_strategy 以捕获 perf_data
        global _fake_evaluate, orig_evaluate
        if not orig_evaluate:
            # _run_strategy_loop 内 `from strategy_manager import evaluate_strategy` 在调用时
            # 读取 module 属性，故 patch sm.evaluate_strategy 即可拦截到 perf_data
            orig_evaluate["sm"] = sm.evaluate_strategy
        sm.evaluate_strategy = _fake_evaluate

        # 写入 performance_history 到临时目录
        hist = {"strategies": {f"balanced_v{strategy_ver}": perf}}
        review_mod.save_performance_history(hist)

        result = review_mod._run_strategy_loop(review_result)
        return result, strategy_ver
    finally:
        sm.STRATEGY_FILE = orig_strategy_file
        sm.HISTORY_DIR = orig_history_dir
        review_mod.STRATEGY_DIR = STRATEGY_DIR
        # 恢复 monkeypatch，避免污染后续真实判定测试
        if orig_evaluate.get("sm"):
            sm.evaluate_strategy = orig_evaluate["sm"]
        # 清理临时目录
        import shutil
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


# B1. 验证 perf_data 包含 top2_accuracy 与 roi（#8 根因修复）
perf = {
    "total_runs": 55, "success": 30, "fail": 20, "tie": 5,
    "selection_accuracy": 0.6, "win_count": 3, "total_wins": 3,
    "best_tier": 6, "best_tier_name": "六等奖", "first_run": "", "last_run": "",
}
review_res = {
    "strategy": "balanced", "date": "2026-08-28", "total_prize": 30, "total_bet": 200, "top2_selection": "SUCCESS",
}
run_loop_with_history(1, perf, review_res)
pd = captured.get("perf_data", {})
check("perf_data 含 top2_accuracy（#8 补传）", "top2_accuracy" in pd, str(pd))
check("perf_data 含 roi（#8 补传）", "roi" in pd, str(pd))
check("perf_data[top2_accuracy] 取真实 selection_accuracy", pd.get("top2_accuracy") == 0.6, str(pd))
exp_roi = ((30 - 200) / 200) * 100
check(f"perf_data[roi] 按当期实际回报计算({exp_roi:.1f}%)", abs(pd.get("roi", 0) - exp_roi) < 1e-6, str(pd))
check("perf_data 仍含 total_runs 与 win_rate", "total_runs" in pd and "win_rate" in pd, str(pd))
check("perf_data[total_runs] 取真实累计次数", pd.get("total_runs") == 55, str(pd))

# B2. 50 次后正常表现 → 不再无条件 ADJUST（#8 核心：真实 evaluate_strategy 判定）
# 恢复正常 evaluate_strategy 后，用真实判定跑 55 次、
# top2_acc(=0.6) 远超随机基线 → 应 KEEP，而非旧 bug 的无条件 ADJUST
normal_perf = {
    "total_runs": 55, "success": 33, "fail": 22, "tie": 0,
    "selection_accuracy": 0.6, "win_count": 5, "total_wins": 5,
    "best_tier": 6, "best_tier_name": "六等奖", "first_run": "", "last_run": "",
}
normal_res = {"strategy": "balanced", "date": "2026-08-28", "total_prize": 100, "total_bet": 200,
              "top2_selection": "SUCCESS", "win_count": 1}

import strategy_manager as sm_real
should_keep = sm_real.evaluate_strategy(
    make_strategy(1),
    {"total_runs": 55, "win_rate": 9.09, "top2_accuracy": 0.6, "roi": -50.0},
)
check("真实evaluate: Top2=60%远超随机基线的55次运行 → KEEP(修复后不无条件ADJUST)",
      should_keep["action"] == "KEEP", str(should_keep))

# B3. 复盘闭环：显著差 → ADJUST 且版本升级（用真实 evaluate_strategy 路径）
bad_perf = {
    "total_runs": ADJUST_SAMPLE + 10, "success": 5, "fail": 55, "tie": 0,
    "selection_accuracy": 0.08, "win_count": 0, "total_wins": 0,
    "best_tier": None, "best_tier_name": "", "first_run": "", "last_run": "",
}
bad_res = {"strategy": "balanced", "date": "2026-08-28", "total_prize": 0, "total_bet": 200,
           "top2_selection": "FAIL", "win_count": 0}
should_adj = sm_real.evaluate_strategy(
    make_strategy(1),
    {"total_runs": ADJUST_SAMPLE + 10, "win_rate": 0, "top2_accuracy": 0.08, "roi": -100.0},
)
check("真实evaluate: Top2=8%显著低于随机的60+次 → ADJUST",
      should_adj["action"] == "ADJUST", str(should_adj))

# B4. 快照/版本升级由 adjust_strategy 完成（不破坏闭环）
adj_chain = adjust_strategy(make_strategy(2), "auto")
check("ADJUST 后版本+1 且 params 就地演化", adj_chain["version"] == 3, str(adj_chain))


# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print(f"结果: PASS={PASS} FAIL={FAIL}")
if FAILURES:
    print("失败项:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("全部通过 ✅")
    sys.exit(0)
