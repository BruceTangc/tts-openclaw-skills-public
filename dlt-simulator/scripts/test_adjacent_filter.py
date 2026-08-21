#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for adjacent_filter strategy in generator.py

adjacent_filter（邻号过滤）：压制「与最近一期（data[0]）开奖号码相差 1」
的号码权重，体现「邻号延续概率低」的统计规律。

- 前区（1-35，取5）：号码 n 与 data[0]["front"] 中任一号码 m 满足 |n-m|==1
  （n = m±1）→ 权重压到 0.5；非邻号 → balanced 基础权重
  （1.0 + hot 加成 1.5 + miss>15 加成 1.0 + rising 加成 0.5）
- 后区（1-12，取2）：号码 n 与 data[0]["back"] 中任一号码相差 1 → 权重压到 0.5；
  非邻号 → balanced 基础权重
- 边界：空数据（total==0）走已有空数据退化（全 1.0）；total>=1 时 data[0] 即最近一期；
  前后区独立；window 只截取统计期数范围，data[0] 仍是最近一期；越界号码忽略。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generator import compute_weights, generate_top_candidates, _KNOWN_STRATEGIES
from common import load_config

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]


def _make_history(n=30, last_front=(1, 2, 3, 4, 5), last_back=(1, 2)):
    """构造 n 期历史：最近一期（data[0]）= last_front + last_back，
    其余期前区循环 5 段、后区循环 3 组（保证有历史多样性）。"""
    draws = []
    for i in range(n):
        if i == 0:
            front = list(last_front)
            back = list(last_back)
        else:
            base = (i % 5) * 5
            front = sorted([base + 1, base + 2, base + 3, base + 4, base + 5])
            back = [(i % 3) + 1, (i % 3) + 4]
        draws.append({"front": front, "back": back})
    return draws


def _adjacent_set(numbers, lo, hi):
    """与 numbers 中任一号码相差 1 的（范围内）号码集合"""
    s = set()
    for m in numbers:
        if lo <= m <= hi:
            if m - 1 >= lo:
                s.add(m - 1)
            if m + 1 <= hi:
                s.add(m + 1)
    return s


def _assert_close(a, b, tol=1e-9):
    assert abs(a - b) <= tol, f"期望 {a} == {b}（容差 {tol}）"


def test_known_strategies_contains_adjacent_filter():
    """adjacent_filter 已注册到 _KNOWN_STRATEGIES"""
    assert "adjacent_filter" in _KNOWN_STRATEGIES, "adjacent_filter 未加入 _KNOWN_STRATEGIES"
    print("PASS: adjacent_filter 已注册到 _KNOWN_STRATEGIES")


