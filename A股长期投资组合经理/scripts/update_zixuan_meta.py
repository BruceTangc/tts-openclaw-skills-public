#!/usr/bin/env python3
"""
自选股元数据管理脚本（含云端同步）。
当 LLM 将一只股票加入自选后，需要调用本脚本记录 added_date，
并同步到东方财富云端自选股。

用法：
  python3 update_zixuan_meta.py add 000933 25.35    # 记录加入日期和基准价，同步到云端
  python3 update_zixuan_meta.py remove 000933        # 移除元数据，同步删除云端
  python3 update_zixuan_meta.py list                  # 查看所有自选元数据
  python3 update_zixuan_meta.py sync                  # 从云端拉取自选股，补全本地元数据

注意事项：
  - 股票代码强制 6 位字符串（内部 zfill(6)）
  - LLM 必须在执行 mx-zixuan skill 加入自选后立即调用本脚本
"""
import json, os, sys, subprocess
from datetime import date

BASE_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
META_FILE = os.path.join(BASE_DIR, "memory", "zixuan_added_dates.json")
MX_ZIXUAN = os.path.join(BASE_DIR, "skills/mx-zixuan/mx_zixuan.py")


def zfill_code(code):
    return str(code).strip().zfill(6)


def load_meta():
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}


def save_meta(meta):
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    with open(META_FILE, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def cmd_add(args):
    code = zfill_code(args[0])
    base_price = float(args[1]) if len(args) > 1 else None

    # 同步到云端自选股
    r = subprocess.run([sys.executable, MX_ZIXUAN, "add", code], capture_output=True, text=True, timeout=30)
    if r.returncode == 0:
        print(f"☁️  云端: {code} 已加入东方财富自选股")
    else:
        print(f"⚠️  云端同步失败: {r.stderr[:100]}")

    meta = load_meta()
    meta[code] = {
        "added_date": date.today().isoformat(),
        "base_price": base_price,
    }
    save_meta(meta)
    print(f"✅ {code}: 已记录加入日期={date.today()}, 基准价={base_price}")


def cmd_remove(args):
    code = zfill_code(args[0])
    meta = load_meta()
    if code in meta:
        # 同步删除云端自选股
        r = subprocess.run([sys.executable, MX_ZIXUAN, "delete", code], capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            print(f"☁️  云端: {code} 已从东方财富自选股删除")
        else:
            print(f"⚠️  云端同步失败: {r.stderr[:100]}")
        del meta[code]
        save_meta(meta)
        print(f"🗑️ {code}: 已移除元数据")
    else:
        print(f"⚠️ {code}: 不在元数据中")


def cmd_list(args):
    meta = load_meta()
    if not meta:
        print("📋 自选股元数据为空")
        return
    print(f"📋 自选股元数据 ({len(meta)} 只):")
    for code, info in sorted(meta.items()):
        print(f"  {code} | 加入: {info.get('added_date','?')} | 基准价: {info.get('base_price','?')}")


def cmd_sync(args):
    """从云端拉取自选股列表，与本地元数据合并"""
    r = subprocess.run([sys.executable, MX_ZIXUAN, "query"], capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"❌ 云端查询失败: {r.stderr[:200]}")
        return
    # 从输出中解析股票代码
    import re
    cloud_codes = set(re.findall(r'(\d{6})', r.stdout))
    meta = load_meta()
    local_codes = set(meta.keys())
    missing = cloud_codes - local_codes
    stale = local_codes - cloud_codes
    if missing:
        for code in sorted(missing):
            meta[code] = {"added_date": date.today().isoformat(), "base_price": None, "synced_from_cloud": True}
            print(f"➕ {code}: 云端有但本地无→已补录")
    if stale:
        for code in sorted(stale):
            print(f"➖ {code}: 本地有但云端无→未删除（保留元数据）")
    if not missing and not stale:
        print("✅ 云端与本地完全一致，无需同步")
    save_meta(meta)
    print(f"📊 本地: {len(meta)}只 | 云端: {len(cloud_codes)}只")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    cmds = {
        'add': cmd_add,
        'remove': cmd_remove,
        'list': cmd_list,
        'sync': cmd_sync,
    }

    if cmd not in cmds:
        print(f"❌ 未知命令: {cmd}")
        print(f"可用命令: add, remove, list, sync")
        return

    cmds[cmd](args)


if __name__ == '__main__':
    main()