#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chi_square.py — 卡方检验模块

检验号码出现频率是否偏离均匀分布
"""
import math
from collections import Counter

from common import load_config

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]


def chi_square_test(observed_counts, expected_counts):
    """
    卡方检验

    Args:
        observed_counts: 观测频次列表
        expected_counts: 期望频次列表

    Returns:
        dict: chi2, df, p_value, is_reject (是否拒绝均匀分布假设)
    """
    if len(observed_counts) != len(expected_counts):
        raise ValueError("观测和期望长度不一致")
    if len(observed_counts) < 2:
        raise ValueError("至少需要2个类别")

    chi2 = 0.0
    for o, e in zip(observed_counts, expected_counts):
        if e > 0:
            chi2 += (o - e) ** 2 / e

    df = len(observed_counts) - 1
    p_value = _chi2_p_value(chi2, df)

    return {
        "chi2": round(chi2, 4),
        "df": df,
        "p_value": round(p_value, 6),
        "is_reject": p_value < 0.05,
        "significance": _significance_label(p_value),
    }


def _chi2_p_value(x, df):
    """
    卡方分布的 p 值近似计算（使用正态近似）

    对于 df >= 1，当 df 较大时使用 Wilson-Hilferty 变换
    """
    if df <= 0:
        return 1.0
    if x <= 0:
        return 1.0

    # Wilson-Hilferty 变换：chi2 近似正态
    z = ((x / df) ** (1/3) - (1 - 2/(9*df))) / math.sqrt(2/(9*df))
    # 标准正态CDF近似
    p_value = _normal_cdf_upper(z)
    return max(0.0, min(1.0, p_value))


def _normal_cdf_upper(z):
    """标准正态分布上尾概率 P(Z > z) 的近似"""
    if z < -8:
        return 1.0
    if z > 8:
        return 0.0
    # Abramowitz & Stegun 近似
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    d = 0.3989422804014327  # 1/sqrt(2*pi)
    p = d * math.exp(-z * z / 2) * (
        t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    )
    return p if z > 0 else 1.0 - p


def _significance_label(p_value):
    """显著性标签"""
    if p_value < 0.001:
        return "*** 高度显著"
    elif p_value < 0.01:
        return "** 非常显著"
    elif p_value < 0.05:
        return "* 显著"
    else:
        return "不显著"


def front_chi_square(draws, window=None):
    """
    前区号码卡方检验

    H0: 号码出现频率均匀分布
    """
    data = draws[:window] if window else draws
    total = len(data)
    if total == 0:
        return None

    front_freq = Counter()
    for d in data:
        for n in d["front"]:
            front_freq[n] += 1

    numbers = list(range(FRONT_MIN, FRONT_MAX + 1))
    observed = [front_freq.get(n, 0) for n in numbers]
    expected_per = total * 5 / 35  # 每个号码期望出现次数
    expected = [expected_per] * 35

    return chi_square_test(observed, expected)


def back_chi_square(draws, window=None):
    """
    后区号码卡方检验

    H0: 号码出现频率均匀分布
    """
    data = draws[:window] if window else draws
    total = len(data)
    if total == 0:
        return None

    back_freq = Counter()
    for d in data:
        for n in d["back"]:
            back_freq[n] += 1

    numbers = list(range(BACK_MIN, BACK_MAX + 1))
    observed = [back_freq.get(n, 0) for n in numbers]
    expected_per = total * 2 / 12  # 每个号码期望出现次数
    expected = [expected_per] * 12

    return chi_square_test(observed, expected)


def full_chi_square(draws):
    """
    完整卡方检验

    Returns:
        dict: front_result, back_result
    """
    front = front_chi_square(draws)
    back = back_chi_square(draws)
    return {"front": front, "back": back}


def format_chi_square(result):
    """格式化输出"""
    lines = ["📊 卡方检验分析（H0: 均匀分布）"]
    lines.append("=" * 50)

    for zone, label in [("front", "前区"), ("back", "后区")]:
        r = result.get(zone)
        if r:
            lines.append(f"{label}: χ²={r['chi2']:.4f}, df={r['df']}, p={r['p_value']:.6f}")
            lines.append(f"  → {r['significance']}")
            if r["is_reject"]:
                lines.append(f"  → 拒绝均匀分布假设，号码分布存在显著偏差")
            else:
                lines.append(f"  → 不拒绝均匀分布假设")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from fetch_history import fetch_history

    parser = argparse.ArgumentParser(description="卡方检验")
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    draws = fetch_history()
    if not draws:
        print("无历史数据")
        exit(1)

    result = full_chi_square(draws)
    if args.json:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_chi_square(result))
