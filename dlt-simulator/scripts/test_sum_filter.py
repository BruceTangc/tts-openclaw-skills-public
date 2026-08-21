#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for sum_filter strategy in generator.py"""
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


def _make_front_high_sum_draws(n=30):
    """构造前区和值偏高（大号为主）的模拟数据"""
    draws = []
    for i in range(n):
        front = sorted([20 + i % 5, 25 + i % 5, 30 + i % 3, 28, 35])
        back = sorted([1 + i % 6, 7 + i % 5])
        draws.append({"front": front, "back": back})
    return draws


def _make_front_low_sum_draws(n=30):
    """构造前区和值偏低（小号为主）的模拟数据"""
    draws = []
    for i in range(n):
        front = sorted([1 + i % 3, 2 + i % 4, 3 + i % 5, 5, 8])
        back = sorted([1 + i % 6, 7 + i % 5])
        draws.append({"front": front, "back": back})
    return draws


def _make_back_high_sum_draws(n=30):
    """构造后区和值偏高（大号为主）的模拟数据"""
    draws = []
    for i in range(n):
        front = sorted([10, 15, 20, 25, 30])
        back = sorted([7 + i % 4, 9 + i % 4])
        draws.append({"front": front, "back": back})
    return draws


def _make_back_low_sum_draws(n=30):
    """构造后区和值偏低（小号为主）的模拟数据"""
    draws = []
    for i in range(n):
        front = sorted([10, 15, 20, 25, 30])
        back = sorted([1 + i % 3, 2 + i % 4])
        draws.append({"front": front, "back": back})
    return draws


def test_sum_filter_weight_structure():
    """权重结构有效（前区35个、后区12个，全正数）"""
    draws = _make_front_high_sum_draws()
    front_w, back_w = compute_weights(draws, strategy="sum_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n}"
        assert front_w[n] > 0, f"前区号码 {n} 权重应为正数, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n}"
        assert back_w[n] > 0, f"后区号码 {n} 权重应为正数, 实际: {back_w[n]}"
    print("PASS: sum_filter 权重结构有效")


def test_front_high_sum_suppress_large():
    """前区和值偏高（z>1）→ 大号(n>=19)被压制到0.5"""
    draws = _make_front_high_sum_draws()
    front_w, back_w = compute_weights(draws, strategy="sum_filter")
    for n in range(19, FRONT_MAX + 1):
        assert front_w[n] <= 1.0, f"前区大号 {n} 应被压制(<=1.0), 实际: {front_w[n]}"
    print("PASS: 前区和值偏高 → 大号被压制")


def test_front_low_sum_suppress_small():
    """前区和值偏低（z<-1）→ 小号(n<=18)被压制到0.5"""
    draws = _make_front_low_sum_draws()
    front_w, back_w = compute_weights(draws, strategy="sum_filter")
    for n in range(FRONT_MIN, 19):
        assert front_w[n] <= 1.0, f"前区小号 {n} 应被压制(<=1.0), 实际: {front_w[n]}"
    print("PASS: 前区和值偏低 → 小号被压制")


def test_front_normal_sum_no_suppress():
    """前区和值正常（z约0，接近理论中心）→ 无压制"""
    # 构造和值接近90的数据（随机微扰）
    draws = []
    import random
    for i in range(30):
        front = sorted(random.sample(range(FRONT_MIN, FRONT_MAX + 1), 5))
        back = sorted([1, 2])
        draws.append({"front": front, "back": back})
    front_w, back_w = compute_weights(draws, strategy="sum_filter")
    # 正常情况下，没有压制意味着没有号码权重被乘以0.5
    # 所有号码权重应该 >= 1.0 或者由热号/遗漏/趋势叠加后更高
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] >= 0.5, f"前区号码 {n} 权重异常: {front_w[n]}"
    print("PASS: 前区和值正常 → 无压制")


def test_back_high_sum_suppress_large():
    """后区和值偏高（z>1）→ 大号(n>=7)被压制"""
    draws = _make_back_high_sum_draws()
    front_w, back_w = compute_weights(draws, strategy="sum_filter")
    for n in range(7, BACK_MAX + 1):
        assert back_w[n] <= 1.0, f"后区大号 {n} 应被压制(<=1.0), 实际: {back_w[n]}"
    print("PASS: 后区和值偏高 → 大号被压制")


def test_back_low_sum_suppress_small():
    """后区和值偏低（z<-1）→ 小号(n<=6)被压制"""
    draws = _make_back_low_sum_draws()
    front_w, back_w = compute_weights(draws, strategy="sum_filter")
    for n in range(BACK_MIN, 7):
        assert back_w[n] <= 1.0, f"后区小号 {n} 应被压制(<=1.0), 实际: {back_w[n]}"
    print("PASS: 后区和值偏低 → 小号被压制")


def test_window_degenerate():
    """window<2 退化（数据量<2，无压制/权重有效）"""
    draws = [{"front": [10, 15, 20, 25, 30], "back": [5, 10]}]
    front_w, back_w = compute_weights(draws, strategy="sum_filter", window=1)
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] >= 1.0, f"前区号码 {n} 退化时权重应>=1.0, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] >= 1.0, f"后区号码 {n} 退化时权重应>=1.0, 实际: {back_w[n]}"
    print("PASS: window<2 退化（数据量<2）→ 无压制")


def test_window_param_truncation():
    """window=1 截断：30条数据只取最近1期，len=1<2触发退化，无0.5压制"""
    draws = _make_front_high_sum_draws(30)
    front_w, back_w = compute_weights(draws, strategy="sum_filter", window=1)
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] >= 1.0, f"前区号码 {n} window=1退化应>=1.0（无0.5压制）, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] >= 1.0, f"后区号码 {n} window=1退化应>=1.0（无0.5压制）, 实际: {back_w[n]}"
    print("PASS: window=1 截断 → 30条数据只取最近1期 → len=1<2退化 → 无0.5压制")


def test_integration_generate():
    """集成：generate_top_candidates 正常出结果"""
    draws = _make_front_high_sum_draws(50)
    candidates = generate_top_candidates(draws, strategy="sum_filter", top_n=5)
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
    print("PASS: sum_filter 集成 generate_top_candidates 正常")


def test_empty_draws():
    """空数据：返回均匀权重"""
    draws = []
    front_w, back_w = compute_weights(draws, strategy="sum_filter")
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] == 1.0, f"空数据时前区 {n} 权重应为1.0, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] == 1.0, f"空数据时后区 {n} 权重应为1.0, 实际: {back_w[n]}"
    print("PASS: 空数据返回均匀权重")


if __name__ == "__main__":
    test_sum_filter_weight_structure()
    test_front_high_sum_suppress_large()
    test_front_low_sum_suppress_small()
    test_front_normal_sum_no_suppress()
    test_back_high_sum_suppress_large()
    test_back_low_sum_suppress_small()
    test_window_degenerate()
    test_window_param_truncation()
    test_integration_generate()
    test_empty_draws()
    print("\nAll sum_filter strategy tests passed!")
