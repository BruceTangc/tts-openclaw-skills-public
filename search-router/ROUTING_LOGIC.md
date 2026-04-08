# Search Router - 智能路由逻辑详解

## 📊 整体架构图

```
用户查询
    │
    ▼
┌─────────────────────────────────────┐
│  1. 查询分类器 (Classifier)         │
│     - 关键词匹配                    │
│     - 意图识别                      │
│     - 置信度计算                    │
└─────────────────────────────────────┘
    │
    ├──────────────────────────────────┐
    ▼                                  ▼
┌─────────────────┐          ┌─────────────────┐
│ 查询类型        │          │ 路由策略        │
│ - realtime      │          │ - auto          │
│ - news          │          │ - tavily_only   │
│ - technical     │          │ - searxng_only  │
│ - research      │          │ - both          │
│ - general       │          └─────────────────┘
└─────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  2. 路由决策 (Router)               │
│     根据查询类型 → 选择引擎          │
└─────────────────────────────────────┘
    │
    ├──────────────┬──────────────┬──────────────┐
    ▼              ▼              ▼              ▼
┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
│Tavily  │   │SearXNG │   │ 两者  │   │ 回退  │
│ Adapter│   │ Adapter│   │ 并行  │   │ 逻辑  │
└────────┘   └────────┘   └────────┘   └────────┘
    │              │              │
    └──────────────┴──────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  3. 结果合并器 (Merger)             │
│     - 收集结果                      │
│     - 去重（基于 URL）              │
│     - 排序（按相关度）              │
│     - 格式化输出                    │
└─────────────────────────────────────┘
    │
    ▼
最终结果（带路由报告）
```

---

## 🔍 详细流程

### 步骤 1: 查询分类

```javascript
输入："OpenClaw 安装教程"

↓ 关键词扫描
- 实时关键词：0 个匹配
- 新闻关键词：0 个匹配
- 技术关键词：2 个匹配（"教程", "安装"）
- 研究关键词：0 个匹配

↓ 评分
technical: 4 分 (2 个关键词 × 2 分)
其他：0 分

↓ 决策
最高分 >= 2 分 → 确定为 technical 类型
置信度 = min(4/5, 1.0) = 80%

↓ 引擎映射
technical → Tavily

输出：{
  type: 'technical',
  engine: 'tavily',
  confidence: 0.8,
  scores: { technical: 4, realtime: 0, news: 0, research: 0 }
}
```

---

### 步骤 2: 路由决策

```javascript
输入：查询分类结果 + 配置策略

↓ 策略检查
strategy = config.routing.default_strategy

if strategy === 'auto':
  if classification.engine === 'both':
    engines = ['tavily', 'searxng']
  else:
    engines = [classification.engine]
else if strategy === 'tavily_only':
  engines = ['tavily']
else if strategy === 'searxng_only':
  engines = ['searxng']
else if strategy === 'both':
  engines = ['tavily', 'searxng']

↓ 引擎可用性检查
if tavily.enabled === false:
  engines.remove('tavily')
if searxng.enabled === false:
  engines.remove('searxng')

↓ 回退逻辑
if engines.length === 0:
  engines = ['tavily']  // 默认回退

输出：['tavily', 'searxng']
```

---

### 步骤 3: 并行搜索

```javascript
输入：查询 + 引擎列表 ['tavily', 'searxng']

↓ 并行执行
Promise.all([
  tavilyAdapter.search(query, options),
  searxngAdapter.search(query, options)
])

↓ 结果
[
  {
    success: true,
    engine: 'tavily',
    results: [
      { title: '...', url: '...', content: '...' },
      ...
    ]
  },
  {
    success: true,
    engine: 'searxng',
    results: [
      { title: '...', url: '...', content: '...' },
      ...
    ]
  }
]
```

---

### 步骤 4: 结果合并

