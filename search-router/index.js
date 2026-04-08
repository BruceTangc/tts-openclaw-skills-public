/**
 * Search Router - 智能搜索路由
 * 
 * 根据查询类型自动选择最佳搜索引擎（Tavily / SearXNG / 两者）
 */

let config;
try {
  config = require('./config/default.json');
} catch (error) {
  console.warn('⚠️  警告：无法加载配置文件，使用默认配置');
  config = {
    engines: { tavily: { enabled: true }, searxng: { enabled: true } },
    routing: { default_strategy: 'auto' },
    output: { max_results_per_engine: 5, deduplicate: true, show_engine_source: true }
  };
}
const classifier = require('./utils/classifier');
const preprocessor = require('./utils/preprocessor');
const tavilyAdapter = require('./utils/tavily-adapter');
const searxngAdapter = require('./utils/searxng-adapter');
const merger = require('./utils/merger');
const { cache } = require('./utils/cache');

/**
 * 主处理函数
 */
async function handler(input) {
  const startTime = Date.now();
  
  try {
    // 解析输入
    const { query, options = {} } = parseInput(input);
    
    if (!query || query.trim() === '') {
      return '❌ **Search Router 失败**\n\n💡 请提供搜索查询，例如：search("OpenClaw 文档")';
    }
    
    // 查询预处理
    const originalQuery = query;
    const processedQuery = preprocessor.preprocessQuery(query);
    const language = preprocessor.detectLanguage(query);
    const hasUrl = preprocessor.extractUrls(query).length > 0;
    const hasCode = preprocessor.containsCode(query);
    
    // 分类查询（使用预处理后的查询）
    const classification = classifier.classifyQuery(processedQuery);
    
    // 添加额外信息
    classification.language = language;
    classification.hasUrl = hasUrl;
    classification.hasCode = hasCode;
    
    // 获取路由策略
    const strategy = options.engine || config.routing.default_strategy;
    
    // 根据策略执行搜索（带缓存和降级）
    const results = await executeSearchWithCache(processedQuery, classification, strategy, options);
    
    // 合并结果
    const mergedOutput = merger.mergeResults(results.results, {
      deduplicate: config.output.deduplicate,
      maxResults: config.output.max_results_per_engine * 2,
      showEngineSource: config.output.show_engine_source
    });
    
    // 生成路由报告
    const timing = Date.now() - startTime;
    const routingReport = merger.generateRoutingReport(
      classification,
      results.enginesUsed,
      timing
    );
    
    // 返回完整结果
    return routingReport + mergedOutput;
    
  } catch (error) {
    return `❌ **Search Router 失败**\n\n${error.message}`;
  }
}

/**
 * 解析输入
 */
function parseInput(input) {
  if (typeof input === 'string') {
    return { query: input, options: {} };
  }
  
  if (typeof input === 'object') {
    const { query, engine, ...options } = input;
    return { query: query || '', options };
  }
  
  throw new Error('无效的输入格式');
}

/**
 * 执行搜索（带缓存和降级）
 */
async function executeSearchWithCache(query, classification, strategy, options) {
  const results = [];
  const enginesUsed = [];
  const startTime = Date.now();
  
  // 确定要使用的引擎
  let enginesToUse = determineEngines(classification, strategy);
  
  // 检查引擎是否启用
  if (config.tavily && !config.tavily.enabled) {
    enginesToUse = enginesToUse.filter(e => e !== 'tavily');
  }
  if (config.searxng && !config.searxng.enabled) {
    enginesToUse = enginesToUse.filter(e => e !== 'searxng');
  }
  
  // 如果所有引擎都被禁用，回退到 Tavily
  if (enginesToUse.length === 0) {
    enginesToUse = ['tavily'];
  }
  
  // 并行执行搜索（带超时和缓存）
  const searchPromises = enginesToUse.map(async (engine) => {
    const engineStartTime = Date.now();
    
    try {
      // 检查缓存
      const cachedResult = cache.get(engine, query, options);
      if (cachedResult) {
        console.log(`✅ ${engine} 缓存命中`);
        enginesUsed.push(engine);
        return cachedResult;
      }
      
      // 执行搜索（带超时）
      const timeout = options.timeout || config.searxng?.timeout || 10000;
      let result;
      
      if (engine === 'tavily') {
        result = await withTimeout(
          tavilyAdapter.search(query, {
            max_results: config.output.max_results_per_engine,
            use_cache: true
          }),
          timeout
        );
      } else if (engine === 'searxng') {
        result = await withTimeout(
          searxngAdapter.search(query, {
            limit: config.output.max_results_per_engine
          }),
          timeout
        );
      }
      
      // 检查搜索结果
      if (result && result.success) {
        enginesUsed.push(engine);
        // 存入缓存
        cache.set(engine, query, result, options);
      } else {
        console.warn(`⚠️  ${engine} 搜索失败：${result?.error || '未知错误'}`);
      }
      
      return result;
      
    } catch (error) {
      console.warn(`⚠️  ${engine} 超时或失败：${error.message}`);
      return { success: false, engine, error: error.message, results: [] };
    }
  });
  
  const searchResults = await Promise.all(searchPromises);
  
  const totalTiming = Date.now() - startTime;
  console.log(`⚡ 总耗时：${totalTiming}ms`);
  
  return {
    results: searchResults,
    enginesUsed
  };
}

/**
 * 确定使用哪些引擎
 */
function determineEngines(classification, strategy) {
  if (strategy === 'auto') {
    if (classification.engine === 'both') {
      return ['tavily', 'searxng'];
    } else {
      return [classification.engine];
    }
  } else if (strategy === 'tavily_only') {
    return ['tavily'];
  } else if (strategy === 'searxng_only') {
    return ['searxng'];
  } else if (strategy === 'both') {
    return ['tavily', 'searxng'];
  }
  
  return ['tavily'];
}

/**
 * 带超时的 Promise
 */
function withTimeout(promise, timeoutMs) {
  return Promise.race([
    promise,
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error(`超时 (${timeoutMs}ms)`)), timeoutMs)
    )
  ]);
}

/**
 * 获取帮助信息
 */
function help() {
  const lines = [
    '🔀 **Search Router 帮助**',
    '',
    '**功能**: 智能路由搜索请求到最佳引擎（Tavily / SearXNG）',
    '',
    '**使用方式**:',
    '```',
    '// 自动路由（推荐）',
    'search("OpenClaw 文档")',
    '',
    '// 指定引擎',
    'search({ query: "AI 新闻", engine: "tavily" })',
    'search({ query: "最新科技", engine: "searxng" })',
    'search({ query: "综合搜索", engine: "both" })',
    '```',
    '',
    '**路由策略**:',
    '- 🔍 Tavily: 技术内容、深度研究、文档查询',
    '- 🌐 SearXNG: 实时信息、新闻、多源聚合',
    '- 🔄 双引擎：综合搜索，合并结果',
    '',
    '**自动分类**:',
    '- 实时信息 → SearXNG',
    '- 新闻 → SearXNG',
    '- 技术/开发 → Tavily',
    '- 研究/分析 → Tavily',
    '- 通用 → 双引擎'
  ];
  
  return lines.join('\n');
}

/**
 * 版本信息
 */
function version() {
  const pkg = require('./package.json');
  return {
    name: pkg.name,
    version: pkg.version,
    lastUpdated: pkg.search_router?.last_updated || 'unknown'
  };
}

module.exports = {
  handler,
  help,
  version,
  classifyQuery: classifier.classifyQuery
};
