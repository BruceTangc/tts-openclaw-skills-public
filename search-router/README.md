# Search Router - 智能搜索路由

🔀 根据查询类型自动选择最佳搜索引擎（Tavily / SearXNG / 两者）

## 快速开始

```javascript
// 智能搜索（自动路由）
search("OpenClaw 安装教程")

// 查看帮助
search.help()
```

## 功能特性

- 🧠 **智能分类** - 自动识别查询类型
- 🔀 **自动路由** - 选择最佳引擎
- 🔄 **双引擎模式** - 合并结果
- 🎯 **去重排序** - 智能去重
- ⚡ **快速响应** - 并行搜索

## 路由规则

| 查询类型 | 关键词 | 使用引擎 |
|---------|--------|---------|
| 实时信息 | 最新、刚刚、现在 | SearXNG |
| 新闻 | 新闻、报道、媒体 | SearXNG |
| 技术 | 教程、文档、API、代码 | Tavily |
| 研究 | 研究、分析、报告 | Tavily |
| 通用 | 无明确倾向 | 双引擎 |

## 使用示例

```javascript
// 自动路由
search("Python 教程")  // → Tavily
search("最新科技新闻")  // → SearXNG
search("人工智能")      // → 双引擎

// 指定引擎
search({ query: "AI", engine: "tavily" })
search({ query: "新闻", engine: "searxng" })
search({ query: "综合", engine: "both" })
```

## 配置

编辑 `config/default.json` 配置 API Key 和引擎：

```json
{
  "tavily": {
    "enabled": true,
    "api_key": "tvly-your-api-key"
  },
  "searxng": {
    "enabled": true,
    "url": "http://localhost:8080"
  }
}
```

## 测试

```bash
# 验证配置
npm run validate

# 运行测试
npm run test
```

## 依赖

- Node.js
- Python 3 (SearXNG)
- Tavily API Key
- SearXNG 实例

## 许可证

MIT-0

## 作者

brucetangc
