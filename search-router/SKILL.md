---
name: search-router
description: Smart Search Router - Intelligently route searches between Tavily and SearXNG based on query type
author: brucetangc
version: 1.0.0
homepage: https://github.com/brucetangc
triggers:
  - "搜索"
  - "查找"
  - "search"
  - "查询"
metadata: {"clawdbot":{"emoji":"🔀","requires":{"bins":["node","python3"]},"config":{"env":{"TAVILY_API_KEY":{"description":"Tavily API Key","default":"","required":false},"SEARXNG_URL":{"description":"SearXNG URL","default":"http://localhost:8080","required":false}}}}}
---

# Search Router - 智能搜索路由

🔀 根据查询类型自动选择最佳搜索引擎（Tavily / SearXNG / 两者）

## 功能特性

- 🧠 **智能分类** - 自动识别查询类型（实时/新闻/技术/研究/通用）
- 🔀 **自动路由** - 根据查询类型选择最佳引擎
- 🔄 **双引擎模式** - 同时使用两个引擎，合并结果
- 🎯 **去重排序** - 智能去重，按相关度排序
- ⚡ **快速响应** - 并行搜索，超时保护

## 路由策略

| 查询类型 | 关键词示例 | 使用引擎 | 原因 |
|---------|-----------|---------|------|
| 🔴 实时信息 | 最新、刚刚、现在、today | SearXNG | 提供更新的搜索结果 |
| 📰 新闻 | 新闻、报道、媒体、headline | SearXNG | 聚合多个新闻源 |
| 💻 技术 | 教程、文档、API、代码、github | Tavily | 更适合技术内容 |
| 📖 研究 | 研究、分析、报告、论文、趋势 | Tavily | 提供 AI 答案和深度内容 |
| 🔍 通用 | 无明确倾向 | 双引擎 | 获得更全面的结果 |

## 使用示例

### 自动路由（推荐）

```javascript
// 技术搜索 → 自动使用 Tavily
search("OpenClaw 安装教程")

// 新闻搜索 → 自动使用 SearXNG
search("最新 AI 新闻")

// 通用搜索 → 自动使用双引擎
search("人工智能发展")
```

### 指定引擎

```javascript
// 强制使用 Tavily
search({ query: "OpenClaw", engine: "tavily" })

// 强制使用 SearXNG
search({ query: "科技新闻", engine: "searxng" })

// 使用双引擎
search({ query: "综合搜索", engine: "both" })
```

### 带参数搜索

```javascript
search({
  query: "AI 框架对比",
  engine: "auto",  // auto/tavily/searxng/both
  max_results: 10,
  show_routing: true  // 显示路由决策过程
})
```

## 配置

编辑 `config/default.json`：

```json
{
  "tavily": {
    "enabled": true,
    "api_key": "tvly-your-api-key"
  },
  "searxng": {
    "enabled": true,
    "url": "http://localhost:8080"
  },
  "routing": {
    "mode": "auto",
    "default_strategy": "auto"
  }
}
```

## 输出示例

```
🔀 **智能路由决策**

**查询类型**: technical
**置信度**: 80.0%
**使用引擎**: 🔍 Tavily
**总耗时**: 2345ms

**决策原因**:
- 检测到技术/开发相关内容
- Tavily 更适合技术文档和代码搜索
- 匹配关键词类型：technical

───────────────────────────────────────

📊 **搜索结果** (共 5 条)
   - 🔍 Tavily: 5 条
   - 🌐 SearXNG: 0 条

**1. OpenClaw Tutorial**
   链接：https://...
   摘要：...
```

## 命令

| 命令 | 描述 |
|------|------|
| `search(query)` | 智能搜索（自动路由） |
| `search({query, engine})` | 指定引擎搜索 |
| `help()` | 查看帮助 |
| `version()` | 版本信息 |

## 依赖

- Node.js
- Python 3 (用于 SearXNG)
- Tavily API Key
- SearXNG 实例

## 优势

### Tavily 优势
- ✅ AI 优化的搜索结果
- ✅ 提供 AI 答案
- ✅ 适合技术内容
- ✅ 支持深度研究
- ✅ 内容提取功能

### SearXNG 优势
- ✅ 隐私保护
- ✅ 多引擎聚合
- ✅ 实时性更好
- ✅ 无 API 限制
- ✅ 可自定义

### 组合优势
- 🎯 自动选择最佳引擎
- 🔄 双引擎互补
- 📊 更全面的结果
- ⚡ 并行搜索更快

## 更新日志

### v1.0.0 (2026-04-05)
- 初始版本
- 智能查询分类
- 自动路由功能
- 双引擎支持
- 结果合并去重
