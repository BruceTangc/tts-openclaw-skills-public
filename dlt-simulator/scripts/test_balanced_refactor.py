#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_balanced_refactor.py — Balanced 统计重构回归测试

覆盖：
1. omission 语义：_build_freq 记录“最近一次出现位置”，与 statistics.omission_analysis 一致
2. Wilson CI 三态：正常(normal) / 偏高(high) / 偏低(low)
3. 策略参数 propagation：改 hot_weight / balanced_omission_adjust 后 compute_weights 权重变化
4. Balanced 分布回归：1000 轮 × 10 组，检查无高位漂移 / 无 exposure 塌缩 /
   hot vs balanced 不同 / Random 严格均匀
5. prediction 端到端：含 distribution_diagnostics，BUY/WATCH 数量与合法号码范围

运行：
    cd scripts && python3 test_balanced_refactor.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import random
from collections import Counter

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


print("=" * 64)
print("DLT Balanced 统计重构回归测试")
print("=" * 64)

# ---------------------------------------------------------------------------
# 1. omission 语义
# ---------------------------------------------------------------------------
print("\n[1] omission 语义（最近一次出现位置，不被更老出现覆盖）")
from generator import _build_freq
from statistics import omission_analysis

data = [
    {"front": [1, 2, 3, 4, 5], "back": [1, 2]},      # index 0（最新）
    {"front": [6, 7, 8, 9, 10], "back": [3, 4]},     # index 1
    {"front": [1, 11, 12, 13, 14], "back": [1, 5]},  # index 2（1 再次出现，更老）
    {"front": [2, 15, 16, 17, 18], "back": [6, 7]},  # index 3（2 再次出现，更老）
]
ff, bf, fl, bl, total = _build_freq(data)
check("前区号码1遗漏=0（取最新index0，不被index2覆盖）", fl.get(1) == 0, f"{fl.get(1)}")
check("前区号码2遗漏=0（取最新index0，不被index3覆盖）", fl.get(2) == 0, f"{fl.get(2)}")
check("前区号码6遗漏=1", fl.get(6) == 1, f"{fl.get(6)}")
check("前区号码11遗漏=2", fl.get(11) == 2, f"{fl.get(11)}")
check("后区号码1遗漏=0（不被index2覆盖）", bl.get(1) == 0, f"{bl.get(1)}")
check("后区号码3遗漏=1", bl.get(3) == 1, f"{bl.get(3)}")
check("后区号码6遗漏=3", bl.get(6) == 3, f"{bl.get(6)}")

om = omission_analysis(data)
check("与 statistics.omission_analysis 前区一致",
      om["front_omission"][1] == fl[1] and om["front_omission"][11] == fl[11] == 2)
check("与 statistics.omission_analysis 后区一致",
      om["back_omission"][1] == bl[1] and om["back_omission"][6] == bl[6] == 3)

# ---------------------------------------------------------------------------
# 2. Wilson CI 三态
# ---------------------------------------------------------------------------
print("\n[2] Wilson CI 三态（normal/high/low）")
from confidence import frequency_ci

# 构造 100 期：号码1 每期都出现(high)，号码3 出现14期(~expected normal)，号码2 0期(low)
synthetic = []
for i in range(100):
    front = [1, 3 if i < 14 else 30, 11, 12, 13]
    synthetic.append({"front": front, "back": [1, 2]})

ci = frequency_ci(synthetic)
f1 = ci["front"][1]
f2 = ci["front"][2]
f3 = ci["front"][3]
check("号码1(100/100) 判为 high", f1["abnormal_direction"] == "high", f"{f1['abnormal_direction']} / freq={f1['frequency']}")
check("号码2(0/100) 判为 low", f2["abnormal_direction"] == "low", f"{f2['abnormal_direction']} / freq={f2['frequency']}")
check("号码3(14/100≈期望) 判为 normal", f3["abnormal_direction"] == "normal", f"{f3['abnormal_direction']} / freq={f3['frequency']}")
# 内部一致性：abnormal_direction 必须与 expected 落区间关系一致
check("high 判定等价于 expected < ci_lower",
      (f1["abnormal_direction"] == "high") == (f1["expected"] < f1["ci_lower"]))
check("low 判定等价于 expected > ci_upper",
      (f2["abnormal_direction"] == "low") == (f2["expected"] > f2["ci_upper"]))
check("normal 判定等价于 expected 落在 CI 内",
      (f3["abnormal_direction"] == "normal") == (f3["ci_lower"] <= f3["expected"] <= f3["ci_upper"]))

# ---------------------------------------------------------------------------
# 3. 策略参数 propagation
# ---------------------------------------------------------------------------
print("\n[3] 策略参数 propagation（改参数后 compute_weights 权重变化）")
from fetch_history import fetch_history
from generator import compute_weights, generate_top_candidates
from strategy_manager import get_generator_params, default_strategy_params

