#!/usr/bin/env python3
"""
假设卡操作 helper script — 替代 python3 -c 内联脚本。

用法：
  # 创建新假设卡（从 stdin 读取完整 JSON）
  echo '{"code":"600519","name":"贵州茅台",...}' | python3 hypothesis_helper.py create 600519

  # 更新假设卡字段（精确修改，禁止手工 patch）
  python3 hypothesis_helper.py update 600519 --set lifecycle=BUILD

  # 追加 evidence_log 条目（只允许 append，禁止覆盖）
  python3 hypothesis_helper.py append-log 600519 --date 2026-08-13 --source cron7 --note "审查结论..."

  # 批量更新字段
  python3 hypothesis_helper.py update 600519 --set lifecycle=REDUCE --set target_position_pct=5

  # 追加 falsifier 条目
  python3 hypothesis_helper.py append-falsifier 600519 --metric "批价下跌10%" --action RE_STUDY
"""
import json, os, sys, argparse
from datetime import datetime

HYPOTHESIS_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}/memory/hypothesis_cards")


def get_path(code):
    return os.path.join(HYPOTHESIS_DIR, f"{code}.json")


def load_card(code):
    path = get_path(code)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def save_card(code, card):
    path = get_path(code)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(card, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def cmd_create(args):
    """从 stdin 读取完整 JSON 创建假设卡"""
    data = sys.stdin.read().strip()
    if not data:
        print("❌ stdin 为空，无法创建假设卡")
        sys.exit(1)
    try:
        card = json.loads(data)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")
        sys.exit(1)
    code = args.code or card.get("code", "")
    if not code or len(code) != 6:
        print(f"❌ 股票代码无效: {code}")
        sys.exit(1)
    card["code"] = code
    save_card(code, card)
    print(f"✅ 假设卡已创建: {code} ({card.get('name', '')})")


def cmd_update(args):
    """精确更新假设卡字段"""
    card = load_card(args.code)
    if card is None:
        print(f"❌ 假设卡不存在: {args.code}")
        sys.exit(1)
    for kv in args.set:
        if "=" not in kv:
            print(f"❌ 格式错误，需要 key=value: {kv}")
            sys.exit(1)
        key, val = kv.split("=", 1)
        # 尝试解析数字
        try:
            val = int(val)
        except ValueError:
            try:
                val = float(val)
            except ValueError:
                pass
        card[key] = val
    save_card(args.code, card)
    print(f"✅ 假设卡已更新: {args.code} → {', '.join(args.set)}")


def cmd_append_log(args):
    """追加 evidence_log 条目"""
    card = load_card(args.code)
    if card is None:
        print(f"❌ 假设卡不存在: {args.code}")
        sys.exit(1)
    log = card.setdefault("evidence_log", [])
    entry = {
        "date": args.date or datetime.now().strftime("%Y-%m-%d"),
        "source": args.source or "cron",
        "note": args.note or "",
    }
    log.append(entry)
    card["last_reviewed"] = entry["date"]
    save_card(args.code, card)
    print(f"✅ evidence_log 已追加: {args.code} ({entry['date']}, {entry['source']})")


def cmd_append_falsifier(args):
    """追加 falsifier 条目"""
    card = load_card(args.code)
    if card is None:
        print(f"❌ 假设卡不存在: {args.code}")
        sys.exit(1)
    falsifiers = card.setdefault("falsifiers", [])
    entry = {"metric": args.metric, "action": args.action}
    falsifiers.append(entry)
    save_card(args.code, card)
    print(f"✅ falsifier 已追加: {args.code} → {args.metric} ({args.action})")


def main():
    p = argparse.ArgumentParser(description="假设卡操作 helper")
    sub = p.add_subparsers(dest="cmd")

    # create
    create_p = sub.add_parser("create", help="从 stdin 创建假设卡")
    create_p.add_argument("code", nargs="?", help="股票代码（6位）")

    # update
    update_p = sub.add_parser("update", help="更新假设卡字段")
    update_p.add_argument("code", help="股票代码")
    update_p.add_argument("--set", action="append", required=True, help="key=value 格式")

    # append-log
    log_p = sub.add_parser("append-log", help="追加 evidence_log")
    log_p.add_argument("code", help="股票代码")
    log_p.add_argument("--date", help="日期 (YYYY-MM-DD)")
    log_p.add_argument("--source", help="来源")
    log_p.add_argument("--note", help="备注")

    # append-falsifier
    f_p = sub.add_parser("append-falsifier", help="追加 falsifier")
    f_p.add_argument("code", help="股票代码")
    f_p.add_argument("--metric", required=True, help="证伪指标")
    f_p.add_argument("--action", required=True, help="触发动作 (RE_STUDY/REDUCE/EXIT)")

    args = p.parse_args()
    if args.cmd == "create":
        cmd_create(args)
    elif args.cmd == "update":
        cmd_update(args)
    elif args.cmd == "append-log":
        cmd_append_log(args)
    elif args.cmd == "append-falsifier":
        cmd_append_falsifier(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
