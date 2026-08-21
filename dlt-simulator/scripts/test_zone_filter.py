#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for zone_filter strategy in generator.py

段划分：前区 1-35 分 7 段（每段 5 号，段号=(n-1)//5），后区 1-12 分 4 段
（每段 3 号，段号=(n-1)//3）。统计最近 window 期各段累计出号频次，压制
"过热段"（显著高于均匀期望 5*window/7 / window/2）内号码权重到 0.5。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generator import compute_weights, generate_top_candidates
from common import load_config

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]


def _front_seg(n):
    """前区段号（与 generator.py 一致）"""
    return (n - 1) // 5


def _back_seg(n):
    """后区段号（与 generator.py 一致）"""
    return (n - 1) // 3


def _make_front_zone0_hot(n=30):
    """前区段0(1-5)过热：25 期全落段0，5 期落段1 → 段0=125次 >> 期望21.4"""
    draws = []
    for i in range(n):
        if i < 25:
            front = [1, 2, 3, 4, 5]
        else:
            front = [6, 7, 8, 9, 10]
        back = [1, 2]
        draws.append({"front": front, "back": back})
    return draws


def _make_front_balanced(n=30):
    """前区各段近似均匀（段0/1出25次，段2-6出20次，比值≤1.17 < 1.5，std>0）"""
    draws = []
    for i in range(n):
        base = (i % 7) * 5
        front = sorted([base + 1, base + 2, base + 3, base + 4, base + 5])
        back = [1, 2]
        draws.append({"front": front, "back": back})
    return draws


def _make_back_zone0_hot(n=20):
    """后区段0(1-3)过热：18 期 [1,2]，2 期 [3,4] → 段0=38次 >> 期望10"""
    draws = []
    for i in range(n):
        if i < 18:
            back = [1, 2]
        else:
            back = [3, 4]
        front = [5, 10, 15, 20, 25]
        draws.append({"front": front, "back": back})
    return draws


def _make_back_balanced(n=32):
    """后区各段近似均匀：段0/1出16次、段2出14次、段3出18次（比值≤1.125 < 1.5，std>0）"""
    draws = []
    for i in range(n):
        if i < 8:
            back = [1, 2]      # 段0
        elif i < 16:
            back = [4, 5]      # 段1
        elif i < 23:
            back = [7, 8]      # 段2
        else:
            back = [10, 11]    # 段3
        front = [5, 10, 15, 20, 25]
        draws.append({"front": front, "back": back})
    return draws


def _make_all_equal():
    """各段次数全相等（std=0）：前区7期每期落不同段、后区4期每期落不同段"""
    draws = []
    for i in range(7):
        base = i * 5
        draws.append({
            "front": sorted([base + 1, base + 2, base + 3, base + 4, base + 5]),
            "back": [(i % 4) * 3 + 1, (i % 4) * 3 + 2],
        })
    return draws


def test_zone_filter_weight_structure():
    """权重结构有效（前区35个、后区12个，全正数）"""
    draws = _make_front_zone0_hot()
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n}"
        assert front_w[n] > 0, f"前区号码 {n} 权重应为正数, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n}"
        assert back_w[n] > 0, f"后区号码 {n} 权重应为正数, 实际: {back_w[n]}"
    print("PASS: zone_filter 权重结构有效")


def test_zone_partition_correct():
    """段划分正确：前区 1/5 同段、31/35 同段；后区 1/3 同段、10/12 同段"""
    assert _front_seg(1) == _front_seg(5) == 0, "前区1和5应同属段0"
    assert _front_seg(6) == _front_seg(10) == 1, "前区6和10应同属段1"
    assert _front_seg(31) == _front_seg(35) == 6, "前区31和35应同属段6"
    assert _front_seg(30) == 5 and _front_seg(31) == 6, "前区30/31应跨段"
    assert _back_seg(1) == _back_seg(3) == 0, "后区1和3应同属段0"
    assert _back_seg(4) == _back_seg(6) == 1, "后区4和6应同属段1"
    assert _back_seg(10) == _back_seg(12) == 3, "后区10和12应同属段3"
    assert _back_seg(9) == 2 and _back_seg(10) == 3, "后区9/10应跨段"
    print("PASS: 段划分正确")