draws = fetch_history()
check("历史数据加载", len(draws) > 0, f"len={len(draws)}")

# 3.1 hot_weight 影响 hot 策略权重
fw_a, _ = compute_weights(draws, "hot", window=200, params={"hot_weight": 1.5})
fw_b, _ = compute_weights(draws, "hot", window=200, params={"hot_weight": 3.0})
check("hot_weight 变化导致前区权重变化", fw_a != fw_b)
sub = draws[:200]
fc = Counter()
for d in sub:
    for n in d["front"]:
        fc[n] += 1
hot_num = fc.most_common(1)[0][0]
check(f"高频号{hot_num} 在更高 hot_weight 下权重更大", fw_b[hot_num] > fw_a[hot_num],
      f"{fw_a[hot_num]} -> {fw_b[hot_num]}")

# 3.2 balanced_omission_adjust 影响 balanced 权重
fb_default, _ = compute_weights(draws, "balanced", window=200, params={})
fb_high, _ = compute_weights(draws, "balanced", window=200, params={"balanced_omission_adjust": 0.5})
check("balanced_omission_adjust 变化导致前区权重变化", fb_default != fb_high)

# 3.3 get_generator_params 返回完整参数（含 balanced 弱修正参数）
gp = get_generator_params()
need_params = {"hot_weight", "cold_weight", "trend_weight", "omission_bonus",
               "balanced_hot_adjust", "balanced_cold_adjust", "balanced_trend_adjust",
               "balanced_omission_adjust", "balanced_max_total_adjust", "exposure_penalty_coef"}
check("get_generator_params 含全部闭环参数", need_params.issubset(gp.keys()), f"{gp.keys()}")

# 3.4 固定 seed 下生成可复现；改参数后结果变化（参数真进生成器）
random.seed(7)
t1 = generate_top_candidates(draws, "balanced", top_n=10, pool_size=200)
random.seed(7)
t2 = generate_top_candidates(draws, "balanced", top_n=10, pool_size=200)
check("固定 seed 生成可复现", [c["front"] + c["back"] for c in t1] == [c["front"] + c["back"] for c in t2])
random.seed(7)
t3 = generate_top_candidates(draws, "balanced", top_n=10, pool_size=200,
                             params={"balanced_omission_adjust": 0.40, "balanced_hot_adjust": 0.20})
check("改 balanced 参数后固定 seed 下结果变化（参数真实影响生成）",
      [c["front"] + c["back"] for c in t1] != [c["front"] + c["back"] for c in t3])

# ---------------------------------------------------------------------------
# 4. Balanced 分布回归（1000 轮 × 10 组）+ Random 严格均匀 + hot vs balanced
# ---------------------------------------------------------------------------
print("\n[4] Balanced 分布回归（1000 轮 × 10 组）")
from stat_rigor import portfolio_distribution, random_baseline_pool

ROUNDS = 1000
TOP_N = 10
random.seed(42)
bal_cands = []
for _ in range(ROUNDS):
    top = generate_top_candidates(draws, "balanced", top_n=TOP_N, pool_size=200)
    bal_cands.extend(top)

bal_diag = portfolio_distribution(bal_cands)
check(f"生成 {len(bal_cands)} 个候选（{ROUNDS}轮×{TOP_N}组）", len(bal_cands) == ROUNDS * TOP_N)

# 无高位漂移：前区高位(18-35)理论占比 18/35≈0.5143
front_high_ratio = bal_diag["front_high_ratio"]
check("前区高位比例无漂移(≈0.5143)", abs(front_high_ratio - 18 / 35) < 0.03, f"{front_high_ratio:.4f}")
back_high_ratio = bal_diag["back_high_ratio"]
check("后区高位比例无漂移(≈0.5)", abs(back_high_ratio - 0.5) < 0.05, f"{back_high_ratio:.4f}")
# 无 exposure 塌缩：最大单号曝光比例应远低于 0.5（未出现单号霸占候选池）
max_fr = bal_diag["max_front_exposure_ratio"]
max_br = bal_diag["max_back_exposure_ratio"]
check("无 exposure 塌缩(前区最大曝光比例<0.35)", max_fr < 0.35, f"{max_fr:.4f}")
check("无 exposure 塌缩(后区最大曝光比例<0.35)", max_br < 0.35, f"{max_br:.4f}")
# 和值均值/标准差：均值接近理论(90)，标准差非退化(>0，未坍缩成单一点)——
# balanced 因软性结构评分(和值/奇偶/区间/高低)会比纯随机更集中，但必须保留一定随机性。
check("和值均值接近理论(80~100)", 80 <= bal_diag["front_sum_mean"] <= 100, f"{bal_diag['front_sum_mean']:.2f}")
check("和值保留随机性(标准差>3，未退化单点)", bal_diag["front_sum_std"] > 3, f"{bal_diag['front_sum_std']:.2f}")

