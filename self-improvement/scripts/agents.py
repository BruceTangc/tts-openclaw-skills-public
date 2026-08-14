#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
agents.py - Agent Registry 管理（V3.2 Multi-Agent Learning OS）

扫描工作区的多个 Agent 工作区，维护 memory/agents/REGISTRY.md，
支持列表 / 状态 / 能力 / 重叠检测。

用法：
  python3 agents.py --list           # 列出所有 Agent
  python3 agents.py --status         # 显示 Agent 状态
  python3 agents.py --capabilities   # 显示 Agent 能力
  python3 agents.py --overlap        # 检测能力重叠

数据存储：memory/agents/registry.json（结构化）+ memory/agents/REGISTRY.md（可读）
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

HOME = os.path.expanduser("~")
OPENCLAW_DIR = os.environ.get("OPENCLAW_HOME") or os.path.join(HOME, ".openclaw")
WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("OPENCLAW_WORKSPACE_DIR") or os.path.join(OPENCLAW_DIR, "workspace")

AGENTS_DIR = os.path.join(WORKSPACE, "memory", "agents")
REGISTRY_JSON = os.path.join(AGENTS_DIR, "registry.json")
REGISTRY_MD = os.path.join(AGENTS_DIR, "REGISTRY.md")

NL = chr(10)  # 真实换行


def discover_agents():
    """扫描工作区目录，识别 Agent 工作区。"""
    agents = []
    base = os.path.dirname(WORKSPACE)
    seen = set()
    for name in sorted(os.listdir(base or ".")):
        if not name.startswith("workspace-"):
            continue
        wdir = os.path.join(base, name)
        if not os.path.isdir(wdir):
            continue
        # 跳过备份目录
        if ".bak" in name:
            continue
        agent_id = name[len("workspace-"):]
        if agent_id in seen:
            continue
        seen.add(agent_id)
        info = {
            "id": agent_id,
            "path": wdir,
            "role": guess_role(wdir, agent_id),
            "skills": count_skills(wdir),
            "status": "active",
            "last_seen": None,
        }
        agents.append(info)

    # 从已有 registry 补充 last_seen 和 role 覆盖
    old = load_registry_data()
    old_map = {a.get("id"): a for a in old.get("agents", [])}
    for a in agents:
        if a["id"] in old_map:
            o = old_map[a["id"]]
            a["last_seen"] = o.get("last_seen")
            if o.get("role"):
                a["role"] = o["role"]
            if o.get("status"):
                a["status"] = o["status"]
    return agents


def guess_role(wdir, agent_id):
    """从工作区 AGENTS.md 猜测角色。"""
    try:
        with open(os.path.join(wdir, "AGENTS.md"), encoding="utf-8") as f:
            content = f.read()[:2000]
        for line in content.splitlines():
            line = line.strip()
            if any(k in line for k in ("角色", "Role", "主管", "负责")):
                cleaned = re.sub(r"[#*`|]", "", line)
                if cleaned and len(cleaned) < 80:
                    return cleaned
    except (OSError, IOError):
        pass
    return "未定义"


def count_skills(wdir):
    skills_dir = os.path.join(wdir, "skills")
    if os.path.isdir(skills_dir):
        try:
            return len([d for d in os.listdir(skills_dir)
                        if os.path.isdir(os.path.join(skills_dir, d))])
        except OSError:
            return 0
    return 0


def load_registry_data():
    if os.path.exists(REGISTRY_JSON):
        try:
            with open(REGISTRY_JSON, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"agents": [], "updated": None}


def save_registry_data(data):
    os.makedirs(AGENTS_DIR, exist_ok=True)
    with open(REGISTRY_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_registry_md(agents):
    os.makedirs(AGENTS_DIR, exist_ok=True)
    lines = ["# Agent Registry", ""]
    lines.append("> 自动生成于 %s（agents.py）" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")
    for a in agents:
        lines.append("## Agent: %s" % a["id"])
        lines.append("- ID: %s" % a["id"])
        lines.append("- Role: %s" % a["role"])
        lines.append("- Path: %s" % a["path"])
        lines.append("- Skills: %d" % a["skills"])
        lines.append("- Status: %s" % a["status"])
        lines.append("- Last seen: %s" % (a["last_seen"] or "unknown"))
        lines.append("")
    with open(REGISTRY_MD, "w", encoding="utf-8") as f:
        f.write(NL.join(lines))


def cmd_list(agents):
    if not agents:
        print("⚠️ 未发现任何 Agent 工作区（workspace-*）")
        return
    print("📇 Agent Registry（%d 个）" % len(agents))
    print()
    for a in agents:
        print("  • %s" % a["id"])
        print("      Role:   %s" % a["role"])
        print("      Skills: %s" % a["skills"])
        print("      Status: %s" % a["status"])


def cmd_status(agents):
    if not agents:
        print("⚠️ 未发现任何 Agent 工作区")
        return
    print("📊 Agent 状态")
    print()
    active = sum(1 for a in agents if a.get("status") == "active")
    print("  总数: %d，active: %d" % (len(agents), active))
    print()
    for a in agents:
        print("  [%s] %s — %s" % (a.get("status", "?"), a["id"], a["role"]))


def cmd_capabilities(agents):
    if not agents:
        print("⚠️ 未发现任何 Agent 工作区")
        return
    print("🧩 Agent 能力")
    print()
    for a in agents:
        print("  %s:" % a["id"])
        print("    role = %s" % a["role"])
        print("    skills = %d 个" % a["skills"])


def cmd_overlap(agents):
    if not agents:
        print("⚠️ 未发现任何 Agent 工作区")
        return
    print("🔍 能力重叠检测（按 role 文本相似）")
    print()
    by_role = defaultdict(list)
    for a in agents:
        by_role[a["role"]].append(a["id"])
    found = False
    for role, ids in by_role.items():
        if len(ids) > 1 and role != "未定义":
            print("  ⚠️ 重叠: [%s] 都定义为「%s」" % (", ".join(ids), role))
            found = True
    if not found:
        print("  ✅ 未发现明显重叠")
        print("  （如需精确检测请扩展 skills 交集分析）")


def main():
    parser = argparse.ArgumentParser(description="Agent Registry 管理（V3.2）")
    parser.add_argument("--list", action="store_true", help="列出所有 Agent")
    parser.add_argument("--status", action="store_true", help="显示 Agent 状态")
    parser.add_argument("--capabilities", action="store_true", help="显示 Agent 能力")
    parser.add_argument("--overlap", action="store_true", help="检测能力重叠")
    args = parser.parse_args()

    agents = discover_agents()

    data = load_registry_data()
    data["agents"] = agents
    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_registry_data(data)
    write_registry_md(agents)

    if args.list:
        cmd_list(agents)
    elif args.status:
        cmd_status(agents)
    elif args.capabilities:
        cmd_capabilities(agents)
    elif args.overlap:
        cmd_overlap(agents)
    else:
        cmd_list(agents)
        print()
        print("用法: agents.py --list|--status|--capabilities|--overlap")


if __name__ == "__main__":
    main()
