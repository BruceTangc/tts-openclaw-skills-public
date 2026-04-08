/**
 * 查询分类器
 * 
 * 分析查询意图，决定使用哪个搜索引擎
 */

let config;
try {
  config = require('../config/default.json');
} catch (error) {
  console.warn('⚠️  警告：无法加载配置文件，使用默认配置');
  config = {
    query_classification: {
      realtime_keywords: ['最新', '刚刚', '现在', 'today', 'now', 'breaking', '实时', '当前', 'recent', 'latest'],
      news_keywords: ['新闻', 'news', '报道', 'report', '媒体', 'media', '头条', 'headline', '事件', 'event'],
      technical_keywords: ['教程', 'tutorial', '文档', 'documentation', 'API', '代码', 'code', '编程', 'programming', '开发', 'development', 'github', 'npm', 'package', 'library', 'framework'],
      research_keywords: ['研究', 'research', '分析', 'analysis', '报告', 'report', '论文', 'paper', '学术', 'academic', '综述', 'review', '对比', 'comparison', '趋势', 'trend']
    }
  };
}

/**
 * 查询类型枚举
 */
const QueryType = {
  REALTIME: 'realtime',      // 实时信息
  NEWS: 'news',              // 新闻
  TECHNICAL: 'technical',    // 技术/开发
  RESEARCH: 'research',      // 研究/分析
  GENERAL: 'general'         // 通用搜索
};

/**
 * 查询类型到引擎的映射
 */
const TypeToEngine = {
  [QueryType.REALTIME]: 'searxng',
  [QueryType.NEWS]: 'searxng',
  [QueryType.TECHNICAL]: 'tavily',
  [QueryType.RESEARCH]: 'tavily',
  [QueryType.GENERAL]: 'both'
};

/**
 * 分类查询
 * 
 * @param {string} query - 搜索查询
 * @returns {Object} 分类结果
 */
function classifyQuery(query) {
  const lowerQuery = query.toLowerCase();
  
  const scores = {
    realtime: 0,
    news: 0,
    technical: 0,
    research: 0
  };
  
  // 检查实时关键词
  for (const keyword of config.query_classification.realtime_keywords) {
    if (lowerQuery.includes(keyword.toLowerCase())) {
      scores.realtime += 2;
    }
  }
  
  // 检查新闻关键词
  for (const keyword of config.query_classification.news_keywords) {
    if (lowerQuery.includes(keyword.toLowerCase())) {
      scores.news += 2;
    }
  }
  
  // 检查技术关键词
  for (const keyword of config.query_classification.technical_keywords) {
    if (lowerQuery.includes(keyword.toLowerCase())) {
      scores.technical += 2;
    }
  }
  
  // 检查研究关键词
  for (const keyword of config.query_classification.research_keywords) {
    if (lowerQuery.includes(keyword.toLowerCase())) {
      scores.research += 2;
    }
  }
  
  // 检查 URL（如果有 URL，倾向于使用 Tavily 提取）
  const urlPattern = /https?:\/\/[^\s]+/i;
  if (urlPattern.test(query)) {
    scores.technical += 1;
  }
  
  // 检查是否包含代码相关符号
  if (/[{}<>()\[\].=;]/.test(query)) {
    scores.technical += 1;
  }
  
  // 检查时间相关词汇（昨天、上周等）
  const timePatterns = [
    /昨天|yesterday/i,
    /上周|last week/i,
    /今天|today/i,
    /最近|recent/i,
    /\d+[小时天周]前|\d+[hdw] ago/i
  ];
  
  for (const pattern of timePatterns) {
    if (pattern.test(query)) {
      scores.realtime += 1;
    }
  }
  
  // 找出得分最高的类型
  let maxScore = 0;
  let detectedType = QueryType.GENERAL;
  
  for (const [type, score] of Object.entries(scores)) {
    if (score > maxScore) {
      maxScore = score;
      detectedType = type;
    }
  }
  
  // 如果没有明显倾向，判断为通用搜索
  if (maxScore < 2) {
    detectedType = QueryType.GENERAL;
  }
  
  // 确定使用的引擎
  const engine = TypeToEngine[detectedType];
  
  // 计算置信度
  const confidence = Math.min(maxScore / 5, 1.0);
  
  return {
    type: detectedType,
    engine,
    confidence,
    scores,
    query
  };
}

/**
 * 获取引擎描述
 */
function getEngineDescription(engine) {
  const descriptions = {
    tavily: '🔍 Tavily - AI 优化的搜索引擎，适合技术内容和深度研究',
    searxng: '🌐 SearXNG - 隐私保护的元搜索引擎，适合实时信息和新闻',
    both: '🔄 双引擎 - 同时使用 Tavily 和 SearXNG，合并结果'
  };
  
  return descriptions[engine] || descriptions.tavily;
}

module.exports = {
  QueryType,
  classifyQuery,
  getEngineDescription
};
