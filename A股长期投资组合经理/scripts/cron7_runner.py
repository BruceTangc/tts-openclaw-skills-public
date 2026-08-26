#!/usr/bin/env python3
"""
Cron 7 有状态执行脚本（收盘复盘+选股）。
将 10 个步骤包装为有状态执行，每步完成后写入 checkpoint。
下次运行时检测 checkpoint，从中断处恢复而非重跑。

用法：
  python3 cron7_runner.py                          # 正常运行全部10步
  python3 cron7_runner.py --resume                 # 从中断处恢复
  python3 cron7_runner.py --checkpoint             # 仅输出最近一次checkpoint状态
  python3 cron7_runner.py --clear-checkpoint       # 清除checkpoint

注意：
  - 本脚本不执行具体数据查询，它将每一步翻译为 exec 指令让 LLM 执行
  - checkpoint 记录每步完成状态和中间结果
  - LLM 每次调用本脚本获取当前应执行的步骤编号
"""
import json, os, sys, subprocess
from datetime import datetime

BASE_DIR = os.path.expanduser("{{OPENCLAW_WORKSPACE}}")
CP_PATH = os.path.join(BASE_DIR, "memory", "checkpoint_cron7.json")

STEPS = [
    {"id": 1, "name": "判断交易日+风控", "desc": "执行 is_trading_day.py + risk_control.py"},
    {"id": 2, "name": "复盘与盈亏统计", "desc": "使用 mx-data + mx-moni 查持仓和自选"},
    {"id": 3, "name": "结构化经验提炼", "desc": "回顾今日操作，识别可复用模式"},
    {"id": 4, "name": "市场阶段判断", "desc": "使用 mx-data 查大盘近20日均线位置"},
    {"id": 5, "name": "板块资金流向", "desc": "使用 mx-data 查板块涨跌排名和主力资金"},
    {"id": 6, "name": "mx-xuangu 条件选股", "desc": "使用 mx-xuangu skill 多条件选股，排除创业板/科创板/北交所"},
    {"id": 7, "name": "filter_main_board 主板过滤", "desc": "filter_main_board.py 硬过滤+基本面验证"},
    {"id": 8, "name": "cleanup_zixuan 健康度检查", "desc": "cleanup_zixuan.py 评估淘汰"},
    {"id": 9, "name": "加入自选+记录元数据", "desc": "使用 mx-zixuan + update_zixuan_meta.py + 查公告"},
    {"id": 10, "name": "生成复盘报告+推送飞书", "desc": "写入 memory/ + 飞书推送"},
]


def load_checkpoint():
    if os.path.exists(CP_PATH):
        try:
            with open(CP_PATH) as f:
                return json.load(f)
        except:
            pass
    return {"completed": [], "current_step": 1, "created_at": None, "updated_at": None}


def save_checkpoint(cp):
    os.makedirs(os.path.dirname(CP_PATH), exist_ok=True)
    cp["updated_at"] = datetime.now().isoformat()
    with open(CP_PATH + ".tmp", 'w') as f:
        json.dump(cp, f, indent=2, ensure_ascii=False)
    os.replace(CP_PATH + ".tmp", CP_PATH)


def clear_checkpoint():
    if os.path.exists(CP_PATH):
        os.remove(CP_PATH)
        print("✅ Checkpoint 已清除")
    else:
        print("ℹ️ 无 checkpoint 需清除")


def show_checkpoint():
    cp = load_checkpoint()
    completed = cp.get("completed", [])
    current = cp.get("current_step", 1)
    print(f"📋 Cron 7 Checkpoint 状态")
    print(f"   已完成的步骤: {len(completed)}/{len(STEPS)}")
    print(f"   下一步: 步骤 {current} ({STEPS[current-1]['name']})" if current <= len(STEPS) else "   全部完成")
    for s in STEPS:
        mark = "✅" if s["id"] in completed else "⬜"
        print(f"   {mark} 步骤{s['id']}: {s['name']}")
    if cp.get("created_at"):
        print(f"   创建时间: {cp['created_at']}")
    if cp.get("updated_at"):
        print(f"   更新时间: {cp['updated_at']}")
    return cp


def cmd_resume():
    """恢复模式：找出从中断的位置继续"""
    cp = load_checkpoint()
    current = cp.get("current_step", 1)
    if current > len(STEPS):
        print("✅ 所有步骤已完成，无需恢复")
        return
    print(f"🔄 检测到 checkpoint，从中断处恢复：")
    print(f"   已完成的步骤: {len(cp.get('completed', []))}")
    print(f"   下一步: 步骤 {current} — {STEPS[current-1]['name']}")
    print(f"   开始时间: {cp.get('created_at', '未知')}")
    print()
    print(f"LLM 应重新读取检查点确认：")
    print(f"  python3 {{OPENCLAW_WORKSPACE}}/skills/A股交易员/scripts/cron7_runner.py --checkpoint")


def complete_step(step_id, cp=None):
    """LLM 在每步完成后调用此函数标记完成"""
    if cp is None:
        cp = load_checkpoint()
    completed = cp.get("completed", [])
    if step_id not in completed:
        completed.append(step_id)
    cp["completed"] = sorted(completed)
    cp["current_step"] = max(completed) + 1
    if not cp.get("created_at"):
        cp["created_at"] = datetime.now().isoformat()
    save_checkpoint(cp)
    print(f"✅ 步骤 {step_id} ({STEPS[step_id-1]['name']}) 标记完成")
    next_step = cp["current_step"]
    if next_step <= len(STEPS):
        print(f"下一步: 步骤 {next_step} — {STEPS[next_step-1]['name']}")
    else:
        print("🎉 所有步骤已完成，可以清除 checkpoint")


def main():
    if len(sys.argv) < 2:
        # 默认：生成新的 checkpoint，输出 LLM 执行计划
        cp = {
            "completed": [],
            "current_step": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        save_checkpoint(cp)
        print(f"📋 Cron 7 执行计划已创建 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"   共 {len(STEPS)} 个步骤")
        print()
        print("LLM 执行流程（每完成一步调用 --complete <N> 标记）：")
        for s in STEPS:
            print(f"   步骤{s['id']}: {s['name']}")
            print(f"       {s['desc']}")
        print()
        print("开始执行步骤 1: 判断交易日")
        return

    cmd = sys.argv[1]

    if cmd == '--resume':
        cmd_resume()
    elif cmd == '--checkpoint':
        show_checkpoint()
    elif cmd == '--clear-checkpoint':
        clear_checkpoint()
    elif cmd == '--complete' and len(sys.argv) > 2:
        complete_step(int(sys.argv[2]))
    else:
        print(__doc__)


if __name__ == '__main__':
    main()
