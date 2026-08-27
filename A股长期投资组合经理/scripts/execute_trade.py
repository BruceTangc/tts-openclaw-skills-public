#!/usr/bin/env python3
"""
尾盘交易执行脚本（异步后台运行）V2.0。

V2.0 变更：买入前增加投资假设卡校验（软检查，无假设卡时告警但不阻止）。
保留 14:45 时间守卫、风控检查、市价单执行。

妙想模拟盘 API 只支持市价单，不支持限价单。
因此本脚本只做一件事：市价下单 + 风控校验 + 推送。

用法：
  python3 execute_trade.py buy "600489" 1000            # 尾盘市价买入
  python3 execute_trade.py sell "601288" 100             # 尾盘市价卖出
  python3 execute_trade.py buy "600489" 1000 --bg        # 后台异步运行
  python3 execute_trade.py status                        # 查询当日委托
  python3 execute_trade.py watch "600489" 23.50 buy 1000 # 盯盘触发

买入口径：
  - 仅限尾盘（14:45-14:50）执行，禁止早盘/盘中市价追高
  - 涨幅 >4% 的股票自动跳过
  - 优先选当天下跌缩量或微涨（1%-3%）的标的
  - V2.0：买入前检查投资假设卡是否存在（无卡告警但不阻止）

注意事项：
  - 股票代码强制 6 位字符串，内部自动 zfill(6)
  - 卖出数量自动按 (usable_shares // 100) * 100 计算
  - 买入自动校验可用资金 + 已有持仓累计仓位
  - API 调用带 3 次退避重试
  - --bg 模式：fork + setsid + fork失败处理，完全脱离父进程
  - 卖出成功后自动更新 state.json（使用统一锁文件防竞态）
  - Circuit Breaker: 检测 state.json 的 circuit_breaker 标记
"""
import json, os, sys, time, subprocess, re, requests, logging, fcntl, resource
from datetime import datetime, date

BASE_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
STATE_PATH = os.path.join(BASE_DIR, "state.json")
LOCK_PATH = os.path.join(BASE_DIR, ".risk_control.lock")  # 统一锁文件
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

# F3 / F4：统一 BUY Gate + 交易意图幂等（本脚本所有 BUY 路径必须经此）
import buy_gate
import trade_intent
MX_MONI = os.path.join(BASE_DIR, "skills/mx-moni/mx_moni.py")
MX_API_URL = "{{MX_MONI_API_BASE}}"
LOG_DIR = os.path.join(BASE_DIR, "logs")
HYPOTHESIS_DIR = os.path.join(BASE_DIR, "memory", "hypothesis_cards")
os.makedirs(LOG_DIR, exist_ok=True)

POLL_INTERVAL = 300
FEISHU_USER = "{{FEISHU_USER_OPENID}}"
INIT_CAPITAL = 200000


# ===== 通用工具 =====

def setup_log(tag):
    log_file = os.path.join(LOG_DIR, f"trade_{tag}_{datetime.now().strftime('%H%M%S')}.log")
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    console = logging.StreamHandler(); console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)
    return log_file


def zfill_code(code):
    return str(code).strip().zfill(6)


def acquire_state_lock():
    """统一锁文件（与 risk_control.py 共享）"""
    lock_fd = open(LOCK_PATH, 'w')
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return lock_fd
        except BlockingIOError:
            time.sleep(0.3)
    # 超时：跳过本轮
    lock_fd.close()
    return None


