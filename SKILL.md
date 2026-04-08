---
name: memory-system
description: 高效记忆系统 - 整合 GitHub 热门项目最佳实践 + Dreaming 梦境整理
author: brucetangc
version: 1.1.0
metadata: {"emoji":"🧠","requires":{"bins":["node"]}}
---

# Memory System - 高效记忆系统

🧠 整合 GitHub 20K+ Stars 记忆系统最佳实践的 OpenClaw 技能

**参考项目：**
- OpenClaw (351K⭐) - Markdown 文件系统
- OpenViking (21.6K⭐) - L0/L1/L2 分层加载
- MemMachine (5.4K⭐) - 三层记忆架构
- engram (2.3K⭐) - SQLite+FTS5 全文搜索
- memsearch (1.1K⭐) - Markdown 优先
- 724-office (1.2K⭐) - 自修复机制

**新增功能：**
- 🌙 Dreaming 梦境整理 (OpenClaw 官方)
- 🔍 嵌入提供商状态检测
- 📊 Dreaming 三阶段支持

---

## 🚀 快速开始

### 查看状态
```
memory-system status
```

### Dreaming 梦境整理
```
# 查看 Dreaming 状态
memory-system dreaming --action status

# 启用 Dreaming
memory-system dreaming --action enable

# 运行梦境整理
memory-system dreaming --action run --phase light
memory-system dreaming --action run --phase rem
memory-system dreaming --action run --phase deep
memory-system dreaming --action run --phase all
```

### 读取记忆
```
# 读取长期记忆
memory-system read --type long

# 读取今日记录
memory-system read --type daily

# 读取指定日期
memory-system read --type daily --date 2026-04-08
```

### 写入记忆
```
# 写入长期记忆
memory-system write --type long --content "用户偏好简体中文"

# 写入日常记录
memory-system write --type daily --content "今天学习了记忆系统"
```

### 搜索记忆
```
memory-system search --query "SearXNG" --limit 10
```

### 提炼记忆
```
# 预览候选
memory-system promote --limit 5

# 应用提炼
memory-system promote --apply --limit 5
```

### 维护
```
# 修复系统
memory-system repair

# 修复并清理过期记录
memory-system repair --cleanOld true

# 导出记忆
memory-system export --format markdown --output /tmp/memory-export.md

# 查看统计
memory-system stats
```

---

## 📋 完整命令

| 命令 | 参数 | 说明 |
|------|------|------|
| `status` | - | 查看记忆系统状态 |
| `read` | `type`, `date` | 读取记忆 |
| `write` | `type`, `content`, `mode` | 写入记忆 |
| `search` | `query`, `limit` | 搜索记忆（全文） |
| `promote` | `apply`, `limit` | 提炼日常记录到长期记忆 |
| `repair` | `cleanOld` | 修复记忆系统 |
| `export` | `format`, `output` | 导出记忆 |
| `stats` | - | 记忆统计 |
| `dreaming` | `action`, `phase` | Dreaming 梦境整理 🌙 |

### Dreaming 参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `action` | `status` | 查看 Dreaming 状态 |
| `action` | `enable` | 启用 Dreaming（创建 DREAMS.md） |
| `action` | `run` | 运行梦境整理 |
| `phase` | `light` | Light 阶段：快速扫描 |
| `phase` | `rem` | REM 阶段：深度关联 |
| `phase` | `deep` | Deep 阶段：生成摘要 |
| `phase` | `all` | 运行全部阶段 |

---

## 📁 文件结构

```
~/.openclaw/workspace/
├── MEMORY.md              # 长期记忆
└── memory/
    ├── YYYY-MM-DD.md      # 日常记录
    └── ...
```

---

## 🎯 核心特性

### ✅ 已实现

| 特性 | 来源 | 说明 |
|------|------|------|
| Markdown 文件系统 | OpenClaw | 人类可读，版本控制友好 |
| 双层记忆结构 | OpenClaw | 长期 + 日常 |
| 全文搜索 | engram | grep 实现，快速搜索 |
| 自动提炼 | MemMachine | 从日常记录提炼到长期记忆 |
| 自修复 | 724-office | 自动创建缺失文件 |
| 导出功能 | memsearch | Markdown 格式导出 |
| 统计分析 | - | 行数、大小统计 |

