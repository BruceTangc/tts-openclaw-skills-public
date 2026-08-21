#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for odd_even_balance_filter strategy in generator.py"""
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


def create_mock_draws():
    """创建模拟历史数据用于测试"""
    draws = []
    for i in range(100):
        front = sorted([10, 15, 20, 25, 30])
        back = sorted([5, 10])
        draws.append({"front": front, "back": back})
    return draws


def test_odd_even_balance_strategy_weights():
    """测试奇偶平衡过滤策略的权重计算"""
    draws = create_mock_draws()
    front_w, back_w = compute_weights(draws, strategy="odd_even_balance_filter")

    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"

    # 所有权重应为正数
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n} 的权重"
        assert front_w[n] > 0, f"前区号码 {n} 权重应为正数, 实际: {front_w[n]}"

    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n} 的权重"
        assert back_w[n] > 0, f"后区号码 {n} 权重应为正数, 实际: {back_w[n]}"

    print("PASS: 奇偶平衡过滤策略权重计算正确")


def test_odd_even_balance_front_odd_suppressed():
    """测试前区奇数过热时奇数被压低"""
    # 构造数据：前区全用奇数号码，奇数频次远高于偶数
    draws = []
    for i in range(50):
        front = sorted([1, 3, 5, 7, 9])  # 全奇数
        back = sorted([2, 4])
        draws.append({"front": front, "back": back})

    front_w, back_w = compute_weights(draws, strategy="odd_even_balance_filter")

    # 奇数号码应被压低到 0.05
    for n in [1, 3, 5, 7, 9]:
        assert front_w[n] <= 0.1, f"奇数号码 {n} 权重应被压低(<=0.1), 实际: {front_w[n]}"

    # 偶数号码应保持较高权重
    for n in [2, 4, 6, 8, 10]:
        assert front_w[n] > 0.5, f"偶数号码 {n} 权重应较高(>0.5), 实际: {front_w[n]}"

    print("PASS: 前区奇数过热时奇数被正确压低")


def test_odd_even_balance_front_even_suppressed():
    """测试前区偶数过热时偶数被压低"""
    # 构造数据：前区全用偶数号码，偶数频次远高于奇数
    draws = []
    for i in range(50):
        front = sorted([2, 4, 6, 8, 10])  # 全偶数
        back = sorted([1, 3])
        draws.append({"front": front, "back": back})

    front_w, back_w = compute_weights(draws, strategy="odd_even_balance_filter")

    # 偶数号码应被压低到 0.05
    for n in [2, 4, 6, 8, 10]:
        assert front_w[n] <= 0.1, f"偶数号码 {n} 权重应被压低(<=0.1), 实际: {front_w[n]}"

    # 奇数号码应保持较高权重
    for n in [1, 3, 5, 7, 9]:
        assert front_w[n] > 0.5, f"奇数号码 {n} 权重应较高(>0.5), 实际: {front_w[n]}"

    print("PASS: 前区偶数过热时偶数被正确压低")


def test_odd_even_balance_back_independent():
    """测试后区独立统计奇偶频次"""
    # 后区全部用奇数号码（1,3,5,7,9,11），奇数过热
    draws = []
    for i in range(50):
        front = sorted([2, 4, 6, 8, 10])  # 前区全偶数
        back = sorted([1, 3])  # 后区全奇数
        draws.append({"front": front, "back": back})

    front_w, back_w = compute_weights(draws, strategy="odd_even_balance_filter")

    # 后区奇数应被压低
    for n in [1, 3, 5, 7, 9, 11]:
        assert back_w[n] <= 0.1, f"后区奇数 {n} 权重应被压低(<=0.1), 实际: {back_w[n]}"

    # 后区偶数应保持较高权重
    for n in [2, 4, 6, 8, 10, 12]:
        assert back_w[n] > 0.5, f"后区偶数 {n} 权重应较高(>0.5), 实际: {back_w[n]}"

    print("PASS: 后区独立统计奇偶频次正确")