def test_front_hot_zone_suppressed():
    """前区段0过热 → 段0号码(1-5)权重压到0.5，其余号码不受压制"""
    draws = _make_front_zone0_hot()
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    for n in range(1, 6):
        assert front_w[n] == 0.5, f"前区过热段号码 {n} 应压到0.5, 实际: {front_w[n]}"
    for n in range(6, FRONT_MAX + 1):
        assert front_w[n] >= 1.0, f"前区非过热段号码 {n} 应>=1.0, 实际: {front_w[n]}"
    print("PASS: 前区过热段 → 段内号码压到0.5")


def test_front_no_hot_zone_no_suppress():
    """前区无过热段 → 无压制（全部>=1.0，无0.5）"""
    draws = _make_front_balanced()
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] >= 1.0, f"前区号码 {n} 应>=1.0, 实际: {front_w[n]}"
        assert front_w[n] != 0.5, f"前区号码 {n} 不应为0.5"
    print("PASS: 前区无过热段 → 无压制")


def test_back_hot_zone_suppressed():
    """后区段0过热 → 段0号码(1-3)权重压到0.5，其余号码不受压制"""
    draws = _make_back_zone0_hot()
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    for n in range(1, 4):
        assert back_w[n] == 0.5, f"后区过热段号码 {n} 应压到0.5, 实际: {back_w[n]}"
    for n in range(4, BACK_MAX + 1):
        assert back_w[n] >= 1.0, f"后区非过热段号码 {n} 应>=1.0, 实际: {back_w[n]}"
    print("PASS: 后区过热段 → 段内号码压到0.5")


def test_back_no_hot_zone_no_suppress():
    """后区无过热段 → 无压制（全部>=1.0，无0.5）"""
    draws = _make_back_balanced()
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] >= 1.0, f"后区号码 {n} 应>=1.0, 实际: {back_w[n]}"
        assert back_w[n] != 0.5, f"后区号码 {n} 不应为0.5"
    print("PASS: 后区无过热段 → 无压制")


def test_zero_hit_segment_not_suppressed():
    """某段0次出号不触发压制：前区段2-6零次 → 其号码(11-35)保持>=1.0"""
    draws = _make_front_zone0_hot()
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    for n in range(11, FRONT_MAX + 1):  # 段2..段6 全部0次
        assert front_w[n] >= 1.0, f"零出号段号码 {n} 应>=1.0, 实际: {front_w[n]}"
        assert front_w[n] != 0.5, f"零出号段号码 {n} 不应被压制为0.5"
    print("PASS: 零出号段不触发压制")


def test_window_degenerate():
    """window<2 退化：只取1期过热数据 → 无压制（全1.0起算）"""
    draws = _make_front_zone0_hot(30)
    front_w, back_w = compute_weights(draws, strategy="zone_filter", window=1)
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] >= 1.0, f"前区号码 {n} window=1退化应>=1.0, 实际: {front_w[n]}"
        assert front_w[n] != 0.5, f"前区号码 {n} 退化时不应为0.5"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] >= 1.0, f"后区号码 {n} window=1退化应>=1.0, 实际: {back_w[n]}"
        assert back_w[n] != 0.5, f"后区号码 {n} 退化时不应为0.5"
    print("PASS: window<2 退化 → 无压制")


def test_std_zero_all_segments_equal():
    """std=0 / 各段次数全相等 → 退化无压制（每段恰等于期望，比值条件不成立）"""
    draws = _make_all_equal()
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] >= 1.0, f"std=0 时前区号码 {n} 应>=1.0, 实际: {front_w[n]}"
        assert front_w[n] != 0.5, f"std=0 时前区号码 {n} 不应为0.5"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] >= 1.0, f"std=0 时后区号码 {n} 应>=1.0, 实际: {back_w[n]}"
        assert back_w[n] != 0.5, f"std=0 时后区号码 {n} 不应为0.5"
    print("PASS: std=0 / 各段全相等 → 退化无压制")


