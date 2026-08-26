#!/usr/bin/env python3
"""position_check.py - 仓位决策脚本 (V2.0)

V2.0 变更：
- SELL_WEAK 降级为 WEAK_ALERT，不再生成直接卖出指令。
- 主力资金流入不再自动生成 BUY 目标，改为 FUND_FLOW_REF 参考提示。
- 主力资金流出不再自动生成 SELL 指令，改为 FUND_FLOW_ALERT 警报。
- calc_price_alert() 替代原 calc_price_target()，不再输出短线回调/反弹目标价。
- 所有价格信号仅触发 Cron 7 审查投资假设，不直接生成交易。

用法:
  python3 position_check.py 000426,600711,601168,000807,000933  --text
  python3 position_check.py 000426  --text
"""
import json, os, re, subprocess, sys, argparse

WORKSPACE = "{{OPENCLAW_WORKSPACE}}"
MX_DIR = WORKSPACE + "/skills/mx-data"
MX_SCRIPT = MX_DIR + "/mx_data.py"
TMP = WORKSPACE + "/tmp/mx_data_output"
STATE_FILE = WORKSPACE + "/state.json"

def query(q):
    os.makedirs(TMP, exist_ok=True)
    r = subprocess.run(["python3", MX_SCRIPT, q, TMP], capture_output=True, text=True, timeout=60, cwd=MX_DIR)
    if r.returncode != 0:
        return None
    files = [f for f in os.listdir(TMP) if f.endswith("_raw.json")]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(TMP, f)), reverse=True)
    if not files:
        return None
    try:
        with open(os.path.join(TMP, files[0])) as fh:
            return json.load(fh)
    except:
        return None

