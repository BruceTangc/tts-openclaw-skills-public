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

# 体彩官方历史数据 JSON API（实测可用：gameNo=85 超级大乐透，分页拉全量）
OFFICIAL_GAME_NO = "85"
OFFICIAL_URL = (
    "https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
    "?gameNo={game}&provinceId=0&pageSize={pageSize}&isVerify=1&pageNo={pageNo}"
)
OFFICIAL_PAGE_SIZE = 100

# 后备源（js-lottery 干净但只 10 期；500.com 解析易脏；体彩 html 壳不可用）
BACKUP_URLS = [
    "https://www.js-lottery.com/wfzq/dlt/data",            # 干净但仅最近 10 期
    "https://datachart.500.com/dlt/history/newinc/history.php?limit={limit}&sort=0",  # 解析易脏，后备
]

# 大乐透规则（用于数据合法性校验）
_FRONT_MAX = 35
_BACK_MAX = 12


def _parse_official(json_str):
    """解析体彩官方 JSON API 返回的历史开奖（分页内部用）。"""
    try:
        data = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return []
    if data.get("success") is not True and data.get("errorCode") != "0":
        return []
    value = data.get("value") or {}
    lst = value.get("list") or []
    draws = []
    for item in lst:
        result = (item.get("lotteryDrawResult") or "").split()
        if len(result) >= 7:
            draws.append({
                "issue": str(item.get("lotteryDrawNum", "") or "").strip(),
                "front": [int(n) for n in result[:5]],
                "back": [int(n) for n in result[5:7]],
                "date": str(item.get("lotteryDrawTime", "") or "").strip()[:10],
            })
    return draws


def _fetch_official_total():
    """查询官方接口总期数。"""
    try:
        url = OFFICIAL_URL.format(game=OFFICIAL_GAME_NO, pageSize=1, pageNo=1)
        html = _http_get(url, timeout=15)
        data = json.loads(html)
        return int((data.get("value") or {}).get("total", 0))
    except Exception:
        return 0


def _fetch_official(limit):
    """从官方接口翻页拉取历史，直至覆盖 limit 或拉完。

    返回按期号降序的原始 draw 列表（未校验）。
    """
    draws = []
    total = _fetch_official_total()
    if not total:
        total = limit
    total = min(total, limit or total)
    page_no = 1
    while len(draws) < total:
        page_size = OFFICIAL_PAGE_SIZE
        url = OFFICIAL_URL.format(game=OFFICIAL_GAME_NO, pageSize=page_size, pageNo=page_no)
        html = _http_get(url, timeout=20)
        page_draws = _parse_official(html)
        if not page_draws:
            break
        draws.extend(page_draws)
        if len(page_draws) < page_size:
            break
        page_no += 1
    return draws


def _is_valid_draw(d):
    """校验一条开奖记录是否合法（数据完整性门）。

    合法条件：前区 5 个、后区 2 个，前区 1-35、后区 1-12、无重复，期号非空。
    非法记录必须丢弃，绝不写入缓存/历史 —— 防止脏数据（如 500.com 期号截断、
    号码错切出 82/90 这类非前区号）污染后续 Bootstrap / 复盘结果。
    """
    front = d.get("front") or []
    back = d.get("back") or []
    # 必须恰好 5+2
    if len(front) != 5 or len(back) != 2:
        return False
    # 前区必须 1-35，后区必须 1-12
    if any(not (1 <= int(n) <= _FRONT_MAX) for n in front):
        return False
    if any(not (1 <= int(n) <= _BACK_MAX) for n in back):
        return False
    # 不允许重复号码
    if len(set(front)) != 5 or len(set(back)) != 2:
        return False
    # 期号非空（主源可能有 date 缺失容忍，但 issue 必须有）
    if not str(d.get("issue", "") or "").strip():
        return False
    return True


def _clean_draws(draws):
    """过滤并规范化，只保留合法记录（脏数据丢弃）。"""
    cleaned = []
    for d in draws:
        nd = _normalize_draw(d)
        if _is_valid_draw(nd):
            cleaned.append(nd)
    return cleaned


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
            # 缓存也要过校验，防历史脏缓存污染
            cached = _clean_draws(cached)
            if cached:
                return cached

    draws = []

    # 2. 首选：体彩官方 JSON API（翻页拉全量历史，数据最干净完整）
    try:
        draws = _fetch_official(limit or 3000)
        draws = _clean_draws(draws)
        if draws:
            draws.sort(key=_issue_sort_key, reverse=True)
            return _save_and_return(draws, limit)
    except Exception as e:
        print(f"  ⚠️ 官方接口获取失败: {e}", file=sys.stderr)
        draws = []

    # 3. 后备源（js-lottery / 500.com），统一过校验
    for url_template in BACKUP_URLS:
        try:
            if "{limit}" in url_template:
                url = url_template.format(limit=limit)
            else:
                url = url_template
            html = _http_get(url, timeout=15)
            if "500.com" in url:
                parsed = _parse_500com(html)
            else:
                parsed = _parse_js_lottery(html)
            valid = _clean_draws(parsed)
            if valid:
                draws = valid
                break
        except Exception as e:
            print(f"  ⚠️ 后备源获取失败: {e}", file=sys.stderr)
            continue

    # 4. 规范化、排序、落盘
    draws = _clean_draws(draws)
    draws.sort(key=_issue_sort_key, reverse=True)
    return _save_and_return(draws, limit)


def _issue_sort_key(d):
    """期号排序键：数字型按期号数值，非数字型放最后。"""
    s = str(d.get("issue", "") or "").strip()
    if s.isdigit():
        return (1, int(s))
    return (0, 0)


def _save_and_return(draws, limit=None):
    """清理后落盘并返回（脏数据不写盘）。"""
    if draws:
        _save_cache(draws)
        _save_history(draws)
    return draws[:limit] if limit else draws


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
