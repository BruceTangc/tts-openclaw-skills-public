#!/usr/bin/env python3
"""auction_check.py - 竞价量比计算
计算 竞价量/昨日成交量 比值，判断开盘信号真假。
用法:
  python3 auction_check.py 000426,600711,601168
  python3 auction_check.py 000426,600711 --text
"""
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

def get_auction_volume(code):
    """查单只股票的竞价量"""
    q = "%s 今日竞价成交量" % code
    raw = query(q)
    if not raw:
        return None
    try:
        tables = raw["data"]["data"]["searchDataResultDTO"]["dataTableDTOList"]
    except:
        return None
    for t in tables:
        rows = t.get("table", {})
        for fid, vals in rows.items():
            if fid == "headName" or not isinstance(vals, list):
                continue
            for v in vals:
                s = str(v)
                if "万股" in s or "万" in s:
                    vol = ev(s)
                    if vol is not None:
                        return vol
    return None

def get_yesterday_volume(code):
    """查单只股票的昨日成交量"""
    q = "%s 昨日成交量" % code
    raw = query(q)
    if not raw:
        return None
    try:
        tables = raw["data"]["data"]["searchDataResultDTO"]["dataTableDTOList"]
    except:
        return None
    for t in tables:
        rows = t.get("table", {})
        for fid, vals in rows.items():
            if fid == "headName" or not isinstance(vals, list):
                continue
            for v in vals:
                s = str(v)
                if "万股" in s or "万" in s:
                    vol = ev(s)
                    if vol is not None:
                        return vol
    return None

def get_open_price(code):
    """查单只股票今日开盘价"""
    q = "%s 今日开盘价" % code
    raw = query(q)
    if not raw:
        return None
    try:
        tables = raw["data"]["data"]["searchDataResultDTO"]["dataTableDTOList"]
    except:
        return None
    for t in tables:
        rows = t.get("table", {})
        for fid, vals in rows.items():
            if fid == "headName" or not isinstance(vals, list):
                continue
            for v in vals:
                s = str(v)
                if "元" in s:
                    p = ev(s)
                    if p is not None:
                        return p
    return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("codes", nargs="?", help="股票代码逗号分隔")
    p.add_argument("--text", action="store_true")
    args = p.parse_args()
    if not args.codes:
        print(json.dumps({"error": "need codes"}))
        sys.exit(1)

    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    results = {}

    for c in codes:
        sig = {"竞价量比": None, "竞价放量": None, "竞价缩量": None}
        det = {}
        # 查竞价量
        auction_v = get_auction_volume(c)
        det["auction_volume"] = auction_v
        # 查昨日成交量
        yesterday_v = get_yesterday_volume(c)
        det["yesterday_volume"] = yesterday_v
        # 计算比值
        if auction_v is not None and yesterday_v is not None and yesterday_v > 0:
            ratio = auction_v / yesterday_v
            det["auction_volume_ratio"] = ratio
            sig["竞价量比"] = ratio
            if ratio > 0.15:
                sig["竞价放量"] = True
            elif ratio < 0.02:
                sig["竞价缩量"] = True
        # 查开盘价
        open_p = get_open_price(c)
        det["open_price"] = open_p

        results[c] = {"name": c, "signals": sig, "detail": det}

    # 汇总
    high = [c for c in codes if c in results and results[c]["signals"].get("竞价放量")]
    low = [c for c in codes if c in results and results[c]["signals"].get("竞价缩量")]
    out = {"signals": results, "summary": {"total": len(codes), "竞价放量": high, "竞价缩量": low}}

    if args.text:
        print("共 %d 只" % len(codes))
        if high: print("竞价放量(>15%%): %s" % str(high))
        if low: print("竞价缩量(<2%%): %s" % str(low))
        for c in codes:
            if c in results:
                print("")
                print("--- %s ---" % c)
                for k, v in results[c]["signals"].items():
                    if v is not None:
                        if isinstance(v, float):
                            print("  %s: %.4f" % (k, v))
                        else:
                            print("  %s: %s" % (k, v))
                for k, v in results[c]["detail"].items():
                    if v is not None:
                        print("  [%s] %s" % (k, v))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()