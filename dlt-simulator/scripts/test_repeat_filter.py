#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for repeat_filter strategy in generator.py

repeat_filter（重号过滤）：压制「上期（最近一期）已开出的号码」权重，
体现彩票「重号概率低」的统计规律。

- 前区（1-35）：上期开出的号码（在 data[0]["front"] 中）→ 权重压到 0.5；
  未开出的 → balanced 基础权重（1.0 + hot 加成 1.5 + miss>15 加成 1.0 + rising 加成 0.5）
- 后区（1-12）：上期开出的号码（在 data[0]["back"] 中）→ 权重压到 0.5；
  未开出的 → balanced 基础权重
- 边界：空数据（total==0）走已有空数据退化（全 1.0）；total>=1 时 data[0] 即上期；
  前后区独立；window 只截取统计期数范围，data[0] 仍是最近一期。
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


def _assert_close(a, b, tol=1e-9):
    assert abs(a - b) <= tol, f"期望 {a} == {b}（容差 {tol}）"


def test_known_strategies_contains_repeat_filter():
    """repeat_filter 已注册到 _KNOWN_STRATEGIES"""
    assert "repeat_filter" in _KNOWN_STRATEGIES, "repeat_filter 未加入 _KNOWN_STRATEGIES"
    print("PASS: repeat_filter 已注册到 _KNOWN_STRATEGIES")


