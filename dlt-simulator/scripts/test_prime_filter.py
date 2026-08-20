#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for prime_filter strategy in generator.py"""
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


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


FRONT_PRIMES = {n for n in range(FRONT_MIN, FRONT_MAX + 1) if _is_prime(n)}
BACK_PRIMES = {n for n in range(BACK_MIN, BACK_MAX + 1) if _is_prime(n)}


def create_mock_draws():
    """创建模拟历史数据用于测试"""
    draws = []
    for i in range(100):
        front = sorted([10, 15, 20, 25, 30])
        back = sorted([5, 10])
        draws.append({"front": front, "back": back})
    return draws


def test_prime_filter_strategy_weights():
    """测试过滤质数策略的权重计算"""
    draws = create_mock_draws()
    front_w, back_w = compute_weights(draws, strategy="prime_filter")

    # 前区权重数量
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, f"前区权重数量错误: {len(front_w)}"

    # 前区质数权重应极低，非质数权重应较高
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        assert n in front_w, f"前区缺少号码 {n} 的权重"
        if _is_prime(n):
            assert front_w[n] <= 0.1, f"质数 {n} 权重应极低(<=0.1), 实际: {front_w[n]}"
        else:
            assert front_w[n] > 0.5, f"非质数 {n} 权重应较高(>0.5), 实际: {front_w[n]}"

    # 后区权重数量
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, f"后区权重数量错误: {len(back_w)}"

    # 后区质数权重应极低，非质数权重应较高
    for n in range(BACK_MIN, BACK_MAX + 1):
        assert n in back_w, f"后区缺少号码 {n} 的权重"
        if _is_prime(n):
            assert back_w[n] <= 0.1, f"后区质数 {n} 权重应极低(<=0.1), 实际: {back_w[n]}"
        else:
            assert back_w[n] > 0.5, f"后区非质数 {n} 权重应较高(>0.5), 实际: {back_w[n]}"

    print("PASS: 过滤质数策略权重计算正确")


def test_prime_filter_vs_balanced():
    """测试过滤质数策略与balanced策略的差异"""
    draws = create_mock_draws()
    front_w_bal, back_w_bal = compute_weights(draws, strategy="balanced")
    front_w_pf, back_w_pf = compute_weights(draws, strategy="prime_filter")

    # prime_filter下质数权重应比balanced低很多
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if _is_prime(n):
            assert front_w_pf[n] < front_w_bal[n], (
                f"质数 {n} 在prime_filter下权重应低于balanced: {front_w_pf[n]} vs {front_w_bal[n]}"
            )

    for n in range(BACK_MIN, BACK_MAX + 1):
        if _is_prime(n):
            assert back_w_pf[n] < back_w_bal[n], (
                f"后区质数 {n} 在prime_filter下权重应低于balanced: {back_w_pf[n]} vs {back_w_bal[n]}"
            )

    # prime_filter下非质数权重应不低于balanced
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        if not _is_prime(n):
            assert front_w_pf[n] >= front_w_bal[n], (
                f"非质数 {n} 在prime_filter下权重应不低于balanced: {front_w_pf[n]} vs {front_w_bal[n]}"
            )

    print("PASS: 过滤质数策略与balanced策略有显著差异")


def test_prime_filter_edge_cases():
    """测试过滤质数策略的边界情况"""
    # 空数据
    draws = []
    front_w, back_w = compute_weights(draws, strategy="prime_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "空数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "空数据时后区权重数量错误"

    # 少量数据
    draws = [{"front": [1, 2, 3, 4, 5], "back": [1, 2]}]
    front_w, back_w = compute_weights(draws, strategy="prime_filter")
    assert len(front_w) == FRONT_MAX - FRONT_MIN + 1, "少量数据时前区权重数量错误"
    assert len(back_w) == BACK_MAX - BACK_MIN + 1, "少量数据时后区权重数量错误"

    print("PASS: 过滤质数策略边界情况测试通过")


def test_prime_filter_integration():
    """测试过滤质数策略与生成器的集成"""
    draws = create_mock_draws()
    candidates = generate_top_candidates(draws, strategy="prime_filter", top_n=5)

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

    print("PASS: 过滤质数策略与生成器集成测试通过")


def test_prime_filter_front_prime_distribution():
    """测试过滤质数策略前区应偏向非质数"""
    draws = create_mock_draws()
    candidates = generate_top_candidates(draws, strategy="prime_filter", top_n=20)

    total_prime = 0
    total_non_prime = 0
    for c in candidates:
        for n in c["front"]:
            if _is_prime(n):
                total_prime += 1
            else:
                total_non_prime += 1

    # 非质数应明显多于质数（策略压低质数权重）
    assert total_non_prime > total_prime, (
        f"prime_filter策略前区应偏向非质数: 质数={total_prime}, 非质数={total_non_prime}"
    )

    print(f"PASS: 过滤质数策略前区偏向非质数 (质数={total_prime}, 非质数={total_non_prime})")


def test_prime_filter_back_prime_distribution():
    """测试过滤质数策略后区应偏向非质数"""
    draws = create_mock_draws()
    candidates = generate_top_candidates(draws, strategy="prime_filter", top_n=20)

    total_prime = 0
    total_non_prime = 0
    for c in candidates:
        for n in c["back"]:
            if _is_prime(n):
                total_prime += 1
            else:
                total_non_prime += 1

    # 非质数应明显多于质数
    assert total_non_prime > total_prime, (
        f"prime_filter策略后区应偏向非质数: 质数={total_prime}, 非质数={total_non_prime}"
    )

    print(f"PASS: 过滤质数策略后区偏向非质数 (质数={total_prime}, 非质数={total_non_prime})")


if __name__ == "__main__":
    test_prime_filter_strategy_weights()
    test_prime_filter_vs_balanced()
    test_prime_filter_edge_cases()
    test_prime_filter_integration()
    test_prime_filter_front_prime_distribution()
    test_prime_filter_back_prime_distribution()
    print("\nAll prime_filter strategy tests passed!")