```javascript
输入：多个引擎的结果数组

↓ 1. 扁平化
allResults = []
for resultObj in resultsArray:
  allResults.concat(resultObj.results)

↓ 2. 过滤失败结果
allResults = allResults.filter(r => r && r.title)

↓ 3. 去重（基于 URL）
seen = Set()
unique = []
for result in allResults:
  urlKey = result.url.toLowerCase()
  if !seen.has(urlKey):
    seen.add(urlKey)
    unique.push(result)

↓ 4. 排序
allResults.sort((a, b) => {
  if a.type === 'answer' return -1  // AI 答案优先
  if b.type === 'answer' return 1
  if a.score && b.score return b.score - a.score  // 按分数
  return 0
})

↓ 5. 限制数量
allResults = allResults.slice(0, maxResults)

↓ 6. 格式化输出
输出 Markdown 格式：
📊 **搜索结果** (共 X 条)
   - 🔍 Tavily: X 条
   - 🌐 SearXNG: X 条

**1. 标题** 🔍
   链接：...
   摘要：...
```

---

## 🧠 查询分类规则

### 关键词库

```javascript
realtime_keywords = [
  '最新', '刚刚', '现在', 'today', 'now', 'breaking',
  '实时', '当前', 'recent', 'latest'
]

news_keywords = [
  '新闻', 'news', '报道', 'report', '媒体', 'media',
  '头条', 'headline', '事件', 'event'
]

technical_keywords = [
  '教程', 'tutorial', '文档', 'documentation', 'API',
  '代码', 'code', '编程', 'programming', '开发', 'development',
  'github', 'npm', 'package', 'library', 'framework'
]

research_keywords = [
  '研究', 'research', '分析', 'analysis', '报告', 'report',
  '论文', 'paper', '学术', 'academic', '综述', 'review',
  '对比', 'comparison', '趋势', 'trend'
]
```

### 评分算法

```javascript
function classifyQuery(query) {
  scores = { realtime: 0, news: 0, technical: 0, research: 0 }
  
  // 关键词匹配（每个 +2 分）
  for keyword in realtime_keywords:
    if query.includes(keyword): scores.realtime += 2
  
  // 时间模式匹配（每个 +1 分）
  if /昨天 | 上周 | 今天 | 最近/.test(query):
    scores.realtime += 1
  
  // URL 检测（+1 分，倾向于 Tavily 提取）
  if /https?:\/\//.test(query):
    scores.technical += 1
  
  // 代码符号检测（+1 分）
  if /[{}<>()\[\].=;]/.test(query):
    scores.technical += 1
  
  // 找出最高分
  maxScore = max(scores.values())
  detectedType = scores.keyWithMaxValue()
  
  // 置信度计算
  confidence = min(maxScore / 5, 1.0)
  
  // 如果分数太低，判定为通用
  if maxScore < 2:
    detectedType = 'general'
  
  return { type: detectedType, confidence, scores }
}
```

---

## 🔄 路由映射表

| 查询类型 | 关键词示例 | 匹配分数 | 使用引擎 | 原因 |
|---------|-----------|---------|---------|------|
| **realtime** | "最新 AI 动态" | realtime: 4 | SearXNG | 实时性更好 |
| **news** | "科技新闻报道" | news: 4 | SearXNG | 新闻源聚合 |
| **technical** | "Python 教程" | technical: 4 | Tavily | 技术内容优化 |
| **research** | "AI 趋势分析" | research: 4 | Tavily | 深度研究支持 |
| **general** | "人工智能" | 所有：0 | 双引擎 | 综合结果 |

---

## ⚡ 性能优化

### 并行搜索

```javascript
// ❌ 串行（慢）
const tavilyResults = await tavily.search(query);
const searxngResults = await searxng.search(query);

// ✅ 并行（快）
const [tavilyResults, searxngResults] = await Promise.all([
  tavily.search(query),
  searxng.search(query)
]);
// 总耗时 = max(tavily 耗时，searxng 耗时)
```

### 缓存机制

