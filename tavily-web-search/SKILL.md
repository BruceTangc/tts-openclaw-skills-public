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
metadata: {"clawdbot":{"emoji":"🔍","requires":{"bins":["node"],"npm":["node-fetch"]},"config":{"env":{"TAVILY_API_KEY":{"description":"Tavily API Key — 从 https://tavily.com 获取","required":true}}}}}
---

# Tavily Web Search

> ⚠️ **需要 API Key**：本 Skill 依赖 Tavily API。
> - 获取地址：https://tavily.com
> - 设置方式：**只通过环境变量**设置，config 文件中不存储 Key

完整的 Tavily API 集成，支持网页搜索、内容提取、用量查询等功能。

## 功能列表

| 功能 | 状态 | 说明 |
|------|------|------|
| 🔍 `search` | ✅ 启用 | 网页搜索 |
| 📄 `extract` | ✅ 启用 | 内容提取 |
| 📊 `usage` | ✅ 启用 | 用量查询 |
| 🕷️ `crawl` | ⏸️ 已实现未启用 | 整站爬取 |
| 🗺️ `map` | ⏸️ 已实现未启用 | 站点地图 |
| 📖 `research` | ⏸️ 已实现未启用 | 深度研究 |
| 📊 `research_status` | ⏸️ 已实现未启用 | 研究状态查询 |

## 配置

API Key 只通过环境变量设置：

```bash
export TAVILY_API_KEY="你的 key"
```

> ⚠️ 不要将 API Key 写入任何 config 文件，防止意外上传到公开仓库。

## 使用示例

### CLI 方式（推荐，路径无关）
```bash
# 搜索
node scripts/tavily.js search "AI Agent 进展"

# 搜索（带参数）
node scripts/tavily.js search "油价" --topic news --time-range week --answer advanced
node scripts/tavily.js search "AI" --images --favicon --max-results 3
node scripts/tavily.js search "敏感内容" --safe-search --depth basic

# 提取网页
node scripts/tavily.js extract https://example.com

# 查看用量
node scripts/tavily.js usage

# 帮助
node scripts/tavily.js --help
```
> 💡 CLI 脚本通过 `__dirname` 定位依赖，从任意目录调用均可正常工作。

### JS 方式
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
  - basic/fast/ultra-fast: 1 credit；advanced: 2 credits
- `max_results` - 结果数量（0-20）
- `topic` - 主题：general/news/finance
- `time_range` - 时间范围：day/week/month/year（或简写 d/w/m/y）
- `start_date` / `end_date` - 日期范围（YYYY-MM-DD）
- `include_answer` - AI 答案：true/false/"basic"/"advanced"
- `include_raw_content` - 原始内容：true/false/"markdown"/"text"
- `include_images` - 包含图片
- `include_image_descriptions` - 包含图片描述（需配合 include_images）
- `include_favicon` - 包含站点图标
- `include_domains` - 限定域名列表
- `exclude_domains` - 排除域名列表
- `country` - 国家（如 china、united states）
- `chunks_per_source` - 每源分块数 1-3（仅 advanced 深度有效）
- `auto_parameters` - 自动根据意图配置搜索参数
- `exact_match` - 精确匹配（查询中包含引号短语时绕过语义搜索）
- `safe_search` - 过滤成人/不安全内容（企业版）
- `include_usage` - 返回用量信息

### Extract
- `urls` - URL 列表（必填，最多 20 个）
- `extract_depth` - 提取深度：basic（1 credit/5 URL）/advanced（2 credits/5 URL）
- `format` - 输出格式：markdown/text
- `query` - 用于 rerank 的意图
- `chunks_per_source` - 分块数 1-5（需配合 query）
- `include_images` - 提取页面图片
- `include_favicon` - 包含站点图标
- `include_usage` - 包含本次用量信息
- `timeout` - 超时秒数（1-60）

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

### v1.1.0 (2026-05-26)
- 补齐全部官方 API 参数（exact_match、safe_search、include_usage、include_favicon、include_image_descriptions、auto_parameters、country）
- 增加参数校验（search_depth、topic、time_range、include_answer、include_raw_content 等）
- 增强 CLI（--images、--favicon、--usage、--country、--exact-match、--answer basic/advanced、--raw markdown/text）
- 修复 API 错误解析（支持 string/detail 两种格式）
- 修复 Retry-After 头解析（支持秒数和 HTTP-date）
- 增加缓存最大条目限制（防内存泄漏）
- 增加查询回显和用量显示
- 增加 safe_search 深度兼容性校验

### v1.2.0 (2026-05-26)
- 增加 finance topic 不支持 fast/ultra-fast 的校验
- 增加 fast/ultra-fast 不支持 include_raw_content 的校验
- 增加 country 仅在 topic=general 时有效的校验
- 代码重构：布尔值归一化抽取 coerceBool helper
- 移除内部 console.log 噪音（缓存命中、参数警告等）
