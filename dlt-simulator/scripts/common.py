#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
common.py — 公共工具函数
"""
from pathlib import Path
import json
import random
import math

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "config.json"
DATA_DIR = ROOT / "data"
STRATEGY_DIR = ROOT / "strategies"
REPORT_DIR = ROOT / "reports"

for d in (DATA_DIR, STRATEGY_DIR, REPORT_DIR):
    d.mkdir(exist_ok=True)
(STRATEGY_DIR / "strategy_history").mkdir(exist_ok=True)
(STRATEGY_DIR / "experiments").mkdir(exist_ok=True)
for sub in ("predictions", "reviews", "statistics", "performance"):
    (REPORT_DIR / sub).mkdir(exist_ok=True)


def load_config():
    return load_json(CONFIG_PATH)


def load_json(path):
    path = Path(path)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def combination_key(front, back):
    return (tuple(sorted(front)), tuple(sorted(back)))


def format_front(front):
    return " ".join(f"{x:02d}" for x in sorted(front))


def format_back(back):
    return " ".join(f"{x:02d}" for x in sorted(back))


def format_combination(front, back):
    return f"{format_front(front)} + {format_back(back)}"


def random_combination():
    cfg = load_config()
    front = sorted(random.sample(range(cfg["front_min"], cfg["front_max"] + 1), cfg["front_pick"]))
    back = sorted(random.sample(range(cfg["back_min"], cfg["back_max"] + 1), cfg["back_pick"]))
    return front, back


def mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def variance(values):
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - 1)


def std(values):
    return math.sqrt(variance(values))
