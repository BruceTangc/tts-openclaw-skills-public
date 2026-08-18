#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_history.py — 从体彩官网抓取历史开奖数据

数据源：https://www.lottery.gov.cn/
缓存策略：本地缓存每日刷新，避免重复请求
"""
import json
import re
import sys
import urllib.request
from datetime import date, datetime
from pathlib import Path

from common import ROOT, DATA_DIR, load_json, save_json

HISTORY_FILE = DATA_DIR / "history_draws.json"
CACHE_FILE = DATA_DIR / "history_cache.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.lottery.gov.cn/",
}

# 备用数据源
BACKUP_URLS = [
    "https://datachart.500.com/dlt/history/newinc/history.php?limit={limit}&sort=0",
    "https://www.js-lottery.com/wfzq/dlt/data",
]


def _http_get(url, timeout=20):
    """通用 HTTP GET"""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def _parse_lottery_gov(html):
    """解析体彩官网返回的 JSON 数据"""
    draws = []
    try:
        data = json.loads(html)
        if isinstance(data, list):
            for item in data:
                front = []
                back = []
                nums = item.get("lotteryDrawResult", "").split()
                if len(nums) >= 7:
                    front = [int(n) for n in nums[:5]]
                    back = [int(n) for n in nums[5:7]]
                    draws.append({
                        "issue": item.get("lotteryDrawNum", ""),
                        "front": front,
                        "back": back,
                        "date": item.get("lotteryDrawTime", "")[:10],
                    })
        elif isinstance(data, dict) and "value" in data:
            for item in data["value"]:
                front = []
                back = []
                nums = item.get("lotteryDrawResult", "").split()
                if len(nums) >= 7:
                    front = [int(n) for n in nums[:5]]
                    back = [int(n) for n in nums[5:7]]
                    draws.append({
                        "issue": item.get("lotteryDrawNum", ""),
                        "front": front,
                        "back": back,
                        "date": item.get("lotteryDrawTime", "")[:10],
                    })
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    return draws


def _parse_500com(html):
    """解析 500.com HTML 表格"""
    draws = []
    pattern = r'<td[^>]*>(\d+)</td>.*?<td[^>]*>(\d{2})</td>.*?<td[^>]*>(\d{2})</td>.*?<td[^>]*>(\d{2})</td>.*?<td[^>]*>(\d{2})</td>.*?<td[^>]*>(\d{2})</td>.*?<td[^>]*>(\d{2})</td>.*?<td[^>]*>(\d{2})</td>'
    for m in re.finditer(pattern, html, re.DOTALL):
        issue = m.group(1)
        nums = [int(m.group(i)) for i in range(2, 9)]
        if len(nums) == 7:
            draws.append({
                "issue": issue,
                "front": nums[:5],
                "back": nums[5:],
                "date": "",
            })
    return draws


def _parse_js_lottery(html):
    """解析 js-lottery.com HTML"""
    draws = []
    pattern = r'<td[^>]*>(\d{4}-\d{2}-\d{2})</td>\s*<td[^>]*>(\d+)</td>\s*<td[^>]*>\s*((?:\d{2}\s+){6}\d{2})\s*</td>'
    for m in re.finditer(pattern, html, re.DOTALL):
        nums = m.group(3).strip().split()
        if len(nums) == 7:
            draws.append({
                "date": m.group(1),
                "issue": m.group(2),
                "front": [int(x) for x in nums[:5]],
                "back": [int(x) for x in nums[5:]],
            })
    return draws


def _load_cache():
    """加载本地缓存（当天有效）"""
    if not CACHE_FILE.exists():
        return None
    try:
        data = load_json(CACHE_FILE)
        if data and data.get("date") == str(date.today()):
            return data.get("draws", [])
    except Exception:
        pass
    return None


def _save_cache(draws):
    """保存本地缓存"""
    save_json(CACHE_FILE, {
        "date": str(date.today()),
        "draws": [
            {
                "issue": d["issue"],
                "front": d["front"],
                "back": d["back"],
                "date": d.get("date", ""),
            }
            for d in draws
        ],
    })


def _save_history(draws):
    """保存完整历史数据"""
    save_json(HISTORY_FILE, draws)


def _normalize_draw(d):
    """确保 draw 数据格式一致"""
    front = d.get("front", [])
    back = d.get("back", [])
    if isinstance(front, tuple):
        front = list(front)
    if isinstance(back, tuple):
        back = list(back)
    return {
        "issue": str(d.get("issue", "")),
        "front": front,
        "back": back,
        "date": d.get("date", ""),
    }


def fetch_history(limit=3000, force=False):
    """
    抓取历史开奖数据

    Args:
        limit: 最大抓取期数
        force: 强制刷新（忽略缓存）

    Returns:
        list[dict]: 按期号降序排列的开奖数据列表
    """
    # 1. 尝试缓存
    if not force:
        cached = _load_cache()
        if cached:
            return [_normalize_draw(d) for d in cached]

    draws = []

    # 2. 尝试体彩官网
    try:
        url = f"https://www.lottery.gov.cn/kj/kjlb.html?dlt"
        html = _http_get(url, timeout=15)
        draws = _parse_lottery_gov(html)
    except Exception as e:
        print(f"  ⚠️ 体彩官网获取失败: {e}", file=sys.stderr)

    # 3. 尝试备用源
    if not draws:
        for url_template in BACKUP_URLS:
            try:
                url = url_template.format(limit=limit)
                html = _http_get(url, timeout=15)
                if "500.com" in url:
                    draws = _parse_500com(html)
                else:
                    draws = _parse_js_lottery(html)
                if draws:
                    break
            except Exception as e:
                print(f"  ⚠️ 备用源获取失败: {e}", file=sys.stderr)
                continue

    # 4. 规范化并排序
    draws = [_normalize_draw(d) for d in draws]
    draws.sort(key=lambda d: d["issue"], reverse=True)

    # 5. 保存缓存和历史
    if draws:
        _save_cache(draws)
        _save_history(draws)

    return draws


def get_latest_draw():
    """获取最新一期开奖数据"""
    draws = fetch_history(limit=10)
    return draws[0] if draws else None


def get_draws_by_range(start_issue=None, end_issue=None):
    """按期号范围获取数据"""
    draws = fetch_history()
    if start_issue:
        draws = [d for d in draws if d["issue"] >= start_issue]
    if end_issue:
        draws = [d for d in draws if d["issue"] <= end_issue]
    return draws


def get_recent_draws(n=100):
    """获取最近 N 期数据"""
    draws = fetch_history()
    return draws[:n]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="抓取大乐透历史开奖数据")
    parser.add_argument("--limit", type=int, default=3000, help="最大抓取期数")
    parser.add_argument("--force", action="store_true", help="强制刷新")
    parser.add_argument("--recent", type=int, default=0, help="显示最近N期")
    parser.add_argument("--json", action="store_true", help="JSON输出")
    args = parser.parse_args()

    draws = fetch_history(limit=args.limit, force=args.force)
    print(f"已加载 {len(draws)} 期历史开奖数据")

    if args.recent > 0:
        for d in draws[:args.recent]:
            front_str = " ".join(f"{n:02d}" for n in d["front"])
            back_str = " ".join(f"{n:02d}" for n in d["back"])
            print(f"  {d['issue']} | {front_str} + {back_str}")

    if args.json and draws:
        latest = draws[0]
        print(json.dumps(latest, ensure_ascii=False))
