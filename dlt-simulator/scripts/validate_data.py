#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_data.py — 数据验证模块

验证开奖数据的完整性、格式正确性、逻辑一致性
"""
import sys
from pathlib import Path

from common import load_config, combination_key


cfg = load_config()
FRONT_MIN = cfg["front_min"]
FRONT_MAX = cfg["front_max"]
FRONT_PICK = cfg["front_pick"]
BACK_MIN = cfg["back_min"]
BACK_MAX = cfg["back_max"]
BACK_PICK = cfg["back_pick"]


class ValidationError(Exception):
    """数据验证错误"""
    pass


def validate_single_draw(draw, index=None):
    """
    验证单期开奖数据

    Args:
        draw: dict with keys: issue, front, back, date
        index: 用于错误定位的索引

    Returns:
        bool: 验证通过
        list[str]: 错误信息列表
    """
    errors = []
    prefix = f"第{index}期" if index is not None else "未知期"

    # 必需字段检查
    for field in ("issue", "front", "back"):
        if field not in draw:
            errors.append(f"{prefix}: 缺少字段 {field}")

    if errors:
        return False, errors

    issue = draw["issue"]
    front = draw["front"]
    back = draw["back"]

    # 期号验证
    if not isinstance(issue, str) or len(issue) < 4:
        errors.append(f"{prefix}({issue}): 期号格式异常")

    # 前区验证
    if not isinstance(front, (list, tuple)) or len(front) != FRONT_PICK:
        errors.append(f"{prefix}({issue}): 前区需要{FRONT_PICK}个号码，实际{len(front)}")
    else:
        for num in front:
            if not isinstance(num, int) or num < FRONT_MIN or num > FRONT_MAX:
                errors.append(f"{prefix}({issue}): 前区号码 {num} 超出范围 {FRONT_MIN}-{FRONT_MAX}")
        if len(set(front)) != len(front):
            errors.append(f"{prefix}({issue}): 前区号码有重复")

    # 后区验证
    if not isinstance(back, (list, tuple)) or len(back) != BACK_PICK:
        errors.append(f"{prefix}({issue}): 后区需要{BACK_PICK}个号码，实际{len(back)}")
    else:
        for num in back:
            if not isinstance(num, int) or num < BACK_MIN or num > BACK_MAX:
                errors.append(f"{prefix}({issue}): 后区号码 {num} 超出范围 {BACK_MIN}-{BACK_MAX}")
        if len(set(back)) != len(back):
            errors.append(f"{prefix}({issue}): 后区号码有重复")

    return len(errors) == 0, errors


def validate_history(draws):
    """
    批量验证历史数据

    Args:
        draws: list of draw dicts

    Returns:
        tuple: (valid_count, error_count, all_errors)
    """
    valid_count = 0
    error_count = 0
    all_errors = []
    seen_issues = set()

    for i, draw in enumerate(draws):
        ok, errs = validate_single_draw(draw, index=i + 1)
        if ok:
            valid_count += 1
            issue = draw["issue"]
            if issue in seen_issues:
                all_errors.append(f"第{i+1}期({issue}): 期号重复")
                error_count += 1
            else:
                seen_issues.add(issue)
        else:
            error_count += 1
            all_errors.extend(errs)

    return valid_count, error_count, all_errors


def validate_combination(front, back):
    """
    验证用户输入的组合格式

    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(front, (list, tuple)) or len(front) != FRONT_PICK:
        return False, f"前区需要{FRONT_PICK}个号码"
    if not isinstance(back, (list, tuple)) or len(back) != BACK_PICK:
        return False, f"后区需要{BACK_PICK}个号码"

    for num in front:
        if not isinstance(num, int) or num < FRONT_MIN or num > FRONT_MAX:
            return False, f"前区号码 {num} 超出范围 {FRONT_MIN}-{FRONT_MAX}"
    for num in back:
        if not isinstance(num, int) or num < BACK_MIN or num > BACK_MAX:
            return False, f"后区号码 {num} 超出范围 {BACK_MIN}-{BACK_MAX}"

    if len(set(front)) != len(front):
        return False, "前区号码有重复"
    if len(set(back)) != len(back):
        return False, "后区号码有重复"

    return True, ""


def check_draw_continuity(draws):
    """
    检查开奖数据的连续性（期号是否连续）

    Args:
        draws: 按期号降序排列的开奖数据列表

    Returns:
        list[str]: 警告信息列表
    """
    warnings = []
    issues = [int(d["issue"]) for d in draws if d["issue"].isdigit()]

    if len(issues) < 2:
        return warnings

    issues.sort(reverse=True)
    for i in range(len(issues) - 1):
        diff = issues[i] - issues[i + 1]
        if diff != 1:
            warnings.append(f"期号 {issues[i+1]} 到 {issues[i]} 之间有缺口(差{diff})")

    return warnings


def data_quality_report(draws):
    """
    生成数据质量报告

    Returns:
        dict: 质量报告
    """
    valid_count, error_count, all_errors = validate_history(draws)
    warnings = check_draw_continuity(draws)

    total = len(draws)
    return {
        "total": total,
        "valid": valid_count,
        "errors": error_count,
        "warnings": len(warnings),
        "quality_score": round(valid_count / total * 100, 2) if total > 0 else 0,
        "error_details": all_errors[:20],
        "warning_details": warnings[:20],
    }


if __name__ == "__main__":
    import json
    import argparse
    from common import DATA_DIR

    parser = argparse.ArgumentParser(description="验证大乐透数据")
    parser.add_argument("--file", default=str(DATA_DIR / "history_draws.json"))
    parser.add_argument("--check", nargs=2, type=int, metavar=("FRONT", "BACK"))
    args = parser.parse_args()

    if args.check:
        # 验证单个组合
        ok, err = validate_combination(args.check[:5], args.check[5:])
        print("✅ 通过" if ok else f"❌ {err}")
    else:
        # 验证历史数据文件
        from common import load_json
        draws = load_json(args.file) or []
        report = data_quality_report(draws)
        print(f"数据质量报告:")
        print(f"  总期数: {report['total']}")
        print(f"  有效: {report['valid']}")
        print(f"  异常: {report['errors']}")
        print(f"  警告: {report['warnings']}")
        print(f"  质量分: {report['quality_score']}%")
        for e in report["error_details"][:10]:
            print(f"  ❌ {e}")
        for w in report["warning_details"][:10]:
            print(f"  ⚠️ {w}")
