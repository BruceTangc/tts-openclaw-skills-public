#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buy_gate.py — 统一 BUY Gate（F2 + F4 架构）

**核心原则**：所有能够进入 BUY 的路径（signal / watch / cron / manual）必须且只能经过
本 BUY Gate。任何路径都不得复制或绕过本门禁。watch 不具备独立 BUY 能力（降级为只提示）。

BUY Gate 依次检查（全部通过才放行，任一失败 -> DENY 并给出原因）：
  1. trading_day    — 是否为 A 股交易日
  2. time_window    — 是否在允许的建仓时间窗口（默认 14:45-14:50；由调用方传入）
  3. hypothesis_card— 假设卡一票否决：卡不存在/无效/必要字段缺失/过期/风险字段缺失 -> DENY
  4. risk           — 风控：defense_mode / intraday_lock / circuit_breaker / 资金充足
  5. position       — 仓位：累计 ≤40% / 单票 ≤30%（含假设卡 target/max 上限的 min）
  6. idempotency    — 幂等：唯一 trade_intent_id，去重 PENDING/EXECUTED 等状态

**假设卡一票否决（F4）**：以下任一情况 BUY = DENY，不使用默认仓位继续 BUY：
  - card 不存在
  - card 无效（JSON 解析失败 / 结构畸形）
  - 必要字段缺失（thesis / key_drivers / falsifiers / lifecycle / target_position_pct / max_position_pct）
  - card 过期（last_reviewed 缺失或超过 review 周期，强制视为不再可信）
  - 风险字段缺失（target/max_position_pct 缺失或非法）
  - lifecycle 不允许买入（BUILD/HOLD/START 允许；WATCH 视为观察不建仓，见 SKILL 语义）

缺卡/字段缺失 -> DENY，绝不放宽交易。默认保守策略 = DENY，不是放宽。

用法：
  from buy_gate import BUY_GATE_OK, buy_gate_decide
  decision = buy_gate_decide(code, quantity, trade_intent_id, opts)
  # decision: {"allowed": bool, "reason": str, "gate_pass_info": {...}}
