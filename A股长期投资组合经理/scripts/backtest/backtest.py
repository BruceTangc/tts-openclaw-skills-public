#!/usr/bin/env python3
import os, sys, json, argparse, subprocess, pandas as pd, numpy as np, akshare as ak
from datetime import datetime, timedelta
WORKSPACE = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
CACHE = os.path.join(WORKSPACE, "tmp/backtest_cache")
os.makedirs(CACHE, exist_ok=True)

def sina(code):
    code = code.strip().zfill(6)
    return ("sz" if code.startswith("0") or code.startswith("3") else "sh") + code

def fetch(code, years=3):
    f = os.path.join(CACHE, "%s_%dy.parquet" % (code, years))
    if os.path.exists(f):
        try:
            df = pd.read_parquet(f)
            if len(df) > 0: return df
        except: pass
    try:
        df = ak.stock_zh_a_daily(symbol=sina(code))
        if df is None or len(df) == 0: return None
        df = df.rename(columns={"date":"date","close":"close","open":"open","high":"high","low":"low","volume":"volume","amount":"amount","turnover":"turnover"})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        cutoff = df["date"].max() - timedelta(days=365*years)
        df = df[df["date"] >= cutoff].reset_index(drop=True)
        df["ma20"] = df["close"].rolling(20).mean()
        df["vma5"] = df["volume"].rolling(5).mean()
        df["vr"] = df["volume"] / df["vma5"].replace(0, np.nan)
        df.to_parquet(f)
        return df
    except: return None

def run(code, df, cap=200000):
    if df is None or len(df) < 60: return None
    cash = cap; shares = 0; ep = 0; ec = 0; trades = []; hold = False
    for i in range(20, len(df)):
        r = df.iloc[i]; p = r["close"]; ma = r["ma20"]; vr = r["vr"]
        if pd.isna(vr): vr = 1.0
        if not hold:
            sig = False; why = ""
            if p > ma and vr > 1.2: sig = True; why = "站上20MA+放量"
            if ma*0.97 < p < ma*1.03 and vr < 0.8: sig = True; why = "缩量企稳20MA"
            if sig:
                mx = cap * 0.4; q = int(mx / p / 100) * 100
                if q >= 100 and cash >= q * p * 1.001:
                    c = q * p * 1.001; cash -= c; shares = q; ep = p; ec = c; hold = True
                    trades.append({"d":str(r["date"])[:10],"t":"BUY","p":round(p,2),"q":q,"w":why})
        if hold:
            pnl = (p - ep) / ep; sig = False; why = ""
            if pnl <= -0.08: sig = True; why = "硬止损-8%"
            elif pnl <= -0.05 and vr < 0.5: sig = True; why = "软止损+缩量"
            elif p < ma * 0.95: sig = True; why = "跌破20MA"
            elif pnl > 0.15: sig = True; why = "止盈+15%"
            if sig:
                rev = shares * p * 0.999; cash += rev
                trades.append({"d":str(r["date"])[:10],"t":"SELL","p":round(p,2),"q":shares,"pnl":round(rev-ec,2),"w":why})
                shares = 0; hold = False
    if hold:
        fp = df.iloc[-1]["close"]; rev = shares * fp * 0.999; cash += rev
        trades.append({"d":str(df.iloc[-1]["date"])[:10],"t":"SELL","p":round(fp,2),"q":shares,"pnl":round(rev-ec,2),"w":"平仓"})
    ret = (cash / cap - 1) * 100
    days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
    yr = max(days/365.25, 0.5)
    ar = ((cash/cap)**(1/yr)-1)*100
    sells = [t for t in trades if t["t"]=="SELL" and "pnl" in t]
    w = [t for t in sells if t["pnl"]>0]; l = [t for t in sells if t["pnl"]<=0]
    wr = len(w)/max(len(w)+len(l),1)*100
    aw = np.mean([t["pnl"] for t in w]) if w else 0
    al = abs(np.mean([t["pnl"] for t in l])) if l else 1
    return {"c":code,"ret":round(ret,2),"ar":round(ar,2),"wr":round(wr,1),"plr":round(aw/al,2) if al>0 else 999,"n":len([t for t in trades if t["t"]=="BUY"]),"days":days,"trades":trades}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("codes", nargs="?", help="股票代码逗号分隔")
    p.add_argument("--years", type=int, default=3)
    p.add_argument("--capital", type=int, default=200000)
    p.add_argument("--list", action="store_true")
    args = p.parse_args()
    if args.list:
        r = subprocess.run(["python3",os.path.join(WORKSPACE,"skills/mx-zixuan/mx_zixuan.py"),"查询我的自选股列表"],capture_output=True,text=True,timeout=30,cwd=os.path.join(WORKSPACE,"skills/mx-zixuan"))
        print(r.stdout[:2000]); return
    if not args.codes: print("python3 backtest.py 000426"); sys.exit(1)
    codes = [c.strip() for c in args.codes.split(",") if c.strip()]
    results = {}
    for c in codes:
        df = fetch(c, args.years)
        if df is None: continue
        r = run(c, df, args.capital)
        if r: results[c] = r
    if not results: print(json.dumps({"error":"all failed"})); sys.exit(1)
    L = ["="*60,"  策略回测报告","  "+datetime.now().strftime("%Y-%m-%d %H:%M"),"="*60]
    for r in results.values():
        L.append(""); L.append("  "+r["c"]); L.append("  "+"-"*40)
        L.append("  区间: %d天 (%.1f年)" % (r["days"],r["days"]/365.25))
        L.append("  收益: %+.2f%% (年化 %+.2f%%)" % (r["ret"],r["ar"]))
        L.append("  胜率: %.1f%% (盈亏比 %.2f)" % (r["wr"],r["plr"]))
        L.append("  交易: %d笔" % r["n"])
        for t in r["trades"]:
            if t["t"]=="BUY": L.append("    BUY  %s %s %d股@%.2f" % (t["d"],t["w"],t["q"],t["p"]))
            else: L.append("    SELL %s %s %d股@%.2f (%+.0f)" % (t["d"],t["w"],t["q"],t["p"],t.get("pnl",0)))
    L.append(""); L.append("="*60)
    for r in results.values():
        L.append("  %s: 收益%+.2f%% 胜率%.1f%% 盈亏比%.2f %d笔" % (r["c"],r["ret"],r["wr"],r["plr"],r["n"]))
    L.append("="*60)
    print(json.dumps({"report":chr(10).join(L)},ensure_ascii=False,indent=2))

if __name__=="__main__": main()