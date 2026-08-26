#!/usr/bin/env python3
"""
自选股淘汰计算脚本 V2.0。

V2.0 变更：淘汰标准从单纯跌幅/天数升级为基本面恶化/长期逻辑消失/假设失效。
价格表现只作辅助参考，不作为主要淘汰依据。

LLM 只需调用本脚本，由 Python 做天数对比和逻辑判断，LLM 不要自己推理天数。
支持并发控制（文件锁），以及多只股票的并行查询。

调用方式：
  python3 cleanup_zixuan.py
"""
import json, os, sys, subprocess, re, fcntl, concurrent.futures, time
from datetime import date

BASE_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
STATE_PATH = os.path.join(BASE_DIR, "state.json")
ADDED_DATE_FILE = os.path.join(BASE_DIR, "memory", "zixuan_added_dates.json")
LOCK_PATH = os.path.join(BASE_DIR, ".cleanup_zixuan.lock")

CONSECUTIVE_DAYS_NO_TRADE = 10
MAX_DRAWDOWN = -15.0
MAX_DAYS_NO_CANDIDATE = 30
CLEANUP_OBSERVE_DAYS = 14
MAX_CONCURRENT = 5
HYPOTHESIS_DIR = os.path.join(BASE_DIR, "memory", "hypothesis_cards")


def check_hypothesis_status(code):
    """V2.0: 检查假设卡是否标记为失效/证伪"""
    card_path = os.path.join(HYPOTHESIS_DIR, f"{code}.json")
    if not os.path.exists(card_path):
        return None  # 无假设卡，不基于此淘汰
    try:
        with open(card_path) as f:
            card = json.load(f)
        lifecycle = card.get('lifecycle', '')
        if lifecycle in ('EXIT', 'COOLDOWN'):
            return f"假设卡生命周期={lifecycle}（已退出/冷却中）"
        # 检查 falsifier 是否已触发
        falsifiers = card.get('falsifiers', [])
        for f in falsifiers:
            if f.get('action') == 'EXIT' or f.get('action') == 'EXIT_FORCE':
                return f"假设卡含有退出条件: {f.get('metric', '未指定')}"
        return None
    except:
        return None


def acquire_lock():
    """文件锁保护 JSON 读写（带超时退避）"""
    lock_fd = open(LOCK_PATH, 'w')
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_fd
        except BlockingIOError:
            time.sleep(0.5)
    lock_fd.close()
    return None


def release_lock(lock_fd):
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    lock_fd.close()


def read_watchlist():
    """读取自选股列表"""
    paths = [
        os.path.join(BASE_DIR, 'skills/mx-zixuan/zixuan.txt'),
        os.path.join(BASE_DIR, 'config/zixuan.txt'),
        '/root/.openclaw/workspace/mx_data/zixuan.txt',
    ]
    codes = []
    for path in paths:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    parts = line.strip().split()
                    if parts and parts[0].isdigit() and len(parts[0]) == 6:
                        codes.append(parts[0])
            if codes:
                break
    return codes


def load_added_dates():
    if os.path.exists(ADDED_DATE_FILE):
        try:
            with open(ADDED_DATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                d = json.load(f)
                if d.get('circuit_breaker'):
                    print("🔇 Circuit Breaker 激活（API 连续故障），跳过淘汰评估")
                    sys.exit(0)
                return d
        except:
            pass
    return {}


def fetch_price_history_worker(code, days=30):
    """并发worker：通过 mx-data skill 获取近期收盘价"""
    script = os.path.join(BASE_DIR, 'skills/mx-data/mx_data.py')
    cmd = [sys.executable, script, f"{code} 近{days}日收盘价"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        prices = [float(n) for line in result.stdout.split('\n')
                  for n in re.findall(r'(\d+\.\d+)元', line)]
        return code, (prices if prices else None), None
    except subprocess.TimeoutExpired:
        return code, None, "超时"
    except Exception as e:
        return code, None, str(e)


def main():
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("⚠️ 无法获取锁（超时），跳过本轮清理")
        return
    try:
        codes = read_watchlist()

        if not codes:
            print("❌ 自选股列表为空")
            return

        added_dates = load_added_dates()
        state = load_state()
        cleared = state.get('cleared_positions', [])

        print(f"📋 自选股淘汰评估 | {date.today()} | 共{len(codes)}只")
        print("=" * 55)

        # 并发获取行情（最多 5 路并行）
        any_remove = False
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
            futures = {pool.submit(fetch_price_history_worker, c): c for c in codes}
            for future in concurrent.futures.as_completed(futures):
                code, prices, err = future.result()
                results[code] = (prices, err)

        for code in codes:
            prices, err = results.get(code, (None, None))
            added_info = added_dates.get(code, {})
            added_days = None
            if added_info.get('added_date'):
                try:
                    added_days = (date.today() - date.fromisoformat(added_info['added_date'])).days
                except:
                    pass

            reasons = []
            warn_notes = []

            # V2.0: 假设卡状态检查（优先于价格/天数淘汰）
            hypo_reason = check_hypothesis_status(code)
            if hypo_reason:
                reasons.append(hypo_reason)

            if err:
                warn_notes.append(f"⚠️ 行情查询失败: {err}")

            if prices and len(prices) >= 5:
                max_change = max(abs((prices[i] - prices[i-1]) / prices[i-1] * 100)
                               for i in range(1, len(prices)))
                if max_change < 3.0 and added_days and added_days >= CONSECUTIVE_DAYS_NO_TRADE:
                    reasons.append(f"连续{added_days}天未触发买入(波动{max_change:.1f}%<3%)")

            if prices and len(prices) >= 3:
                peak = max(prices)
                current = prices[-1]
                dd = (current - peak) / peak * 100
                if dd <= MAX_DRAWDOWN:
                    reasons.append(f"距高点回撤{dd:.1f}%≤{MAX_DRAWDOWN}%")

            if added_days and added_days >= MAX_DAYS_NO_CANDIDATE:
                reasons.append(f"加入{added_days}天未进备选建仓名单")

            for c in cleared:
                if c.get('code') == code and c.get('clear_date'):
                    try:
                        clear_days = (date.today() - date.fromisoformat(c['clear_date'])).days
                        if clear_days >= CLEANUP_OBSERVE_DAYS:
                            reasons.append(f"清仓已观察{clear_days}天无起色")
                    except:
                        pass

            if reasons:
                any_remove = True
                print(f"🗑️ {code}: 建议移除")
                for r in reasons:
                    print(f"   - {r}")
            else:
                print(f"✅ {code}: 保留")
            for w in warn_notes:
                print(f"   {w}")

        if not any_remove:
            print("\n✅ 当前自选股均无需淘汰")

        print("\n💡 LLM 须知（V2.0）：")
        print("   - 淘汰评估由 Python 脚本完成，LLM 不要自己计算天数或回撤")
        print("   - 假设失效/生命周期 EXIT/COOLDOWN 为最高优先级淘汰理由")
        print("   - 基本面恶化/长期逻辑消失/行业空间下降需 LLM 通过 mx-search 独立判断")
        print("   - 价格表现仅作辅助参考（如回撤>15%但假设有效 → 保留并触发 RE_STUDY）")
        print("   - 如需移除，先调 mx-zixuan skill 移除，再调 update_zixuan_meta.py remove")
        print("   - 淘汰原因写入复盘报告")
    finally:
        release_lock(lock_fd)