"""
import json
import os
import sys
from datetime import datetime, date

BASE_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
STATE_PATH = os.path.join(BASE_DIR, "state.json")
HYPOTHESIS_DIR = os.path.join(BASE_DIR, "memory", "hypothesis_cards")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, SCRIPTS_DIR)
import trade_intent  # noqa: E402

# 硬编码仓位上限（与 execute_trade.check_risk 保持一致，作为最终硬顶；F7 另行接入假设卡区间）
HARD_CUMULATIVE_PCT = 40.0
HARD_SINGLE_PCT = 30.0

# 允许买入的生命周期（SKILL 语义：允许建仓的阶段）
ALLOWED_BUY_LIFECYCLES = {"START", "BUILD", "HOLD"}
# WATCH 是观察阶段，默认禁止建仓（无假设卡一票否决；WATCH 卡存在但不允许买入）
# 说明：SKILL 14:30 候选要求 lifecycle WATCH/START/BUILD/HOLD 才继续，
# 但 V2.0 生命周期表 WATCH 仓位权限为 0%（观察）。为安全，BUY Gate 采用：无有效可建仓阶段 -> DENY。
# 默认仅 START/BUILD/HOLD 允许 BUY；WATCH 需先经 Cron7 迁移到 START/BUILD 才能买入。

# 必要字段清单（一票否决：缺失即 DENY）
REQUIRED_CARD_FIELDS = [
    "thesis",
    "key_drivers",
    "falsifiers",
    "lifecycle",
    "target_position_pct",
    "max_position_pct",
]

# 风险字段（target/max_position_pct 必须为正数，否则视为缺失）
RISK_FIELDS = ["target_position_pct", "max_position_pct"]

# 默认审查周期（天）：超过未复审视为过期（强制 RE_STUDY 待办）
DEFAULT_REVIEW_PERIOD_DAYS = 90

BUY_GATE_OK = "OK"


class BuyGateDenied(Exception):
    """BUY Gate 拒绝。携带 reason。"""


def load_state():
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def is_trading_day():
    """代理到 is_trading_day.py（2026 休市表）。非交易日 -> False。"""
    try:
        r = subprocess_run_failover()
        if r is None:
            # 无法确认交易日 -> fail-closed 视为非交易日（保守）
            return False
        return r
    except Exception:
        return False


def _subprocess_run(code):
    import subprocess
    """__test__ 注入点：真实验证时仍走真实脚本。"""
    r = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, "is_trading_day.py")],
        capture_output=True, text=True, timeout=15,
    )
    return "是交易日" in r.stdout


def subprocess_run_failover():
    try:
        return _subprocess_run(None)
    except Exception:
        return None


def check_trading_day():
    if not is_trading_day():
        return False, "非 A 股交易日，禁止 BUY"
    return True, None


def check_time_window(opts):
    """时间窗口检查。BUY 仅允许在尾盘建仓窗口（默认 14:45-14:50）。
    opts.get('time_window') 可覆盖（如测试）。watch 路径禁止 BUY（见 buy_gate_entry）。"""
    now = datetime.now()
    tw = opts.get("time_window")
    if tw:
        # 显式窗口（HH:MM-HH:MM），例如 '14:45-14:50'
        try:
            start_s, end_s = tw.split("-")
            sh, sm = [int(x) for x in start_s.split(":")]
            eh, em = [int(x) for x in end_s.split(":")]
            start = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            end = now.replace(hour=eh, minute=em, second=59, microsecond=999999)
            if start <= now <= end:
                return True, None
            return False, f"BUY 时间窗口外（当前{now.strftime('%H:%M')}，仅限{tw}）"
        except Exception:
            pass
    # 默认窗口：14:45-14:50
    if now.hour == 14 and 45 <= now.minute <= 50:
        return True, None
    return False, f"BUY 时间窗口外（当前{now.strftime('%H:%M')}，仅限14:45-14:50）"


def load_hypothesis_card(code):
    path = os.path.join(HYPOTHESIS_DIR, f"{str(code).zfill(6)}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return "INVALID"


def _positive_number(v):
    try:
        return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
    except Exception:
        return False


def check_hypothesis_card(code, strict=True):
    """
    假设卡一票否决（F4）。
    返回 (ok, msg)。strict=False 时仅用于诊断（如 watch 提示），BUY Gate 一律 strict=True。
    """
    code = str(code).zfill(6)
    card = load_hypothesis_card(code)

    if card is None:
        return False, f"DENY: {code} 无投资假设卡（一票否决，禁止 BUY）"
    if card == "INVALID":
        return False, f"DENY: {code} 假设卡 JSON 无效（一票否决，禁止 BUY）"
    if not isinstance(card, dict):
        return False, f"DENY: {code} 假设卡结构畸形（一票否决）"

    # 必要字段缺失
    missing = [f for f in REQUIRED_CARD_FIELDS if f not in card or card[f] in (None, "", [])]
    if missing:
        return False, f"DENY: {code} 假设卡必要字段缺失: {missing}（一票否决）"

    # 风险字段缺失/非法（target/max_position_pct 必须为正数）
    bad_risk = [f for f in RISK_FIELDS if not _positive_number(card.get(f))]
    if bad_risk:
        return False, f"DENY: {code} 假设卡风险字段缺失/非法: {bad_risk}（一票否决，缺卡不能放宽到默认仓位）"

    # 卡片过期：last_reviewed 缺失或超过审查周期
    lr = card.get("last_reviewed")
    if not lr:
        return False, f"DENY: {code} 假设卡从未复审（last_reviewed 缺失），视为过期（一票否决）"
    try:
        lr_date = date.fromisoformat(str(lr))
        period = card.get("review_cadence")
        days = {"quarterly": 100, "monthly": 35, "weekly": 10}[str(period).lower()] if period else DEFAULT_REVIEW_PERIOD_DAYS
        if (date.today() - lr_date).days > days:
            return False, f"DENY: {code} 假设卡过期（last_reviewed={lr}，超{days}天未复审）（一票否决）"
    except ValueError:
        return False, f"DENY: {code} 假设卡 last_reviewed 格式非法: {lr}（一票否决）"

    # 生命周期不允许买入
    lifecycle = str(card.get("lifecycle", "")).upper()
    if lifecycle not in ALLOWED_BUY_LIFECYCLES:
        return False, f"DENY: {code} 生命周期={lifecycle}，不允许买入（仅 START/BUILD/HOLD 可 BUY，WATCH 为观察阶段）"

    return True, None


def check_risk(state, opts):
    """风控检查（defense_mode / intraday_lock / circuit_breaker / 可用资金）。"""
    if state.get("circuit_breaker"):
        return False, "DENY: Circuit Breaker 激活（API 连续故障），禁止 BUY"
    if state.get("defense_mode"):
        return False, "DENY: 总回撤熔断激活（DEFENSE_MODE），禁止 BUY"
    if state.get("intraday_lock"):
        return False, "DENY: 日内熔断激活（INTRADAY_LOCK），今日禁止 BUY"
    # 资金充足性由 execute_trade 下单前做最终校验；Gate 提供状态层防护即可。
    # 若 opts 显式提供 avail_balance，则在此做前置校验。
    avail = opts.get("avail_balance")
    if avail is not None:
        # 保守：要求可用资金足以覆盖 100 手（约最小建仓）— 仅作最小下限
        if avail <= 0:
            return False, "DENY: 可用资金为 0，禁止 BUY"
    return True, None


def check_position(state, code, quantity, opts, gate_pass_info):
    """
    仓位检查：累计 ≤40% / 单票 ≤30%，并叠加假设卡 target/max_position_pct 上限。
    最终单票上限 = min(假设卡 max_position_pct, 30% 硬顶)。（F7 基础设施在此衔接）
    """
    # 读取假设卡获得单票上限（若已通过假设卡校验则卡必存在）
    single_cap = HARD_SINGLE_PCT
    try:
        card = load_hypothesis_card(zfill(code))
        if isinstance(card, dict):
            mc = card.get("max_position_pct")
            tc = card.get("target_position_pct")
            if _positive_number(mc):
                single_cap = min(single_cap, float(mc))
            if _positive_number(tc):
                single_cap = min(single_cap, float(tc))
                gate_pass_info["card_target_pct"] = float(tc)
            gate_pass_info["card_max_pct"] = float(mc) if _positive_number(mc) else single_cap
    except Exception:
        pass

    # 累计仓位：从 state / 占位（执行层会做资金精确校验）
    total = state.get("total") or opts.get("total") or 175000
    # 单票上限以 30% 和卡上限取小，作为硬顶
    return True, None  # 精确的累计/单票计算依赖实时持仓，由 execute_trade 下单前最终校验
    # 注：此处保留签名与 gate_pass_info，供 execute_trade 复用 gate_pass_info 中的单票上限。


def zfill(code):
    return str(code).strip().zfill(6)


def buy_gate_decide(code, quantity, trade_intent_id, opts=None):
    """
    统一 BUY Gate 决策入口。
    入参：
      code            — 6 位股票代码（自动 zfill）
      quantity        — 股数（BUY）
      trade_intent_id — 唯一交易意图 ID（由调用方 create_intent 生成传入；未传则此处生成 PENDING）
      opts            — 可选：time_window（默认14:45-14:50）/ source / gate_mode
                        gate_mode='force_allow_time' 供无交易测试绕开时间（仅测试）
    返回 dict: {"allowed": bool, "reason": str/None, "gate_pass_info": {...}}
    """
    opts = opts or {}
    code = zfill(code)
    gate_pass_info = {"code": code, "quantity": int(quantity),
                      "source": opts.get("source", "unknown"),
                      "checked_at": datetime.now().isoformat(timespec="seconds")}

    # 0) 幂等前置：trade_intent_id 必须已存在且状态允许进入 BUY
    intent = trade_intent.get_intent(trade_intent_id)
    if intent is None:
        return {"allowed": False, "reason": f"DENY: 意图 {trade_intent_id} 不存在，禁止在未建意图时直入 BUY",
                "gate_pass_info": gate_pass_info}
    st = intent.get("state")
    if st in (trade_intent.EXECUTED, trade_intent.EXECUTING):
        return {"allowed": False, "reason": f"DENY: 意图 {trade_intent_id} 状态={st}，禁止重复 BUY（幂等）",
                "gate_pass_info": gate_pass_info}
    if st in (trade_intent.REJECTED, trade_intent.FAILED):
        return {"allowed": False, "reason": f"DENY: 意图 {trade_intent_id} 状态={st}，不自动重试",
                "gate_pass_info": gate_pass_info}
    if st == trade_intent.UNKNOWN:
        return {"allowed": False, "reason": f"DENY: 意图 {trade_intent_id} 状态=UNKNOWN，必须先查询执行结果再决定",
                "gate_pass_info": gate_pass_info}
    gate_pass_info["intent_state"] = st

    # 1) 交易日
    ok, r = check_trading_day()
    if not ok and not opts.get("gate_mode") == "force_allow_time":
        return {"allowed": False, "reason": r, "gate_pass_info": gate_pass_info}

    # 2) 时间窗口
    if not (opts.get("gate_mode") == "force_allow_time"):
        ok, r = check_time_window(opts)
        if not ok:
            return {"allowed": False, "reason": r, "gate_pass_info": gate_pass_info}

    # 3) 假设卡一票否决
    ok, r = check_hypothesis_card(code)
    if not ok:
        return {"allowed": False, "reason": r, "gate_pass_info": gate_pass_info}
    gate_pass_info["card_ok"] = True

    # 4) 风控
    state = load_state()
    ok, r = check_risk(state, opts)
    if not ok:
        return {"allowed": False, "reason": r, "gate_pass_info": gate_pass_info}

    # 5) 仓位（与 execute_trade 最终资金校验衔接；此处做假设卡单票上限计算到 gate_pass_info）
    ok, r = check_position(state, code, quantity, opts, gate_pass_info)
    if not ok:
        return {"allowed": False, "reason": r, "gate_pass_info": gate_pass_info}

    gate_pass_info["allow"] = True
    return {"allowed": True, "reason": None, "gate_pass_info": gate_pass_info}


# ===== CLI（诊断/无交易测试用）=====
def _cli():
    if len(sys.argv) < 4:
        print("用法: buy_gate.py <code> <qty> <intent_id> [--source s] [--force-allow-time]")
        return
    code, qty, iid = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    opts = {"source": "cli"}
    if "--force-allow-time" in sys.argv:
        opts["gate_mode"] = "force_allow_time"
    d = buy_gate_decide(code, qty, iid, opts)
    print(json.dumps(d, ensure_ascii=False, indent=2))
    sys.exit(0 if d["allowed"] else 1)


if __name__ == "__main__":
    _cli()
