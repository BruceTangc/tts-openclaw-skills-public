# 🧠 OpenClaw 记忆系统 Skill v1.1.0

> 整合 GitHub 20K+ Stars 记忆系统最佳实践 + DeepSeek 向量搜索

**版本：** 1.1.0 (DeepSeek)  
**作者：** brucetangc  
**创建时间：** 2026-04-08

---

## 🚀 快速开始

### 安装
```bash
# Skill 已内置于工作区
cd /home/admin/.openclaw/workspace/skills/memory-system
```

### 使用
```bash
# 查看状态
memory-system status

# 写入记忆
memory-system write --type daily --content "今天学习了记忆系统"

# 搜索记忆
memory-system search --query "关键词"

# 提炼记忆
memory-system promote --apply --limit 5

# 建立记忆索引（新增）
memory-system index              # 普通索引
memory-system index --force true # 强制重新索引

# Dreaming 梦境整理
memory-system dreaming --action run --phase all
```

---

## 📋 完整命令

| 命令 | 参数 | 说明 |
|------|------|------|
| `status` | - | 查看记忆系统状态 |
| `read` | `type`, `date` | 读取记忆 |
| `write` | `type`, `content`, `mode` | 写入记忆 |
| `search` | `query`, `limit` | 搜索记忆 |
| `promote` | `apply`, `limit` | 提炼记忆 |
| `repair` | `cleanOld` | 修复系统 |
| `export` | `format`, `output` | 导出记忆 |
| `stats` | - | 记忆统计 |
| `dreaming` | `action`, `phase` | Dreaming 梦境整理 |
| `index` | `force` | **建立记忆索引** ⭐ |

---

## 🎯 核心特性

### ✅ 已实现

| 特性 | 来源 | 说明 |
|------|------|------|
| Markdown 文件系统 | OpenClaw | 人类可读，版本控制 |
| 双层记忆结构 | OpenClaw | 长期 + 日常 |
| 全文搜索 | engram | grep 实现 |
| 自动提炼 | MemMachine | 日常→长期记忆 |
| 自修复 | 724-office | 自动创建缺失文件 |
| 导出备份 | memsearch | Markdown 导出 |
| Dreaming | OpenClaw | Light→REM→Deep 三阶段 |

### ⚡ 配置

**对话模型：** qwen3.5-plus（通义千问）  
**向量搜索：** deepseek-embed（DeepSeek）  
**API Key：** sk-edec198608534518a530012a1434498d

---

## 📁 文件结构

```
memory-system/
├── index.js              # 核心逻辑（21KB）
├── README.md             # 本文件
├── scripts/              # 备份脚本（5 个）
└── tavily-web-search/    # Tavily 搜索 Skill
```

---

## 🔧 备份脚本

| 脚本 | 用途 |
|------|------|
| `backup-memory.sh` | 本地备份 |
| `backup-to-github.sh` | GitHub 备份 |
| `backup-to-aliyun.sh` | 阿里云盘备份 |
| `backup-hybrid.sh` | 混合备份 |
| `setup-github-repo.sh` | GitHub 配置 |

---

## 📝 使用示例

### 1. 查看状态
```bash
memory-system status
```

### 2. 写入日常记录
```bash
memory-system write --type daily --content "今天完成了记忆系统配置"
```

### 3. 搜索记忆
```bash
memory-system search --query "记忆系统" --limit 10
```

### 4. 提炼记忆
```bash
memory-system promote --apply --limit 5
```

### 5. Dreaming 梦境整理
```bash
memory-system dreaming --action run --phase all
```

---

## 🌐 GitHub 仓库

### 私人仓库（记忆备份）
- **地址：** https://github.com/brucetangc/tts-openclaw-skills-private
- **内容：** MEMORY.md + memory/
- **自动备份：** 每天凌晨 2:00

### 公开仓库（Skills）
- **地址：** https://github.com/brucetangc/tts-openclaw-skills-public
- **内容：** 记忆系统 Skill + tavily-web-search
- **手动更新**

---

## 📊 测试报告

**测试结果：** 8/8 通过 ✅

| 测试项 | 状态 |
|--------|------|
| status | ✅ |
| write | ✅ |
| search | ✅ |
| stats | ✅ |
| dreaming | ✅ |
| promote | ✅ |
| export | ✅ |
| repair | ✅ |

---

## ⚠️ 注意事项

1. **隐私保护：** 不存储密码、API Key
2. **定期备份：** 配置自动备份到 GitHub
3. **本地优先：** GitHub 是备份，本地是主要数据源

---

## 📚 参考项目

- OpenClaw (351K⭐)
- OpenViking (21.6K⭐)
- MemMachine (5.4K⭐)
- engram (2.3K⭐)
- memsearch (1.1K⭐)
- 724-office (1.2K⭐)

---

**最后更新：** 2026-04-08  
**版本：** 1.1.0 (DeepSeek)
