/**
 * Tavily 搜索引擎适配器
 */

const path = require('path');
let tavily;
try {
  // 使用绝对路径
  tavily = require(path.resolve(__dirname, '../../tavily-web-search'));
} catch (error) {
  console.warn('⚠️  Tavily 模块未找到，请确保 tavily-web-search 已安装');
  tavily = null;
}

/**
 * 搜索 Tavily
 */
async function search(query, options = {}) {
  if (!tavily) {
    return {
      success: false,
      engine: 'tavily',
      error: 'Tavily 模块未安装',
      results: []
    };
  }
  
  const {
    max_results = 5,
    search_depth = 'basic',
    topic = 'general',
    time_range,
    include_answer = false,
    use_cache = true
  } = options;
  
  try {
    const result = await tavily.handler({
      command: 'search',
      query,
      max_results,
      search_depth,
      topic,
      time_range,
      include_answer,
      use_cache
    });
    
    return {
      success: true,
      engine: 'tavily',
      results: parseResults(result),
      raw: result
    };
  } catch (error) {
    return {
      success: false,
      engine: 'tavily',
      error: error.message,
      results: []
    };
  }
}

/**
 * 解析 Tavily 结果
 */
function parseResults(result) {
  const results = [];
  
  if (!result || typeof result !== 'string') {
    return results;
  }
  
  // 简单解析 Markdown 格式的结果
  const lines = result.split('\n');
  let currentResult = null;
  
  for (const line of lines) {
    // 跳过空行和分隔线
    if (!line.trim() || line.startsWith('──')) continue;
    
    // 标题行：**1. 标题**
    if (line.startsWith('**') && line.includes('**')) {
      if (currentResult) {
        results.push(currentResult);
      }
      currentResult = {
        title: line.replace(/\*\*/g, '').replace(/^\d+\.\s*/, '').trim(),
        url: '',
        content: '',
        engine: 'tavily'
      };
    } 
    // URL 行
    else if (line.trim().startsWith('链接：')) {
      if (currentResult) {
        currentResult.url = line.replace('链接：', '').trim();
      }
    } 
    // 摘要行
    else if (line.trim().startsWith('摘要：')) {
      if (currentResult) {
        currentResult.content = line.replace('摘要：', '').trim();
      }
    } 
    // AI 答案
    else if (line.includes('AI 答案')) {
      if (currentResult) {
        results.push(currentResult);
      }
      currentResult = null;
      results.push({
        title: 'AI 答案',
        url: '',
        content: line.replace(/🤖|AI 答案|\*\*/g, '').trim(),
        engine: 'tavily',
        type: 'answer'
      });
    }
  }
  
  // 添加最后一个结果
  if (currentResult && currentResult.title) {
    results.push(currentResult);
  }
  
  return results;
}

module.exports = {
  search,
  parseResults
};