def release_lock(lock_fd):
    if lock_fd:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_state_locked(state):
    """带统一锁写 state.json"""
    lock_fd = acquire_state_lock()
    if lock_fd is None:
        logging.warning("⚠️ 无法获取 state.json 锁，跳过状态更新")
        return False
    try:
        with open(STATE_PATH + ".tmp", 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(STATE_PATH + ".tmp", STATE_PATH)
        return True
    finally:
        release_lock(lock_fd)


def api_retry(fn, retries=3, delay=2):
    """统一重试：4xx 不重试，5xx/网络超时重试"""
    last_exc = None
    for attempt in range(retries):
        try:
            result = fn()
            if hasattr(result, 'status_code'):
                if result.status_code in (401, 403):
                    return result, "auth_error"
                result = result.json()
            return result, None
        except requests.exceptions.Timeout:
            last_exc = "timeout"
            if attempt < retries - 1: time.sleep(delay * (attempt + 1))
        except requests.exceptions.ConnectionError:
            last_exc = "connection"
            if attempt < retries - 1: time.sleep(delay * (attempt + 1))
        except Exception as e:
            last_exc = str(e)
            if attempt < retries - 1: time.sleep(delay * (attempt + 1))
    return None, last_exc


def get_api_key():
    key = os.environ.get('MX_APIKEY_MONI', '')
    if not key:
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                c = json.load(f)
            key = c.get('env', {}).get('MX_APIKEY_MONI', '')
    return key


def get_feishu_token():
    try:
        with open(os.path.expanduser("~/.openclaw/openclaw.json")) as f:
            cfg = json.load(f)
        fs = cfg.get('channels', {}).get('feishu', {})
        app_id, app_secret = fs.get('appId', ''), fs.get('appSecret', '')
        r = requests.post("{{FEISHU_API_BASE}}/open-apis/auth/v3/tenant_access_token/internal",
                          json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
        return r.json().get('tenant_access_token', '')
    except:
        return ''





def push_feishu(token, title, body_text):
    if not token:
        return
    try:
        content = json.dumps({"zh_cn": {"title": title, "content": [[{"tag": "text", "text": body_text}]]}})
        payload = json.dumps({"receive_id": FEISHU_USER, "msg_type": "post", "content": content})
        requests.post("{{FEISHU_API_BASE}}/open-apis/im/v1/messages?receive_id_type=open_id",
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      data=payload, timeout=10)
    except:
        pass

_global_fs_token = None

def get_fs_token_cached():
    """缓存飞书 token，后台模式只请求一次"""
    global _global_fs_token
    if _global_fs_token:
        return _global_fs_token
    try:
        config_path = os.path.expanduser("~/.openclaw/openclaw.json")
        if os.path.exists(config_path):
            with open(config_path) as f:
                cfg = json.load(f)
            fs = cfg.get('channels', {}).get('feishu', {})
            app_id = fs.get('appId', '')
            app_secret = fs.get('appSecret', '')
            # 跳过被脱敏的 secret（含 * 号表示已脱敏）
            if app_secret and '*' not in app_secret and app_id:
                r = requests.post(
                    "{{FEISHU_API_BASE}}/open-apis/auth/v3/tenant_access_token/internal",
                    json={"app_id": app_id, "app_secret": app_secret}, timeout=10
                )
                d = r.json()
                if d.get('code') == 0:
                    _global_fs_token = d.get('tenant_access_token', '')
    except:
        pass
    return _global_fs_token or ""


# 标记：mx_moni 调用超时（执行结果未知）。用于幂等——timeout 不能直接重试 BUY。
class _CallTimeout:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __repr__(self):
        return "<CALL_TIMEOUT>"

CALL_TIMEOUT = _CallTimeout()


def call_mx_moni(query, timeout=30):
    """调用 mx_moni.py（带重试）。
    返回：
      - 成功 -> stdout 字符串
      - 3 次重试均超时 -> CALL_TIMEOUT 哨兵（结果未知，严禁当作确定失败/成功）
      - 确定失败（非超时异常/空输出） -> ""
    """
    cmd = [sys.executable, MX_MONI, query]
    all_timeout = True
    for attempt in range(3):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            all_timeout = False
            return r.stdout
        except subprocess.TimeoutExpired:
            if attempt < 2: time.sleep(3 * (attempt + 1))
        except Exception as e:
            all_timeout = False
            if attempt < 2: time.sleep(2)
    if all_timeout:
        return CALL_TIMEOUT
    return ""


# ===== API 查询（带重试） =====

def get_balance():
    """获取可用资金（带重试）"""
    key = get_api_key()
    if not key:
        return 0, None
    def _do():
        return requests.post(f"{MX_API_URL}/api/claw/mockTrading/balance",
                             json={'moneyUnit': 1},
                             headers={'Content-Type': 'application/json', 'apikey': key}, timeout=15)
    data, err = api_retry(_do)
    if err or not data:
        return 0, err
    d = data.get('data', {})
    unit = d.get('currencyUnit', 1)
    if unit > 1:
        return d.get('availBalance', 0) / unit, None
    return d.get('availBalance', 0), None


def get_positions():
    """获取全部持仓（带重试）"""
    key = get_api_key()
    if not key:
        return [], None
    def _do():
        return requests.post(f"{MX_API_URL}/api/claw/mockTrading/positions",
                             json={'moneyUnit': 1},
                             headers={'Content-Type': 'application/json', 'apikey': key}, timeout=15)
    data, err = api_retry(_do)
    if err or not data:
        return [], err
    pos_list = data.get('data', {}).get('posList', []) or []
    return pos_list, None


def get_available_shares(code):
    pos_list, _ = get_positions()
    for pos in pos_list:
        if str(pos.get('secCode', '')).zfill(6) == zfill_code(code):
            return pos.get('availCount', 0)
    return 0


# ===== 风控检查 =====

def check_circuit_breaker(state):
    """Circuit Breaker 检查"""
    if state.get('circuit_breaker'):
        return False, "Circuit Breaker 激活（API 连续故障），跳过所有交易操作"
    return True, None


def check_hypothesis_card(code):
    """F4: 假设卡一票否决（真拒绝）。委托给 buy_gate 的严格校验。
    卡不存在 / 无效 / 必要字段缺失 / 过期 / 风险字段缺失 / 生命周期不允许 -> DENY。"""
    ok, msg = buy_gate.check_hypothesis_card(code, strict=True)
    return ok, msg


def check_risk(trade_type, code, price, quantity, is_market):
    """
    仓位风险前置检查（含已持仓累计仓位计算）。
    """
    state = load_state()

    # CB 检查
    ok, reason = check_circuit_breaker(state)
    if not ok:
        return False, reason

    if trade_type == 'buy':
        if state.get('defense_mode'):
            return False, "总回撤熔断激活（DEFENSE_MODE），禁止买入"
        if state.get('intraday_lock'):
            return False, "日内熔断激活（INTRADAY_LOCK），今日禁止买入"
        # 可用资金检查
        avail_balance, err = get_balance()
        if avail_balance <= 0 and err:
            return False, f"查询可用资金失败: {err}"
        unit_price = float(price) if not is_market else 0
        estimated_cost = unit_price * quantity if unit_price > 0 else quantity * 9999
        if estimated_cost > avail_balance * 0.95:
            return False, f"可用资金不足：需约{estimated_cost:.0f}元，可用{avail_balance:.0f}元"

        # 累计仓位检查（已持仓 + 本次买入）
        pos_list, _ = get_positions()
        total = state.get('total', INIT_CAPITAL)
        existing_pos_value = sum(p.get('value', 0) for p in pos_list if p.get('secCode'))
        new_pos_value = min(estimated_cost, avail_balance * 0.95)
        total_pos_ratio = (existing_pos_value + new_pos_value) / total * 100 if total > 0 else 0
        if total_pos_ratio > 40:
            return False, f"累计仓位{total_pos_ratio:.1f}%（含已有{existing_pos_value:.0f}+新{new_pos_value:.0f}）超40%上限"

        # 单票仓位检查（不超过总资产30%）
        for p in pos_list:
            if p.get('secCode') and str(p.get('secCode')).zfill(6) == code:
                existing_single = p.get('value', 0)
                single_ratio = (existing_single + new_pos_value) / total * 100 if total > 0 else 0
                if single_ratio > 30:
                    return False, f"单票仓位{single_ratio:.1f}%（含已有{existing_single:.0f}+新{new_pos_value:.0f}）超30%上限"
                break

    return True, None


# ===== 交易核心 =====

def update_cleared_positions(code):
    """卖出成功后更新 cleared_positions（带统一锁）"""
    lock_fd = acquire_state_lock()
    if lock_fd is None:
        logging.warning("⚠️ 无法获取锁，跳过 cleared_positions 更新")
        return
    try:
        state = load_state()
        cleared = state.get('cleared_positions', [])
        for c in cleared:
            if c.get('code') == zfill_code(code):
                return
        cleared.append({"code": zfill_code(code), "clear_date": date.today().isoformat()})
        state['cleared_positions'] = cleared
        with open(STATE_PATH + ".tmp", 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(STATE_PATH + ".tmp", STATE_PATH)
    finally:
        release_lock(lock_fd)


def execute_trade(trade_type, code, price, quantity):
    code = zfill_code(code)
    is_market = price and str(price).lower() == 'market'
    query = f"{'市价买入' if trade_type == 'buy' else '市价卖出'} {code} {quantity}" if is_market \
        else f"{'买入' if trade_type == 'buy' else '卖出'} {code} {price} {quantity}"

    if trade_type == 'sell':
        avail = get_available_shares(code)
        if avail <= 0:
            return {"status": "error", "message": f"{code} 可用股数为 0"}
        max_sell = (avail // 100) * 100
        if max_sell < 100 and avail > 0:
            max_sell = avail
        if quantity > max_sell:
            logging.info(f"卖出数量从 {quantity} 调整为可用股数 {max_sell}")
            quantity = max_sell

    output = call_mx_moni(query)
    # 超时：执行结果未知（可能已下单，也可能未下单）——必须标 UNKNOWN，严禁当作确定结果
    if output is CALL_TIMEOUT:
        return {"status": "timeout", "code": code, "type": trade_type,
                "quantity": quantity, "price": price, "order_id": None,
                "output": "", "message": "mx_moni 调用超时，执行结果未知"}
    output = output or ""
    order_id = None
    m = re.search(r'委托编号[：:\s]*(\S+)', output)
    if m:
        order_id = m.group(1)

    if trade_type == 'sell' and '失败' not in output:
        update_cleared_positions(code)

    return {"status": "submitted" if "失败" not in output else "failed",
            "code": code, "type": trade_type, "quantity": quantity, "price": price,
            "order_id": order_id, "output": output}


def get_order_status():
    return call_mx_moni("我的委托")


def check_order_filled(output):
    if not output: return False
    if '已成' in output or '全部成交' in output:
        if '已报' in output or '部成' in output: return False
        return True
    return False


def poll_until_filled(order_info, deadline_ts):
    if not order_info.get('order_id'):
        return order_info
    oid = order_info['order_id']
    while time.time() < deadline_ts:
        time.sleep(POLL_INTERVAL)
        logging.info(f"检查委托 {oid} 状态...")
        output = get_order_status()
        if check_order_filled(output):
            logging.info(f"委托 {oid} 已成交!")
            order_info['status'] = 'filled'; order_info['output'] = output; return order_info
        if '废单' in output:
            logging.info(f"委托 {oid} 已废单")
            order_info['status'] = 'cancelled'; order_info['output'] = output; return order_info
    logging.info(f"限价单未成交，撤单改市价...")
    call_mx_moni(f"撤单 {oid}")
    logging.info("改用市价单重发...")
    mkt = execute_trade(order_info['type'], order_info['code'], 'market', order_info['quantity'])
    order_info['market_order'] = mkt; order_info['status'] = 'resubmitted_market'
    return order_info


# ===== 后台运行 =====

def daemonize():
    """fork + setsid + close_fds，完全脱离父进程"""
    try:
        pid = os.fork()
    except OSError as e:
        return -1  # fork 失败
    if pid > 0:
        return pid
    # 子进程
    try:
        os.setsid()
    except:
        pass
    try:
        pid2 = os.fork()
        if pid2 > 0:
            os._exit(0)
    except OSError:
        os._exit(1)
    # 关闭 fd
    try:
        maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
        if maxfd == resource.RLIM_INFINITY: maxfd = 1024
        for fd in range(3, maxfd):
            try: os.close(fd)
            except: pass
    except:
        pass
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 0); os.dup2(devnull, 1); os.dup2(devnull, 2)
    os.close(devnull)
    return 0


# ===== 主执行 =====

def run_buy_guarded(code, price_str, quantity, background):
    """
    F3+F2+F4：统一 BUY 入口。所有能进入 BUY 的路径（signal/watch/cron/manual）最终都落到这里。

    调用链：
      run()/其他入口 ──> run_buy_guarded
        ├─> trade_intent.create_intent()   （建 PENDING 意图 + 幂等去重）
        ├─> buy_gate.buy_gate_decide()     （统一 BUY Gate：交易日/时间/假设卡/风控/仓位/幂等）
        ├─> trade_intent.mark_running()    （PENDING->EXECUTING）
        ├─> execute_trade()                （真正下单）
        └─> trade_intent.settle_intent()   （EXECUTING->EXECUTED/FAILED/REJECTED/UNKNOWN）

    幂等保证：
      - 相同 trade_intent_id 重复进入时，create_intent 直接返回既有状态；
      - UNKNOWN 状态严禁直接重试 BUY，必须先 query_unknown_before_retry 查执行结果。
    """
    try:
        # 0) 创建/去重交易意图（PENDING）
        opts_gate = {"source": "execute_trade"}
        intent_id, intent_state = trade_intent.create_intent(
            code, "buy", quantity,
            source=opts_gate["source"],
            intent_id=None,  # 每次 BUY 自动生成唯一 trade_intent_id
        )
        opts_gate["intent_id"] = intent_id

        # 若已存在且非 PENDING：幂等拦截（不得重复 BUY）
        if intent_state != trade_intent.PENDING:
            reason = f"BUY 被幂等拦截：意图 {intent_id} 状态={intent_state}"
            logging.warning(reason)
            if background:
                push_feishu(get_fs_token_cached(), "🛡️ 幂等拦截", reason)
            return None

        # 1) 统一 BUY Gate
        decision = buy_gate.buy_gate_decide(code, quantity, intent_id, opts_gate)
        if not decision["allowed"]:
            reason = decision["reason"]
            logging.error(reason)
            trade_intent.settle_intent(intent_id, trade_intent.REJECTED, message=reason)
            if background:
                push_feishu(get_fs_token_cached(), "❌ BUY Gate 拒绝", reason)
            return None
        gate_pass_info = decision["gate_pass_info"]
        logging.info(f"BUY Gate 通过: {gate_pass_info}")

        # 2) 二次校验：实时涨幅 >4% 放弃（保留 V2.0 防突变逻辑）
        current_pct = get_current_change_pct(code)
        if current_pct is not None and current_pct > 4:
            reason = f"❌ 涨幅{current_pct:.1f}%>4%，自动放弃买入（二次校验拦截）"
            logging.warning(reason)
            trade_intent.settle_intent(intent_id, trade_intent.REJECTED, message=reason)
            if background:
                push_feishu(get_fs_token_cached(), f"❌ 涨幅超限: {code}", reason)
            return None

        # 3) PENDING -> EXECUTING（标记开始执行，防重复进入）
        ok, entry = trade_intent.mark_running(intent_id, gate_pass_info=gate_pass_info)
        if not ok:
            st = entry.get("state") if isinstance(entry, dict) else None
            reason = f"BUY 已被占用（状态={st}），禁止重复执行"
            logging.warning(reason)
            if background:
                push_feishu(get_fs_token_cached(), "🛡️ 幂等拦截", reason)
            return None

        # 4) 真正下单（市价单；若执行超时/异常，交由 UNKNOWN 处理）
        result = execute_trade("buy", code, price_str, quantity)
        status = result.get("status", "unknown")
        order_id = result.get("order_id")

        # 4.1) 超时：执行结果未知。严禁直接重试，必须 UNKNOWN 后 query_unknown_before_retry
        if status == "timeout":
            msg = (f"⏱ BUY 调用超时，结果未知，状态置 UNKNOWN\n"
                   f"   必须先查询执行结果（intent retry-query）再决定是否重试")
            logging.error(msg)
            trade_intent.settle_intent(intent_id, trade_intent.UNKNOWN,
                                       order_id=order_id, message=msg)
            if background:
                push_feishu(get_fs_token_cached(), "⏱ BUY UNKNOWN（需查结果）", msg)
            return None

        if status == "failed":
            msg = f"❌ 下单失败: {result.get('message') or result.get('output', '')}"
            logging.error(msg)
            trade_intent.settle_intent(intent_id, trade_intent.FAILED, order_id=order_id, message=msg)
            if background:
                push_feishu(get_fs_token_cached(), "❌ 交易失败", msg)
            return None

        # 5) 成交确认后 EXECUTING -> EXECUTED（仅在确认成交/提交成功后标记，避免漏单）
        trade_intent.settle_intent(intent_id, trade_intent.EXECUTED,
                                   order_id=order_id, message=result.get("output", "")[:200])
        final_msg = f"✅ BUY 已完成 | {code} | {quantity}股 | 委托 {order_id or 'N/A'}"
        logging.info(final_msg)
        if background:
            push_feishu(get_fs_token_cached(), f"💰 交易结果: {code}", final_msg)
        return result
    except trade_intent.IntentLockError as e:
        msg = f"❌ 意图状态锁异常，BUY 未执行（fail-closed）: {e}"
        logging.error(msg)
        if background:
            push_feishu(get_fs_token_cached(), "❌ BUY 未执行", msg)
        return None
    except Exception as e:
        # 未知异常：绝不能盲目重试 BUY。标记 UNKNOWN（必须查结果后再决定）。
        msg = f"⚠️ BUY 执行异常，状态置 UNKNOWN（需查执行结果再决定）: {e}"
        logging.error(msg)
        try:
            trade_intent.mark_unknown_if_stale(intent_id)
        except Exception:
            pass
        if background:
            push_feishu(get_fs_token_cached(), "⚠️ BUY UNKNOWN", msg)
        return None


def run(trade_type, code, price_str, quantity, background):
    setup_log(f"{trade_type}_{code}")
    code = zfill_code(code)
    quantity = int(quantity)
    is_market = price_str.lower() == 'market'

    # 妙想模拟盘不支持限价单（所有限价单返回 code:100），一律转市价单
    if not is_market:
        logging.warning(f"⚠️ 妙想模拟盘不支持限价单，自动转为市价单")
        is_market = True
        price_str = 'market'

    logging.info(f"执行{'买入' if trade_type == 'buy' else '卖出'} {code} {'市价' if is_market else price_str} {quantity}股")

    # ===== F3+F2+F4: 所有 BUY 必须经统一 BUY Gate + 意图幂等 =====
    if trade_type == 'buy':
        guarded = run_buy_guarded(code, price_str, quantity, background)
        if background:
            # 后台模式：结果已由 run_buy_guarded 推送飞书，主进程可直接结束
            return
        if guarded is None:
            # 被拒/失败，run_buy_guarded 已推送并记录意图
            return
        # 前台模式把 guarded 结果作为交易 result 继续尾盘闭环（限价旧逻辑），
        # 但 V2.0 市价单下无需尾盘轮询，直接输出即可
        return

    # ===== 卖出路径（不经过 BUY Gate；卖出仍保留时间/风控/仓位检查） =====
    ok, reason = check_risk(trade_type, code, price_str, quantity, is_market)
    if not ok:
        msg = f"❌ 风险检查未通过: {reason}"
        logging.error(msg)
        if background:
            push_feishu(get_fs_token_cached(), "❌ 交易被风控拦截", msg)
        return

    result = execute_trade(trade_type, code, price_str, quantity)
    if result['status'] == 'failed':
        msg = f"❌ 下单失败: {result.get('message') or result.get('output', '')}"
        logging.error(msg)
        if background:
            push_feishu(get_fs_token_cached(), "❌ 交易失败", msg)
        return

    oid = result.get('order_id', 'N/A')
    logging.info(f"订单已提交 (ID: {oid})")

    # 尾盘闭环判断
    now = datetime.now()
    is_late = (now.hour == 14 and now.minute >= 30) or now.hour > 14
    if is_late and not is_market and oid:
        deadline = now.replace(hour=14, minute=50, second=0, microsecond=0)
        if deadline <= now:
            # 已过 14:50，直接转市价（跳过限价阶段）
            logging.info("已过 14:50，直接改用市价单...")
            result = execute_trade(trade_type, code, 'market', quantity)
            if result['status'] != 'failed':
                result['status'] = 'resubmitted_market'
        else:
            logging.info(f"尾盘限价单，轮询至 {deadline.strftime('%H:%M')}...")
            result = poll_until_filled(result, deadline.timestamp())

    status_map = {'filled': '✅ 已成交', 'cancelled': '❌ 已废单',
                  'resubmitted_market': '🔄 已转市价重发', 'submitted': '📋 已提交'}
    final_msg = f"{status_map.get(result['status'], result['status'])} | {code} | {quantity}股"
    logging.info(f"最终状态: {final_msg}")
    if background:
        push_feishu(get_fs_token_cached(), f"💰 交易结果: {code}", final_msg)


# ===== 盯盘触发模式 =====

POLL_INTERVAL_WATCH = 300  # 5分钟查一次价


def watch_price(code, target_price, direction, quantity, deadline_str=None):
    """
    盯盘触发模式：轮询当前价，到目标价时市价执行。

    参数:
        code: 股票代码
        target_price: 触发价（BUY: 低于此价触发, SELL: 高于此价触发）
        direction: 'buy' 或 'sell'
        quantity: 股数
        deadline_str: 截止时间，HH:MM 格式，超过则放弃
    """
    code = zfill_code(code)
    target_price = float(target_price)
    quantity = int(quantity)

    # 解析截止时间
    deadline = None
    if deadline_str:
        try:
            h, m = [int(x) for x in deadline_str.split(":")]
            now = datetime.now()
            deadline = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if deadline <= now:
                deadline = deadline.replace(day=deadline.day + 1)
        except:
            pass
    if deadline is None:
        # 默认尾盘截止 14:50
        now = datetime.now()
        deadline = now.replace(hour=14, minute=50, second=0, microsecond=0)
        if deadline <= now:
            deadline = deadline.replace(day=deadline.day + 1)

    tag = f"{direction[0]}_{code}_{target_price}"
    log_file = setup_log(tag)

    logging.info(f"开始盯盘 {code} {'买入' if direction == 'buy' else '卖出'} 目标价 {target_price} 数量 {quantity} 截止 {deadline.strftime('%H:%M')}")

    while time.time() < deadline.timestamp():
        # 查当前价
        price = get_current_price(code)
        if price is None:
            logging.warning(f"查价失败，5分钟后重试")
            time.sleep(POLL_INTERVAL_WATCH)
            continue

        logging.info(f"当前价 {price:.2f} 目标 {'≤' if direction == 'buy' else '≥'} {target_price:.2f}")

        triggered = False
        if direction == 'buy' and price <= target_price:
            triggered = True
            logging.info(f"✅ 触发买入！现价 {price:.2f} ≤ 目标 {target_price:.2f}")
        elif direction == 'sell' and price >= target_price:
            triggered = True
            logging.info(f"✅ 触发卖出！现价 {price:.2f} ≥ 目标 {target_price:.2f}")

        if triggered:
            if direction == 'buy':
                # F2: watch 不具备独立 BUY 能力——降级为只提示，不实际下单。
                # BUY 只能经统一 BUY Gate（run_buy_guarded / 14:45 cron）执行，watch 禁止绕过风控。
                msg = (f"🔔 盯盘提醒（仅提示，不自动买入）| {code} | 现价 {price:.2f} ≤ 目标 {target_price:.2f}\n"
                       f"   如需建仓，请走统一 BUY Gate（14:45 cron 二次验价后执行）")
                logging.info(msg)
                push_feishu(get_fs_token_cached(), f"🔔 盯盘提示: {code}", msg)
                return {"status": "alert_only", "code": code, "price": price, "quantity": quantity,
                        "direction": "buy", "note": "watch BUY 已降级为只提示，禁止绕过 BUY Gate 下单"}
            # SELL：维持原盯盘执行（卖出不受 BUY Gate 约束）
            result = call_mx_moni(f"市价卖出 {code} {quantity}")
            if '失败' not in result:
                msg = f"✅ 触发成功 | {code} | 卖出 {quantity}股 | 触发价 {price:.2f}"
                logging.info(msg)
                push_feishu(get_fs_token_cached(), f"💰 盯盘触发: {code}", msg)
                return {"status": "triggered", "code": code, "price": price, "quantity": quantity}
            else:
                msg = f"❌ 触发但下单失败: {result[:200]}"
                logging.error(msg)
                push_feishu(get_fs_token_cached(), f"❌ 盯盘失败: {code}", msg)
                return {"status": "failed", "code": code, "error": result}

        time.sleep(POLL_INTERVAL_WATCH)

    # 超时未触发
    msg = f"⏰ 盯盘到期未触发 | {code} | 目标 {target_price:.2f} | 方向 {'买入' if direction == 'buy' else '卖出'}"
    logging.info(msg)
    push_feishu(get_fs_token_cached(), f"⏰ 盯盘到期: {code}", msg)
    return {"status": "timeout", "code": code, "target": target_price}


def get_current_change_pct(code):
    """通过 mx_data 查询当前涨幅（买入前二次校验用）"""
    code = zfill_code(code)
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "skills/mx-data/mx_data.py"),
             f"{code} 最新价 涨跌幅",
             os.path.join(BASE_DIR, "tmp/mx_data_output")],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.join(BASE_DIR, "skills/mx-data")
        )
        if r.returncode != 0:
            return None
        out = r.stdout
        m = re.search(r'涨跌幅[：\s]*([+\-]?[\d.]+)%', out)
        if m:
            return float(m.group(1))
        return None
    except:
        return None


