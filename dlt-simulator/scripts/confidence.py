#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
confidence.py — Wilson 置信区间模块

用于计算号码出现频率的置信区间，判断频率是否偏离期望值
"""
import math
from collections import Counter

from common import load_config

cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
FRONT_PICK = cfg["front_pick"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]
BACK_PICK = cfg["back_pick"]
CONFIDENCE_LEVEL = cfg["confidence_level"]


def wilson_ci(successes, trials, confidence=None):
    """
    Wilson 置信区间（单侧/双侧）

    Args:
        successes: 成功次数（号码出现次数）
        trials: 总试验次数（总期数）
        confidence: 置信水平（默认0.95）

    Returns:
        tuple: (lower_bound, upper_bound) 概率的置信区间
    """
    if confidence is None:
        confidence = CONFIDENCE_LEVEL
    if trials == 0:
        return 0.0, 1.0

    z = _z_score(confidence)
    p_hat = successes / trials
    n = trials
    denominator = 1 + z * z / n
    center = (p_hat + z * z / (2 * n)) / denominator
    spread = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n) / denominator

    return max(0.0, center - spread), min(1.0, center + spread)


def margin_of_error(successes, trials, confidence=None):
    """
    置信区间的半宽度（误差范围）

    Args:
        successes: 成功次数
        trials: 总试验次数
        confidence: 置信水平（默认0.95）

    Returns:
        float: 置信区间的半宽度 (upper - lower) / 2
    """
    if trials == 0:
        return 0.5
    lower, upper = wilson_ci(successes, trials, confidence)
    return (upper - lower) / 2


def _z_score(confidence):
    """对应置信水平的 z 分数（近似）"""
    # 常用值：90%->1.645, 95%->1.96, 99%->2.576
    table = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576,
    }
    # 线性插值
    if confidence in table:
        return table[confidence]
    keys = sorted(table.keys())
    if confidence <= keys[0]:
        return table[keys[0]]
    if confidence >= keys[-1]:
        return table[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= confidence <= keys[i + 1]:
            t = (confidence - keys[i]) / (keys[i + 1] - keys[i])
            return table[keys[i]] + t * (table[keys[i + 1]] - table[keys[i]])
    return 1.96


def frequency_ci(draws, window=None):
    """
    计算每个号码出现频率的置信区间

    Returns:
        dict: {
            "front": {num: (observed_freq, ci_lower, ci_upper, is_abnormal)},
            "back": {num: (observed_freq, ci_lower, ci_upper, is_abnormal)}
        }
    """
    data = draws[:window] if window else draws
    total = len(data)
    if total == 0:
        return {"front": {}, "back": {}}

    front_freq = Counter()
    back_freq = Counter()
    for d in data:
        for n in d["front"]:
            front_freq[n] += 1
        for n in d["back"]:
            back_freq[n] += 1

    # 前区期望频率：每次选5个/35个
    front_expected = FRONT_PICK / (FRONT_MAX - FRONT_MIN + 1)
    back_expected = BACK_PICK / (BACK_MAX - BACK_MIN + 1)

    front_result = {}
    for n in range(FRONT_MIN, FRONT_MAX + 1):
        count = front_freq.get(n, 0)
        p_hat = count / total
        ci_low, ci_high = wilson_ci(count, total)
        is_abnormal = p_hat < ci_low or p_hat > ci_high
        front_result[n] = {
            "observed": count,
            "frequency": round(p_hat, 4),
            "expected": round(front_expected, 4),
            "ci_lower": round(ci_low, 4),
            "ci_upper": round(ci_high, 4),
            "is_abnormal": is_abnormal,
            "deviation": round(p_hat - front_expected, 4),
        }

    back_result = {}
    for n in range(BACK_MIN, BACK_MAX + 1):
        count = back_freq.get(n, 0)
        p_hat = count / total
        ci_low, ci_high = wilson_ci(count, total)
        is_abnormal = p_hat < ci_low or p_hat > ci_high
        back_result[n] = {
            "observed": count,
            "frequency": round(p_hat, 4),
            "expected": round(back_expected, 4),
            "ci_lower": round(ci_low, 4),
            "ci_upper": round(ci_high, 4),
            "is_abnormal": is_abnormal,
            "deviation": round(p_hat - back_expected, 4),
        }

    return {"front": front_result, "back": back_result}


def abnormal_numbers(ci_result):
    """提取异常号码（频率偏离置信区间的）"""
    abnormals = {"front_high": [], "front_low": [], "back_high": [], "back_low": []}
    for n, info in ci_result.get("front", {}).items():
        if info["is_abnormal"]:
            if info["deviation"] > 0:
                abnormals["front_high"].append((n, info["deviation"]))
            else:
                abnormals["front_low"].append((n, abs(info["deviation"])))
    for n, info in ci_result.get("back", {}).items():
        if info["is_abnormal"]:
            if info["deviation"] > 0:
                abnormals["back_high"].append((n, info["deviation"]))
            else:
                abnormals["back_low"].append((n, abs(info["deviation"])))
    # 按偏离程度排序
    for k in abnormals:
        abnormals[k].sort(key=lambda x: x[1], reverse=True)
    return abnormals


def format_ci(ci_result):
    """格式化输出置信区间结果"""
    lines = ["📊 Wilson 置信区间分析"]
    lines.append("=" * 50)

    front = ci_result.get("front", {})
    back = ci_result.get("back", {})

    abnormal_count = sum(1 for v in front.values() if v["is_abnormal"])
    abnormal_count += sum(1 for v in back.values() if v["is_abnormal"])

    lines.append(f"异常号码数: {abnormal_count}")

    if abnormal_count > 0:
        abnormals = abnormal_numbers(ci_result)
        if abnormals["front_high"]:
            lines.append(f"前区偏高: {' '.join(f'{n:02d}(+{d:.3f})' for n, d in abnormals['front_high'][:5])}")
        if abnormals["front_low"]:
            lines.append(f"前区偏低: {' '.join(f'{n:02d}(-{d:.3f})' for n, d in abnormals['front_low'][:5])}")
        if abnormals["back_high"]:
            lines.append(f"后区偏高: {' '.join(f'{n:02d}(+{d:.3f})' for n, d in abnormals['back_high'][:3])}")
        if abnormals["back_low"]:
            lines.append(f"后区偏低: {' '.join(f'{n:02d}(-{d:.3f})' for n, d in abnormals['back_low'][:3])}")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    from fetch_history import fetch_history

    parser = argparse.ArgumentParser(description="Wilson 置信区间分析")
    parser.add_argument("--window", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    draws = fetch_history()
    if not draws:
        print("无历史数据")
        exit(1)

    result = frequency_ci(draws, window=args.window)
    if args.json:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_ci(result))
