/**
 * 结果合并器
 * 
 * 合并来自多个引擎的搜索结果，去重，排序
 */

/**
 * 合并结果
 */
function mergeResults(resultsArray, options = {}) {
  const {
    deduplicate = true,
    maxResults = 10,
    showEngineSource = true
  } = options;
  
  // 从每个引擎的结果中提取 results 数组
  let allResults = [];
  for (const resultObj of resultsArray) {
    if (resultObj && resultObj.results && Array.isArray(resultObj.results)) {
      allResults = allResults.concat(resultObj.results);
    }
  }
  
  // 过滤掉失败的结果
  allResults = allResults.filter(r => r && r.title);
  
  // 去重
  if (deduplicate) {
    allResults = deduplicateResults(allResults);
  }
  
  // 排序（按相关度）
  allResults = sortResults(allResults);
  
  // 限制结果数量
  allResults = allResults.slice(0, maxResults);
  
  // 格式化输出
  return formatResults(allResults, { showEngineSource });
}

/**
 * 去重结果（基于 URL）
 */
function deduplicateResults(results) {
  const seen = new Set();
  const unique = [];
  
  for (const result of results) {
    const urlKey = result.url.toLowerCase().trim();
    
    if (!seen.has(urlKey)) {
      seen.add(urlKey);
      unique.push(result);
    }
  }
  
  return unique;
}

/**
 * 排序结果
 */
function sortResults(results) {
  return results.sort((a, b) => {
    // AI 答案优先
    if (a.type === 'answer') return -1;
    if (b.type === 'answer') return 1;
    
    // 按分数排序（如果有）
    if (a.score && b.score) {
      return b.score - a.score;
    }
    
    // 默认保持原顺序
    return 0;
  });
}

/**
 * 格式化结果为 Markdown
 */
function formatResults(results, options = {}) {
  const { showEngineSource = true } = options;
  
  const lines = [];
  
  // 统计
  const tavilyCount = results.filter(r => r.engine === 'tavily').length;
  const searxngCount = results.filter(r => r.engine === 'searxng').length;
  
  lines.push(`📊 **搜索结果** (共 ${results.length} 条)`);
  if (showEngineSource) {
    lines.push(`   - 🔍 Tavily: ${tavilyCount} 条`);
    lines.push(`   - 🌐 SearXNG: ${searxngCount} 条`);
  }
  lines.push('');
  
  // 输出结果
  results.forEach((result, index) => {
    const engineIcon = result.engine === 'tavily' ? '🔍' : '🌐';
    const engineTag = showEngineSource ? ` ${engineIcon}` : '';
    
    // AI 答案特殊处理
    if (result.type === 'answer') {
      lines.push(`🤖 **AI 答案**${engineTag}`);
      lines.push(result.content);
      lines.push('');
      return;
    }
    
    // 普通结果
    lines.push(`**${index + 1}. ${result.title}**${engineTag}`);
    
    if (result.url) {
      lines.push(`   链接：${result.url}`);
    }
    
    if (result.content) {
      const content = result.content.length > 200 
        ? result.content.substring(0, 200) + '...' 
        : result.content;
      lines.push(`   摘要：${content}`);
    }
    
    if (result.engines && result.engines.length > 0) {
      lines.push(`   来源：${result.engines.slice(0, 3).join(', ')}`);
    }
    
    lines.push('');
  });
  
  return lines.join('\n');
}

/**
 * 生成路由决策报告
 */
function generateRoutingReport(classification, enginesUsed, timing) {
  const lines = [];
  
  lines.push('🔀 **智能路由决策**');
  lines.push('');
  lines.push(`**查询类型**: ${classification.type}`);
  lines.push(`**置信度**: ${(classification.confidence * 100).toFixed(1)}%`);
  lines.push(`**使用引擎**: ${enginesUsed.join(', ')}`);
  lines.push(`**总耗时**: ${timing}ms`);
  lines.push('');
  lines.push('**决策原因**:',);
  
  // 解释决策原因
  const reasons = getDecisionReasons(classification);
  reasons.forEach(reason => {
    lines.push(`- ${reason}`);
  });
  
  lines.push('');
  lines.push('───────────────────────────────────────');
  lines.push('');
  
  return lines.join('\n');
}

/**
 * 获取决策原因
 */
function getDecisionReasons(classification) {
  const reasons = [];
  const { type, scores } = classification;
  
  switch (type) {
    case 'realtime':
      reasons.push('检测到实时信息需求关键词');
      reasons.push('SearXNG 提供更新的搜索结果');
      break;
      
    case 'news':
      reasons.push('检测到新闻相关关键词');
      reasons.push('SearXNG 聚合多个新闻源');
      break;
      
    case 'technical':
      reasons.push('检测到技术/开发相关内容');
      reasons.push('Tavily 更适合技术文档和代码搜索');
      break;
      
    case 'research':
      reasons.push('检测到研究分析需求');
      reasons.push('Tavily 提供 AI 答案和深度内容');
      break;
      
    case 'general':
      reasons.push('未检测到明显倾向');
      reasons.push('使用双引擎获得更全面的结果');
      break;
  }
  
  // 添加关键词匹配信息
  const topScore = Math.max(...Object.values(scores));
  if (topScore >= 2) {
    const matchedTypes = Object.entries(scores)
      .filter(([_, score]) => score >= 2)
      .map(([type]) => type);
    
    if (matchedTypes.length > 0) {
      reasons.push(`匹配关键词类型：${matchedTypes.join(', ')}`);
    }
  }
  
  return reasons;
}

module.exports = {
  mergeResults,
  deduplicateResults,
  sortResults,
  formatResults,
  generateRoutingReport
};