def get_current_price(code):
    """通过 mx_data 查询当前价"""
    code = zfill_code(code)
    try:
        r = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "skills/mx-data/mx_data.py"),
             f"{code} 最新价",
             os.path.join(BASE_DIR, "tmp/mx_data_output")],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.join(BASE_DIR, "skills/mx-data")
        )
        if r.returncode != 0:
            return None
        # 解析最新价
        out = r.stdout
        m = re.search(r'最新价[：\s]*([\d.]+)', out)
        if m:
            return float(m.group(1))
        return None
    except:
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    background = '--bg' in sys.argv
    args = [a for a in sys.argv[2:] if a != '--bg']
    if cmd == 'status':
        print(get_order_status()); return
    if cmd == 'watch':
        # python3 execute_trade.py watch <代码> <目标价> buy|sell <数量> [--deadline HH:MM] [--bg]
        if len(args) < 4:
            print("用法: python3 execute_trade.py watch <代码> <目标价> buy|sell <数量> [--deadline HH:MM] [--bg]")
            print("示例: python3 execute_trade.py watch 600489 23.50 buy 1000 --deadline 14:50")
            return
        code = args[0]
        target_price = args[1]
        direction = args[2]
        quantity = args[3]
        deadline_str = None
        if '--deadline' in args:
            di = args.index('--deadline')
            if di + 1 < len(args):
                deadline_str = args[di + 1]
        if background:
            ret = daemonize()
            if ret == -1:
                print("❌ fork 失败"); return
            if ret > 0:
                print(f"🚀 盯盘已在后台启动 (PID={ret})")
                print(f"   {code} {'买入' if direction == 'buy' else '卖出'} 目标价 ≤{target_price} 数量 {quantity}")
                print(f"   到价后自动市价执行，完成后推飞书通知")
                return
            sys.stdout = open(os.devnull, 'w'); sys.stderr = open(os.devnull, 'w')
        result = watch_price(code, target_price, direction, quantity, deadline_str)
        print(json.dumps(result, ensure_ascii=False))
        return
    if cmd in ('buy', 'sell'):
        if len(args) < 2:
            print(f"用法: python3 execute_trade.py {cmd} <代码> <价格/market> [数量] [--bg]"); return
        code, price_str = args[0], args[1].lower()
        quantity = args[2] if len(args) > 2 else "100"
        if background:
            ret = daemonize()
            if ret == -1:
                print("❌ fork 失败，无法后台运行"); return
            if ret > 0:
                print(f"🚀 execute_trade.py 已在后台启动 (PID={ret})")
                print(f"   交易: {cmd} {code} {price_str} {quantity}")
                print(f"   完成后自动推送飞书通知，LLM 无需等待")
                return
            sys.stdout = open(os.devnull, 'w'); sys.stderr = open(os.devnull, 'w')
        run(cmd, code, price_str, quantity, background)
        return
    if cmd in ('trade-intent', 'intent'):
        # 幂等状态排查/UNKNOWN 处理（无交易）：
        #   python3 execute_trade.py intent status
        #   python3 execute_trade.py intent get <intent_id>
        #   python3 execute_trade.py intent list
        #   python3 execute_trade.py intent retry-query <intent_id> <filled|not-filled> [--order-id XXX]
        if not args:
            print("用法: intent {status|list|get <id>|retry-query <id> <filled|not-filled> [--order-id X]}")
            return
        sub = args[0]
        if sub == 'status':
            trade_intent.intent_status()
        elif sub == 'list':
            for e in trade_intent.list_intents():
                print(f"{e.get('intent_id')} | {e.get('code')} | {e.get('state')} | {e.get('created_at')} | {e.get('message')}")
        elif sub == 'get' and len(args) >= 2:
            print(json.dumps(trade_intent.get_intent(args[1]), ensure_ascii=False, indent=2))
        elif sub == 'retry-query' and len(args) >= 3:
            iid, verdict = args[1], args[2]
            oid = None
            if '--order-id' in args:
                oid = args[args.index('--order-id') + 1]
            filled = verdict == 'filled'
            ok, entry = trade_intent.resolve_unknown(iid, filled, order_id=oid)
            print(json.dumps({"ok": ok, "entry": entry}, ensure_ascii=False, indent=2))
        else:
            print("未知 intent 子命令")
        return
    print(f"❌ 未知命令: {cmd}")

if __name__ == '__main__':
    main()
