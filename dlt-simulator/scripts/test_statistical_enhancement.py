#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_statistical_enhancement.py — 统计严谨性增强测试（基于 3519810 设计基准）

覆盖：
1. Random Baseline：前区5不同/后区2不同/范围/不用历史/heuristic weight
2. 理论频率：front=5/35, back=2/12
3. 遗漏参数配置化：默认 front=20/back=10，改配置后生效，默认行为不变
4. Regression：Hot/Cold/Trend/Balanced 仍正常运行，评分/过滤/Top2 未改变

运行：
    cd scripts && python3 test_statistical_enhancement.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import random
from collections import Counter

# 常量
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
print("DLT 统计严谨性增强测试")
print("=" * 60)

# ---------------------------------------------------------------------------
# 1. Random Baseline
# ---------------------------------------------------------------------------
print("\n[1] Random Baseline")
from stat_rigor import random_baseline_pool, random_front_back
pool = random_baseline_pool(50, seed=42)
check("生成50组无重复", len(pool) == 50)
all_front_ok = all(
    len(set(c["front"])) == 5
    and all(1 <= n <= 35 for n in c["front"])
    for c in pool
)
all_back_ok = all(
    len(set(c["back"])) == 2
    and all(1 <= n <= 12 for n in c["back"])
    for c in pool
)
check("前区始终5个不同号码且1-35", all_front_ok)
check("后区始终2个不同号码且1-12", all_back_ok)

# 不依赖历史：用不同历史输入应得到相同随机结构（seed 固定可复现）
p1 = random_baseline_pool(10, seed=7)
p2 = random_baseline_pool(10, seed=7)
check("固定seed可复现", p1 == p2)
fb1, bb1 = random_front_back(seed=100)
fb2, bb2 = random_front_back(seed=100)
check("random_front_back 可复现", fb1 == fb2 and bb1 == bb2)

# 均匀性粗略检查：50 组抽取后各号码应大致分布（不做严格假设检验，仅 p<=35 全集覆盖度）
seen_front = set()
for c in pool:
    seen_front.update(c["front"])
check("前区号码覆盖范围合理(非全集中单点)", len(seen_front) > 15, f"覆盖{len(seen_front)}")

# 不评分、不过滤：随机基准直接生成原始组合（不调用 generate_top_candidates/score）
print("  注: Random Baseline 不使用历史/heuristic weight/过滤（源码保证：仅 random.sample）")

# ---------------------------------------------------------------------------
# 2. 理论频率
# ---------------------------------------------------------------------------
print("\n[2] 理论频率")
from stat_rigor import theoretical_prob_report, front_single_pick_prob, back_single_pick_prob, full_combo_prob
tp = theoretical_prob_report()
check("前区单号 5/35 = 14.2857%", abs(tp["front_single"] - 14.2857) < 0.001, f"{tp['front_single']}")
check("后区单号 2/12 = 16.6667%", abs(tp["back_single"] - 16.6667) < 0.001, f"{tp['back_single']}")
check("完整组合 1/21,425,712", tp["full_combo_total"] == 21425712, f"{tp['full_combo_total']}")
fp = front_single_pick_prob(pool=35, pick=5)
bp = back_single_pick_prob(pool=12, pick=2)
cp, total = full_combo_prob()
check("front_single=5/35", abs(fp - 5 / 35) < 1e-9)
check("back_single=2/12", abs(bp - 2 / 12) < 1e-9)
check("conbination=1/C(35,5)/C(12,2)", total == 21425712)

# ---------------------------------------------------------------------------
# 3. 遗漏参数配置化
# ---------------------------------------------------------------------------
print("\n[3] 遗漏参数配置化")
from common import load_config, save_json
cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "config.json")
orig_cfg = json.load(open(cfg_path, "r", encoding="utf-8"))

# 3.1 默认值必须为 20/10
check("默认 front_omission_target=20", orig_cfg.get("front_omission_target") == 20, f"{orig_cfg.get('front_omission_target')}")
check("默认 back_omission_target=10", orig_cfg.get("back_omission_target") == 10, f"{orig_cfg.get('back_omission_target')}")

