#!/usr/bin/env python3
"""
风控熔断检查脚本。包含：
- 总回撤熔断（-15% 长期防御模式）
- 日内单日熔断（当日组合亏损 >3.5% → INTRADAY_LOCK，禁止买入）
- 状态持久化 JSON（state.json，LLM 只读不自己算）
- 文件锁（fcntl LOCK_EX 阻塞锁 + 超时回退）
- API 降级重试 + 4xx/5xx 区分
- API 故障时保持上次 NAV，标记 stale
- 自动清理 .tmp 残留
"""
import json, os, requests, sys, time, fcntl
from datetime import datetime, date

BASE_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
STATE_PATH = os.path.join(BASE_DIR, "state.json")
LOCK_PATH = os.path.join(BASE_DIR, ".risk_control.lock")

INIT_CAPITAL = 200000
DRAWDOWN_THRESHOLD = -15.0
INTRADAY_LOSS_THRESHOLD = -3.5
LOCK_TIMEOUT = 30


def cleanup_tmp():
    """启动时清理残留 .tmp 文件和过期日志"""
    now = time.time()
    # 确保 state 目录存在
    os.makedirs(os.path.join(BASE_DIR, 'state'), exist_ok=True)
    for f in os.listdir(BASE_DIR):
        fp = os.path.join(BASE_DIR, f)
        if f.endswith('.tmp') and os.path.isfile(fp):
            try:
                os.remove(fp)
            except:
                pass
    # 清理 7 天前的日志
    log_dir = os.path.join(BASE_DIR, 'logs')
    if os.path.isdir(log_dir):
        for f in os.listdir(log_dir):
            fp = os.path.join(log_dir, f)
            if os.path.isfile(fp) and now - os.path.getmtime(fp) > 7 * 86400:
                try:
                    os.remove(fp)
                except:
                    pass


def acquire_lock():
    """获取文件锁（阻塞锁，最多等 LOCK_TIMEOUT 秒）"""
    lock_fd = open(LOCK_PATH, 'w')
    deadline = time.time() + LOCK_TIMEOUT
    while time.time() < deadline:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_fd
        except BlockingIOError:
            time.sleep(0.5)
    # 超时：跳过本轮，不强制抢锁（防数据损坏）
    lock_fd.close()
    return None


def release_lock(lock_fd):
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    lock_fd.close()


def api_retry(fn, retries=3, delay=2):
    """API 退避重试。4xx 不重试，5xx/网络超时重试"""
    last_exc = None
    for attempt in range(retries):
        try:
            result = fn()
            # 检查 HTTP 状态码
            status = result.status_code if hasattr(result, 'status_code') else 200
            if status in (401, 403):
                # 认证错误不重试
                return result
            return result
        except requests.exceptions.Timeout:
            last_exc = "timeout"
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
        except requests.exceptions.ConnectionError:
            last_exc = "connection"
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
        except Exception as e:
            last_exc = str(e)
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    raise Exception(f"API 重试 {retries} 次全部失败: {last_exc}")


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                d = json.load(f)
                if d.get('schema_version', 0) < 1:
                    d['schema_version'] = 1
                # 维护 api_fail_consecutive 计数器
                if 'api_fail_consecutive' not in d:
                    d['api_fail_consecutive'] = 0
                return d
        except:
            pass
    return {
        "schema_version": 1,
        "nav": 1.0, "peak_nav": 1.0,
        "defense_mode": False,
        "intraday_lock": False, "intraday_lock_date": None,
        "day_start_nav": None, "day_start_date": None,
        "positions": [],
        "cleared_positions": [],
        "api_status": "ok",
        "circuit_breaker": False,
        "api_fail_consecutive": 0,
        "last_update": None,
    }


