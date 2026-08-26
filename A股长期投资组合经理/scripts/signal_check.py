#!/usr/bin/env python3
import json, os, re, subprocess, sys, argparse

WORKSPACE = "{{OPENCLAW_WORKSPACE}}"
MX_DIR = WORKSPACE + "/skills/mx-data"
MX_SCRIPT = MX_DIR + "/mx_data.py"
TMP = WORKSPACE + "/tmp/mx_data_output"

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
        with open(os.path.join(TMP, files[0])) as f:
            return json.load(f)
    except:
        return None

def ev(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip().replace(",", "").replace(" ", "")
    if "亿元" in s:
        try:
            return float(s.replace("亿元", "")) * 100000000
        except:
            return None
    if "万元" in s:
        try:
            return float(s.replace("万元", "")) * 10000
        except:
            return None
    if "元" in s:
        try:
            return float(s.replace("元", ""))
        except:
            return None
    if "%" in s:
        try:
            return float(s.replace("%", ""))
        except:
            return None
    try:
        return float(s)
    except:
        return None

def calc(codes, raw):
    res = {}
    try:
        tables = raw["data"]["data"]["searchDataResultDTO"]["dataTableDTOList"]
    except:
        return None
    if not tables:
        return None
    # Use the first table that has data arrays
    used_tables = []
    for t in tables:
        rows = t.get("table", {})
        has_data = False
        for v in rows.values():
            if isinstance(v, list) and len(v) > 0:
                has_data = True
                break
        if has_data:
            used_tables.append(t)
    if not used_tables:
        return None
    # Try to parse each stock
    for t in used_tables:
        en = t.get("entityName", "")
        rows = t.get("table", {})
        # Check if this is multi-stock (array length > 1) or single-stock
        max_len = 1
        for v in rows.values():
            if isinstance(v, list) and len(v) > max_len:
                max_len = len(v)
        if max_len > 1:
            # Multi-stock: use position mapping
            # Check if entity name has a stock code
            m = re.search(r'(\d{6})', en)
            if m:
                # Single stock with code in entity name
                c = m.group(1)
                if c in codes:
                    if c not in res:
                        res[c] = {"name": en.split("(")[0] if "(" in en else en, "signals": {}, "detail": {}}
                    for fid, vals in rows.items():
                        if not isinstance(vals, list) or not vals:
                            continue
                        v = str(vals[0])
                        if "%" in v:
                            pct = ev(v)
                            if pct is not None:
                                res[c]["detail"]["change_pct"] = pct
                                if pct > 5: res[c]["signals"]["涨幅过大"] = True
                                elif pct >= 3: res[c]["signals"]["涨幅偏大"] = True
                                elif pct < -3: res[c]["signals"]["低开走弱"] = True
                                elif -1 < pct < 2: res[c]["signals"]["缩量企稳"] = True
                                else: res[c]["signals"]["涨幅温和"] = True
                        if "ZLJE" in str(fid):
                            inflow = ev(v)
                            if inflow is not None:
                                res[c]["detail"]["main_force_inflow"] = inflow
                                if inflow > 0: res[c]["signals"]["主力净流入"] = True
            else:
                # Multi-stock: use position indexing
                for i in range(min(max_len, len(codes))):
                    c = codes[i]
                    if c not in res:
                        res[c] = {"name": c, "signals": {}, "detail": {}}
                for fid, vals in rows.items():
                    if not isinstance(vals, list):
                        continue
                    for i, v in enumerate(vals):
                        if i >= len(codes):
                            break
                        c = codes[i]
                        sv = str(v)
                        if "%" in sv:
                            pct = ev(sv)
                            if pct is not None:
                                res[c]["detail"]["change_pct"] = pct
                                if pct > 5: res[c]["signals"]["涨幅过大"] = True
                                elif pct >= 3: res[c]["signals"]["涨幅偏大"] = True
                                elif pct < -3: res[c]["signals"]["低开走弱"] = True
                                elif -1 < pct < 2: res[c]["signals"]["缩量企稳"] = True
                                else: res[c]["signals"]["涨幅温和"] = True
                        if "ZLJE" in str(fid):
                            inflow = ev(sv)
                            if inflow is not None:
                                res[c]["detail"]["main_force_inflow"] = inflow
                                if inflow > 0: res[c]["signals"]["主力净流入"] = True
        else:
            # Single-stock: check entity name for code
            for c in codes:
                if c in en:
                    if c not in res:
                        res[c] = {"name": en.split("(")[0] if "(" in en else en, "signals": {}, "detail": {}}
                    for fid, vals in rows.items():
                        if not isinstance(vals, list) or not vals:
                            continue
                        v = str(vals[0])
                        if "%" in v:
                            pct = ev(v)
                            if pct is not None:
                                res[c]["detail"]["change_pct"] = pct
                                if pct > 5: res[c]["signals"]["涨幅过大"] = True
                                elif pct >= 3: res[c]["signals"]["涨幅偏大"] = True
                                elif pct < -3: res[c]["signals"]["低开走弱"] = True
                                elif -1 < pct < 2: res[c]["signals"]["缩量企稳"] = True
                                else: res[c]["signals"]["涨幅温和"] = True
                        if "ZLJE" in str(fid):
                            inflow = ev(v)
                            if inflow is not None:
                                res[c]["detail"]["main_force_inflow"] = inflow
                                if inflow > 0: res[c]["signals"]["主力净流入"] = True
                    break
    # Fill defaults and calculate scores
    for c in codes:
        if c in res:
            s = res[c]["signals"]
            for k in ["主力净流入", "涨幅过大", "低开走弱", "缩量企稳"]:
                if k not in s:
                    s[k] = None
            score = 50
            if s.get("主力净流入") == True: score += 20
            if s.get("主力净流入") == False: score -= 10
            if s.get("涨幅过大") == True: score -= 20
            if s.get("低开走弱") == True: score -= 15
            if s.get("缩量企稳") == True: score += 10
            s["综合评分"] = max(0, min(100, score))
    return res

def main():
    p = argparse.ArgumentParser()
    p.add_argument("codes", nargs="?", help="股票代码逗号分隔")
    p.add_argument("--text", action="store_true")
    args = p.parse_args()
    if not args.codes:
        print(json.dumps({"error": "need codes"}))
        sys.exit(1)
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    q = ",".join(codes) + " 今日涨跌幅 成交量 换手率 主力资金净流入"
    raw = query(q)
    if not raw:
        raw = query(",".join(codes) + " 今日涨跌幅 成交量 主力资金净流入")
    if not raw:
        print(json.dumps({"error": "query failed", "codes": codes}))
        sys.exit(1)
    sigs = calc(codes, raw)
    if not sigs:
        print(json.dumps({"error": "calc failed"}))
        sys.exit(1)
    buy = [c for c in codes if c in sigs and sigs[c]["signals"].get("主力净流入") == True and not sigs[c]["signals"].get("涨幅过大")]
    avoid = [c for c in codes if c in sigs and (sigs[c]["signals"].get("涨幅过大") == True or sigs[c]["signals"].get("低开走弱") == True)]
    watch = [c for c in codes if c in sigs and c not in buy and c not in avoid]
    out = {"signals": sigs, "summary": {"total": len(codes), "buy": buy, "watch": watch, "avoid": avoid}}
    if args.text:
        print("共 %d 只" % len(codes))
        print("买入: %s" % buy)
        print("关注: %s" % watch)
        print("回避: %s" % avoid)
        for c in codes:
            if c in sigs:
                print("")
                print("--- %s ---" % c)
                for k, v in sigs[c]["signals"].items():
                    print("  %s: %s" % (k, v))
                for k, v in sigs[c]["detail"].items():
                    print("  [%s] %s" % (k, v))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
