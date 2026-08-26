#!/usr/bin/env python3
"""
价格警报前置校验脚本 - stop_loss_guard.py (V2.0)

V2.0 核心变更：价格大幅下跌不再直接驱动卖出，而是触发"重新研究(RE_STUDY)"。
脚本不再输出强制卖出指令，而是写入 RE_STUDY_REQUIRED 到 state.json。
仅黑天鹅事件（ST/立案/造假）保留强制卖出 —— 由 LLM 通过 mx-search 独立判断。

用法：
  python3 stop_loss_guard.py <持仓JSON文件路径>
  python3 stop_loss_guard.py --latest   # 自动查找最新的持仓JSON
  python3 stop_loss_guard.py --check-code 601288   # 指定股票代码检查

退出码语义 (V2.0)：
  - 0: 正常（无价格警报）
  - 1: RE_STUDY_REQUIRED（价格跌破-8%阈值，触发重新研究，不是强制卖出）
  - 2: SOFT_ALERT（价格跌破-5%阈值，建议关注）
  - 3: 数据错误
"""
import json, os, sys, glob, re
from datetime import datetime

BASE_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
OUTPUT_DIR = os.path.join(BASE_DIR, "tmp/mx_data_output")
STATE_PATH = os.path.join(BASE_DIR, "state.json")

# V2.0：价格阈值作为警报触发线，不直接驱动卖出
HARD_ALERT_PCT = -8.0  # %  → RE_STUDY_REQUIRED
SOFT_ALERT_PCT = -5.0  # %  → 关注提示


def find_latest_position_json():
    """查找最新的 mx_moni 持仓 JSON 文件"""
    pattern = os.path.join(OUTPUT_DIR, "mx_moni_我的持仓_*.json")
    files = glob.glob(pattern)
    if not files:
        pattern = os.path.join(OUTPUT_DIR, "mx_moni_持仓_*.json")
        files = glob.glob(pattern)
    if not files:
        pattern = os.path.join(OUTPUT_DIR, "mx_moni_查询*持仓*.json")
        files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def write_re_study(state, code, name, profit_pct, price, cost):
    """写 RE_STUDY_REQUIRED 到 state.json 的 re_study_list"""
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH) as f:
                state_data = json.load(f)
        else:
            state_data = {}
    except:
        state_data = {}

    if 're_study_list' not in state_data:
        state_data['re_study_list'] = []

    # 去重：同一股票不重复添加
    existing_codes = [e.get('code', '') for e in state_data['re_study_list']]
    if code not in existing_codes:
        state_data['re_study_list'].append({
            'code': code,
            'name': name,
            'profitPct': round(profit_pct, 2),
            'price': price,
            'costPrice': cost,
            'triggered_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'trigger': 'price_alert_hard' if profit_pct <= HARD_ALERT_PCT else 'price_alert_soft',
            'status': 'pending_review'
        })

    # 原子写入
    tmp_path = STATE_PATH + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(state_data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, STATE_PATH)
    return True


def parse_cost(cost_price_raw, cost_price_dec):
    """解析成本价：costPrice / 10^costPriceDec"""
    if not cost_price_raw or cost_price_raw <= 0:
        return None
    return cost_price_raw / (10 ** cost_price_dec)


def parse_price(price_raw, price_dec):
    """解析现价：price / 10^priceDec"""
    if not price_raw or price_raw <= 0:
        return None
    return price_raw / (10 ** price_dec)


