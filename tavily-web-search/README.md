# Tavily Web Search for OpenClaw

🔍 完整的 Tavily API 集成，支持网页搜索、内容提取、用量查询等功能。

## 特性

- ✅ **网页搜索** - AI 优化的实时搜索
- ✅ **内容提取** - 从 URL 提取清洁内容
- ✅ **用量查询** - 实时查看 API 使用情况
- ⏸️ **整站爬取** - 智能网站爬取（已实现，未启用）
- ⏸️ **站点地图** - 生成网站结构图（已实现，未启用）
- ⏸️ **深度研究** - 自动研究报告（已实现，未启用）
- 🔄 **自动更新** - 从官方文档同步最新 API

## 快速开始

### 1. 安装依赖

```bash
cd ~/.openclaw/workspace/skills/tavily-web-search
npm install
```

### 2. 配置 API Key

编辑 `config/default.json`：

```json
{
  "api_key": "tvly-your-api-key"
}
```

或使用环境变量：

```bash
export TAVILY_API_KEY="tvly-your-api-key"
```

### 3. 使用

```javascript
// 搜索
tavily("OpenClaw 文档")

// 提取网页
tavily({ 
  command: "extract", 
  urls: ["https://docs.openclaw.ai"] 
})

// 查看用量
tavily({ command: "usage" })
```

## 命令说明

### ✅ 已启用

| 命令 | 描述 | 示例 |
|------|------|------|
| `search` | 网页搜索 | `tavily("AI 发展趋势")` |
| `extract` | 内容提取 | `tavily({command:"extract",urls:["https://..."]})` |
| `usage` | 用量查询 | `tavily({command:"usage"})` |

### ⏸️ 已实现但未启用

| 命令 | 描述 | 启用方式 |
|------|------|---------|
| `crawl` | 整站爬取 | 修改 `config/default.json` |
| `map` | 站点地图 | 修改 `config/default.json` |
| `research` | 深度研究 | 修改 `config/default.json` |
| `research_status` | 研究状态 | 修改 `config/default.json` |

## 自动更新

```bash
# 检查更新
npm run check-updates

# 应用更新
npm run update
```

## 参数说明

### Search 参数

```javascript
{
  query: "搜索关键词",              // 必填
  search_depth: "basic",           // basic/advanced/fast/ultra-fast
  max_results: 5,                  // 0-20
  topic: "general",                // general/news/finance
  time_range: "week",              // day/week/month/year
  start_date: "2026-01-01",        // YYYY-MM-DD
  end_date: "2026-12-31",          // YYYY-MM-DD
  include_answer: true,            // AI 答案
  include_raw_content: "markdown", // markdown/text
  include_images: false,           // 图片
  include_domains: ["github.com"], // 限定域名
  exclude_domains: ["spam.com"],   // 排除域名
  country: "china",                // 国家
  chunks_per_source: 3             // 每源块数
}
```

### Extract 参数

```javascript
{
  urls: ["https://..."],           // 必填，最多 20 个
  query: "意图描述",                // 用于 rerank
  chunks_per_source: 3,            // 1-5
  extract_depth: "basic",          // basic/advanced
  format: "markdown",              // markdown/text
  include_images: false,           // 图片
  include_favicon: false,          // 网站图标
  timeout: 10                      // 1-60 秒
}
```

## 项目结构

```
tavily-web-search/
├── index.js                    # 主入口
├── package.json                # 依赖配置
├── config/
│   └── default.json            # 配置文件
├── commands/
│   ├── search.js               # 搜索
│   ├── extract.js              # 提取
│   ├── usage.js                # 用量
│   ├── crawl.js                # 爬取（禁用）
│   ├── map.js                  # 地图（禁用）
│   ├── research.js             # 研究（禁用）
│   └── research-status.js      # 研究状态（禁用）
├── utils/
│   ├── api.js                  # API 封装
│   └── formatter.js            # 格式化
└── scripts/
    ├── update-from-docs.js     # 自动更新
    └── check-updates.js        # 检查更新
```

## 开发

### 测试

```bash
# 测试搜索
node -e "const t=require('./index');t.handler('OpenClaw').then(console.log)"

# 测试提取
node -e "const t=require('./index');t.handler({command:'extract',urls:['https://...']}).then(console.log)"

# 测试用量
node -e "const t=require('./index');t.handler({command:'usage'}).then(console.log)"
```

### 添加新功能

1. 在 `commands/` 创建新文件
2. 在 `index.js` 导入并注册
3. 在 `config/default.json` 配置启用状态
4. 在 `utils/api.js` 添加 API 方法

## 注意事项

- ⚠️ API Key 请妥善保管，不要提交到版本控制
- ⚠️ 企业级功能（Key 管理）需要 Enterprise 计划
- ⚠️ 部分功能有速率限制，请注意使用频率

## 许可证

MIT-0

## 作者

brucetangc

## 更新日志

### v1.0.0 (2026-04-05)
- 初始版本
- 支持 search、extract、usage
- 实现 crawl、map、research（禁用）
- 支持自动更新从官方文档
