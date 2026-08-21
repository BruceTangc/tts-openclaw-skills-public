#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for span_filter strategy in generator.py

span_filter（跨度过滤）：压制「跨度偏离历史均值」的号码，实现跨度回归。

- 前区（1-35，取5）：window 期每期跨度 max(front)-min(front) 的均值 μ_f，
  理论跨度中心 = 24。
  - μ_f > 24（历史偏分散）→ 压制「极端号」：n ≤ 10 或 n ≥ 26 压到 0.5
  - μ_f < 24（历史偏集中）→ 压制「中心号」：11 ≤ n ≤ 25 压到 0.5
  - 其余按 balanced 基础权重（1.0 + hot 1.5 + miss>15 1.0 + rising 0.5）
- 后区（1-12，取2）：window 期后区跨度均值 μ_b，理论中心 = 6。
  - μ_b > 6 → 压制极端号：n ≤ 2 或 n ≥ 11 压到 0.5
  - μ_b < 6 → 压制中心号：3 ≤ n ≤ 10 压到 0.5
  - 其余按 balanced（1.0 + hot 1.5）
- 边界：空数据（total==0）→ 全 1.0；单期（total==1）跨度样本不足 → 退化
  balanced 不压制；window 只截取统计期数；越界号码（36/0/13/0）忽略不崩溃；
  前后区独立统计。
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

FRONT_SPAN_CENTER = 24.0
BACK_SPAN_CENTER = 6.0


def _assert_close(a, b, tol=1e-9):
    assert abs(a - b) <= tol, f"期望 {a} == {b}（容差 {tol}）"


def _make_front_wide(n=30):
    """前区跨度大（μ_f=34 > 24）：每期 front 跨 34，应压制极端号 n≤10 或 n≥26"""
    draws = []
    for _ in range(n):
        draws.append({"front": [1, 30, 31, 32, 35], "back": [4, 5]})
    return draws


def _make_front_narrow(n=30):
    """前区跨度小（μ_f=4 < 24）：每期 front 跨 4，应压制中心号 11≤n≤25"""
    draws = []
    for _ in range(n):
        draws.append({"front": [5, 6, 7, 8, 9], "back": [4, 5]})
    return draws


def _make_back_wide(n=30):
    """后区跨度大（μ_b=11 > 6）：每期 back 跨 11，应压制极端号 n≤2 或 n≥11"""
    draws = []
    for _ in range(n):
        draws.append({"front": [5, 10, 15, 20, 25], "back": [1, 12]})
    return draws


def _make_back_narrow(n=30):
    """后区跨度小（μ_b=1 < 6）：每期 back 跨 1，应压制中心号 3≤n≤10"""
    draws = []
    for _ in range(n):
        draws.append({"front": [5, 10, 15, 20, 25], "back": [4, 5]})
    return draws


def test_known_strategies_contains_span_filter():
    """span_filter 已注册到 _KNOWN_STRATEGIES"""
    assert "span_filter" in _KNOWN_STRATEGIES, "span_filter 未加入 _KNOWN_STRATEGIES"
    print("PASS: span_filter 已注册到 _KNOWN_STRATEGIES")