```javascript
// Tavily 内置缓存（5 分钟 TTL）
const cacheKey = `search:${JSON.stringify({query, options})}`;
const cached = cache.get(cacheKey);
if (cached) {
  return cached;  // <100ms
}
const result = await api.search(query);
cache.set(cacheKey, result);  // 存入缓存
```

### 超时保护

```javascript
// SearXNG 超时
exec(cmd, { timeout: 30000 }, callback);

// Tavily 超时
fetch(url, { timeout: 30000 });

// 整体超时
Promise.race([
  searchPromise,
  new Promise((_, reject) => 
    setTimeout(() => reject(new Error('超时')), 30000)
  )
]);
```

---

## 🛡️ 错误处理

### 引擎失败回退

```javascript
try {
  results = await Promise.allSettled([
    tavily.search(query),
    searxng.search(query)
  ]);
  
  // 过滤失败的结果
  successfulResults = results.filter(r => r.status === 'fulfilled');
  
  if (successfulResults.length === 0) {
    throw new Error('所有引擎都失败了');
  }
  
  // 继续处理成功的结果
  return mergeResults(successfulResults);
  
} catch (error) {
  return formatError(error);
}
```

### 配置验证

```javascript
// 启动时验证
if (!config.tavily.enabled && !config.searxng.enabled) {
  throw new Error('至少需要启用一个引擎');
}

// 运行时检查
if (!tavily.api_key || tavily.api_key === 'default') {
  console.warn('Tavily API Key 未配置');
  tavily.enabled = false;  // 自动禁用
}
```

---

## 📈 决策示例

### 示例 1: 技术查询

```
输入："OpenClaw 安装教程"

分类过程:
- 扫描关键词：发现"教程"、"安装"
- technical 得分：4 分
- 置信度：80%
- 判定类型：technical

路由决策:
- technical → Tavily
- 检查 Tavily 状态：✅ 启用
- 最终引擎：['tavily']

执行:
- 调用 Tavily API
- 返回 5 条结果

输出:
🔀 **智能路由决策**
**查询类型**: technical
**使用引擎**: 🔍 Tavily
**决策原因**: 检测到技术/开发相关内容

📊 **搜索结果** (5 条)
...
```

---

### 示例 2: 新闻查询

```
输入："最新 AI 新闻"

分类过程:
- 扫描关键词：发现"最新"、"新闻"
- realtime 得分：4 分
- news 得分：4 分
- 置信度：80%
- 判定类型：realtime（先匹配）

路由决策:
- realtime → SearXNG
- 检查 SearXNG 状态：✅ 启用
- 最终引擎：['searxng']

执行:
- 调用 SearXNG API
- 返回 5 条新闻

输出:
🔀 **智能路由决策**
**查询类型**: realtime
**使用引擎**: 🌐 SearXNG
**决策原因**: 检测到实时信息需求关键词

📊 **搜索结果** (5 条)
...
```

---

### 示例 3: 通用查询

```
输入："人工智能"

分类过程:
- 扫描关键词：无匹配
- 所有得分：0 分
- 置信度：0%
- 判定类型：general

路由决策:
- general → 双引擎
- 最终引擎：['tavily', 'searxng']

执行:
- 并行调用两个 API
- Tavily 返回 5 条
- SearXNG 返回 5 条
- 合并去重 → 10 条

输出:
🔀 **智能路由决策**
**查询类型**: general
**使用引擎**: 🔍 Tavily + 🌐 SearXNG
**决策原因**: 未检测到明显倾向

📊 **搜索结果** (10 条)
...
```

---

## 🎯 总结

**智能路由的核心逻辑**：

1. **理解查询** - 通过关键词匹配识别意图
2. **选择引擎** - 根据意图选择最适合的搜索引擎
3. **并行执行** - 同时调用多个引擎（如果配置）
4. **合并优化** - 去重、排序、格式化
5. **透明展示** - 告诉用户为什么这样选择

**优势**：
- 🎯 精准匹配查询类型
- ⚡ 并行搜索提高速度
- 🔄 双引擎互补不足
- 🛡️ 错误处理和回退
- 📊 透明的决策过程
