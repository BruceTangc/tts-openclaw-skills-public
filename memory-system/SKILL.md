---
name: memory-system
description: OpenClaw 记忆系统 - 整合 GitHub 20K+ Stars 最佳实践 + DeepSeek 向量搜索
author: brucetangc
version: 1.1.0
homepage: https://github.com/openclaw/openclaw
triggers:
  - "记忆"
  - "memory"
  - "MEMORY"
  - "回忆"
  - "搜索记忆"
  - "写入记忆"
  - "dreaming"
  - "梦境"
metadata: {
  "clawdbot": {
    "emoji": "🧠",
    "requires": {
      "bins": ["bash", "git"]
    },
    "config": {
      "env": {
        "MEMORY_WORKSPACE": {
          "description": "记忆工作区路径（可选）",
          "default": "",
          "required": false
        },
        "DEEPSEEK_API_KEY": {
          "description": "DeepSeek API Key（用于向量搜索，可选）",
          "default": "",
          "required": false
        }
      }
    }
  }
}
---

# 🧠 Memory System - 记忆系统

整合 GitHub 20K+ Stars 记忆系统最佳实践 + DeepSeek 向量搜索。

## 功能列表

| 功能 | 状态 | 说明 |
|------|------|------|
| 📊 `status` | ✅ 启用 | 查看记忆系统状态 |
| 📖 `read` | ✅ 启用 | 读取记忆（日常/长期） |
| ✍️ `write` | ✅ 启用 | 写入记忆 |
| 🔍 `search` | ✅ 启用 | 搜索记忆（关键词/向量） |
| 🎯 `promote` | ✅ 启用 | 提炼记忆到长期记忆 |
| 🔧 `repair` | ✅ 启用 | 修复记忆系统 |
| 📤 `export` | ✅ 启用 | 导出记忆 |
| 📈 `stats` | ✅ 启用 | 记忆统计 |
| 💭 `dreaming` | ✅ 启用 | 梦境整理（自动提炼） |

## 快速开始

### 查看状态
```javascript
memory-system({ command: "status" })
```

### 写入记忆
```javascript
// 写入日常记忆
memory-system({
  command: "write",
  type: "daily",
  content: "今天学习了记忆系统架构",
  mode: "append"
})

// 写入长期记忆
memory-system({
  command: "write",
  type: "longterm",
  content: "用户偏好：默认使用简体中文回复",
  mode: "prepend"
})
```

### 读取记忆
```javascript
// 读取今天的日常记忆
memory-system({
  command: "read",
  type: "daily",
  date: "2026-04-09"
})

// 读取长期记忆
memory-system({ command: "read", type: "longterm" })
```

### 搜索记忆
```javascript
// 关键词搜索
memory-system({
  command: "search",
  query: "用户偏好",
  limit: 5
})

// 向量搜索（需要 DeepSeek API）
memory-system({
  command: "search",
  query: "用户喜欢什么语言",
  limit: 5,
  vector: true
})
```

### 提炼记忆
```javascript
// 从日常记忆提炼到长期记忆
memory-system({
  command: "promote",
  apply: true,
  limit: 5
})
```

### 梦境整理
```javascript
// 自动整理日常记忆到长期记忆
memory-system({
  command: "dreaming",
  action: "run",
  phase: "all"
})
```

## 参数说明

### Write
- `type` - 记忆类型：`daily`（日常）/ `longterm`（长期）
- `content` - 记忆内容（必填）
- `mode` - 写入模式：`append`（追加）/ `prepend`（前置）/ `overwrite`（覆盖）

### Read
- `type` - 记忆类型：`daily` / `longterm`
- `date` - 日期（仅 daily 需要）：`YYYY-MM-DD` 格式
- `limit` - 返回数量限制

### Search
- `query` - 搜索关键词（必填）
- `limit` - 返回数量限制（默认 5）
- `vector` - 是否使用向量搜索（需要 DeepSeek API）

### Promote
- `apply` - 是否直接应用提炼结果
- `limit` - 处理的日常记忆数量

### Dreaming
- `action` - 操作：`run`（执行）/ `preview`（预览）
- `phase` - 阶段：`all`（全部）/ `analyze`（分析）/ `promote`（提炼）

## 记忆结构

```
workspace/
├── memory/
│   ├── YYYY-MM-DD.md    # 日常记忆（每天一个文件）
│   └── ...
└── MEMORY.md            # 长期记忆（单一文件）
```

### 日常记忆 (memory/YYYY-MM-DD.md)
- 记录当天的具体事件、对话、操作
- 每天自动创建新文件
- 适合记录临时性、细节性信息

### 长期记忆 (MEMORY.md)
-  curated 的长期知识、偏好、决策
- 手动或自动从日常记忆提炼
- 适合记录持久性、重要性信息

## 备份脚本

### GitHub 备份
```bash
./scripts/backup-to-github.sh
```

### 阿里云备份
```bash
./scripts/backup-to-aliyun.sh
```

### 混合备份（推荐）
```bash
./scripts/backup-hybrid.sh
```

### 自动备份设置
```bash
# 添加到 crontab
0 2 * * * /path/to/backup-hybrid.sh
```

## 完整示例

### 会话启动时读取记忆
```javascript
// 1. 读取今天的日常记忆
const todayMemory = memory-system({
  command: "read",
  type: "daily",
  date: "2026-04-09"
});

// 2. 读取长期记忆
const longtermMemory = memory-system({
  command: "read",
  type: "longterm"
});

// 3. 合并上下文
const context = {
  today: todayMemory,
  longterm: longtermMemory
};
```

### 会话结束时写入记忆
```javascript
// 写入重要事件到日常记忆
memory-system({
  command: "write",
  type: "daily",
  content: "帮助用户发布了 excel-generator skill 到公开仓库",
  mode: "append"
});

// 写入用户偏好到长期记忆
memory-system({
  command: "write",
  type: "longterm",
  content: "用户偏好：技能发布到 GitHub 公开仓库",
  mode: "prepend"
});
```

### 定期梦境整理
```javascript
// 每天凌晨 2 点执行
memory-system({
  command: "dreaming",
  action: "run",
  phase: "all"
});
```

## 更新日志

### v1.1.0 (2026-04-08)
- 整合 GitHub 20K+ Stars 记忆系统最佳实践
- 支持 DeepSeek 向量搜索
- 添加完整的备份脚本（GitHub/Aliyun/混合）
- 支持 dreaming 梦境整理功能
- 实现记忆提炼（promote）功能

### v1.0.0 (2026-04-01)
- 初始版本
- 基础记忆读写功能
- 日常记忆和长期记忆分离
