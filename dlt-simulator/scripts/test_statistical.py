#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for statistical strategy in generator.py"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generator import compute_weights
from common import load_config

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]


def create_mock_draws():
    """创建模拟历史数据用于测试"""
    draws = []
    # 生成100期模拟数据
    for i in range(100):
        front = sorted([10, 15, 20, 25, 30])  # 固定组合便于测试
        back = sorted([5, 10])  # 固定组合便于测试
        draws.append({"front": front, "back": back})
    return draws


def test_statistical_strategy_weights():
    """测试统计分析策略的权重计算"""
    draws = create_mock_draws()
    front_w, back_w = compute_weights(draws, strategy="statistical")
    
    # 检查前区权重
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n} 的权重"
        assert front_w[n] > 0, f"前区号码 {n} 权重应大于0"
    
    # 检查后区权重
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n} 的权重"
        assert back_w[n] > 0, f"后区号码 {n} 权重应大于0"
    
    # 检查权重是否合理（不应过大或过小）
    for w in front_w.values():
        assert 0.1 < w < 10, f"前区权重异常: {w}"
    for w in back_w.values():
        assert 0.1 < w < 10, f"后区权重异常: {w}"
    
    print("PASS: 统计分析策略权重计算正确")


def test_statistical_strategy_vs_balanced():
    """测试统计分析策略与balanced策略的差异"""
    draws = create_mock_draws()
    front_w_bal, back_w_bal = compute_weights(draws, strategy="balanced")
    front_w_stat, back_w_stat = compute_weights(draws, strategy="statistical")
    
    # 检查权重是否不同（策略应该产生不同的权重）
    front_diff = sum(abs(front_w_bal[n] - front_w_stat[n]) for n in range(FRONT_MIN, FRONT_MAX + 1))
    back_diff = sum(abs(back_w_bal[n] - back_w_stat[n]) for n in range(BACK_MIN, BACK_MAX + 1))
    
    # 至少有一些差异
    assert front_diff > 0, "统计策略与balanced策略的前区权重应有差异"
    assert back_diff > 0, "统计策略与balanced策略的后区权重应有差异"
    
    print("PASS: 统计分析策略与balanced策略有显著差异")


def test_statistical_strategy_edge_cases():
    """测试统计分析策略的边界情况"""
    # 测试空数据
    draws = []
    front_w, back_w = compute_weights(draws, strategy="statistical")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "空数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "空数据时后区权重数量错误"
    
    # 测试少量数据
    draws = [{"front": [1, 2, 3, 4, 5], "back": [1, 2]}]
    front_w, back_w = compute_weights(draws, strategy="statistical")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "少量数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "少量数据时后区权重数量错误"
    
    print("PASS: 统计分析策略边界情况测试通过")


def test_statistical_strategy_integration():
    """测试统计分析策略与生成器的集成"""
    from generator import generate_top_candidates
    
    draws = create_mock_draws()
    candidates = generate_top_candidates(draws, strategy="statistical", top_n=5)
    
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
    
    print("PASS: 统计分析策略与生成器集成测试通过")


if __name__ == "__main__":
    test_statistical_strategy_weights()
    test_statistical_strategy_vs_balanced()
    test_statistical_strategy_edge_cases()
    test_statistical_strategy_integration()
    print("\nAll statistical strategy tests passed!")