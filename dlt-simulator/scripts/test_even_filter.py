#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for even_filter strategy in generator.py"""
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


def test_even_filter_strategy_weights():
    """测试过滤偶数策略的权重计算"""
    draws = create_mock_draws()
    front_w, back_w = compute_weights(draws, strategy="even_filter")

    # 检查前区权重数量
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"

    # 检查偶数号码权重极低
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n} 的权重"
        if n % 2 == 0:
            assert front_w[n] <= 0.1, f"偶数 {n} 权重应极低(<=0.1), 实际: {front_w[n]}"
        else:
            assert front_w[n] > 0.5, f"奇数 {n} 权重应较高(>0.5), 实际: {front_w[n]}"

    # 检查后区权重（不受even_filter影响，应与balanced一致）
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n} 的权重"
        assert back_w[n] > 0, f"后区号码 {n} 权重应大于0"

    print("PASS: 过滤偶数策略权重计算正确")


def test_even_filter_vs_balanced():
    """测试过滤偶数策略与balanced策略的差异"""
    draws = create_mock_draws()
    front_w_bal, _ = compute_weights(draws, strategy="balanced")
    front_w_ef, _ = compute_weights(draws, strategy="even_filter")

    # even_filter下偶数权重应比balanced低很多
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n % 2 == 0:
            assert front_w_ef[n] < front_w_bal[n], \
                f"偶数 {n} 在even_filter下权重应低于balanced: {front_w_ef[n]} vs {front_w_bal[n]}"

    # even_filter下奇数权重应不低于balanced
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if n % 2 == 1:
            assert front_w_ef[n] >= front_w_bal[n], \
                f"奇数 {n} 在even_filter下权重应不低于balanced: {front_w_ef[n]} vs {front_w_bal[n]}"

    print("PASS: 过滤偶数策略与balanced策略有显著差异")


def test_even_filter_edge_cases():
    """测试过滤偶数策略的边界情况"""
    # 测试空数据
    draws = []
    front_w, back_w = compute_weights(draws, strategy="even_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "空数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "空数据时后区权重数量错误"

    # 测试少量数据
    draws = [{"front": [1, 2, 3, 4, 5], "back": [1, 2]}]
    front_w, back_w = compute_weights(draws, strategy="even_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "少量数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "少量数据时后区权重数量错误"

    print("PASS: 过滤偶数策略边界情况测试通过")


def test_even_filter_integration():
    """测试过滤偶数策略与生成器的集成"""
    draws = create_mock_draws()
    candidates = generate_top_candidates(draws, strategy="even_filter", top_n=5)

    # 检查生成结果
    assert len(candidates) == 5, f"应生成5个候选，实际生成{len(candidates)}"
    for c in candidates:
        assert "front" in c, "候选缺少front字段"
        assert "back" in c, "候选缺少back字段"
        assert "score" in c, "候选缺少score字段"
        assert len(c["front"]) == 5, f"前区应有5个号码，实际有{len(c['front'])}"
        assert len(c["back"]) == 2, f"后区应有2个号码，实际有{len(c['back'])}"

        # 检查号码范围
        for n in c["front"]:
            assert FRONT_MIN <= n <= FRONT_MAX, f"前区号码{n}超出范围"
        for n in c["back"]:
            assert BACK_MIN <= n <= BACK_MAX, f"后区号码{n}超出范围"

    print("PASS: 过滤偶数策略与生成器集成测试通过")


def test_even_filter_front_zone_lean_odd():
    """测试过滤偶数策略前区应偏向奇数"""
    draws = create_mock_draws()
    candidates = generate_top_candidates(draws, strategy="even_filter", top_n=20)

    # 统计所有候选中奇数和偶数的数量
    total_odd = 0
    total_even = 0
    for c in candidates:
        for n in c["front"]:
            if n % 2 == 1:
                total_odd += 1
            else:
                total_even += 1

    # 奇数应明显多于偶数（前区5个号码×20个候选=100个号码）
    assert total_odd > total_even, \
        f"even_filter策略前区应偏向奇数: 奇数={total_odd}, 偶数={total_even}"

    print(f"PASS: 过滤偶数策略前区偏向奇数 (奇数={total_odd}, 偶数={total_even})")


if __name__ == "__main__":
    test_even_filter_strategy_weights()
    test_even_filter_vs_balanced()
    test_even_filter_edge_cases()
    test_even_filter_integration()
    test_even_filter_front_zone_lean_odd()
    print("\nAll even_filter strategy tests passed!")
