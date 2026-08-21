#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for tail_filter strategy in generator.py"""
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


def test_tail_filter_strategy_weights():
    """测试尾数过滤策略的权重计算"""
    draws = create_mock_draws()
    front_w, back_w = compute_weights(draws, strategy="tail_filter")

    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"

    # 所有权重应为正数
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n} 的权重"
        assert front_w[n] > 0, f"前区号码 {n} 权重应为正数, 实际: {front_w[n]}"

    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n} 的权重"
        assert back_w[n] > 0, f"后区号码 {n} 权重应为正数, 实际: {back_w[n]}"

    print("PASS: 尾数过滤策略权重计算正确")


def test_tail_filter_top_tail_suppressed():
    """测试高频尾数被压低"""
    # 构造数据：尾数0的号码大量出现（10,20,30），尾数1也多（11,21），
    # 尾数3少（13），尾数5少（15）。这样top-3尾数={0,1}+某个，
    # 而尾数3/5/7/9等不在top-3中
    draws = []
    for i in range(50):
        front = sorted([10, 20, 30, 11, 21])
        back = sorted([5, 10])
        draws.append({"front": front, "back": back})

    front_w, back_w = compute_weights(draws, strategy="tail_filter")

    # 尾数0的号码（10,20,30）应被压低
    for n in [10, 20, 30]:
        assert front_w[n] < 0.5, f"高频尾数号码 {n} (尾数0) 权重应被压低, 实际: {front_w[n]}"

    # 尾数1的号码（11,21）也被压低（尾数1也在top-3）
    for n in [11, 21]:
        assert front_w[n] < 0.5, f"高频尾数号码 {n} (尾数1) 权重应被压低, 实际: {front_w[n]}"

    # 尾数5的号码（15）不在top-3中，权重应更高
    assert front_w[15] > front_w[10], f"尾数5的15权重应高于尾数0的10: {front_w[15]} vs {front_w[10]}"
    assert front_w[15] > 1.0, f"非高频尾数号码15权重应>1.0, 实际: {front_w[15]}"

    print("PASS: 高频尾数被正确压低")


def test_tail_filter_vs_balanced():
    """测试tail_filter与balanced策略的差异"""
    draws = create_mock_draws()
    front_w_bal, back_w_bal = compute_weights(draws, strategy="balanced")
    front_w_tf, back_w_tf = compute_weights(draws, strategy="tail_filter")

    # tail_filter下高频尾数号码权重应低于balanced
    # 尾数0的号码：10,20,30
    for n in [10, 20, 30]:
        assert front_w_tf[n] < front_w_bal[n], (
            f"高频尾数号码 {n} 在tail_filter下权重应低于balanced: {front_w_tf[n]} vs {front_w_bal[n]}"
        )

    print("PASS: tail_filter与balanced策略有显著差异")


def test_tail_filter_edge_cases():
    """测试尾数过滤策略的边界情况"""
    # 空数据
    draws = []
    front_w, back_w = compute_weights(draws, strategy="tail_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "空数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "空数据时后区权重数量错误"

    # 少量数据
    draws = [{"front": [1, 2, 3, 4, 5], "back": [1, 2]}]
    front_w, back_w = compute_weights(draws, strategy="tail_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "少量数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "少量数据时后区权重数量错误"

    print("PASS: 尾数过滤策略边界情况测试通过")


def test_tail_filter_integration():
    """测试尾数过滤策略与生成器的集成"""
    draws = create_mock_draws()
    candidates = generate_top_candidates(draws, strategy="tail_filter", top_n=5)

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

    print("PASS: 尾数过滤策略与生成器集成测试通过")


def test_tail_filter_back_weights():
    """测试后区尾数过滤权重"""
    # 后区范围1-12，尾数实际覆盖0-2
    draws = []
    for i in range(50):
        front = sorted([1, 2, 3, 4, 5])
        back = sorted([1, 10])  # 尾数1和0高频
        draws.append({"front": front, "back": back})

    front_w, back_w = compute_weights(draws, strategy="tail_filter")

    # 尾数1和0高频，应被压低
    assert back_w[1] < 0.5, f"高频尾数后区号码 1 (尾数1) 权重应被压低, 实际: {back_w[1]}"
    assert back_w[10] < 0.5, f"高频尾数后区号码 10 (尾数0) 权重应被压低, 实际: {back_w[10]}"

    print("PASS: 后区尾数过滤权重正确")


if __name__ == "__main__":
    test_tail_filter_strategy_weights()
    test_tail_filter_top_tail_suppressed()
    test_tail_filter_vs_balanced()
    test_tail_filter_edge_cases()
    test_tail_filter_integration()
    test_tail_filter_back_weights()
    print("\nAll tail_filter strategy tests passed!")
