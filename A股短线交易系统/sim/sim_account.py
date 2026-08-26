#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股短线模拟账户引擎 (V1.1)
独立于东财妙想的内部虚拟账本系统。所有资金/持仓/订单/成交可追溯、可对账。

核心命令（详见 SKILL.md「引擎命令」章节）：
  init / status / order / cancel / tick / expire / positions / orders / fills /
  settle / reconcile / stats / cashflow / corp_action / shadow / snapshot

原则：不使用未来数据、不编造行情、不默认成交；T+1、涨跌停排队、竞价撮合、
幂等、TTL、对账、风控一应俱全。
"""

import argparse
import json
import os
import sys
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SKILL_DIR, "data")
CONFIG_PATH = os.path.join(SKILL_DIR, "config.json")

DEFAULT_CONFIG = {
    "fees": {
        "commission_rate": 0.00025,     # 佣金 万2.5
        "min_commission": 5.0,          # 最低佣金 5 元
        "stamp_tax_rate": 0.0005,       # 印花税 卖出单向 0.5‰
        "stamp_tax_side": "SELL",
        "transfer_fee_rate": 0.00001,   # 过户费 双向 0.01‰
        "transfer_fee_side": "BOTH"
    },
    "risk": {
        "max_single_position_pct": 0.20,
        "max_topic_exposure_pct": 0.50,
        "max_total_position_pct": 0.80,
        "weak_market_max_total_pct": 0.20,
        "extreme_market_max_total_pct": 0.10,
        "daily_loss_reduce_pct": 0.015,
        "daily_loss_stop_pct": 0.02,
        "daily_loss_lock_pct": 0.03,
        "drawdown_reduce_pct": 0.05,
        "drawdown_stop_pct": 0.08,
        "drawdown_protect_pct": 0.10
    },
    "interest": {"idle_annual_rate": 0.0},
    "market_regime": "NORMAL"
}

ORDER_STATUS = ("PENDING", "PARTIAL_FILLED", "FILLED", "CANCELLED", "REJECTED", "EXPIRED")
TIF_VALUES = ("GTC", "IOC", "FOK")
SESSIONS = ("AUCTION_AM", "CONTINUOUS", "AUCTION_PM", "AFTER_HOURS", "KLINE")
DATA_GRADES = ("DATA_A", "DATA_B", "DATA_C", "DATA_INVALID", "DATA_CONFLICT")

# ------------------------------------------------------------------
# 运行模式语义（防止未来数据污染实时模拟）：
#
#   REALTIME（实时模拟）：AUCTION_AM / CONTINUOUS / AUCTION_PM / AFTER_HOURS
#     只允许使用订单/撮合时点【当时已可获得】的数据（当前 tick 的 price 等）。
#     禁止用当天（或未来）的 low/high/close 回填更早时点的成交。
#
#   KLINE = HISTORICAL_REPLAY（历史回放）：
#     仅对【已经走完】的时段/K线成立，允许用完整 K 线的 low/high 判断
#     该时段内订单是否曾触达价格。这是事后回放，不是实时模拟，
#     也不得与实时盘中混用去凭空制造未来成交。
#
#   判定标准：若一笔成交的时间戳早于其 K 线时段结束时间，但成交价格
#   依据了该时段收盘后才确定的 low/high，即为未来函数，禁止。
# ------------------------------------------------------------------
HISTORICAL_REPLAY_SESSION = "KLINE"   # 该会话 = 历史回放模式


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            for k in ("fees", "risk", "interest"):
                if k in loaded and isinstance(loaded[k], dict):
                    cfg[k].update(loaded[k])
            if "market_regime" in loaded:
                cfg["market_regime"] = loaded["market_regime"]
    return cfg


CONFIG = load_config()


def _money(x):
    return round(float(x) + 1e-9, 2)


# ---------------------------------------------------------------- 状态读写

def _path(name):
    return os.path.join(DATA_DIR, name)


def _load(name, default):
    p = _path(name)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def _save(name, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now().strftime("%Y-%m-%d")


# ---------------------------------------------------------------- 日志

def log(event, obj="", old="", new="", reason="", src=""):
    logdir = os.path.join(DATA_DIR, "logs")
    os.makedirs(logdir, exist_ok=True)
    entry = {"ts": now(), "event": event, "object": obj,
             "old": old, "new": new, "reason": reason, "src": src}
    with open(os.path.join(logdir, today() + ".jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- 账本

def get_account():
    return _load("account.json", {
        "account_id": "SHORT_TERM_SIM",
        "name": "A股短线模拟账户",
        "initial_capital": 0.0,
        "cash": 0.0, "frozen": 0.0,
        "total_fees": 0.0,
        "realized_pnl_gross": 0.0, "realized_pnl_net": 0.0,
        "max_asset": 0.0, "max_drawdown": 0.0,
        "prev_close_asset": 0.0, "prev_close_date": None,
        "status": "NORMAL", "data_status": "DATA_A", "risk_status": "NORMAL",
        "intraday_lock": False, "protect": False,
        "created": now(), "last_settle_date": None,
    })


def save_account(acc):
    _save("account.json", acc)


def get_positions():
    return _load("positions.json", {})


def save_positions(pos):
    _save("positions.json", pos)


def get_orders():
    return _load("orders.json", [])


def save_orders(orders):
    _save("orders.json", orders)


def get_fills():
    return _load("fills.json", [])


def save_fills(fills):
    _save("fills.json", fills)


def get_cashflow():
    return _load("cashflow.json", [])


def save_cashflow(cf):
    _save("cashflow.json", cf)


def get_market():
    return _load("market.json", {})


def save_market(mkt):
    _save("market.json", mkt)


def add_cashflow(acc, category, code, amount, note=""):
    cf = get_cashflow()
    cf.append({"ts": now(), "date": today(), "category": category,
               "code": code, "amount": _money(amount),
               "balance": _money(acc["cash"]), "note": note})
    save_cashflow(cf)


# ---------------------------------------------------------------- 总账计算

def position_market_value(pos, mkt):
    mv = 0.0
    for code, p in pos.items():
        last = p.get("last_price") or 0.0
        mv += p["total"] * last
    return _money(mv)


def total_assets(acc, pos, mkt):
    return _money(acc["cash"] + acc["frozen"] + position_market_value(pos, mkt))


def position_pct(pos_mv, assets):
    return (pos_mv / assets) if assets else 0.0


# ---------------------------------------------------------------- 费用

def calc_fees(amount, side):
    f = CONFIG["fees"]
    commission = max(amount * f["commission_rate"], f["min_commission"])
    stamp = amount * f["stamp_tax_rate"] if f["stamp_tax_side"] == side else 0.0
    transfer = amount * f["transfer_fee_rate"] if f["transfer_fee_side"] == "BOTH" else 0.0
    total = commission + stamp + transfer
    return _money(total), {"commission": _money(commission),
                           "stamp_tax": _money(stamp),
                           "transfer_fee": _money(transfer)}


# ---------------------------------------------------------------- 对账

def reconcile(acc, pos, mkt, verbose=True):
    errors = []
    mv = position_market_value(pos, mkt)
    total = _money(acc["cash"] + acc["frozen"] + mv)

    if acc["cash"] < -0.001:
        errors.append("可用资金为负: %s" % acc["cash"])
    if acc["frozen"] < -0.001:
        errors.append("冻结资金为负: %s" % acc["frozen"])
    for code, p in pos.items():
        if p["total"] < 0 or p["sellable"] < 0 or p["today_buy_qty"] < 0:
            errors.append("持仓数量异常: %s" % code)
        if abs(p["total"] - (p["sellable"] + p["today_buy_qty"] + p["frozen_qty"])) > 0:
            errors.append("持仓T+1关系异常: %s" % code)

    if errors:
        acc["status"] = "RECONCILIATION_ERROR"
        acc["risk_status"] = "RECONCILIATION_ERROR"
        log("RECONCILIATION", "", "", "", "; ".join(errors), "reconcile")
    else:
        if acc["status"] == "RECONCILIATION_ERROR":
            acc["status"] = "NORMAL"
            acc["risk_status"] = "NORMAL"
        log("RECONCILIATION", "PASS", "", "", "", "reconcile")
    save_account(acc)
    if verbose:
        print("对账: %s" % ("PASS" if not errors else "ERROR"))
        for e in errors:
            print("  -", e)
    return (not errors), errors


# ---------------------------------------------------------------- 风控

def current_drawdown(acc, assets):
    if acc["max_asset"] <= 0:
        return 0.0
    return (acc["max_asset"] - assets) / acc["max_asset"]


def daily_loss_pct(acc, assets):
    base = acc.get("prev_close_asset") or acc["initial_capital"] or assets
    if base <= 0:
        return 0.0
    return (assets - base) / base


def risk_check_new_buy(acc, pos, mkt, code, qty, price, topic=None):
    r = CONFIG["risk"]
    assets = total_assets(acc, pos, mkt)
    mv = position_market_value(pos, mkt)

    if acc["status"] == "RECONCILIATION_ERROR":
        return False, "对账异常，禁止新增交易"
    if acc.get("protect"):
        return False, "ACCOUNT_PROTECTED：账户保护期，禁止开新仓"
    if acc.get("intraday_lock"):
        return False, "INTRADAY_LOCK：日内锁定，禁止新增仓"

    dd = current_drawdown(acc, assets)
    if dd >= r["drawdown_protect_pct"]:
        acc["protect"] = True
        save_account(acc)
        return False, "回撤>=%.0f%%：账户保护" % (r["drawdown_protect_pct"] * 100)
    if dd >= r["drawdown_stop_pct"]:
        return False, "回撤>=%.0f%%：暂停主动新增仓" % (r["drawdown_stop_pct"] * 100)

    dl = daily_loss_pct(acc, assets)
    if dl <= -r["daily_loss_lock_pct"]:
        acc["intraday_lock"] = True
        save_account(acc)
        return False, "当日亏损>=%.1f%%：INTRADAY_LOCK" % (r["daily_loss_lock_pct"] * 100)
    if dl <= -r["daily_loss_stop_pct"]:
        return False, "当日亏损>=%.1f%%：停止普通新增仓" % (r["daily_loss_stop_pct"] * 100)

    buy_amount = qty * price
    new_mv = mv + buy_amount
    new_pos_pct = new_mv / assets if assets else 1.0
    regime_cap = {"NORMAL": r["max_total_position_pct"],
                  "WEAK": r["weak_market_max_total_pct"],
                  "EXTREME": r["extreme_market_max_total_pct"]}.get(
                      CONFIG["market_regime"], r["max_total_position_pct"])
    if new_pos_pct > regime_cap:
        return False, "总仓位超限（%.1f%%>%.0f%% 当前%s）" % (
            new_pos_pct * 100, regime_cap * 100, CONFIG["market_regime"])

    existing = pos.get(code, {})
    total_qty = existing.get("total", 0) + qty
    single_amount = total_qty * price
    single_pct = single_amount / assets if assets else 1.0
    if single_pct > r["max_single_position_pct"]:
        return False, "单票仓位超限（%.1f%%>%.0f%%）" % (
            single_pct * 100, r["max_single_position_pct"] * 100)

    if topic:
        topic_amount = sum(
            (p.get("topic") == topic) * (p["total"] * (p.get("last_price") or 0))
            for p in pos.values()) + buy_amount
        if topic_amount / assets > r["max_topic_exposure_pct"]:
            return False, "题材[%s]敞口超限" % topic

    return True, ""


# ---------------------------------------------------------------- 持仓更新

def update_position_fill(pos, code, direction, qty, price, fees, ts, model):
    if code not in pos:
        pos[code] = {"code": code, "name": "", "market": "",
                     "total": 0, "sellable": 0, "frozen_qty": 0, "today_buy_qty": 0,
                     "cost_price": 0.0, "cost_amount": 0.0,
                     "last_price": price, "unrealized_pnl": 0.0,
                     "realized_gross": 0.0, "realized_net": 0.0,
                     "fees": 0.0, "topic": "",
                     "first_buy_time": None, "last_buy_time": None, "last_sell_time": None}
    p = pos[code]
    if direction == "BUY":
        new_cost = p["cost_amount"] + qty * price + fees
        p["cost_amount"] = _money(new_cost)
        p["total"] += qty
        p["today_buy_qty"] += qty
        if not p["first_buy_time"]:
            p["first_buy_time"] = ts
        p["last_buy_time"] = ts
        p["cost_price"] = _money(p["cost_amount"] / p["total"]) if p["total"] else _money(price)
    else:
        gross = (price - p["cost_price"]) * qty
        net = gross - fees
        p["realized_gross"] = _money(p["realized_gross"] + gross)
        p["realized_net"] = _money(p["realized_net"] + net)
        p["total"] -= qty
        # 成交只减少 total 与 frozen_qty：sellable 在卖单冻结时已扣减，这里不再重复扣。
        # 账务恒等式 total = sellable + today_buy_qty + frozen_qty 天然成立。
        p["frozen_qty"] = max(0, p.get("frozen_qty", 0) - qty)
        p["last_sell_time"] = ts
        if p["total"] > 0:
            p["cost_amount"] = _money(p["cost_amount"] - qty * p["cost_price"])
            p["cost_price"] = _money(p["cost_amount"] / p["total"])
        else:
            p["cost_amount"] = 0.0
            p["cost_price"] = 0.0
    p["fees"] = _money(p.get("fees", 0.0) + fees)
    p["last_price"] = price
    if p["total"] <= 0:
        pos.pop(code, None)


def mark_to_market(pos, mkt):
    for code, p in pos.items():
        q = mkt.get(code, {})
        last = q.get("price") or p.get("last_price") or 0.0
        if last:
            p["last_price"] = last
        p["unrealized_pnl"] = _money(p["total"] * p["last_price"] - p["cost_amount"])


# ---------------------------------------------------------------- 成交

def apply_fill(acc, pos, order, qty, price, basis, model="", src=""):
    side = order["direction"]
    amount = qty * price
    fees, detail = calc_fees(amount, side)
    ts = now()
    acc["total_fees"] = _money(acc["total_fees"] + fees)

    if side == "BUY":
        # 下单时已按委托价冻结资金（qty*委托价）。
        # 成交时：实际成交额 = qty*成交价；解冻本笔对应的委托冻结额；
        #   委托冻结额 - 实际成交额的差额释放回 cash，避免留下永久 frozen。
        #   部分成交时只解冻/释放本笔成交对应的部分，剩余未成交订单冻结继续保留。
        frozen_price = order.get("price", price)  # 下单时冻结所用的单价（委托价/市价基准价）
        frozen_for_fill = _money(qty * frozen_price)   # 本笔成交对应的委托冻结额
        amount = _money(qty * price)                    # 本笔成交实际成交额
        refund_diff = _money(frozen_for_fill - amount)  # 多冻结差额 → 释放回 cash
        acc["cash"] = _money(acc["cash"] - fees + refund_diff)
        acc["frozen"] = max(0.0, _money(acc["frozen"] - frozen_for_fill))
        add_cashflow(acc, "TRADE_SETTLEMENT", order["code"], -amount,
                     "买入 %sx%d@%.2f" % (order["code"], qty, price))
        if refund_diff > 0:
            add_cashflow(acc, "UNFREEZE_DIFF", order["code"], refund_diff,
                         "释放多冻结金额 %.2f" % refund_diff)
        if fees > 0:
            add_cashflow(acc, "FEE", order["code"], -fees, "买入费用 佣%.2f/印%.2f/过%.2f" % (
                detail["commission"], detail["stamp_tax"], detail["transfer_fee"]))
        update_position_fill(pos, order["code"], "BUY", qty, price, fees, ts, model)
    else:
        acc["cash"] = _money(acc["cash"] + amount - fees)
        add_cashflow(acc, "TRADE_SETTLEMENT", order["code"], amount,
                     "卖出 %sx%d@%.2f" % (order["code"], qty, price))
        if fees > 0:
            add_cashflow(acc, "FEE", order["code"], -fees, "卖出费用 佣%.2f/印%.2f/过%.2f" % (
                detail["commission"], detail["stamp_tax"], detail["transfer_fee"]))
        update_position_fill(pos, order["code"], "SELL", qty, price, fees, ts, model)

    order["filled_qty"] += qty
    order["filled_amount"] = _money(order.get("filled_amount", 0.0) + amount)
    order["avg_price"] = _money(order["filled_amount"] / order["filled_qty"])
    order["fees"] = _money(order.get("fees", 0.0) + fees)
    order["status"] = "FILLED" if order["filled_qty"] >= order["qty"] else "PARTIAL_FILLED"

    fills = get_fills()
    fills.append({
        "fill_id": "F%06d" % (len(fills) + 1),
        "order_id": order["order_id"],
        "ts": ts, "date": today(),
        "code": order["code"], "direction": side,
        "qty": qty, "price": _money(price), "amount": _money(amount),
        "fees": _money(fees), "fill_type": basis, "src": src,
        "model": model or order.get("model", ""),
        "strategy": order.get("model", ""),
        "note": order.get("reason", ""),
    })
    save_fills(fills)
    log("FILL", order["code"], "", "%dx%d@%.2f" % (qty, qty, price), basis, src)
    return fees


# ---------------------------------------------------------------- 撮合条件

def _order_can_fill(order, q, session):
    code = order["code"]
    direction = order["direction"]
    grade = q.get("grade", "DATA_A")
    if grade in ("DATA_INVALID", "DATA_CONFLICT"):
        return False, None, "数据无效/冲突，禁止成交"
    if q.get("suspend"):
        return False, None, "停牌/不可交易"
    if q.get("price") is None:
        return False, None, "无最新价"

    price = q["price"]
    limit_up = q.get("limit_up")
    limit_down = q.get("limit_down")
    seal_qty = q.get("seal_qty", 0)

    if session == "AUCTION_AM":
        open_p = q.get("open")
        if open_p is None:
            return False, None, "竞价无开盘价"
        if direction == "BUY":
            return order["price"] >= open_p, open_p, "早盘竞价撮合"
        else:
            return order["price"] <= open_p, open_p, "早盘竞价撮合"

    if session == "AUCTION_PM":
        close_p = q.get("close")
        if close_p is None:
            return False, None, "尾盘竞价无收盘价"
        if direction == "BUY":
            return order["price"] >= close_p, close_p, "尾盘竞价撮合"
        else:
            return order["price"] <= close_p, close_p, "尾盘竞价撮合"

    if session == "AFTER_HOURS":
        close_p = q.get("close")
        if close_p is None:
            return False, None, "盘后交易无收盘价"
        if direction == "BUY":
            return order["price"] >= close_p, close_p, "盘后固定价格"
        else:
            return order["price"] <= close_p, close_p, "盘后固定价格"

    if session == "KLINE":
        if direction == "BUY":
            low = q.get("low")
            return (low is not None and low <= order["price"]), order["price"], "SIMULATED_KLINE_FILL"
        else:
            high = q.get("high")
            return (high is not None and high >= order["price"]), order["price"], "SIMULATED_KLINE_FILL"

    # CONTINUOUS
    if direction == "BUY":
        if limit_up and price >= limit_up and order["price"] >= limit_up:
            if seal_qty and seal_qty > 0:
                return False, None, "涨停封单排队中(seal_qty=%d)" % seal_qty
            return False, None, "涨停无法确认排队成交"
        if price <= order["price"]:
            return True, order["price"], "连续竞价成交"
        return False, None, "价格未到限价"
    else:
        if limit_down and price <= limit_down and order["price"] <= limit_down:
            if seal_qty and seal_qty > 0:
                return False, None, "跌停封单排队中(seal_qty=%d)" % seal_qty
            return False, None, "跌停无法确认排队成交"
        if price >= order["price"]:
            return True, order["price"], "连续竞价成交"
        return False, None, "价格未到限价"


# ---------------------------------------------------------------- 命令实现

def cmd_init(args):
    acc = get_account()
    acc["initial_capital"] = _money(args.initial)
    acc["cash"] = _money(args.initial)
    acc["frozen"] = 0.0
    acc["max_asset"] = _money(args.initial)
    acc["prev_close_asset"] = _money(args.initial)
    acc["status"] = "NORMAL"
    acc["risk_status"] = "NORMAL"
    acc["intraday_lock"] = False
    acc["protect"] = False
    save_account(acc)
    save_positions({})
    save_orders([])
    save_fills([])
    save_cashflow([])
    add_cashflow(acc, "INITIAL", "", acc["initial_capital"], "初始入金")
    log("SYSTEM", "init", "", "%s" % args.initial, "", "cli")
    print("OK 账户初始化: %s 初始资金 %.2f" % (acc["account_id"], acc["initial_capital"]))


def cmd_status(args):
    acc = get_account()
    pos = get_positions()
    mkt = get_market()
    assets = total_assets(acc, pos, mkt)
    mv = position_market_value(pos, mkt)
    acc["max_asset"] = max(acc["max_asset"], assets)
    acc["max_drawdown"] = max(acc["max_drawdown"], current_drawdown(acc, assets))
    save_account(acc)
    total_pnl = assets - acc["initial_capital"]
    print("【短线模拟账户】%s" % acc["account_id"])
    print("  总资产: %.2f | 现金: %.2f | 冻结: %.2f | 持仓市值: %.2f" % (
        assets, acc["cash"], acc["frozen"], mv))
    print("  总仓位: %.1f%% | 当日盈亏: %.2f | 累计盈亏: %.2f (%.2f%%)" % (
        position_pct(mv, assets) * 100,
        assets - (acc["prev_close_asset"] or acc["initial_capital"]),
        total_pnl,
        (total_pnl / acc["initial_capital"] * 100) if acc["initial_capital"] else 0))
    print("  最大资产: %.2f | 最大回撤: %.2f%% | 累计费用: %.2f" % (
        acc["max_asset"], acc["max_drawdown"] * 100, acc["total_fees"]))
    print("  已实现: gross %.2f / net %.2f | 状态: %s | 数据: %s | 风控: %s" % (
        acc["realized_pnl_gross"], acc["realized_pnl_net"],
        acc["status"], acc["data_status"], acc["risk_status"]))


def cmd_order(args):
    acc = get_account()
    pos = get_positions()
    mkt = get_market()
    orders = get_orders()

    direction = args.side.upper()
    if direction not in ("BUY", "SELL"):
        print("ERR direction 必须为 buy/sell")
        sys.exit(1)

    if args.client_order_id:
        for o in orders:
            if o.get("client_order_id") == args.client_order_id:
                print("IDEMPOTENT 幂等命中: 订单 %s 状态=%s（未重复下单）" % (o["order_id"], o["status"]))
                return o["order_id"]

    qty = args.qty
    # 交易数量硬校验（最终执行层，不信任上层 Agent 已检查）：
    #   BUY：qty 必须为正整数，且为 100 股（一人手）的整数倍。
    #   SELL：允许 100 股整数倍，或等于全部可卖持仓（整仓卖出含零股）。
    #   错误数量必须在创建订单/修改资金/持仓/冻结之前 REJECT，不产生任何状态变化。
    try:
        qty_str = str(qty).strip()
        if not qty_str.lstrip('-').isdigit() or '.' in qty_str:
            raise ValueError
        qty = int(qty)
    except (ValueError, TypeError):
        print("ERR REJECTED: 交易数量必须为正整数（手），收到非法值: %r" % (args.qty,))
        sys.exit(1)
    if qty <= 0:
        print("ERR REJECTED: 交易数量必须 > 0，收到: %d" % qty)
        sys.exit(1)
    _is_sell = direction == "SELL"
    # 统一数量约束（最终执行层，不信任上层 Agent 已检查）：
    #   BUY 与 SELL 都必须为 100 股（一手）的整数倍。
    #   不保留“SELL 整仓允许零股”之类的任何例外。
    if qty % 100 != 0:
        print("ERR REJECTED: %s 数量必须是 100 股（一手）的整数倍，收到: %d" % ("买入" if not _is_sell else "卖出", qty))
        sys.exit(1)

    is_market = args.type.upper() == "MARKET"

    q = mkt.get(args.code, {})
    grade = q.get("grade", "DATA_A")
    if grade in ("DATA_INVALID", "DATA_CONFLICT"):
        print("ERR REJECTED: 数据%s，禁止下单" % grade)
        sys.exit(1)
    if q.get("suspend"):
        print("ERR REJECTED: 停牌，禁止下单")
        sys.exit(1)

    # 市价单：成交价用最新行情价（无需盯盘/限价等待）；限价单：用传入价
    if is_market:
        mkt_price = q.get("price")
        if mkt_price is None:
            print("ERR REJECTED: 市价单需要最新行情价（先 tick 喂价）")
            sys.exit(1)
        price = float(mkt_price)
    else:
        if args.price is None:
            print("ERR REJECTED: 限价单必须指定价格")
            sys.exit(1)
        price = float(args.price)

    # 价格硬校验：必须 > 0，且不能是 NaN / Infinity / 非法数值。
    # 在创建订单/修改任何账户状态之前 REJECT。
    try:
        if not (price > 0):
            raise ValueError
        if price != price:  # NaN
            raise ValueError
        if price in (float('inf'), float('-inf')):
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        print("ERR REJECTED: 非法价格: %r（必须为 >0 的有限数值）" % (args.price,))
        sys.exit(1)

    if direction == "BUY":
        ok, reason = risk_check_new_buy(acc, pos, mkt, args.code, qty, price, args.topic)
        if not ok:
            print("ERR REJECTED: %s" % reason)
            sys.exit(1)
        need = _money(qty * price)
        if acc["cash"] < need:
            print("ERR REJECTED: 可用资金不足 (需 %.2f, 有 %.2f)" % (need, acc["cash"]))
            sys.exit(1)
        acc["cash"] = _money(acc["cash"] - need)
        acc["frozen"] = _money(acc["frozen"] + need)
        log("CASH", "freeze-buy", "", "%.2f" % need, "下单冻结", "order")
    else:
        p = pos.get(args.code)
        sellable = p.get("sellable", 0) if p else 0
        if sellable < qty:
            today_buy = p.get("today_buy_qty", 0) if p else 0
            print("ERR REJECTED: 可卖数量不足 (可卖%d, 当日买入%d 需次日可卖)" % (sellable, today_buy))
            sys.exit(1)
        if p:
            # 卖单冻结：从 sellable 扣减可卖数量，转入 frozen_qty。
            # 账务恒等式 total = sellable + today_buy_qty + frozen_qty 天然成立。
            p["sellable"] = p.get("sellable", 0) - qty
            p["frozen_qty"] = p.get("frozen_qty", 0) + qty
        log("POSITION", "freeze-sell", "", "%d" % qty, "下单冻结持仓", "order")

    oid = "O%06d" % (len(orders) + 1)
    order = {
        "order_id": oid, "account_id": acc["account_id"],
        "client_order_id": args.client_order_id,
        "code": args.code, "direction": direction,
        "qty": qty, "price": price,
        "order_type": "MARKET" if is_market else "LIMIT", "tif": args.tif.upper(),
        "submit_time": now(), "valid_seconds": args.ttl,
        "filled_qty": 0, "filled_amount": 0.0, "avg_price": 0.0, "fees": 0.0,
        "status": "PENDING", "reject_reason": "",
        "session": args.session.upper(), "model": args.model,
        "topic": args.topic, "reason": args.reason,
        "data_src": grade, "data_ts": q.get("ts", ""),
    }
    orders.append(order)
    save_orders(orders)
    save_account(acc)
    save_positions(pos)
    log("ORDER", oid, "", "%s %s %dx%.2f" % (direction, args.code, qty, price), "", "order")

    # 市价单：立即按最新可得价成交（无需等待后续 tick / 无需盯盘）。
    # 成交前仍必须通过统一的有效性检查，不能绕过涨跌停封单排队/停牌/数据等级等硬约束。
    # 这里显式用 CONTINUOUS 会话语义做检查，该分支已覆盖：
    #   涨停封单排队(seal_qty)、跌停封单排队(seal_qty)、停牌、数据无效/冲突、无最新价。
    # 市价单语义不变：只要最新价有效且非封死/不可成交，即按该最新价成交。
    # （price 已设为最新价，_order_can_fill 里 price<=order.price 恒成立，不会因限价条件误拒。）
    if is_market:
        fillable, fprice, reason = _order_can_fill(order, q, "CONTINUOUS")
        if not fillable:
            _cancel_order(oid, "市价单成交前检查未通过: %s" % reason, acc, pos, orders)
            save_positions(pos)
            save_orders(orders)
            save_account(acc)
            print("ERR 市价单 %s 被拒: %s（未成交，已撤销）" % (oid, reason))
            return oid
        apply_fill(acc, pos, order, qty, fprice, "MARKET_FILL", order.get("model", ""), "market")
        save_positions(pos)
        save_orders(orders)
        save_account(acc)
        print("OK 市价单 %s 立即成交 %s %s %d股 @%.2f" % (oid, direction, args.code, qty, fprice))
        return oid

    if order["tif"] in ("IOC", "FOK"):
        fills_ok, fprice, reason = _order_can_fill(order, q, order["session"])
        if fills_ok:
            apply_fill(acc, pos, order, qty, fprice, "IOC_FOK_FILL", order.get("model", ""), "ioc/fok")
            save_positions(pos)
            save_orders(orders)
            save_account(acc)
            print("OK 订单 %s 立即成交 %dx%.2f" % (oid, qty, fprice))
        else:
            _cancel_order(oid, "IOC/FOK 未成交自动撤销", acc, pos, orders)
            print("INFO 订单 %s 未立即成交，已撤销 (%s)" % (oid, reason))
        return oid

    print("OK 订单 %s 已提交: %s %s %d股 @%.2f (%s)" % (oid, direction, args.code, qty, price, order["status"]))
    return oid


def _cancel_order(oid, reason, acc=None, pos=None, orders=None):
    if acc is None:
        acc = get_account()
    if pos is None:
        pos = get_positions()
    if orders is None:
        orders = get_orders()
    for o in orders:
        if o["order_id"] == oid and o["status"] in ("PENDING", "PARTIAL_FILLED"):
            remaining = o["qty"] - o["filled_qty"]
            if o["direction"] == "BUY":
                refund = _money(remaining * o["price"])
                acc["frozen"] = max(0.0, _money(acc["frozen"] - refund))
                acc["cash"] = _money(acc["cash"] + refund)
                log("CASH", "unfreeze-buy", "", "%.2f" % refund, reason, "cancel")
            else:
                p = pos.get(o["code"])
                if p:
                    # 撤单/部分撤单：把剩余冻结数量从 frozen_qty 转回 sellable。
                    # 保持恒等式 total = sellable + today_buy_qty + frozen_qty 天然成立。
                    p["frozen_qty"] = max(0, p.get("frozen_qty", 0) - remaining)
                    p["sellable"] = p.get("sellable", 0) + remaining
                log("POSITION", "unfreeze-sell", "", "%d" % remaining, reason, "cancel")
            o["status"] = "CANCELLED"
            o["reject_reason"] = reason
            log("ORDER", oid, "", "CANCELLED", reason, "cancel")
    save_account(acc)
    save_positions(pos)
    save_orders(orders)


def cmd_cancel(args):
    _cancel_order(args.order_id, "用户撤单")
    print("OK 订单 %s 已撤销（未成交部分解冻）" % args.order_id)


def cmd_tick(args):
    acc = get_account()
    pos = get_positions()
    orders = get_orders()
    mkt = get_market()
    code = args.code
    q = mkt.get(code, {})
    q.update({
        "code": code,
        "price": args.price, "open": args.open, "high": args.high,
        "low": args.low, "close": args.close,
        "volume": args.volume, "amount": args.amount, "pct": args.pct,
        "limit_up": args.limit_up, "limit_down": args.limit_down,
        "seal_qty": args.seal_qty, "suspend": args.suspend,
        "grade": args.grade.upper(), "session": args.session.upper(),
        "ts": now(),
    })
    mkt[code] = q
    save_market(mkt)
    acc["data_status"] = q["grade"]
    save_account(acc)
    log("DATA", code, "", "price=%s grade=%s session=%s" % (args.price, q["grade"], q["session"]), "", "tick")

    matched = 0
    for o in orders:
        if o["status"] not in ("PENDING", "PARTIAL_FILLED"):
            continue
        if o["code"] != code:
            continue
        if o.get("valid_seconds") and o["status"] == "PENDING":
            try:
                sub = datetime.strptime(o["submit_time"], "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - sub).total_seconds() > o["valid_seconds"]:
                    _cancel_order(o["order_id"], "TTL超时自动撤单", acc, pos, orders)
                    continue
            except Exception:
                pass
        fills_ok, fprice, reason = _order_can_fill(o, q, q["session"])
        if fills_ok:
            remaining = o["qty"] - o["filled_qty"]
            apply_fill(acc, pos, o, remaining, fprice, reason, o.get("model", ""), "tick")
            matched += 1
    save_positions(pos)
    save_orders(orders)
    save_account(acc)
    print("OK tick %s: price=%.2f grade=%s session=%s，成交订单 %d 笔" % (
        code, args.price, q["grade"], q["session"], matched))


def cmd_expire(args):
    acc = get_account()
    pos = get_positions()
    orders = get_orders()
    n = 0
    for o in orders:
        if o["status"] not in ("PENDING", "PARTIAL_FILLED"):
            continue
        if not o.get("valid_seconds"):
            continue
        try:
            sub = datetime.strptime(o["submit_time"], "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - sub).total_seconds() > o["valid_seconds"]:
                _cancel_order(o["order_id"], "TTL超时自动撤单", acc, pos, orders)
                n += 1
        except Exception:
            pass
    save_account(acc)
    save_positions(pos)
    save_orders(orders)
    print("OK 过期订单清理 %d 笔" % n)


def cmd_settle(args):
    acc = get_account()
    pos = get_positions()
    mkt = get_market()
    closes = {}
    for pair in args.closes.split(","):
        if ":" in pair:
            c, p = pair.rsplit(":", 1)
            closes[c.strip()] = float(p)
    for code, p in pos.items():
        if code in closes:
            mkt.setdefault(code, {})["price"] = closes[code]
            mkt[code]["close"] = closes[code]
        last = mkt.get(code, {}).get("price")
        if last:
            p["last_price"] = last
    save_market(mkt)
    mark_to_market(pos, mkt)
    save_positions(pos)

    assets_before = acc["prev_close_asset"] or acc["initial_capital"]
    assets_now = total_assets(acc, pos, mkt)
    day_pnl = assets_now - assets_before
    total_pnl = assets_now - acc["initial_capital"]
    acc["prev_close_asset"] = assets_now
    acc["prev_close_date"] = today()
    acc["max_asset"] = max(acc["max_asset"], assets_now)
    acc["max_drawdown"] = max(acc["max_drawdown"], current_drawdown(acc, assets_now))
    acc["intraday_lock"] = False
    save_account(acc)

    for p in pos.values():
        p["sellable"] += p["today_buy_qty"]
        p["today_buy_qty"] = 0
    save_positions(pos)

    rate = CONFIG["interest"]["idle_annual_rate"]
    if rate and rate > 0:
        interest = _money(acc["cash"] * rate / 365.0)
        if interest > 0:
            acc["cash"] = _money(acc["cash"] + interest)
            add_cashflow(acc, "INTEREST", "", interest, "闲置资金计息")
            log("CASH", "interest", "", "%.4f" % interest, "日结计息", "settle")
            save_account(acc)

    _save_snapshot(acc, pos, mkt, assets_now, day_pnl)
    ok, errs = reconcile(acc, pos, mkt, verbose=False)
    print("【短线模拟账户｜收盘】%s" % today())
    print("  初始资金: %.2f | 期末资产: %.2f | 现金: %.2f | 持仓市值: %.2f" % (
        acc["initial_capital"], assets_now, acc["cash"], position_market_value(pos, mkt)))
    print("  今日盈亏: %.2f (%.2f%%) | 累计盈亏: %.2f (%.2f%%)" % (
        day_pnl, (day_pnl / assets_before * 100) if assets_before else 0,
        total_pnl,
        (total_pnl / acc["initial_capital"] * 100) if acc["initial_capital"] else 0))
    print("  最大回撤: %.2f%% | 对账: %s" % (acc["max_drawdown"] * 100, "PASS" if ok else "ERROR"))
    for e in errs:
        print("  -", e)


def _save_snapshot(acc, pos, mkt, assets, day_pnl):
    snapdir = os.path.join(DATA_DIR, "snapshots")
    os.makedirs(snapdir, exist_ok=True)
    snap = {
        "date": today(), "cash": acc["cash"], "frozen": acc["frozen"],
        "position_mv": position_market_value(pos, mkt), "total_assets": assets,
        "day_pnl": day_pnl,
        "total_pnl": assets - acc["initial_capital"],
        "total_return": (assets - acc["initial_capital"]) / acc["initial_capital"] if acc["initial_capital"] else 0,
        "max_drawdown": acc["max_drawdown"],
        "total_position_pct": position_pct(position_market_value(pos, mkt), assets),
        "positions": {k: {"qty": v["total"], "cost": v["cost_price"], "last": v["last_price"],
                          "mv": v["total"] * v["last_price"]} for k, v in pos.items()},
    }
    with open(os.path.join(snapdir, today() + ".json"), "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2, default=str)


def cmd_reconcile(args):
    acc = get_account()
    pos = get_positions()
    mkt = get_market()
    ok, errs = reconcile(acc, pos, mkt)
    sys.exit(0 if ok else 1)


def cmd_stats(args):
    fills = get_fills()
    acc = get_account()
    total = len(fills)
    buys = [f for f in fills if f["direction"] == "BUY"]
    sells = [f for f in fills if f["direction"] == "SELL"]
    gp = sum(f["amount"] for f in sells)
    gc = sum(f["amount"] for f in buys)
    print("【短线模拟账户｜统计】")
    print("  总成交: %d 笔 | 买入 %d | 卖出 %d" % (total, len(buys), len(sells)))
    print("  买入总额: %.2f | 卖出总额: %.2f | 利润因子: %.2f" % (gc, gp, (gp / gc) if gc else 0))
    print("  累计费用: %.2f | 已实现净盈亏: %.2f" % (acc["total_fees"], acc["realized_pnl_net"]))
    models = {}
    for f in fills:
        m = f.get("model") or f.get("strategy") or "未标注"
        models.setdefault(m, []).append(f)
    for m, fs in models.items():
        print("  [%s] 成交 %d 笔" % (m, len(fs)))


def cmd_cashflow(args):
    cf = get_cashflow()
    print("【资金流水】共 %d 条" % len(cf))
    for e in cf[-args.limit:]:
        print("  %s %-16s %-8s %10.2f 余额 %10.2f %s" % (
            e["ts"][:16], e["category"], e["code"], e["amount"], e["balance"], e.get("note", "")))


def cmd_corp_action(args):
    acc = get_account()
    pos = get_positions()
    code = args.code
    if code not in pos:
        print("ERR 无持仓 %s" % code)
        sys.exit(1)
    p = pos[code]
    if args.type == "DIVIDEND":
        cash = _money(args.cash_per_share * p["total"])
        acc["cash"] = _money(acc["cash"] + cash)
        add_cashflow(acc, "DIVIDEND", code, cash, "每股派息%.4f" % args.cash_per_share)
        p["cost_price"] = max(0.0, _money(p["cost_price"] - args.cash_per_share))
        p["cost_amount"] = _money(p["cost_price"] * p["total"])
        log("POSITION", code, "", "除息成本调整", "每股%.4f" % args.cash_per_share, "corp_action")
    elif args.type == "SPLIT":
        add = int(p["total"] * args.shares_per_10 / 10.0)
        new_total = p["total"] + add
        ratio = new_total / p["total"] if p["total"] else 1
        p["cost_price"] = _money(p["cost_price"] / ratio)
        p["total"] = new_total
        p["sellable"] = int(p.get("sellable", 0) + add)
        p["cost_amount"] = _money(p["cost_price"] * p["total"])
        add_cashflow(acc, "CORP_ACTION", code, 0, "每10股送转%d股" % args.shares_per_10)
        log("POSITION", code, "", "送转调整 %d股" % new_total, "", "corp_action")
    save_account(acc)
    save_positions(pos)
    print("OK 除权除息调整完成: %s %s，当前持仓 %d股 @%.2f" % (
        code, args.type, pos[code]["total"], pos[code]["cost_price"]))


def cmd_shadow(args):
    data = _load("shadow.json", [])
    data.append({
        "ts": now(), "date": today(),
        "code": args.code, "direction": args.direction.upper(),
        "qty": args.qty, "theoretical_price": args.price,
        "reason": args.reason, "model": args.model,
        "market_state": args.market, "unfilled_reason": args.unfilled,
        "later_high": args.later_high, "later_low": args.later_low,
        "result": args.result,
    })
    _save("shadow.json", data)
    print("OK 影子记录已保存（正式账户与影子账户严格分离）")


def cmd_snapshot(args):
    acc = get_account()
    pos = get_positions()
    mkt = get_market()
    assets = total_assets(acc, pos, mkt)
    _save_snapshot(acc, pos, mkt, assets, assets - (acc["prev_close_asset"] or acc["initial_capital"]))
    print("OK 快照已保存: %s" % today())


def cmd_positions(args):
    pos = get_positions()
    if not pos:
        print("（空仓）")
        return
    print("股票 | 数量 | 可卖 | 成本 | 最新价 | 市值 | 浮盈亏 | 收益率")
    for code, p in pos.items():
        last = p.get("last_price", 0.0)
        mv = p["total"] * last
        upnl = mv - p["cost_amount"]
        rate = (upnl / p["cost_amount"] * 100) if p["cost_amount"] else 0
        print("%s | %d | %d | %.2f | %.2f | %.2f | %.2f | %.2f%%" % (
            code, p["total"], p["sellable"], p["cost_price"], last, mv, upnl, rate))


def cmd_orders(args):
    orders = get_orders()
    if args.code:
        orders = [o for o in orders if o["code"] == args.code]
    if args.status:
        orders = [o for o in orders if o["status"] == args.status.upper()]
    if not orders:
        print("（无订单）")
        return
    for o in orders[-args.limit:]:
        print("%s | %s | %s | %d@%.2f | 状态=%s | 成交%d | 均价%.2f | %s" % (
            o["order_id"], o["code"], o["direction"], o["qty"], o["price"],
            o["status"], o["filled_qty"], o.get("avg_price", 0), o.get("reject_reason", "")))


def cmd_fills(args):
    fills = get_fills()
    if not fills:
        print("（无成交）")
        return
    for f in fills[-args.limit:]:
        print("%s | %s | %s | %d@%.2f | 金额%.2f | 费%.2f | %s" % (
            f["fill_id"], f["code"], f["direction"], f["qty"], f["price"],
            f["amount"], f["fees"], f["fill_type"]))


def cmd_reset(args):
    if not args.yes:
        print("ERR 危险操作需 --yes 确认")
        sys.exit(1)
    for f in ("account.json", "positions.json", "orders.json", "fills.json",
              "cashflow.json", "market.json", "shadow.json"):
        p = _path(f)
        if os.path.exists(p):
            os.remove(p)
    print("OK 账户数据已重置")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="A股短线模拟账户引擎 V1.1")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("init", help="初始化账户")
    p.add_argument("--initial", type=float, default=10000.0)

    p = sub.add_parser("status", help="账户实时状态")
    p = sub.add_parser("positions", help="持仓")
    p = sub.add_parser("orders", help="订单列表")
    p.add_argument("--code")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=50)
    p = sub.add_parser("fills", help="成交记录")
    p.add_argument("--limit", type=int, default=50)
    p = sub.add_parser("cashflow", help="资金流水")
    p.add_argument("--limit", type=int, default=50)
    p = sub.add_parser("reconcile", help="对账")
    p = sub.add_parser("stats", help="统计")
    p = sub.add_parser("snapshot", help="保存快照")
    p = sub.add_parser("expire", help="TTL过期订单清理")
    p = sub.add_parser("reset", help="重置账户数据")
    p.add_argument("--yes", action="store_true")

    p = sub.add_parser("order", help="下单")
    p.add_argument("side")
    p.add_argument("code")
    p.add_argument("qty", type=int)
    p.add_argument("price", type=float, nargs="?", default=None, help="市价单可省略（用最新价）；限价单必填")
    p.add_argument("--type", default="MARKET", choices=["MARKET", "LIMIT"], help="订单类型，默认市价")
    p.add_argument("--client_order_id", help="客户端唯一流水号（幂等）")
    p.add_argument("--ttl", type=int, help="有效期秒数，超时自动撤单")
    p.add_argument("--tif", default="GTC", choices=["GTC", "IOC", "FOK"])
    p.add_argument("--session", default="CONTINUOUS", choices=SESSIONS)
    p.add_argument("--model", help="交易模型（突破/强势回踩/龙头分歧/弱转强/情绪修复/消息驱动）")
    p.add_argument("--topic", help="题材")
    p.add_argument("--reason", default="")

    p = sub.add_parser("cancel", help="撤单")
    p.add_argument("order_id")

    p = sub.add_parser("tick", help="喂行情并撮合")
    p.add_argument("code")
    p.add_argument("--price", type=float, required=True)
    p.add_argument("--open", type=float)
    p.add_argument("--high", type=float)
    p.add_argument("--low", type=float)
    p.add_argument("--close", type=float)
    p.add_argument("--volume", type=float)
    p.add_argument("--amount", type=float)
    p.add_argument("--pct", type=float)
    p.add_argument("--limit_up", type=float)
    p.add_argument("--limit_down", type=float)
    p.add_argument("--seal_qty", type=float, default=0.0, help="封单量")
    p.add_argument("--suspend", action="store_true")
    p.add_argument("--grade", default="DATA_A", choices=DATA_GRADES)
    p.add_argument("--session", default="CONTINUOUS", choices=SESSIONS)

    p = sub.add_parser("settle", help="每日结算")
    p.add_argument("--closes", required=True, help="code:price,code:price")

    p = sub.add_parser("corp_action", help="除权除息调整")
    p.add_argument("code")
    p.add_argument("--type", required=True, choices=["DIVIDEND", "SPLIT"])
    p.add_argument("--cash_per_share", type=float, default=0.0)
    p.add_argument("--shares_per_10", type=float, default=0.0)

    p = sub.add_parser("shadow", help="影子账户记录")
    p.add_argument("code")
    p.add_argument("direction")
    p.add_argument("qty", type=int)
    p.add_argument("price", type=float)
    p.add_argument("--reason", required=True)
    p.add_argument("--model", default="")
    p.add_argument("--market", default="")
    p.add_argument("--unfilled", default="")
    p.add_argument("--later_high", type=float)
    p.add_argument("--later_low", type=float)
    p.add_argument("--result", default="")

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        sys.exit(0)

    os.makedirs(DATA_DIR, exist_ok=True)

    handlers = {
        "init": cmd_init, "status": cmd_status, "positions": cmd_positions,
        "orders": cmd_orders, "fills": cmd_fills, "cashflow": cmd_cashflow,
        "reconcile": cmd_reconcile, "stats": cmd_stats, "snapshot": cmd_snapshot,
        "expire": cmd_expire, "reset": cmd_reset,
        "order": cmd_order, "cancel": cmd_cancel, "tick": cmd_tick,
        "settle": cmd_settle, "corp_action": cmd_corp_action,
        "shadow": cmd_shadow,
    }
    handlers[args.cmd](args)


if __name__ == "__main__":
    main()