def check_position(pos, state_for_write=None):
    """
    V2.0：检查单只持仓是否触发价格警报。
    返回 (alert_level: str, reason: str, details: dict)
    alert_level: 'normal' | 'soft_alert' | 'hard_alert'
    """
    sec_name = pos.get('secName', '未知')
    sec_code = pos.get('secCode', '未知')
    count = pos.get('count', 0)
    avail = pos.get('availCount', 0)

    if count <= 0 or avail <= 0:
        return 'normal', f"{sec_name}({sec_code}) 持仓为0，无需检查", {}

    # 解析成本价
    cost_price_raw = pos.get('costPrice', 0)
    cost_price_dec = pos.get('costPriceDec', 3)
    cost = parse_cost(cost_price_raw, cost_price_dec)

    # 解析现价
    price_raw = pos.get('price', 0)
    price_dec = pos.get('priceDec', 2)
    price = parse_price(price_raw, price_dec)

    # API 直接返回的盈亏数据
    profit = pos.get('profit', 0)
    profit_pct = pos.get('profitPct', 0)

    details = {
        'secName': sec_name,
        'secCode': sec_code,
        'count': count,
        'availCount': avail,
        'costPriceRaw': cost_price_raw,
        'costPriceDec': cost_price_dec,
        'costPrice': round(cost, 4) if cost else None,
        'priceRaw': price_raw,
        'priceDec': price_dec,
        'price': round(price, 4) if price else None,
        'profit': profit,
        'profitPct': profit_pct,
    }

    # V2.0：价格跌破 -8% → RE_STUDY（硬警报），不强制卖出
    if profit_pct <= HARD_ALERT_PCT:
        # 写入 state.json
        write_re_study({}, sec_code, sec_name, profit_pct,
                       details['price'], details['costPrice'])
        return 'hard_alert', (
            f"🔔 {sec_name}({sec_code}) 触发硬价格警报 → RE_STUDY_REQUIRED\n"
            f"   成本价: {details['costPrice']} 元\n"
            f"   现价: {details['price']} 元\n"
            f"   API浮亏比: {profit_pct:.2f}% (≤{HARD_ALERT_PCT}%)\n"
            f"   浮亏金额: {profit:.2f} 元\n"
            f"   持仓: {count}股 (可用{avail}股)\n"
            f"   ⚠️ V2.0: 不强制卖出。Cron 7 需审查投资假设后决定。\n"
            f"   📋 已写入 state.json → re_study_list"
        ), details

    # V2.0：价格跌破 -5% → 软警报，建议关注
    if profit_pct <= SOFT_ALERT_PCT:
        return 'soft_alert', (
            f"⚠️ {sec_name}({sec_code}) 触发软价格警报\n"
            f"   成本: {details['costPrice']} | 现价: {details['price']}\n"
            f"   API浮亏: {profit_pct:.2f}% (软警报线{SOFT_ALERT_PCT}%)\n"
            f"   建议 Cron 7 审视投资逻辑是否变化"
        ), details

    return 'normal', (
        f"✅ {sec_name}({sec_code}) 正常\n"
        f"   成本: {details['costPrice']} | 现价: {details['price']}\n"
        f"   浮盈/亏: {profit_pct:+.2f}% | 金额: {profit:+.2f} 元"
    ), details


def main():
    # 解析参数
    json_path = None
    target_code = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--latest':
            json_path = find_latest_position_json()
            if not json_path:
                print("❌ 未找到持仓JSON文件，请先执行 mx_moni 查询持仓")
                sys.exit(3)
        elif args[i] == '--check-code' and i + 1 < len(args):
            target_code = args[i + 1]
            i += 1
        elif args[i].endswith('.json'):
            json_path = args[i]
        i += 1

    if not json_path:
        json_path = find_latest_position_json()
        if not json_path:
            print("❌ 未指定持仓JSON文件且自动查找失败")
            print("用法: python3 stop_loss_guard.py <持仓JSON路径> [--check-code CODE]")
            print("      python3 stop_loss_guard.py --latest")
            sys.exit(3)

    if not os.path.exists(json_path):
        print(f"❌ 文件不存在: {json_path}")
        sys.exit(3)

    # 读取JSON
    try:
        with open(json_path) as f:
            raw = json.load(f)
    except Exception as e:
        print(f"❌ JSON解析失败: {e}")
        sys.exit(3)

    # 提取持仓数据
    data = raw.get('data', raw)
    pos_list = data.get('posList', [])
    if not pos_list:
        print("ℹ️ 当前无持仓")
        sys.exit(0)

    file_time = datetime.fromtimestamp(os.path.getmtime(json_path))
    print(f"📋 持仓数据来源: {os.path.basename(json_path)}")
    print(f"   文件时间: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   总资产: {data.get('totalAssets', 'N/A')}")
    print(f"   总盈亏: {data.get('totalProfit', 'N/A')}")
    print()
    print("⚡ V2.0 价格警报模式：触发阈值只写入 RE_STUDY，不强制卖出")
    print()

    any_hard = False
    any_soft = False

    for pos in pos_list:
        sec_code = pos.get('secCode', '')
        # 如果指定了目标代码，只检查该股票
        if target_code and str(sec_code).zfill(6) != str(target_code).zfill(6):
            continue

        alert_level, reason, details = check_position(pos)

        print("=" * 70)
        print(reason)

        if alert_level == 'hard_alert':
            any_hard = True
        elif alert_level == 'soft_alert':
            any_soft = True

    print()

    if any_hard:
        print("🔔 **结论: RE_STUDY_REQUIRED（硬价格警报）**")
        print("   V2.0: 不强制卖出。Cron 7 收盘复盘时审查投资假设后决定。")
        print("   📋 警报已写入 state.json → re_study_list")
        sys.exit(1)
    elif any_soft:
        print("⚠️  **结论: 软价格警报，建议关注**")
        print("   建议 Cron 7 审查相关持仓的投资逻辑")
        sys.exit(2)
    else:
        print("✅ **结论: 所有持仓正常，未触发价格警报**")
        sys.exit(0)


if __name__ == '__main__':
    main()
