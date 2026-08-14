# SETUP-MULTI-AGENT.md — self-improvement-llm 多 Agent 接入指南

> 目标：把 `self-improvement-llm`（V3.2 Multi-Agent Learning OS）从"单 Agent 学习框架"升级成
> 真正覆盖多个 Agent 工作区的统一学习系统。本文件面向**新的一台 OpenClaw 机器**接入时使用。

---

## 一、仓库同步了什么

从本仓库 `skills/self-improvement-llm/` 拉下来的内容：

| 部分 | 说明 | 能否直接使用 |
|:---|:---|:---:|
| `scripts/*.py` | 学习引擎（learn.py）、Learning Bus（bus.py）、Agent 注册（agents.py）、Dream 蒸馏（dream.py）等 | ✅ 零第三方依赖，纯标准库 |
| `SKILL.md` / `_meta.json` / `skill-card.md` | skill 本体定义 | ✅ |
| `references/` | 反思框架等参考资料 | ✅ |
| `hooks/openclaw/handler.js` | 网关启动钩子 | ❌ **坏的，见第二节** |

> 注意：仓库只同步**代码**，不同步 `memory/` 运行数据（`.learning-trail.json`、
> `agents/registry.json`、`agents/bus.json` 等）。每台机器各建各的，互不共享。

---

## 二、hooks 目录为什么是坏的（重要）

`hooks/openclaw/handler.js` 开头引用了三个文件：

```
../../runtime-CChwgwyg.js
../../subsystem-DwIxKdWw.js
../../agent-scope-Df_s1jDI.js
```

这三个文件**不是 skill 自带的**，是安装时 OpenClaw 从主程序内联进来、
且文件名带**机器相关 hash** 的编译产物。它们在本仓库里不存在。

- 我的机器能用，是因为当初安装时编译进了本地 OpenClaw 主程序
- **另一台机器 hash 不同，handler.js 拉过去必然加载失败**，可能拖慢/阻断网关启动

### 处理方式（二选一）

**方式 A：忽略/删除 hooks（推荐，最快）**

```bash
rm -rf skills/self-improvement-llm/hooks
```

脚本和 skill 本体完全不受影响，只是少了"网关启动时自动写 .hook-context.txt"这个便利。
学习引擎、Learning Bus、多 Agent 上报全部照常工作。

**方式 B：在新机器上重新走官方安装，让 OpenClaw 重新编译 hook**

`_meta.json` 里有 `ownerId` + `slug`，可以用 clawhub 官方安装流程重装：

```bash
# 视你的 OpenClaw 版本而定，例如：
openclaw skills install self-improvement-llm
# 或把仓库里 hooks/ 删掉后，用 skill 发布流程重新打包编译
```

---

## 三、最小启动步骤（新机器）

```bash
# 1. 把 skill 放到主工作区 skills/ 下
mkdir -p ~/.openclaw/workspace/skills
cp -r skills/self-improvement-llm ~/.openclaw/workspace/skills/

# 2. 初始化 memory 结构（脚本会自动建目录和默认数据）
cd ~/.openclaw/workspace/skills/self-improvement-llm
python3 scripts/learn.py --build-index      # 建记忆索引
python3 scripts/learn.py --status           # 确认能跑

# 3. 验证 Learning Bus 可用
python3 scripts/bus.py --status

# 4. 跑一次完整学习循环（含 Phase 0 聚合中央 Bus）
python3 scripts/learn.py --cycle
```

`learn.py` 的路径解析：优先读环境变量 `OPENCLAW_WORKSPACE` / `OPENCLAW_WORKSPACE_DIR`，
都没有则用 `~/.openclaw/workspace`。**不硬编码具体机器路径**，所以换机器照常。

---

## 四、启用多 Agent 上报（厂长/财神等）

核心思路：**不给每个 Agent 装一套 skill**，而是共享同一份代码 + 统一写中央 Bus。

### 4.1 共享代码（symlink，沿用工作区惯例）

```bash
# 假设主工作区已装好 self-improvement-llm
for w in 厂长 财神; do
  ln -s ~/.openclaw/workspace/skills/self-improvement-llm \
        ~/.openclaw/workspace-$w/skills/self-improvement-llm
done
```

### 4.2 上报走中央 Bus（关键：--central）

各 Agent 上报时必须带 `--central`，强制写主工作区的中央 Bus：

```bash
cd ~/.openclaw/workspace-厂长
python3 skills/self-improvement-llm/scripts/bus.py --central \
  --topic "报价引擎" \
  --content "材料价波动超3%必须重新取价再报价" \
  --scope AGENT --agent 厂长 --confidence 85
```

- `--central` 会把事件写入 `~/.openclaw/workspace/memory/agents/bus.json`（单一事实源）
- 不带 `--central` 会写各 Agent 自己的工作区，中央引擎看不到，等于白报
- scope 可选：TASK | AGENT | PROJECT | USER | GLOBAL，默认 AGENT

### 4.3 给每个 Agent 的 AGENTS.md 加上报 Hook

在 `workspace-厂长/AGENTS.md`、`workspace-财神/AGENTS.md` 里加一段：
任务收尾/踩坑/验证经验后，用上面 4.2 的命令上报。只报有验证价值的经验，
避免刷屏污染全局学习。

### 4.4 全局学习引擎自动聚合

`learn.py --cycle` 内置 **Phase 0: Aggregate Learning Bus**，会自动：
读取中央 Bus → 去重 → 写入 learning trail（source=external 初始不信任，防记忆污染）→ 事件标记 resolved。

1:00 定时任务（cron）直接跑 `--cycle` 即可，**不需要单独改 cron**。

---

## 五、日常使用速查

```bash
# 学习引擎
python3 scripts/learn.py --cycle            # 完整学习循环（含 Bus 聚合）
python3 scripts/learn.py --status           # 学习统计
python3 scripts/learn.py --build-index      # 重建记忆索引
python3 scripts/learn.py --promote          # 检查可晋升模式

# Learning Bus
python3 scripts/bus.py --status             # 总线状态（pending/resolved）
python3 scripts/bus.py --pending            # 待处理事件
python3 scripts/bus.py --central --status   # 中央 Bus 状态（多 Agent 场景必带 --central）

# Agent 注册
python3 scripts/agents.py --list            # 列出所有 Agent 工作区
python3 scripts/agents.py --status          # 各 Agent 状态
```

---

## 六、已知边界与提醒

1. **hooks 不跨机器**：不要指望 handler.js 直接搬，重装或删除（见第二节）。
2. **运行数据不共享**：memory/ 状态（trail、registry、bus）各机器独立，别误提交。
3. **source=external 初始不信任**：Bus 上报的经验默认 `trusted=False`，这是防记忆污染的
   设计，不是 bug。验证后（重复出现 / 用户确认）会自然晋升。
4. **没有流量先别堆架构**：先让各 Agent 真实上报几周，看中央 Bus 有没有有效内容，
   再决定要不要加 Registry 元数据（last_scan / pending_events 等）。
5. **版本一致性**：改动 `bus.py --central` / `learn.py Phase 0` 等核心逻辑后，
   记得同步回本仓库，避免多台机器逻辑分叉。
