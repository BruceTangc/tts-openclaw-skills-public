---
name: tavily-web-search
description: Tavily Web Search - Full-featured Tavily API integration with auto-update from official docs
author: brucetangc
version: 1.0.0
homepage: https://tavily.com
triggers:
  - "搜索"
  - "查找"
  - "提取"
  - "爬取"
  - "研究"
  - "tavily"
metadata: {"clawdbot":{"emoji":"🔍","requires":{"bins":["node"],"npm":["node-fetch"]},"config":{"env":{"TAVILY_API_KEY":{"description":"Tavily API Key","default":"tvly-dev-xxx","required":false}}}}}
---

# Tavily Web Search

完整的 Tavily API 集成，支持网页搜索、内容提取、用量查询等功能。

## 功能列表

| 功能 | 状态 | 说明 |
|------|------|------|
| 🔍 `search` | ✅ 启用 | 网页搜索 |
| 📄 `extract` | ✅ 启用 | 内容提取 |
| 📊 `usage` | ✅ 启用 | 用量查询 |
| 🕷️ `crawl` | ⏸️ 禁用 | 整站爬取 |
| 🗺️ `map` | ⏸️ 禁用 | 站点地图 |
| 📖 `research` | ⏸️ 禁用 | 深度研究 |
| 📊 `research_status` | ⏸️ 禁用 | 研究状态查询 |

## 配置

编辑 `config/default.json`：

```json
{
  "api_key": "tvly-your-api-key",
  "commands": {
    "search": { "enabled": true },
    "extract": { "enabled": true },
    "usage": { "enabled": true }
  }
}
```

或使用环境变量：
```bash
export TAVILY_API_KEY="tvly-your-api-key"
```

## 使用示例

### 搜索
```javascript
tavily("OpenClaw 文档")
tavily({ command: "search", query: "AI 发展趋势", max_results: 10 })
```

### 提取网页内容
```javascript
tavily({ 
  command: "extract", 
  urls: ["https://docs.openclaw.ai"],
  format: "markdown"
})
```

### 查看用量
```javascript
tavily({ command: "usage" })
```

## 自动更新

本 Skill 支持从 Tavily 官方文档自动更新：

```bash
# 检查更新
npm run check-updates

# 应用更新
npm run update
```

更新内容：
- API 参数同步
- 配置更新
- 代码优化

## 参数说明

### Search
- `query` - 搜索关键词（必填）
- `search_depth` - 搜索深度：basic/advanced/fast/ultra-fast
- `max_results` - 结果数量（0-20）
- `topic` - 主题：general/news/finance
- `time_range` - 时间范围：day/week/month/year
- `include_answer` - 包含 AI 答案
- `include_raw_content` - 包含原始内容

### Extract
- `urls` - URL 列表（必填，最多 20 个）
- `extract_depth` - 提取深度：basic/advanced
- `format` - 输出格式：markdown/text
- `query` - 用于 rerank 的意图

## 错误处理

所有错误都会返回友好的错误信息：
```
❌ **search 失败**

Tavily API Error: 详细错误信息
```

## 更新日志

### v1.0.0 (2026-04-05)
- 初始版本
- 支持 search、extract、usage
- 实现 crawl、map、research（禁用）
- 支持自动更新