# Random 严格均匀
print("\n[4b] Random 严格均匀对照")
rp = random_baseline_pool(10000, seed=42)
rdiag = portfolio_distribution(rp)
check("Random 前区曝光卡方不拒绝均匀(p>0.05)", rdiag["chi2_front_p"] > 0.05, f"p={rdiag['chi2_front_p']:.4f}")
check("Random 后区曝光卡方不拒绝均匀(p>0.05)", rdiag["chi2_back_p"] > 0.05, f"p={rdiag['chi2_back_p']:.4f}")
check("Random 前区高位比例≈0.5143", abs(rdiag["front_high_ratio"] - 18 / 35) < 0.02, f"{rdiag['front_high_ratio']:.4f}")
check("Random 最大前区曝光比例接近均匀(≈0.14)", rdiag["max_front_exposure_ratio"] < 0.20,
      f"{rdiag['max_front_exposure_ratio']:.4f}")

# hot vs balanced 不同
print("\n[4c] hot vs balanced 不同")
random.seed(99)
hot_cands = []
for _ in range(200):
    top = generate_top_candidates(draws, "hot", top_n=TOP_N, pool_size=200)
    hot_cands.extend(top)
hot_diag = portfolio_distribution(hot_cands)
random.seed(99)
bal_sample = []
for _ in range(200):
    top = generate_top_candidates(draws, "balanced", top_n=TOP_N, pool_size=200)
    bal_sample.extend(top)
bal_sample_diag = portfolio_distribution(bal_sample)
check("hot 与 balanced 前区曝光分布不同",
      hot_diag["front_exposure"] != bal_sample_diag["front_exposure"])
check("hot 比 balanced 更集中(最大曝光比例更大)",
      hot_diag["max_front_exposure_ratio"] > bal_sample_diag["max_front_exposure_ratio"],
      f"hot={hot_diag['max_front_exposure_ratio']:.4f} vs bal={bal_sample_diag['max_front_exposure_ratio']:.4f}")

# ---------------------------------------------------------------------------
# 5. prediction 端到端
# ---------------------------------------------------------------------------
print("\n[5] prediction 端到端")
from prediction import generate_prediction
pred = generate_prediction("balanced", 10)
check("预测无错误", "error" not in pred, str(pred.get("error", "")))
check("BUY=2 / WATCH=8", len(pred.get("buy", [])) == 2 and len(pred.get("watch", [])) == 8,
      f"buy={len(pred.get('buy', []))}, watch={len(pred.get('watch', []))}")
check("prediction 含 distribution_diagnostics",
      "distribution_diagnostics" in pred and "portfolio" in pred["distribution_diagnostics"]
      and "random_baseline" in pred["distribution_diagnostics"])
dd_note = pred.get("distribution_diagnostics", {}).get("note", "")
check("distribution_diagnostics 含免责声明", "不预测任何号码下一期的中奖概率" in dd_note, dd_note[:40])
all_legal = True
for c in pred.get("buy", []) + pred.get("watch", []):
    if not (len(set(c["front"])) == 5 and all(1 <= n <= 35 for n in c["front"])
            and len(set(c["back"])) == 2 and all(1 <= n <= 12 for n in c["back"])):
        all_legal = False
check("prediction 候选号码全部合法(前5后2且范围正确)", all_legal)

# ---------------------------------------------------------------------------
# 打印 1000 轮分布诊断（供报告）
# ---------------------------------------------------------------------------
print("\n" + "=" * 64)
print("[诊断] Balanced 1000 轮×10 组分布诊断")
print("=" * 64)
print(f"  候选总数: {bal_diag['n_candidates']}")
print(f"  前区均值: {bal_diag['front_mean']}")
print(f"  和值均值: {bal_diag['front_sum_mean']}  标准差: {bal_diag['front_sum_std']}")
print(f"  前区高位(18-35)比例: {bal_diag['front_high_ratio']} (理论 {18/35:.4f})")
print(f"  后区高位(7-12)比例: {bal_diag['back_high_ratio']} (理论 0.5)")
print(f"  前区最大单号曝光比例: {bal_diag['max_front_exposure_ratio']}")
print(f"  后区最大单号曝光比例: {bal_diag['max_back_exposure_ratio']}")
print(f"  前区 χ² p: {bal_diag['chi2_front_p']}")
print(f"  后区 χ² p: {bal_diag['chi2_back_p']}")
print(f"  [Random 对照] 前区χ²p={rdiag['chi2_front_p']} 后区χ²p={rdiag['chi2_back_p']} "
      f"高位比例={rdiag['front_high_ratio']} 最大曝光={rdiag['max_front_exposure_ratio']}")

# ---------------------------------------------------------------------------
print("\n" + "=" * 64)
print(f"结果: PASS={PASS} FAIL={FAIL}")
if FAILURES:
    print("失败项:")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("全部通过 ✅")
    sys.exit(0)