def test_odd_even_balance_front_back_independent_stats():
    """测试前后区独立统计：前区和后区的奇偶统计互不影响"""
    # 前区奇数过热，后区偶数过热
    draws = []
    for i in range(50):
        front = sorted([1, 3, 5, 7, 9])  # 前区全奇数
        back = sorted([2, 4])  # 后区全偶数
        draws.append({"front": front, "back": back})

    front_w, back_w = compute_weights(draws, strategy="odd_even_balance_filter")

    # 前区奇数被压低（奇数过热）
    for n in [1, 3, 5, 7, 9]:
        assert front_w[n] <= 0.1, f"前区奇数 {n} 应被压低, 实际: {front_w[n]}"
    # 前区偶数权重高
    for n in [2, 4, 6, 8, 10]:
        assert front_w[n] > 0.5, f"前区偶数 {n} 应保持高权重, 实际: {front_w[n]}"

    # 后区偶数被压低（偶数过热）
    for n in [2, 4, 6, 8, 10, 12]:
        assert back_w[n] <= 0.1, f"后区偶数 {n} 应被压低, 实际: {back_w[n]}"
    # 后区奇数权重高
    for n in [1, 3, 5, 7, 9, 11]:
        assert back_w[n] > 0.5, f"后区奇数 {n} 应保持高权重, 实际: {back_w[n]}"

    print("PASS: 前后区独立统计奇偶频次正确")


def test_odd_even_balance_edge_cases():
    """测试奇偶平衡过滤策略的边界情况"""
    # 空数据
    draws = []
    front_w, back_w = compute_weights(draws, strategy="odd_even_balance_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "空数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "空数据时后区权重数量错误"
    # 空数据应返回均匀权重
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert front_w[n] == 1.0, f"空数据时前区号码 {n} 权重应为1.0, 实际: {front_w[n]}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert back_w[n] == 1.0, f"空数据时后区号码 {n} 权重应为1.0, 实际: {back_w[n]}"

    # 少量数据
    draws = [{"front": [1, 2, 3, 4, 5], "back": [1, 2]}]
    front_w, back_w = compute_weights(draws, strategy="odd_even_balance_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "少量数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "少量数据时后区权重数量错误"

    print("PASS: 奇偶平衡过滤策略边界情况测试通过")


def test_odd_even_balance_integration():
    """测试奇偶平衡过滤策略与生成器的集成"""
    draws = create_mock_draws()
    candidates = generate_top_candidates(draws, strategy="odd_even_balance_filter", top_n=5)

    assert len(candidates) == 5, f"应生成5个候选，实际生成{len(candidates)}"
    for c in candidates:
        assert "front" in c, "候选缺少front字段"
        assert "back" in c, "候选缺少back字段"
        assert "score" in c, "候选缺少score字段"
        assert len(c["front"]) == 5, f"前区应有5个号码，实际有{len(c['front'])}"
        assert len(c["back"]) == 2, f"后区应有2个号码，实际有{len(c['back'])}"

        for n in c["front"]:
            assert FRONT_MIN <= n <= FRONT_MAX, f"前区号码{n}超出范围"
        for n in c["back"]:
            assert BACK_MIN <= n <= BACK_MAX, f"后区号码{n}超出范围"

    print("PASS: 奇偶平衡过滤策略与生成器集成测试通过")


def test_odd_even_balance_vs_balanced():
    """测试odd_even_balance_filter与balanced策略的差异"""
    draws = create_mock_draws()
    front_w_bal, back_w_bal = compute_weights(draws, strategy="balanced")
    front_w_oe, back_w_oe = compute_weights(draws, strategy="odd_even_balance_filter")

    # 在odd_even_balance_filter下，某些号码权重应与balanced不同
    # 至少有一个号码的权重发生变化
    front_diff = any(abs(front_w_oe[n] - front_w_bal[n]) > 0.01 for n in range(FRONT_MIN, FRONT_MAX + 1))
    back_diff = any(abs(back_w_oe[n] - back_w_bal[n]) > 0.01 for n in range(BACK_MIN, BACK_MAX + 1))
    assert front_diff or back_diff, "odd_even_balance_filter与balanced策略应有差异"

    print("PASS: odd_even_balance_filter与balanced策略有差异")


if __name__ == "__main__":
    test_odd_even_balance_strategy_weights()
    test_odd_even_balance_front_odd_suppressed()
    test_odd_even_balance_front_even_suppressed()
    test_odd_even_balance_back_independent()
    test_odd_even_balance_front_back_independent_stats()
    test_odd_even_balance_edge_cases()
    test_odd_even_balance_integration()
    test_odd_even_balance_vs_balanced()
    print("\nAll odd_even_balance_filter strategy tests passed!")