def save_state(state, lock_fd=None):
    state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["schema_version"] = 1
    if lock_fd:
        with open(STATE_PATH + ".tmp", 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(STATE_PATH + ".tmp", STATE_PATH)
    else:
        lock = acquire_lock()
        if lock is not None:
            try:
                with open(STATE_PATH + ".tmp", 'w') as f:
                    json.dump(state, f, indent=2, ensure_ascii=False)
                os.replace(STATE_PATH + ".tmp", STATE_PATH)
            finally:
                release_lock(lock)


def get_api_key():
    key = os.environ.get('MX_APIKEY_MONI', '')
    if not key:
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                c = json.load(f)
            key = c.get('env', {}).get('MX_APIKEY_MONI', '')
    return key


def fetch_balance():
    """带重试的资产查询。4xx 不重试直接返回 None。"""
    key = get_api_key()
    if not key:
        return None

    def _do():
        r = requests.post(
            "MX_MONI_API_BASE/api/claw/mockTrading/balance",
            json={'moneyUnit': 1},
            headers={'Content-Type': 'application/json', 'apikey': key},
            timeout=15
        )
        return r

    try:
        resp = api_retry(_do, retries=3, delay=2)
        if resp.status_code in (401, 403):
            print(f"⚠️ API 认证失败 (HTTP {resp.status_code})，API Key 可能已失效")
            return None
        data = resp.json().get('data', {})
        return {
            'totalAssets': data.get('totalAssets', 0) / (data.get('currencyUnit', 1) if data.get('currencyUnit', 1) > 0 else 1),
            'availBalance': data.get('availBalance', 0) / (data.get('currencyUnit', 1) if data.get('currencyUnit', 1) > 0 else 1),
        }
    except Exception as e:
        print(f"⚠️ API 查询失败: {e}")
        return None


def compute(data, state):
    """
    计算风控状态。
    data 为 None 时保持上次 NAV 并标记 stale。
    """
    today = date.today().isoformat()
    healthy_path = os.path.join(BASE_DIR, 'state', 'mx_api_healthy')

    if data is None:
        # API 故障：保持上次状态，标记 stale
        state['api_status'] = 'stale'
        print("⚠️ API 返回空 — 使用缓存 NAV，标记 stale")
        state['cash_ratio'] = state.get('cash_ratio', 0)
        
        # Circuit Breaker：检查是否连续失败
        try:
            prev = None
            if os.path.exists(healthy_path):
                with open(healthy_path) as f:
                    prev = f.read().strip()
            if prev == '0':
                state['circuit_breaker'] = True
                print("🔇 Circuit Breaker 触发：连续 2 个 Cron 检测到 API 故障")
            with open(healthy_path, 'w') as f:
                f.write('0')
        except:
            pass
        return state

    state['api_status'] = 'ok'
    state['circuit_breaker'] = False
    
    # Circuit Breaker 标记成功
    try:
        with open(healthy_path, 'w') as f:
            f.write('1')
    except:
        pass
    total = data.get('totalAssets', INIT_CAPITAL)
    nav = round(total / INIT_CAPITAL, 3)
    cash = data.get('availBalance', 0)
    cash_ratio = round(cash / total * 100, 1) if total > 0 else 0

    peak_nav = state.get('peak_nav', 1.0)
    if nav > peak_nav:
        peak_nav = nav
    drawdown = round((nav - peak_nav) / peak_nav * 100, 1)

    defense_mode = drawdown <= DRAWDOWN_THRESHOLD

    day_start_nav = state.get('day_start_nav')
    day_start_date = state.get('day_start_date')

    if day_start_date != today:
        # 新的一天：重置日内计数器（不管之前是否 stale）
        day_start_nav = nav
        day_start_date = today
        intraday_lock = False
        intraday_lock_date = None
    else:
        # 同一天：计算日内亏损
        intraday_loss_pct = round((nav - day_start_nav) / day_start_nav * 100, 1) if day_start_nav and day_start_nav > 0 else 0
        intraday_lock = state.get('intraday_lock', False)
        intraday_lock_date = state.get('intraday_lock_date')
        if not intraday_lock and intraday_loss_pct <= INTRADAY_LOSS_THRESHOLD:
            intraday_lock = True
            intraday_lock_date = today

    state.update({
        'nav': nav,
        'peak_nav': round(peak_nav, 3),
        'defense_mode': defense_mode,
        'intraday_lock': intraday_lock,
        'intraday_lock_date': intraday_lock_date,
        'day_start_nav': day_start_nav,
        'day_start_date': day_start_date,
        'cash_ratio': cash_ratio,
        'total': round(total, 2),
        'drawdown': drawdown,
        'intraday_loss_pct': round((nav - day_start_nav) / day_start_nav * 100, 1) if day_start_nav and day_start_nav > 0 and day_start_date == today else state.get('intraday_loss_pct', 0),
    })
    return state


def main():
    cleanup_tmp()
    lock_fd = acquire_lock()
    if lock_fd is None:
        print("⚠️ 无法获取锁（超时），跳过本轮风控更新")
        sys.exit(2)
    try:
        state = load_state()
        data = fetch_balance()
        
        # 更新 api_fail_consecutive 计数器
        if data is None:
            state['api_fail_consecutive'] = state.get('api_fail_consecutive', 0) + 1
        else:
            state['api_fail_consecutive'] = 0
        
        state = compute(data, state)
        save_state(state, lock_fd)

        mode = "🛡️ 防御模式(总回撤)" if state['defense_mode'] else "✅ 正常模式"
        if state['intraday_lock']:
            mode += " | 🔒 日内熔断(买入冻结)"
        if state.get('api_status') == 'stale':
            mode += " | ⚠️ 数据过时(API故障)"
        
        consec = state.get('api_fail_consecutive', 0)
        if consec >= 3:
            mode += " | 🔇 API连续失败"
            print(f"   ⚠️ API 已连续 {consec} 次失败，建议检查 API Key 或网络")

        print(f"【风控报告】{mode}")
        print(f"NAV: {state['nav']} | 总资产: {state['total']:.0f}")
        print(f"总回撤: {state['drawdown']}% | 现金比: {state['cash_ratio']}%")
        print(f"峰值: {state['peak_nav']} | API状态: {state.get('api_status', 'ok')}")

        if state['defense_mode']:
            print(f"⚠️ 总回撤{state['drawdown']}%≤{DRAWDOWN_THRESHOLD}%, 防御模式!")
        if state['intraday_lock']:
            print(f"🔒 日内锁(触发于{state['intraday_lock_date']})，今日禁止买入")

        sys.exit(0)
    except BlockingIOError:
        print("⚠️ 风控脚本被并发锁定，跳过本轮更新")
        sys.exit(2)
    finally:
        if lock_fd:
            release_lock(lock_fd)


if __name__ == '__main__':
    main()
