#!/usr/bin/env python3
"""
简单合同风险评分示例脚本（规则引擎 stub）
实际使用时可将合同文本传入，匹配 review_rules.yaml 进行扣分。

用法示例：
  python risk_score.py --text "合同约定100%预付款，且乙方承担无限责任"
"""

import argparse
import re
import yaml
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[1] / "contract-review" / "review_rules.yaml"
ENGINE_PATH = Path(__file__).resolve().parents[1] / "contract-review" / "risk_engine.yaml"


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def score_text(text: str) -> dict:
    rules = load_yaml(RULES_PATH)
    engine = load_yaml(ENGINE_PATH)
    base = engine.get("base_score", 100)
    dimensions = engine.get("dimensions", {})
    deduct = {k: 0.0 for k in dimensions}

    hits = []

    for level in ["high_risk", "medium_risk"]:
        group = rules.get(level, {})
        for rule_id, rule in group.items():
            keywords = rule.get("keywords", [])
            for kw in keywords:
                # 规则ID以 missing_ 开头时使用反向匹配（找不到才扣分）
                is_negative = rule_id.startswith("missing_")
                if is_negative:
                    # 全部关键词都不在文本中才触发
                    matched = all(kw not in text for kw in keywords)
                    if matched:
                        dim = rule.get("dimension", "争议解决与其他")
                        weight = dimensions.get(dim, {}).get("weight", 5)
                        ratio = rule.get("deduct_ratio", 0.5)
                        points = weight * ratio
                        new_val = min(weight, deduct.get(dim, 0) + points)
                        deduct[dim] = new_val
                        hits.append({"rule": rule_id, "level": level, "keyword": "|".join(keywords), "dimension": dim, "risk": rule.get("risk"), "suggestion": rule.get("suggestion"), "deduct": points})
                    break  # 一次性判断所有关键词
                else:
                    matched = kw in text
                    if matched:
                        dim = rule.get("dimension", "争议解决与其他")
                        weight = dimensions.get(dim, {}).get("weight", 5)
                        ratio = rule.get("deduct_ratio", 0.5)
                        points = weight * ratio
                        # 同一维度不超过 weight
                        new_val = min(weight, deduct.get(dim, 0) + points)
                        deduct[dim] = new_val
                        hits.append({
                            "rule": rule_id,
                            "level": level,
                            "keyword": kw,
                            "dimension": dim,
                            "risk": rule.get("risk"),
                            "suggestion": rule.get("suggestion"),
                            "deduct": points
                        })
                    break  # 同一规则命中一次即可

    total_deduct = sum(deduct.values())
    final = max(0, base - total_deduct)

    # 等级
    levels = engine.get("levels", {})
    level_name = "Critical"
    action = ""
    for rng, info in levels.items():
        lo, hi = map(int, rng.split("-"))
        if lo <= final <= hi:
            level_name = info["level"]
            action = info["action"]
            break

    return {
        "score": round(final, 1),
        "level": level_name,
        "action": action,
        "deduct_detail": deduct,
        "hits": hits
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True, help="合同相关文本片段")
    args = parser.parse_args()

    result = score_text(args.text)
    print(f"风险评分：{result['score']} / 100")
    print(f"等级：{result['level']}")
    print(f"建议：{result['action']}")
    print("\n命中规则：")
    for h in result["hits"]:
        print(f"- [{h['level']}] {h['risk']}（关键词：{h['keyword']}）")
        print(f"  建议：{h['suggestion']}")


if __name__ == "__main__":
    main()
