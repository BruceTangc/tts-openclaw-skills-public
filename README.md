# Memory System Skill

🧠 高效记忆系统 - 整合 GitHub 热门项目最佳实践

## 安装

此技能已内置于工作区，无需额外安装。

## 使用

```bash
# 查看状态
memory-system status

# 读取记忆
memory-system read --type long
memory-system read --type daily --date 2026-04-08

# 写入记忆
memory-system write --type daily --content "今天学习了记忆系统"

# 搜索
memory-system search --query "关键词"

# 提炼
memory-system promote --apply --limit 5

# 维护
memory-system repair
memory-system export --output /tmp/memory.md
memory-system stats
```

## 文件结构

```
skills/memory-system/
├── index.js       # 核心逻辑
├── SKILL.md       # 技能配置
└── README.md      # 本文件
```

## 特性

- ✅ Markdown 文件系统（OpenClaw）
- ✅ 双层记忆结构（长期 + 日常）
- ✅ 全文搜索（engram）
- ✅ 自动提炼（MemMachine）
- ✅ 自修复（724-office）
- ✅ 导出备份（memsearch）

## 参考项目

- OpenClaw (351K⭐)
- OpenViking (21.6K⭐)
- MemMachine (5.4K⭐)
- engram (2.3K⭐)
- memsearch (1.1K⭐)
- 724-office (1.2K⭐)

## License

MIT