def ev(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip().replace(",", "").replace(" ", "")
    if "亿元" in s:
        try: return float(s.replace("亿元", "")) * 100000000
        except: return None
    if "万元" in s:
        try: return float(s.replace("万元", "")) * 10000
        except: return None
    if "万股" in s:
        try: return float(s.replace("万股", "")) * 10000
        except: return None
    if "股" in s:
        try: return float(s.replace("股", ""))
        except: return None
    if "%" in s:
        try: return float(s.replace("%", ""))
        except: return None
    try: return float(s)
    except: return None

def parse_hist(raw):
    """从 mx_data 历史查询结果中提取价格序列（从旧到新排序）"""
    try:
        tables = raw["data"]["data"]["searchDataResultDTO"]["dataTableDTOList"]
    except (KeyError, TypeError):
        return []
    for t in tables:
        tbl = t.get("table", {})
        head = tbl.get("headName", [])
        if not isinstance(head, list) or len(head) < 2:
            continue
        for fid, vals in tbl.items():
            if fid == "headName" or not isinstance(vals, list) or len(vals) != len(head):
                continue
            prices = []
            for v in vals:
                sv = str(v).replace("元", "").strip()
                try:
                    prices.append(float(sv))
                except ValueError:
                    pass
            if len(prices) == len(head):
                prices.reverse()
                return prices
    return []


def query_hist(code):
    """查询近3日收盘价，返回从旧到新的价格列表"""
    q = "%s 近3日收盘价" % code
    return parse_hist(query(q))


def check_weak_relative(codes):
    """检查持仓股是否连续3日弱于沪深300，返回 {code: {diff, reason}}"""
    idx_prices = query_hist("000300")
    if not idx_prices or len(idx_prices) < 3:
        return {}
    idx_ret = (idx_prices[-1] - idx_prices[0]) / idx_prices[0]
    weak = {}
    for c in codes:
        prices = query_hist(c)
        if not prices or len(prices) < 3:
            continue
        stk_ret = (prices[-1] - prices[0]) / prices[0]
        diff = stk_ret - idx_ret
        if diff <= -0.015:
            weak[c] = {
                "diff": round(diff * 100, 2),
                "stock_ret": round(stk_ret * 100, 2),
                "index_ret": round(idx_ret * 100, 2),
                "reason": "连续3日相对沪深300弱 %.1f%%（个股%.1f%% vs 指数%.1f%%）" % (diff*100, stk_ret*100, idx_ret*100)
            }
    return weak


def get_total_asset():
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        return state.get("total", 175000)
    except:
        return 175000

def calc(codes, raw):
    res = {}
    try:
        tables = raw["data"]["data"]["searchDataResultDTO"]["dataTableDTOList"]
    except:
        return None
    if not tables:
        return None
    used_tables = [t for t in tables if t.get("table", {}).get("headName") is not None]
    if not used_tables:
        used_tables = tables
    for t in used_tables:
        rows = t.get("table", {})
        names = rows.get("headName", [])
        if not isinstance(names, list):
            continue
        code_positions = {}
        for i, n in enumerate(names):
            m = re.search(r'(\d{6})', str(n))
            if m:
                code_positions[i] = m.group(1)
        if not code_positions:
            continue
        for fid, vals in rows.items():
            if fid == "headName" or not isinstance(vals, list):
                continue
            for i, v in enumerate(vals):
                if i not in code_positions:
                    continue
                c = code_positions[i]
                if c not in codes:
                    continue
                if c not in res:
                    res[c] = {"name": c, "signals": {}, "detail": {}}
                sv = str(v)
                if "ZXJ_f2" in str(fid) or "f2" in str(fid):
                    pr = ev(sv)
                    if pr is not None and pr > 0:
                        res[c]["detail"]["price"] = pr
                if "ZDF_f3" in str(fid) or "f3" in str(fid):
                    pct = ev(sv)
                    if pct is not None:
                        res[c]["detail"]["change_pct"] = pct
                if "ZLJE" in str(fid) or "主力" in str(fid) or "net" in str(fid).lower():
                    inflow = ev(sv)
                    if inflow is not None:
                        res[c]["detail"]["main_force_inflow"] = inflow
    return res

def calc_price_alert(code, det, total_asset):
    """V2.0: 生成价格参考提示，不再输出短线买卖目标价。
    仅提供当前价格、涨跌幅、主力资金流向作为参考数据，
    所有买卖决策由 Cron 7 审查投资假设后做出。"""
    price = det.get("price")
    if price is None or price <= 0:
        return None
    change_pct = det.get("change_pct", 0) or 0
    inflow = det.get("main_force_inflow")
    note = "现价 %.2f | 涨跌 %.1f%%" % (price, change_pct)
    if inflow is not None:
        note += " | 主力资金 %+.0f 万元" % (inflow / 10000)
    return {"type": "reference", "code": code, "current_price": price,
            "change_pct": round(change_pct, 2),
            "main_force_inflow": inflow,
            "note": note,
            "recommendation": "V2.0: 价格信号仅作参考，不自动生成买卖指令；Cron 7 审查投资假设后决定"}

def decide(codes, sigs, total_asset, weak_map=None):
    if weak_map is None:
        weak_map = {}
    actions = []
    hold = []
    for c in codes:
        # WEAK_ALERT 优先级最高，标记警报（V2.0: 不直接生成卖出）
        if c in weak_map:
            w = weak_map[c]
            actions.append({"type": "alert", "code": c, "signal": "WEAK_ALERT",
                           "reason": w["reason"],
                           "recommendation": "Cron 7 审查投资假设后决定是否减仓"})
            continue
        if c not in sigs:
            hold.append(c)
            continue
        s = sigs[c]
        det = s.get("detail", {})
        change_pct = det.get("change_pct")
        inflow = det.get("main_force_inflow")

        # V2.0: 涨幅过高 -> 告警，不自动生成买入
        if change_pct is not None and change_pct >= 3:
            actions.append({"type": "alert", "code": c, "signal": "HIGH_CHANGE_ALERT",
                           "reason": "涨幅 %.1f%% >= 3%%（原则上禁止追高买入）" % change_pct,
                           "recommendation": "V2.0: 等待估值回落或基本面逻辑强化后再评估"})
            continue

        # V2.0: 主力资金流入 -> 仅生成参考提示，不自动生成买入
        if inflow is not None and inflow > 0:
            ref = calc_price_alert(c, det, total_asset)
            if ref:
                ref["signal"] = "FUND_FLOW_REF"
                actions.append(ref)
            else:
                hold.append(c)
            continue

        # V2.0: 主力资金大幅流出 -> 警报，不自动生成卖出
        if inflow is not None and inflow < -100000000:
            actions.append({"type": "alert", "code": c, "signal": "FUND_FLOW_ALERT",
                           "reason": "主力净流出 %.0f 万元 (%.0f 元)" % (inflow / 10000, inflow),
                           "recommendation": "V2.0: 不自动卖出；Cron 7 审查投资假设后决定"})
            continue

        hold.append(c)
    return {"actions": actions, "hold": hold}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("codes", nargs="?", help="股票代码逗号分隔")
    p.add_argument("--text", action="store_true")
    p.add_argument("--total-asset", type=float, help="总资产，默认从 state.json 读取")
    args = p.parse_args()
    if not args.codes:
        print(json.dumps({"error": "need codes"}))
        sys.exit(1)
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    total_asset = args.total_asset if args.total_asset else get_total_asset()
    q = ",".join(codes) + " 今日涨跌幅 最新价 成交量 换手率 主力资金净流入"
    raw = query(q)
    if not raw:
        raw = query(",".join(codes) + " 今日涨跌幅 最新价 成交量 主力资金净流入")
    if not raw:
        print(json.dumps({"error": "query failed", "codes": codes}))
        sys.exit(1)
    sigs = calc(codes, raw)
    if not sigs:
        print(json.dumps({"error": "calc failed"}))
        sys.exit(1)
    # 检查连续3日弱于大盘
    weak_map = check_weak_relative(codes)
    decision = decide(codes, sigs, total_asset, weak_map)
    if args.text:
        print("总资产: %.0f" % total_asset)
        print("操作: %d 条" % len(decision["actions"]))
        print("--- V2.0 信号（全部为警报/参考，不自动生成买卖指令）---")
        for a in decision["actions"]:
            signal_tag = ""
            if a.get("signal") == "WEAK_ALERT":
                signal_tag = " [WEAK_ALERT]"
            elif a.get("signal") == "FUND_FLOW_ALERT":
                signal_tag = " [FUND_FLOW_ALERT]"
            elif a.get("signal") == "FUND_FLOW_REF":
                signal_tag = " [FUND_FLOW_REF]"
            elif a.get("signal") == "HIGH_CHANGE_ALERT":
                signal_tag = " [HIGH_CHANGE_ALERT]"

            if a.get("type") == "alert":
                print("  ALERT %s: %s%s" % (a["code"], a["reason"], signal_tag))
                if a.get("recommendation"):
                    print("    -> %s" % a["recommendation"])
            elif a.get("type") == "reference":
                print("  REF   %s: %s%s" % (a["code"], a.get("note", ""), signal_tag))
                if a.get("recommendation"):
                    print("    -> %s" % a["recommendation"])
            else:
                print("  %s %s: %s%s" % (a["type"].upper(), a["code"], a["reason"], signal_tag))
        if decision["hold"]:
            print("持有: %s" % ", ".join(decision["hold"]))
    print("---")
    print(json.dumps(decision, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