def test_weight_structure():
    """权重结构有效（前区35个、后区12个，全正数）"""
    draws = _make_history(30)
    front_w, back_w = compute_weights(draws, strategy="adjacent_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n}"
        assert front_w[n] > 0, f"前区号码 {n} 权重应为正数, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n}"
        assert back_w[n] > 0, f"后区号码 {n} 权重应为正数, 实际: {back_w[n]}"
    print("PASS: adjacent_filter 权重结构有效")


def test_front_adjacent_numbers_suppressed():
    """前区：与最近一期号码相差1的号码权重==0.5，非邻号>=1.0"""
    draws = _make_history(30)
    last_front = draws[0]["front"]
    assert last_front == [1, 2, 3, 4, 5]
    # 邻号集 = {0..6 与 1..5 相差1} ∩ [1,35] = {1,2,3,4,5,6}
    adj = _adjacent_set(last_front, FRONT_MIN, FRONT_MAX)
    assert adj == {1, 2, 3, 4, 5, 6}, f"邻号集计算错误: {adj}"
    front_w, _ = compute_weights(draws, strategy="adjacent_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n in adj:
            _assert_close(front_w[n], 0.5, tol=1e-9), \
                f"前区邻号 {n} 应压到0.5, 实际: {front_w[n]}"
        else:
            assert front_w[n] >= 1.0, f"前区非邻号 {n} 应>=1.0, 实际: {front_w[n]}"
    print("PASS: 前区邻号压到0.5，非邻号>=1.0")


def test_front_non_adjacent_equals_balanced():
    """前区：非邻号权重与 balanced 策略完全相同"""
    draws = _make_history(30)
    adj = _adjacent_set(draws[0]["front"], FRONT_MIN, FRONT_MAX)
    af_fw, _ = compute_weights(draws, strategy="adjacent_filter")
    bal_fw, _ = compute_weights(draws, strategy="balanced")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n not in adj:
            _assert_close(af_fw[n], bal_fw[n]), \
                f"前区非邻号 {n} 应等于balanced权重, adjacent_filter={af_fw[n]} balanced={bal_fw[n]}"
    print("PASS: 前区非邻号 == balanced 权重")


def test_back_adjacent_numbers_suppressed():
    """后区：与最近一期号码相差1的号码权重==0.5，非邻号>=1.0"""
    draws = _make_history(30)
    last_back = draws[0]["back"]
    assert last_back == [1, 2]
    # 邻号集 = {1..3 与 1,2 相差1} ∩ [1,12] = {1,2,3}
    adj = _adjacent_set(last_back, BACK_MIN, BACK_MAX)
    assert adj == {1, 2, 3}, f"邻号集计算错误: {adj}"
    _, back_w = compute_weights(draws, strategy="adjacent_filter")
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n in adj:
            _assert_close(back_w[n], 0.5, tol=1e-9), \
                f"后区邻号 {n} 应压到0.5, 实际: {back_w[n]}"
        else:
            assert back_w[n] >= 1.0, f"后区非邻号 {n} 应>=1.0, 实际: {back_w[n]}"
    print("PASS: 后区邻号压到0.5，非邻号>=1.0")


def test_back_non_adjacent_equals_balanced():
    """后区：非邻号权重与 balanced 策略完全相同"""
    draws = _make_history(30)
    adj = _adjacent_set(draws[0]["back"], BACK_MIN, BACK_MAX)
    _, af_bw = compute_weights(draws, strategy="adjacent_filter")
    _, bal_bw = compute_weights(draws, strategy="balanced")
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n not in adj:
            _assert_close(af_bw[n], bal_bw[n]), \
                f"后区非邻号 {n} 应等于balanced权重, adjacent_filter={af_bw[n]} balanced={bal_bw[n]}"
    print("PASS: 后区非邻号 == balanced 权重")


def test_empty_draws():
    """空数据（total==0）：前区/后区全 1.0（走已有空数据退化）"""
    front_w, back_w = compute_weights([], strategy="adjacent_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        _assert_close(front_w[n], 1.0), f"空数据时前区 {n} 权重应为1.0, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        _assert_close(back_w[n], 1.0), f"空数据时后区 {n} 权重应为1.0, 实际: {back_w[n]}"
    print("PASS: 空数据 → 前区/后区全 1.0")


def test_single_draw():
    """单期数据（total==1）：邻号压到0.5，其余 == balanced"""
    draws = _make_history(1, last_front=(7, 12, 18, 25, 33), last_back=(4, 9))
    front_adj = _adjacent_set(draws[0]["front"], FRONT_MIN, FRONT_MAX)
    back_adj = _adjacent_set(draws[0]["back"], BACK_MIN, BACK_MAX)
    af_fw, af_bw = compute_weights(draws, strategy="adjacent_filter")
    bal_fw, bal_bw = compute_weights(draws, strategy="balanced")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n in front_adj:
            _assert_close(af_fw[n], 0.5), f"单期数据前区邻号 {n} 应压到0.5, 实际: {af_fw[n]}"
        else:
            _assert_close(af_fw[n], bal_fw[n]), \
                f"单期数据前区非邻号 {n} 应等于balanced, 实际: {af_fw[n]} vs {bal_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n in back_adj:
            _assert_close(af_bw[n], 0.5), f"单期数据后区邻号 {n} 应压到0.5, 实际: {af_bw[n]}"
        else:
            _assert_close(af_bw[n], bal_bw[n]), \
                f"单期数据后区非邻号 {n} 应等于balanced, 实际: {af_bw[n]} vs {bal_bw[n]}"
    print("PASS: 单期数据 → 邻号压到0.5，其余 == balanced")


def test_window_keeps_data0_as_last():
    """window 只截取统计期数：data[0] 仍是最近一期，压制不受 window 影响"""
    draws = _make_history(30)
    front_adj = _adjacent_set(draws[0]["front"], FRONT_MIN, FRONT_MAX)
    back_adj = _adjacent_set(draws[0]["back"], BACK_MIN, BACK_MAX)
    af_fw, af_bw = compute_weights(draws, strategy="adjacent_filter", window=3)
    bal_fw, bal_bw = compute_weights(draws, strategy="balanced", window=3)
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n in front_adj:
            _assert_close(af_fw[n], 0.5), f"window=3 时前区邻号 {n} 应压到0.5, 实际: {af_fw[n]}"
        else:
            _assert_close(af_fw[n], bal_fw[n]), \
                f"window=3 时前区非邻号 {n} 应等于balanced(window=3), 实际: {af_fw[n]} vs {bal_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n in back_adj:
            _assert_close(af_bw[n], 0.5), f"window=3 时后区邻号 {n} 应压到0.5, 实际: {af_bw[n]}"
        else:
            _assert_close(af_bw[n], bal_bw[n]), \
                f"window=3 时后区非邻号 {n} 应等于balanced(window=3), 实际: {af_bw[n]} vs {bal_bw[n]}"
    print("PASS: window=3 时 data[0] 仍为最近一期，压制不受 window 影响")


def test_combination_adjacent_filter_hot():
    """adjacent_filter+hot 组合：product 融合正常（= 两单策略逐号相乘，不报错）"""
    draws = _make_history(30)
    front_adj = _adjacent_set(draws[0]["front"], FRONT_MIN, FRONT_MAX)
    back_adj = _adjacent_set(draws[0]["back"], BACK_MIN, BACK_MAX)
    af_fw, af_bw = compute_weights(draws, strategy="adjacent_filter")
    hot_fw, hot_bw = compute_weights(draws, strategy="hot")
    comb_fw, comb_bw = compute_weights(draws, strategy="adjacent_filter+hot")
    assert len(comb_fw) == FRONT_MAX - FRONT_MIN + 1, "组合后前区权重数量错误"
    assert len(comb_bw) == BACK_MAX - BACK_MIN + 1, "组合后后区权重数量错误"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        _assert_close(comb_fw[n], af_fw[n] * hot_fw[n]), \
            f"前区 {n} 组合权重应为 product: {comb_fw[n]} vs {af_fw[n] * hot_fw[n]}"
        if n in front_adj:
            # 邻号在组合中仍被压制（0.5 因子应保留）
            _assert_close(comb_fw[n], 0.5 * hot_fw[n]), f"前区邻号 {n} 组合权重应含0.5压制因子"
    for n in range(BACK_MIN, BACK_MAX + 1):
        _assert_close(comb_bw[n], af_bw[n] * hot_bw[n]), \
            f"后区 {n} 组合权重应为 product: {comb_bw[n]} vs {af_bw[n] * hot_bw[n]}"
        if n in back_adj:
            _assert_close(comb_bw[n], 0.5 * hot_bw[n]), f"后区邻号 {n} 组合权重应含0.5压制因子"
    print("PASS: adjacent_filter+hot 组合 product 融合正常")


def test_out_of_range_in_last_draw_ignored():
    """data[0] 含越界号码（前区 36/0、后区 13/0）：不崩溃，
    越界号不参与邻号判定，仅范围内号码按规则处理"""
    draws = _make_history(30)
    dirty = [dict(d) for d in draws]
    dirty[0] = {"front": [36, 0, 10, 20, 30], "back": [13, 0, 5]}
    front_w, back_w = compute_weights(dirty, strategy="adjacent_filter")
    # 越界号(36/0/13/0)不参与；范围内号码 10,20,30（前区）和 5（后区）的邻号压到 0.5
    front_adj = _adjacent_set([10, 20, 30], FRONT_MIN, FRONT_MAX)
    back_adj = _adjacent_set([5], BACK_MIN, BACK_MAX)
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n in front_adj:
            _assert_close(front_w[n], 0.5), f"前区邻号 {n} 应压到0.5, 实际: {front_w[n]}"
        else:
            assert front_w[n] >= 1.0, f"前区非邻号 {n} 应>=1.0, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n in back_adj:
            _assert_close(back_w[n], 0.5), f"后区邻号 {n} 应压到0.5, 实际: {back_w[n]}"
        else:
            assert back_w[n] >= 1.0, f"后区非邻号 {n} 应>=1.0, 实际: {back_w[n]}"
    print("PASS: data[0] 越界号码被忽略，不崩溃且压制正确")


def test_integration_generate():
    """集成：generate_top_candidates 使用 adjacent_filter 正常出结果"""
    draws = _make_history(50)
    candidates = generate_top_candidates(draws, strategy="adjacent_filter", top_n=5)
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
    print("PASS: adjacent_filter 集成 generate_top_candidates 正常")


if __name__ == "__main__":
    test_known_strategies_contains_adjacent_filter()
    test_weight_structure()
    test_front_adjacent_numbers_suppressed()
    test_front_non_adjacent_equals_balanced()
    test_back_adjacent_numbers_suppressed()
    test_back_non_adjacent_equals_balanced()
    test_empty_draws()
    test_single_draw()
    test_window_keeps_data0_as_last()
    test_combination_adjacent_filter_hot()
    test_out_of_range_in_last_draw_ignored()
    test_integration_generate()
    print("\nAll adjacent_filter strategy tests passed!")
