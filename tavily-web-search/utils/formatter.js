/**
 * 输出格式化工具
 */

/**
 * 格式化搜索结果
 */
function formatSearchResults(result) {
  const lines = [];
  
  // 查询回显
  if (result.query) {
    lines.push(`🔍 搜索：${result.query}`);
    lines.push('');
  }
  
  // AI 答案（如果有）
  if (result.answer) {
    lines.push('🤖 **AI 答案**:');
    lines.push(result.answer);
    lines.push('');
  }
  
  // 搜索结果
  if (result.results && result.results.length > 0) {
    lines.push('📋 **搜索结果**:');
    lines.push('');
    
    result.results.forEach((item, index) => {
      lines.push(`**${index + 1}. ${item.title || '无标题'}**`);
      lines.push(`   链接：${item.url}`);
      if (item.favicon) {
        lines.push(`   图标：${item.favicon}`);
      }
      if (item.content) {
        lines.push(`   摘要：${item.content.substring(0, 200)}${item.content.length > 200 ? '...' : ''}`);
      }
      if (item.score) {
        lines.push(`   相关度：${(item.score * 100).toFixed(1)}%`);
      }
      // 每个结果附带的图片（include_images 开启时）
      if (item.images && item.images.length > 0) {
        lines.push(`   🖼️ 图片：`);
        item.images.slice(0, 3).forEach(img => {
          lines.push(`   - ${img}`);
        });
      }
      lines.push('');
    });
  } else if (!result.answer) {
    return '🔍 未找到搜索结果';
  }
  
  // 顶层图片（query 相关图片，非 per-result）
  if (result.images && result.images.length > 0) {
    lines.push('🖼️ **相关图片**:');
    result.images.forEach(img => {
      const desc = img.description ? ` (${img.description})` : '';
      lines.push(`- ${img.url}${desc}`);
    });
    lines.push('');
  }
  
  // 后续问题（如果有）
  if (result.follow_up_questions && result.follow_up_questions.length > 0) {
    lines.push('💡 **相关问题**:');
    result.follow_up_questions.forEach(q => {
      lines.push(`- ${q}`);
    });
    lines.push('');
  }
  
  // 用量信息
  if (result.usage) {
    lines.push('📊 **本次搜索用量**');
    if (result.usage.credits_used !== undefined) {
      lines.push(`- 消耗：${result.usage.credits_used} credits`);
    }
    lines.push('');
  }
  
  return lines.join('\n') || '未找到结果';
}

/**
 * 格式化提取结果
 */
function formatExtractResults(result) {
  const lines = [];
  
  if (result.results) {
    result.results.forEach(item => {
      lines.push(`📄 **${item.url}**`);
      if (item.favicon) {
        lines.push(`   图标：${item.favicon}`);
      }
      lines.push('');
      
      if (item.raw_content) {
        lines.push(item.raw_content);
      } else {
        lines.push('⚠️ 未提取到内容');
      }
      
      if (item.images && item.images.length > 0) {
        lines.push('');
        lines.push('🖼️ **页面图片**:');
        item.images.forEach(img => {
          lines.push(`- ${img}`);
        });
      }
      
      lines.push('');
    });
  }
  
  // 用量信息
  if (result.usage) {
    lines.push('📊 **本次提取用量**');
    if (result.usage.credits_used !== undefined) {
      lines.push(`- 消耗：${result.usage.credits_used} credits`);
    }
    lines.push('');
  }
  
  return lines.join('\n') || '未找到结果';
}

/**
 * 格式化用量信息
 */
function formatUsage(result) {
  const lines = [];
  
  lines.push('📊 **Tavily API 用量**');
  lines.push('');
  
  // API Key 用量
  if (result.key) {
    lines.push(`**当前 Key 使用情况**:`);
    lines.push(`- 总用量：${result.key.usage} credits`);
    if (result.key.limit) {
      lines.push(`- 限额：${result.key.limit} credits`);
      lines.push(`- 剩余：${result.key.limit - result.key.usage} credits`);
    }
    lines.push('');
    
    if (result.key.search_usage) lines.push(`- 搜索：${result.key.search_usage} credits`);
    if (result.key.extract_usage) lines.push(`- 提取：${result.key.extract_usage} credits`);
    if (result.key.crawl_usage) lines.push(`- 爬取：${result.key.crawl_usage} credits`);
    if (result.key.map_usage) lines.push(`- 地图：${result.key.map_usage} credits`);
    if (result.key.research_usage) lines.push(`- 研究：${result.key.research_usage} credits`);
    lines.push('');
  }
  
  // 账户用量
  if (result.account) {
    lines.push(`**账户计划**: ${result.account.current_plan}`);
    lines.push(`- 计划用量：${result.account.plan_usage} / ${result.account.plan_limit || '∞'} credits`);
    if (result.account.paygo_usage !== undefined) {
      lines.push(`- 按量付费：${result.account.paygo_usage} / ${result.account.paygo_limit || '∞'} credits`);
    }
  }
  
  return lines.join('\n');
}

/**
 * 格式化错误信息
 */
function formatError(error, command) {
  // 优化错误信息
  const errorMessages = {
    '缺少搜索关键词': '💡 请提供搜索关键词，例如：tavily("OpenClaw")',
    '缺少 URL 参数': '💡 请提供 URL，例如：tavily({command:"extract",urls:["https://..."]})',
    'URL 列表不能为空': '💡 URL 列表不能为空',
    '最多支持 20 个 URL': '💡 最多支持 20 个 URL',
    '缺少 request_id': '💡 请提供 request_id 参数',
    '暂未启用': error.message
  };
  
  let friendlyMessage = error.message;
  for (const [key, value] of Object.entries(errorMessages)) {
    if (error.message.includes(key)) {
      friendlyMessage = value;
      break;
    }
  }
  
  return `❌ **${command} 失败**\n\n${friendlyMessage}`;
}

module.exports = {
  formatSearchResults,
  formatExtractResults,
  formatUsage,
  formatError
};