def test_weight_structure():
    """权重结构有效（前区35个、后区12个，全正数）"""
    draws = _make_history(30)
    front_w, back_w = compute_weights(draws, strategy="repeat_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n}"
        assert front_w[n] > 0, f"前区号码 {n} 权重应为正数, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n}"
        assert back_w[n] > 0, f"后区号码 {n} 权重应为正数, 实际: {back_w[n]}"
    print("PASS: repeat_filter 权重结构有效")


def test_front_repeat_numbers_suppressed():
    """前区：上期开出的号码权重==0.5，未开出号码>=1.0"""
    draws = _make_history(30)
    last_front = set(draws[0]["front"])
    assert last_front == {1, 2, 3, 4, 5}
    front_w, _ = compute_weights(draws, strategy="repeat_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n in last_front:
            _assert_close(front_w[n], 0.5, tol=1e-9), \
                f"前区上期号码 {n} 应压到0.5, 实际: {front_w[n]}"
        else:
            assert front_w[n] >= 1.0, f"前区未开出号码 {n} 应>=1.0, 实际: {front_w[n]}"
    print("PASS: 前区上期号码压到0.5，未开出号码>=1.0")


def test_front_non_repeat_equals_balanced():
    """前区：未开出的号码权重与 balanced 策略完全相同"""
    draws = _make_history(30)
    last_front = set(draws[0]["front"])
    rf_fw, _ = compute_weights(draws, strategy="repeat_filter")
    bal_fw, _ = compute_weights(draws, strategy="balanced")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n not in last_front:
            _assert_close(rf_fw[n], bal_fw[n]), \
                f"前区未开出号码 {n} 应等于balanced权重, repeat_filter={rf_fw[n]} balanced={bal_fw[n]}"
    print("PASS: 前区未开出号码 == balanced 权重")


def test_back_repeat_numbers_suppressed():
    """后区：上期开出的号码权重==0.5，未开出号码>=1.0"""
    draws = _make_history(30)
    last_back = set(draws[0]["back"])
    assert last_back == {1, 2}
    _, back_w = compute_weights(draws, strategy="repeat_filter")
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n in last_back:
            _assert_close(back_w[n], 0.5, tol=1e-9), \
                f"后区上期号码 {n} 应压到0.5, 实际: {back_w[n]}"
        else:
            assert back_w[n] >= 1.0, f"后区未开出号码 {n} 应>=1.0, 实际: {back_w[n]}"
    print("PASS: 后区上期号码压到0.5，未开出号码>=1.0")


def test_back_non_repeat_equals_balanced():
    """后区：未开出的号码权重与 balanced 策略完全相同"""
    draws = _make_history(30)
    last_back = set(draws[0]["back"])
    _, rf_bw = compute_weights(draws, strategy="repeat_filter")
    _, bal_bw = compute_weights(draws, strategy="balanced")
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n not in last_back:
            _assert_close(rf_bw[n], bal_bw[n]), \
                f"后区未开出号码 {n} 应等于balanced权重, repeat_filter={rf_bw[n]} balanced={bal_bw[n]}"
    print("PASS: 后区未开出号码 == balanced 权重")


def test_empty_draws():
    """空数据（total==0）：前区/后区全 1.0（走已有空数据退化）"""
    front_w, back_w = compute_weights([], strategy="repeat_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        _assert_close(front_w[n], 1.0), f"空数据时前区 {n} 权重应为1.0, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        _assert_close(back_w[n], 1.0), f"空数据时后区 {n} 权重应为1.0, 实际: {back_w[n]}"
    print("PASS: 空数据 → 前区/后区全 1.0")


def test_single_draw():
    """单期数据（total==1）：上期号码（即唯一那期）压到0.5，其余 == balanced"""
    draws = _make_history(1, last_front=(7, 12, 18, 25, 33), last_back=(4, 9))
    last_front = set(draws[0]["front"])
    last_back = set(draws[0]["back"])
    rf_fw, rf_bw = compute_weights(draws, strategy="repeat_filter")
    bal_fw, bal_bw = compute_weights(draws, strategy="balanced")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n in last_front:
            _assert_close(rf_fw[n], 0.5), f"单期数据前区 {n} 应压到0.5, 实际: {rf_fw[n]}"
        else:
            _assert_close(rf_fw[n], bal_fw[n]), \
                f"单期数据前区 {n} 应等于balanced, 实际: {rf_fw[n]} vs {bal_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n in last_back:
            _assert_close(rf_bw[n], 0.5), f"单期数据后区 {n} 应压到0.5, 实际: {rf_bw[n]}"
        else:
            _assert_close(rf_bw[n], bal_bw[n]), \
                f"单期数据后区 {n} 应等于balanced, 实际: {rf_bw[n]} vs {bal_bw[n]}"
    print("PASS: 单期数据 → 上期号码压到0.5，其余 == balanced")


def test_window_keeps_data0_as_last():
    """window 只截取统计期数：data[0] 仍是最近一期，压制不受 window 影响"""
    draws = _make_history(30)
    last_front = set(draws[0]["front"])
    last_back = set(draws[0]["back"])
    rf_fw, rf_bw = compute_weights(draws, strategy="repeat_filter", window=3)
    bal_fw, bal_bw = compute_weights(draws, strategy="balanced", window=3)
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n in last_front:
            _assert_close(rf_fw[n], 0.5), f"window=3 时前区 {n} 应压到0.5, 实际: {rf_fw[n]}"
        else:
            _assert_close(rf_fw[n], bal_fw[n]), \
                f"window=3 时前区 {n} 应等于balanced(window=3), 实际: {rf_fw[n]} vs {bal_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n in last_back:
            _assert_close(rf_bw[n], 0.5), f"window=3 时后区 {n} 应压到0.5, 实际: {rf_bw[n]}"
        else:
            _assert_close(rf_bw[n], bal_bw[n]), \
                f"window=3 时后区 {n} 应等于balanced(window=3), 实际: {rf_bw[n]} vs {bal_bw[n]}"
    print("PASS: window=3 时 data[0] 仍为最近一期，压制不受 window 影响")


def test_combination_repeat_filter_hot():
    """repeat_filter+hot 组合：product 融合正常（= 两单策略逐号相乘，不报错）"""
    draws = _make_history(30)
    last_front = set(draws[0]["front"])
    last_back = set(draws[0]["back"])
    rf_fw, rf_bw = compute_weights(draws, strategy="repeat_filter")
    hot_fw, hot_bw = compute_weights(draws, strategy="hot")
    comb_fw, comb_bw = compute_weights(draws, strategy="repeat_filter+hot")
    assert len(comb_fw) == FRONT_MAX - FRONT_MIN + 1, "组合后前区权重数量错误"
    assert len(comb_bw) == BACK_MAX - BACK_MIN + 1, "组合后后区权重数量错误"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        _assert_close(comb_fw[n], rf_fw[n] * hot_fw[n]), \
            f"前区 {n} 组合权重应为 product: {comb_fw[n]} vs {rf_fw[n] * hot_fw[n]}"
        if n in last_front:
            # 重号在组合中仍被压制（0.5 * hot权重 < 未重号的平衡权重 * hot权重 不保证，但 0.5 因子应保留）
            _assert_close(comb_fw[n], 0.5 * hot_fw[n]), f"前区重号 {n} 组合权重应含0.5压制因子"
    for n in range(BACK_MIN, BACK_MAX + 1):
        _assert_close(comb_bw[n], rf_bw[n] * hot_bw[n]), \
            f"后区 {n} 组合权重应为 product: {comb_bw[n]} vs {rf_bw[n] * hot_bw[n]}"
        if n in last_back:
            _assert_close(comb_bw[n], 0.5 * hot_bw[n]), f"后区重号 {n} 组合权重应含0.5压制因子"
    print("PASS: repeat_filter+hot 组合 product 融合正常")


def test_out_of_range_in_last_draw_ignored():
    """data[0] 含越界号码（前区 36/0、后区 13/0）：不崩溃，
    越界号不参与压制判定，仅范围内号码按规则处理"""
    draws = _make_history(30)
    dirty = [dict(d) for d in draws]
    dirty[0] = {"front": [36, 0, 1, 2, 3], "back": [13, 0, 1]}
    front_w, back_w = compute_weights(dirty, strategy="repeat_filter")
    # 越界号(36/0/13/0)不压制任何范围内号码；范围内重号 1,2,3（前区）和 1（后区）压到 0.5
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n in {1, 2, 3}:
            _assert_close(front_w[n], 0.5), f"前区 {n} 应压到0.5, 实际: {front_w[n]}"
        else:
            assert front_w[n] >= 1.0, f"前区 {n} 应>=1.0, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n == 1:
            _assert_close(back_w[n], 0.5), f"后区 {n} 应压到0.5, 实际: {back_w[n]}"
        else:
            assert back_w[n] >= 1.0, f"后区 {n} 应>=1.0, 实际: {back_w[n]}"
    print("PASS: data[0] 越界号码被忽略，不崩溃且压制正确")


def test_integration_generate():
    """集成：generate_top_candidates 使用 repeat_filter 正常出结果"""
    draws = _make_history(50)
    candidates = generate_top_candidates(draws, strategy="repeat_filter", top_n=5)
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
    print("PASS: repeat_filter 集成 generate_top_candidates 正常")


if __name__ == "__main__":
    test_known_strategies_contains_repeat_filter()
    test_weight_structure()
    test_front_repeat_numbers_suppressed()
    test_front_non_repeat_equals_balanced()
    test_back_repeat_numbers_suppressed()
    test_back_non_repeat_equals_balanced()
    test_empty_draws()
    test_single_draw()
    test_window_keeps_data0_as_last()
    test_combination_repeat_filter_hot()
    test_out_of_range_in_last_draw_ignored()
    test_integration_generate()
    print("\nAll repeat_filter strategy tests passed!")
