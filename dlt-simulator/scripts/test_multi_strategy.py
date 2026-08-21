#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for multi-strategy combination ("+") support in generator.py"""
import sys
import os
import warnings

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generator import (
    compute_weights, _compute_weights_single, _parse_strategies, _KNOWN_STRATEGIES,
)
from common import load_config

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]


def create_mock_draws():
    """创建模拟历史数据用于测试（固定 100 期）"""
    draws = []
    for i in range(100):
        front = sorted([10, 15, 20, 25, 30])
        back = sorted([5, 10])
        draws.append({"front": front, "back": back})
    return draws


def _capture_warnings(fn):
    """在 catch_warnings(record=True) 下执行 fn，返回 (结果, 警告列表)"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = fn()
    return result, w


def test_parse_single_equivalent():
    """对 _KNOWN_STRATEGIES 全部 11 名：compute_weights(name) == _compute_weights_single(name)"""
    draws = create_mock_draws()
    for name in _KNOWN_STRATEGIES:
        fw, bw = compute_weights(draws, name)
        fw_s, bw_s = _compute_weights_single(draws, name)
        assert fw == fw_s, f"策略 {name} 前区权重不一致"
        assert bw == bw_s, f"策略 {name} 后区权重不一致"
    print(f"PASS: 全部 {len(_KNOWN_STRATEGIES)} 个策略单名等价")


def test_parse_unknown_warn_skip():
    """'hot+foobar' == 'hot'，且恰好 1 条 UserWarning"""
    draws = create_mock_draws()
    (fw, bw), warns = _capture_warnings(
        lambda: compute_weights(draws, "hot+foobar"))
    fw_hot, bw_hot = compute_weights(draws, "hot")
    assert fw == fw_hot and bw == bw_hot, "未知策略应被跳过，结果等于 hot"
    assert len(warns) == 1, f"应恰好 1 条警告, 实际 {len(warns)}"
    assert issubclass(warns[0].category, UserWarning)
    print("PASS: 未知策略跳过 + 恰好 1 条 UserWarning")


def test_parse_duplicate_dedup():
    """'hot+hot'=='hot'；'hot+cold+hot'=='hot+cold'"""
    draws = create_mock_draws()
    fw1, bw1 = compute_weights(draws, "hot+hot")
    fw_hot, bw_hot = compute_weights(draws, "hot")
    assert fw1 == fw_hot and bw1 == bw_hot, "重复策略应去重"

    fw2, bw2 = compute_weights(draws, "hot+cold+hot")
    fw3, bw3 = compute_weights(draws, "hot+cold")
    assert fw2 == fw3 and bw2 == bw3, "乱序重复应去重保序"
    print("PASS: 重复策略去重")


def test_parse_empty_fallback():
    """''、' '、'foo+bar' 均 == 'balanced'（后两个有 warn）"""
    draws = create_mock_draws()
    fw_b, bw_b = compute_weights(draws, "balanced")

    (fw1, bw1), w1 = _capture_warnings(lambda: compute_weights(draws, ""))
    assert fw1 == fw_b and bw1 == bw_b, "空字符串应回退 balanced"
    assert len(w1) == 0, "空字符串不应有警告"

    (fw2, bw2), w2 = _capture_warnings(lambda: compute_weights(draws, " "))
    assert fw2 == fw_b and bw2 == bw_b, "空白字符串应回退 balanced"
    assert len(w2) == 0, "空白字符串不应有警告"

    (fw3, bw3), w3 = _capture_warnings(lambda: compute_weights(draws, "foo+bar"))
    assert fw3 == fw_b and bw3 == bw_b, "全未知策略应回退 balanced"
    assert len(w3) == 2, f"两个未知策略应产生 2 条警告, 实际 {len(w3)}"
    assert all(issubclass(x.category, UserWarning) for x in w3)
    print("PASS: 空表达式回退 balanced")


def test_parse_whitespace_robust():
    """' hot + tail_filter ' == 'hot+tail_filter'；'hot++cold'=='hot+cold'"""
    draws = create_mock_draws()
    fw1, bw1 = compute_weights(draws, " hot + tail_filter ")
    fw2, bw2 = compute_weights(draws, "hot+tail_filter")
    assert fw1 == fw2 and bw1 == bw2, "首尾空格应被容忍"

    fw3, bw3 = compute_weights(draws, "hot++cold")
    fw4, bw4 = compute_weights(draws, "hot+cold")
    assert fw3 == fw4 and bw3 == bw4, "空段应被容忍"
    print("PASS: 空白/空段鲁棒性")


def test_multi_product_front():
    """逐号 front_w_multi[n] == front_w_hot[n] * front_w_tail[n]（容差 1e-9）"""
    draws = create_mock_draws()
    fw_m, _ = compute_weights(draws, "hot+tail_filter")
    fw_hot, _ = compute_weights(draws, "hot")
    fw_tail, _ = compute_weights(draws, "tail_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        expect = fw_hot[n] * fw_tail[n]
        assert abs(fw_m[n] - expect) <= 1e-9, \
            f"前区 {n}: multi={fw_m[n]} expect={expect}"
    print("PASS: 前区逐号相乘融合")


def test_multi_product_back():
    """逐号 back_w_multi[n] == back_w_hot[n] * back_w_tail[n]"""
    draws = create_mock_draws()
    _, bw_m = compute_weights(draws, "hot+tail_filter")
    _, bw_hot = compute_weights(draws, "hot")
    _, bw_tail = compute_weights(draws, "tail_filter")
    for n in range(BACK_MIN, BACK_MAX + 1):
        expect = bw_hot[n] * bw_tail[n]
        assert abs(bw_m[n] - expect) <= 1e-9, \
            f"后区 {n}: multi={bw_m[n]} expect={expect}"
    print("PASS: 后区逐号相乘融合")


def test_multi_back_no_trend_branch():
    """'hot+trend' 后区 == 'hot+balanced' 后区（trend 后区无分支按 balanced）"""
    draws = create_mock_draws()
    _, bw_t = compute_weights(draws, "hot+trend")
    _, bw_b = compute_weights(draws, "hot+balanced")
    assert bw_t == bw_b, "trend 后区应按 balanced 计算"
    print("PASS: 组合中 trend 后区按 balanced")


def test_multi_back_no_even_filter_branch():
    """'cold+even_filter' 后区 == 'cold+balanced' 后区（even_filter 后区无分支）"""
    draws = create_mock_draws()
    _, bw_e = compute_weights(draws, "cold+even_filter")
    _, bw_b = compute_weights(draws, "cold+balanced")
    assert bw_e == bw_b, "even_filter 后区应按 balanced 计算"
    print("PASS: 组合中 even_filter 后区按 balanced")


def test_multi_empty_data():
    """compute_weights([], 'hot+cold') 全 1.0，且 == compute_weights([], 'balanced')"""
    fw, bw = compute_weights([], "hot+cold")
    fw_b, bw_b = compute_weights([], "balanced")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert fw[n] == 1.0, f"空数据前区 {n} 应为 1.0"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert bw[n] == 1.0, f"空数据后区 {n} 应为 1.0"
    assert fw == fw_b and bw == bw_b
    print("PASS: 空数据全 1.0 且与 balanced 一致")


def test_multi_window_propagation():
    """window=5 时逐号 == 两个单策略 window=5 之积"""
    draws = create_mock_draws()
    fw_m, bw_m = compute_weights(draws, "hot+tail_filter", window=5)
    fw_hot, bw_hot = compute_weights(draws, "hot", window=5)
    fw_tail, bw_tail = compute_weights(draws, "tail_filter", window=5)
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        expect = fw_hot[n] * fw_tail[n]
        assert abs(fw_m[n] - expect) <= 1e-9, \
            f"window 前区 {n}: multi={fw_m[n]} expect={expect}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        expect = bw_hot[n] * bw_tail[n]
        assert abs(bw_m[n] - expect) <= 1e-9, \
            f"window 后区 {n}: multi={bw_m[n]} expect={expect}"
    print("PASS: window 参数正确透传")


def test_multi_all_keys_positive():
    """键齐全、所有权重 > 0"""
    draws = create_mock_draws()
    fw, bw = compute_weights(draws, "hot+cold+trend+even_filter+tail_filter")
    assert set(fw.keys()) == set(range(FRONT_MIN, FRONT_MAX + 1)), "前区键不全"
    assert set(bw.keys()) == set(range(BACK_MIN, BACK_MAX + 1)), "后区键不全"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert fw[n] > 0, f"前区 {n} 权重应为正, 实际 {fw[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert bw[n] > 0, f"后区 {n} 权重应为正, 实际 {bw[n]}"
    print("PASS: 键齐全且所有权重为正")


def test_multi_no_normalization():
    """sum(front_w_multi) != sum(front_w_hot)（未归一化证据）"""
    draws = create_mock_draws()
    fw_m, _ = compute_weights(draws, "hot+tail_filter")
    fw_hot, _ = compute_weights(draws, "hot")
    s_m = sum(fw_m.values())
    s_h = sum(fw_hot.values())
    assert abs(s_m - s_h) > 1e-9, f"多策略应未归一化: sum_multi={s_m} sum_hot={s_h}"
    print(f"PASS: 未归一化 (sum_multi={s_m} != sum_hot={s_h})")


if __name__ == "__main__":
    test_parse_single_equivalent()
    test_parse_unknown_warn_skip()
    test_parse_duplicate_dedup()
    test_parse_empty_fallback()
    test_parse_whitespace_robust()
    test_multi_product_front()
    test_multi_product_back()
    test_multi_back_no_trend_branch()
    test_multi_back_no_even_filter_branch()
    test_multi_empty_data()
    test_multi_window_propagation()
    test_multi_all_keys_positive()
    test_multi_no_normalization()
    print("\nAll multi-strategy tests passed!")