def test_weight_structure():
    """权重结构有效（前区35个、后区12个，全正数）"""
    draws = _make_front_wide(30)
    front_w, back_w = compute_weights(draws, strategy="span_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n}"
        assert front_w[n] > 0, f"前区号码 {n} 权重应为正数, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n}"
        assert back_w[n] > 0, f"后区号码 {n} 权重应为正数, 实际: {back_w[n]}"
    print("PASS: span_filter 权重结构有效")


def test_front_mu_above_center_suppresses_extremes():
    """前区 μ_f>24：n≤10 或 n≥26 权重==0.5，其余 == balanced"""
    draws = _make_front_wide(30)
    spans = [max(d["front"]) - min(d["front"]) for d in draws]
    mu = sum(spans) / len(spans)
    assert mu > FRONT_SPAN_CENTER, f"测试数据 μ_f={mu} 应>24"
    sf_fw, _ = compute_weights(draws, strategy="span_filter")
    bal_fw, _ = compute_weights(draws, strategy="balanced")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n <= 10 or n >= 26:
            _assert_close(sf_fw[n], 0.5), \
                f"μ_f>24 时极端号 {n} 应压到0.5, 实际: {sf_fw[n]}"
        else:
            _assert_close(sf_fw[n], bal_fw[n]), \
                f"μ_f>24 时中心号 {n} 应等于balanced, span_filter={sf_fw[n]} balanced={bal_fw[n]}"
    print("PASS: 前区 μ_f>24 → 极端号0.5，其余==balanced")


def test_front_mu_below_center_suppresses_center():
    """前区 μ_f<24：11≤n≤25 权重==0.5，其余 == balanced"""
    draws = _make_front_narrow(30)
    spans = [max(d["front"]) - min(d["front"]) for d in draws]
    mu = sum(spans) / len(spans)
    assert mu < FRONT_SPAN_CENTER, f"测试数据 μ_f={mu} 应<24"
    sf_fw, _ = compute_weights(draws, strategy="span_filter")
    bal_fw, _ = compute_weights(draws, strategy="balanced")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if 11 <= n <= 25:
            _assert_close(sf_fw[n], 0.5), \
                f"μ_f<24 时中心号 {n} 应压到0.5, 实际: {sf_fw[n]}"
        else:
            _assert_close(sf_fw[n], bal_fw[n]), \
                f"μ_f<24 时极端号 {n} 应等于balanced, span_filter={sf_fw[n]} balanced={bal_fw[n]}"
    print("PASS: 前区 μ_f<24 → 中心号0.5，其余==balanced")


def test_back_mu_above_center_suppresses_extremes():
    """后区 μ_b>6：n≤2 或 n≥11 权重==0.5"""
    draws = _make_back_wide(30)
    spans = [max(d["back"]) - min(d["back"]) for d in draws]
    mu = sum(spans) / len(spans)
    assert mu > BACK_SPAN_CENTER, f"测试数据 μ_b={mu} 应>6"
    _, sf_bw = compute_weights(draws, strategy="span_filter")
    _, bal_bw = compute_weights(draws, strategy="balanced")
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n <= 2 or n >= 11:
            _assert_close(sf_bw[n], 0.5), \
                f"μ_b>6 时极端号 {n} 应压到0.5, 实际: {sf_bw[n]}"
        else:
            _assert_close(sf_bw[n], bal_bw[n]), \
                f"μ_b>6 时中心号 {n} 应等于balanced, span_filter={sf_bw[n]} balanced={bal_bw[n]}"
    print("PASS: 后区 μ_b>6 → 极端号0.5，其余==balanced")


def test_back_mu_below_center_suppresses_center():
    """后区 μ_b<6：3≤n≤10 权重==0.5"""
    draws = _make_back_narrow(30)
    spans = [max(d["back"]) - min(d["back"]) for d in draws]
    mu = sum(spans) / len(spans)
    assert mu < BACK_SPAN_CENTER, f"测试数据 μ_b={mu} 应<6"
    _, sf_bw = compute_weights(draws, strategy="span_filter")
    _, bal_bw = compute_weights(draws, strategy="balanced")
    for n in range(BACK_MIN, BACK_MAX + 1):
        if 3 <= n <= 10:
            _assert_close(sf_bw[n], 0.5), \
                f"μ_b<6 时中心号 {n} 应压到0.5, 实际: {sf_bw[n]}"
        else:
            _assert_close(sf_bw[n], bal_bw[n]), \
                f"μ_b<6 时极端号 {n} 应等于balanced, span_filter={sf_bw[n]} balanced={bal_bw[n]}"
    print("PASS: 后区 μ_b<6 → 中心号0.5，其余==balanced")


def test_front_back_independent():
    """前后区独立统计：前区 μ_f>24 压制极端号，后区不受影响（μ_b=1 压制中心号）"""
    draws = _make_front_wide(30)  # front 跨34(μ_f>24)，back=[4,5] 跨1(μ_b<6)
    sf_fw, sf_bw = compute_weights(draws, strategy="span_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n <= 10 or n >= 26:
            _assert_close(sf_fw[n], 0.5), f"前区极端号 {n} 应压到0.5, 实际: {sf_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        if 3 <= n <= 10:
            _assert_close(sf_bw[n], 0.5), f"后区中心号 {n} 应压到0.5, 实际: {sf_bw[n]}"
    print("PASS: 前后区独立统计（前区压制极端、后区压制中心）")


def test_empty_draws():
    """空数据（total==0）：前区/后区全 1.0（走已有空数据退化）"""
    front_w, back_w = compute_weights([], strategy="span_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        _assert_close(front_w[n], 1.0), f"空数据时前区 {n} 权重应为1.0, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        _assert_close(back_w[n], 1.0), f"空数据时后区 {n} 权重应为1.0, 实际: {back_w[n]}"
    print("PASS: 空数据 → 前区/后区全 1.0")


def test_single_draw_degrades_to_balanced():
    """单期（total==1）：跨度只有 1 个样本无法判断偏离 → 退化 balanced（不压制）"""
    draws = [{"front": [1, 30, 31, 32, 35], "back": [1, 12]}]
    sf_fw, sf_bw = compute_weights(draws, strategy="span_filter")
    bal_fw, bal_bw = compute_weights(draws, strategy="balanced")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        _assert_close(sf_fw[n], bal_fw[n]), \
            f"单期前区 {n} 应退化balanced, span_filter={sf_fw[n]} balanced={bal_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        _assert_close(sf_bw[n], bal_bw[n]), \
            f"单期后区 {n} 应退化balanced, span_filter={sf_bw[n]} balanced={bal_bw[n]}"
    print("PASS: 单期 → 退化 balanced，不压制")


def test_two_draws_can_suppress():
    """两期（total==2，跨度样本=2）：可判断偏离 → 正常压制"""
    draws = [{"front": [1, 30, 31, 32, 35], "back": [1, 12]},
             {"front": [2, 29, 30, 33, 34], "back": [2, 11]}]
    sf_fw, sf_bw = compute_weights(draws, strategy="span_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n <= 10 or n >= 26:
            _assert_close(sf_fw[n], 0.5), f"两期前区极端号 {n} 应压到0.5, 实际: {sf_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n <= 2 or n >= 11:
            _assert_close(sf_bw[n], 0.5), f"两期后区极端号 {n} 应压到0.5, 实际: {sf_bw[n]}"
    print("PASS: 两期 → 正常压制（跨度样本≥2）")


def test_window_truncates_stats():
    """window 只截取统计期数：最近3期 μ_f>24，全量 μ_f<24 → window=3 压制极端号"""
    # data[0..2]（最近3期）跨 34，data[3..] 跨 4 → 全量 μ=(3*34+27*4)/30=7<24
    draws = []
    for i in range(30):
        if i < 3:
            front = [1, 30, 31, 32, 35]
        else:
            front = [5, 6, 7, 8, 9]
        draws.append({"front": front, "back": [4, 5]})
    spans_all = [max(d["front"]) - min(d["front"]) for d in draws]
    mu_all = sum(spans_all) / len(spans_all)
    assert mu_all < FRONT_SPAN_CENTER, f"全量 μ_f={mu_all} 应<24"
    # 无 window：压制中心号
    sf_fw_full, _ = compute_weights(draws, strategy="span_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if 11 <= n <= 25:
            _assert_close(sf_fw_full[n], 0.5), f"全量数据中心号 {n} 应压到0.5"
    # window=3：只统计最近3期（跨34）→ 压制极端号
    sf_fw_w3, _ = compute_weights(draws, strategy="span_filter", window=3)
    bal_fw_w3, _ = compute_weights(draws, strategy="balanced", window=3)
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n <= 10 or n >= 26:
            _assert_close(sf_fw_w3[n], 0.5), f"window=3 极端号 {n} 应压到0.5, 实际: {sf_fw_w3[n]}"
        else:
            _assert_close(sf_fw_w3[n], bal_fw_w3[n]), \
                f"window=3 中心号 {n} 应等于balanced(window=3), 实际: {sf_fw_w3[n]}"
    print("PASS: window 只截取统计期数范围（window=3 压制极端号，全量压制中心号）")


def test_window_single_degrades_to_balanced():
    """window=1（截取后仅1期）：跨度样本不足 → 退化 balanced，不压制"""
    draws = _make_front_wide(30)
    sf_fw, sf_bw = compute_weights(draws, strategy="span_filter", window=1)
    bal_fw, bal_bw = compute_weights(draws, strategy="balanced", window=1)
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        _assert_close(sf_fw[n], bal_fw[n]), \
            f"window=1 前区 {n} 应退化balanced, 实际: {sf_fw[n]} vs {bal_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        _assert_close(sf_bw[n], bal_bw[n]), \
            f"window=1 后区 {n} 应退化balanced, 实际: {sf_bw[n]} vs {bal_bw[n]}"
    print("PASS: window=1 → 退化 balanced，不压制")


def test_out_of_range_numbers_ignored():
    """历史数据含越界号码（前区 36/0、后区 13/0）：忽略不参与跨度统计，不崩溃"""
    # 基础数据：前区跨34（μ_f>24），后区跨11（μ_b>6）；把最近一期换成含越界号的脏数据
    draws = [{"front": [1, 30, 31, 32, 35], "back": [1, 12]} for _ in range(30)]
    dirty = [dict(d) for d in draws]
    dirty[0] = {"front": [36, 0, 1, 30, 35], "back": [13, 0, 1, 12]}
    # 越界号被忽略：dirty[0] 有效前区 {1,30,35} 跨 34（与其余期同跨），
    # 有效后区 {1,12} 跨 11（与其余期同跨）→ μ_f=34>24、μ_b=11>6，方向不变
    sf_fw, sf_bw = compute_weights(dirty, strategy="span_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n <= 10 or n >= 26:
            _assert_close(sf_fw[n], 0.5), f"越界场景前区极端号 {n} 应压到0.5, 实际: {sf_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        if n <= 2 or n >= 11:
            _assert_close(sf_bw[n], 0.5), f"越界场景后区极端号 {n} 应压到0.5, 实际: {sf_bw[n]}"
    print("PASS: 越界号码被忽略，不崩溃且跨度统计正确")


def test_combination_span_filter_hot():
    """span_filter+hot 组合：product 融合正常（= 两单策略逐号相乘）"""
    draws = _make_front_wide(30)
    sf_fw, sf_bw = compute_weights(draws, strategy="span_filter")
    hot_fw, hot_bw = compute_weights(draws, strategy="hot")
    comb_fw, comb_bw = compute_weights(draws, strategy="span_filter+hot")
    assert len(comb_fw) == FRONT_MAX - FRONT_MIN + 1, "组合后前区权重数量错误"
    assert len(comb_bw) == BACK_MAX - BACK_MIN + 1, "组合后后区权重数量错误"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        _assert_close(comb_fw[n], sf_fw[n] * hot_fw[n]), \
            f"前区 {n} 组合权重应为 product: {comb_fw[n]} vs {sf_fw[n] * hot_fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        _assert_close(comb_bw[n], sf_bw[n] * hot_bw[n]), \
            f"后区 {n} 组合权重应为 product: {comb_bw[n]} vs {sf_bw[n] * hot_bw[n]}"
    print("PASS: span_filter+hot 组合 product 融合正常")


def test_integration_generate():
    """集成：generate_top_candidates 使用 span_filter 正常出结果"""
    draws = _make_front_wide(50)
    candidates = generate_top_candidates(draws, strategy="span_filter", top_n=5)
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
    print("PASS: span_filter 集成 generate_top_candidates 正常")


if __name__ == "__main__":
    test_known_strategies_contains_span_filter()
    test_weight_structure()
    test_front_mu_above_center_suppresses_extremes()
    test_front_mu_below_center_suppresses_center()
    test_back_mu_above_center_suppresses_extremes()
    test_back_mu_below_center_suppresses_center()
    test_front_back_independent()
    test_empty_draws()
    test_single_draw_degrades_to_balanced()
    test_two_draws_can_suppress()
    test_window_truncates_stats()
    test_window_single_degrades_to_balanced()
    test_out_of_range_numbers_ignored()
    test_combination_span_filter_hot()
    test_integration_generate()
    print("\nAll span_filter strategy tests passed!")