def test_empty_draws():
    """空数据：返回均匀权重"""
    draws = []
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] == 1.0, f"空数据时前区 {n} 权重应为1.0, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] == 1.0, f"空数据时后区 {n} 权重应为1.0, 实际: {back_w[n]}"
    print("PASS: 空数据返回均匀权重")


def test_front_out_of_range_ignored():
    """前区越界号码（36 超上界 / 0 低出下界）不参与段统计：不崩溃，
    结果与剔除越界号后的合法输入完全一致（越界号按脏数据处理）"""
    draws = []
    for i in range(30):
        if i < 25:
            front = [1, 2, 3, 4, 5]
        else:
            front = [6, 7, 8, 9, 10]
        if i % 5 == 0:
            front = [36, 0, 1, 2, 3]  # 含越界号：36 超上界、0 低出下界
        draws.append({"front": front, "back": [1, 2]})
    cleaned = [{"front": [n for n in d["front"] if FRONT_MIN <= n <= FRONT_MAX],
                "back": d["back"]} for d in draws]
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    front_w_clean, back_w_clean = compute_weights(cleaned, strategy="zone_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] == front_w_clean[n], \
            f"前区 {n} 权重不一致: {front_w[n]} vs {front_w_clean[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] == back_w_clean[n], \
            f"后区 {n} 权重不一致: {back_w[n]} vs {back_w_clean[n]}"
    print("PASS: 前区越界号码(36/0)被忽略，不崩溃且结果与合法输入一致")


def test_back_out_of_range_ignored():
    """后区越界号码（13 超上界 / 0 低出下界）不参与段统计：不崩溃，
    结果与剔除越界号后的合法输入完全一致（越界号按脏数据处理）"""
    draws = []
    for i in range(20):
        if i < 18:
            back = [1, 2]
        else:
            back = [3, 4]
        if i % 5 == 0:
            back = [13, 0]  # 含越界号：13 超上界、0 低出下界
        draws.append({"front": [1, 2, 3, 4, 5], "back": back})
    cleaned = [{"front": d["front"],
                "back": [n for n in d["back"] if BACK_MIN <= n <= BACK_MAX]} for d in draws]
    front_w, back_w = compute_weights(draws, strategy="zone_filter")
    front_w_clean, back_w_clean = compute_weights(cleaned, strategy="zone_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] == front_w_clean[n], \
            f"前区 {n} 权重不一致: {front_w[n]} vs {front_w_clean[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] == back_w_clean[n], \
            f"后区 {n} 权重不一致: {back_w[n]} vs {back_w_clean[n]}"
    print("PASS: 后区越界号码(13/0)被忽略，不崩溃且结果与合法输入一致")


def test_integration_generate():
    """集成：generate_top_candidates 正常出结果"""
    draws = _make_front_zone0_hot(50)
    candidates = generate_top_candidates(draws, strategy="zone_filter", top_n=5)
    assert len(candidates) == 5, f"应生成5个候选，实际生成{len(candidates)}"
    for c in candidates:
        assert "front" in c, "候选缺少front字段"
        assert "back" in c, "候选缺少back字段"
        assert len(c["front"]) == 5, f"前区应有5个号码，实际有{len(c['front'])}"
        assert len(c["back"]) == 2, f"后区应有2个号码，实际有{len(c['back'])}"
        for n in c["front"]:
            assert FRONT_MIN <= n <= FRONT_MAX, f"前区号码{n}超出范围"
        for n in c["back"]:
            assert BACK_MIN <= n <= BACK_MAX, f"后区号码{n}超出范围"
    print("PASS: zone_filter 集成 generate_top_candidates 正常")


if __name__ == "__main__":
    test_zone_filter_weight_structure()
    test_zone_partition_correct()
    test_front_hot_zone_suppressed()
    test_front_no_hot_zone_no_suppress()
    test_back_hot_zone_suppressed()
    test_back_no_hot_zone_no_suppress()
    test_zero_hit_segment_not_suppressed()
    test_window_degenerate()
    test_std_zero_all_segments_equal()
    test_empty_draws()
    test_front_out_of_range_ignored()
    test_back_out_of_range_ignored()
    test_integration_generate()
    print("\nAll zone_filter strategy tests passed!")