### ⚡ 可选增强

| 增强 | 说明 | 实现方式 |
|------|------|----------|
| 向量搜索 | 语义搜索 | 配置嵌入提供商 API Key |
| L0/L1/L2 分层 | OpenViking | 按需加载，节省 Token |
| SQLite 后端 | engram | 更强大的查询能力 |
| MCP 协议 | engram | 跨代理支持 |

---

## 💡 使用示例

### 示例 1：记录用户偏好
```
memory-system write --type long --content "### 🧠 用户偏好\n\n- 语言：简体中文\n- 搜索：优先 SearXNG\n- 交互：简洁直接"
```

### 示例 2：记录日常对话
```
memory-system write --type daily --content "用户询问了 n8n 部署方案，最终选择 Docker 方式"
```

### 示例 3：搜索历史
```
memory-system search --query "n8n" --limit 5
```

### 示例 4：每周提炼
```
# 每周执行一次，提炼重要内容到长期记忆
memory-system promote --apply --limit 5
```

### 示例 5：备份记忆
```
memory-system export --format markdown --output ~/backup/memory-$(date +%Y%m%d).md
```

---

## 🔧 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WORKSPACE` | `~/.openclaw/workspace` | 工作目录 |

### 可选配置

编辑 `~/.openclaw/workspace/memory.config.json`：

```json
{
  "memory": {
    "backend": "builtin",
    "sources": ["MEMORY.md", "memory/*.md"],
    "cache": {
      "enabled": true,
      "maxSize": 1000,
      "ttl": 3600
    },
    "index": {
      "autoReindex": true,
      "dirtyThreshold": 10
    }
  }
}
```

---

## 📊 记忆架构

```
┌─────────────────────────────────────┐
│         长期记忆 (MEMORY.md)         │
│  - 个人偏好                          │
│  - 项目上下文                        │
│  - 重要决策                          │
│  - 技能清单                          │
└─────────────────────────────────────┘
                ↑
                │ promote (自动提炼)
                ↓
┌─────────────────────────────────────┐
│       日常记录 (memory/*.md)         │
│  - 每日完成                          │
│  - 学到的东西                        │
│  - 重要对话                          │
│  - 待跟进事项                        │
└─────────────────────────────────────┘
```

---

## 🚀 性能优化

### 当前性能

| 指标 | 值 |
|------|-----|
| 搜索速度 | ~10ms (全文搜索) |
| 文件大小 | ~1-5 KB (MEMORY.md) |
| 日常记录 | ~100-500 行/天 |
| 索引 | 自动 |

### 优化建议

1. **启用向量搜索** - 配置嵌入提供商 API Key
2. **定期清理** - 每月清理超过 30 天的记录
3. **定期提炼** - 每周提炼重要内容到长期记忆
4. **定期导出** - 每月导出备份

---

## 🔐 安全建议

- ✅ 不存储密码、完整 API Key
- ✅ 敏感配置使用环境变量
- ✅ 定期备份记忆文件
- ✅ 使用版本控制（Git）

---

## 📚 参考资源

- [OpenClaw 官方文档](https://docs.openclaw.ai/concepts/memory)
- [OpenViking](https://github.com/volcengine/OpenViking) - 上下文数据库
- [MemMachine](https://github.com/MemMachine/MemMachine) - 三层记忆
- [engram](https://github.com/Gentleman-Programming/engram) - 持久记忆
- [memsearch](https://github.com/zilliztech/memsearch) - Markdown 记忆

---

## 🐛 常见问题

### Q: 记忆文件在哪里？
A: `~/.openclaw/workspace/MEMORY.md` 和 `~/.openclaw/workspace/memory/`

### Q: 如何备份记忆？
A: 使用 `memory-system export` 导出，或直接复制文件

### Q: 如何清理过期记录？
A: `memory-system repair --cleanOld true`

### Q: 支持向量搜索吗？
A: 需要配置嵌入提供商 API Key，当前使用全文搜索

---

*最后更新：2026-04-08*
*版本：1.0.0*