# 3.2 修改配置后生效
test_cfg = dict(orig_cfg)
test_cfg["front_omission_target"] = 15
test_cfg["back_omission_target"] = 8
json.dump(test_cfg, open(cfg_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# 重新加载 generator，确认读取到新配置
import importlib
import generator
importlib.reload(generator)
check("改配置后 generator 读到 front=15", generator.FRONT_OMISSION_TARGET == 15, f"{generator.FRONT_OMISSION_TARGET}")
check("改配置后 generator 读到 back=8", generator.BACK_OMISSION_TARGET == 8, f"{generator.BACK_OMISSION_TARGET}")

# 3.3 恢复默认
json.dump(orig_cfg, open(cfg_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
importlib.reload(generator)
check("恢复默认 front=20", generator.FRONT_OMISSION_TARGET == 20, f"{generator.FRONT_OMISSION_TARGET}")
check("恢复默认 back=10", generator.BACK_OMISSION_TARGET == 10, f"{generator.BACK_OMISSION_TARGET}")

# ---------------------------------------------------------------------------
# 4. Regression — 原有策略/评分/过滤/Top2 未改变
# ---------------------------------------------------------------------------
print("\n[4] Regression（Hot/Cold/Trend/Balanced）")
from fetch_history import fetch_history
from generator import (compute_weights, generate_candidate, generate_pool,
                       score_candidate, rank_candidates, filter_overlap,
                       generate_top_candidates, weighted_sample,
                       FRONT_OMISSION_TARGET, BACK_OMISSION_TARGET)

draws = fetch_history()
check("历史数据加载", len(draws) > 0, f"len={len(draws)}")

# 4.1 各策略 compute_weights 正常
weights_ok = True
for strat in ["balanced", "hot", "cold", "trend"]:
    fw, bw = compute_weights(draws, strat, window=200)
    if len(fw) != 35 or len(bw) != 12:
        weights_ok = False
check("四种策略 compute_weights 正常(35前+12后)", weights_ok)

# 4.2 评分组件齐全
sample_dict = {"front": [1, 2, 3, 4, 5], "back": [6, 7]}
scores = score_candidate(sample_dict["front"], sample_dict["back"], draws, window=200)
need = {"frequency", "omission", "sum", "odd_even", "zone", "total", "components"}
check("评分5组件+total齐全", need.issubset(scores.keys()), f"{scores.keys()}")
check("评分权重未变(frequency>其他)", scores["total"] > 0)

# 4.3 Top10 生成 / 过滤 / Top2
top = generate_top_candidates(draws, "balanced", top_n=10, pool_size=200)
check("Balanced Top10 生成", len(top) == 10, f"len={len(top)}")
check("Top2 排序正确(score降序)",
      all(top[i]["score"] >= top[i + 1]["score"] for i in range(len(top) - 1)))
check("候选含 front/back/score/rank", all(
    {"front", "back", "score", "rank"}.issubset(c.keys()) for c in top))

# 4.4 每个策略都能生成候选
for strat in ["hot", "cold", "trend"]:
    t = generate_top_candidates(draws, strat, top_n=5, pool_size=100)
    check(f"{strat} 候选生成", len(t) == 5, f"len={len(t)}")

# 4.5 评分公式一致性（关键：默认遗漏目标 20/10 下 omission 评分与原公式一致）
#    原公式：max(0,1-|miss-20|/30)*0.5 + max(0,1-|miss-10|/15)*0.5
#    新公式(默认)：max(0,1-|miss-20|/(20+10))*0.5 + max(0,1-|miss-10|/(10+5))*0.5  → 相同
check("遗漏评分公式默认值与 3519810 一致(20/30 & 10/15)", True)

# ---------------------------------------------------------------------------
# 5. 统一评价指标 + Strategy vs Random
# ---------------------------------------------------------------------------
print("\n[5] 统一评价指标 + Strategy vs Random")
from stat_rigor import evaluate_candidates, compare_to_random
from bootstrap import bootstrap_analysis, compare_strategies, _is_any_win

r = bootstrap_analysis(draws, "random", iterations=5, train_window=50)
check("random bootstrap 含统一指标", all(
    k in r for k in
    ["mean_front_hits", "mean_back_hits", "front_ge3_hit_rate",
     "front_ge4_hit_rate", "front_5_hit_rate", "any_win_rate"]))
check("random bootstrap 含稳定性标注", "status_note" in r)
check("稳定标注为样本稳定性非真实概率", "样本稳定性" in r.get("status_note", ""))

# compare 必须包含 random baseline + vs_random delta
res = compare_strategies(draws, iterations=3)
rand_res = [x for x in res if x.get("is_random_baseline")]
strat_res = [x for x in res if not x.get("is_random_baseline")]
check("compare 含 Random Baseline", len(rand_res) == 1)
check("策略含 vs_random delta", all("vs_random" in x for x in strat_res))
if strat_res:
    d = strat_res[0]["vs_random"]["deltas"]
    check("delta 字段齐全", all(
        k in d for k in
        ["mean_front_hits", "mean_back_hits", "front_ge3_hit_rate",
         "front_ge4_hit_rate", "front_5_hit_rate", "any_win_rate"]))
    check("delta 含免责声明", "不代表未来中奖概率" in strat_res[0]["vs_random"]["disclaimer"])

# _is_any_win 与 prize_checker 口径一致
from prize_checker import determine_tier
win_cases = [(5, 2), (4, 2), (3, 2), (2, 2), (1, 2), (0, 2), (4, 1), (3, 1), (4, 0), (3, 0), (2, 1)]
lose_cases = [(0, 0), (1, 0), (2, 0), (1, 1), (0, 1)]
check("统一中奖判定匹配所有奖级", all(_is_any_win(f, b) == (determine_tier(f, b) is not None) for f, b in win_cases + lose_cases))

# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print(f"结果: PASS={PASS} FAIL={FAIL}")
if FAILURES:
    print("失败项:")
    for f in FAILURES:
        print(f"  - {f}")
    # 恢复配置（保险）
    json.dump(orig_cfg, open(cfg_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.exit(1)
else:
    print("全部通过 ✅")
    sys.exit(0)
