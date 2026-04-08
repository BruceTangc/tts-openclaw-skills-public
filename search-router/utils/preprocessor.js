/**
 * 查询预处理
 * 
 * 标准化查询，去除无意义内容
 */

/**
 * 预处理查询
 */
function preprocessQuery(query) {
  if (!query || typeof query !== 'string') {
    return '';
  }

  let processed = query;

  // 1. 去除多余空格
  processed = processed.trim().replace(/\s+/g, ' ');

  // 2. 去除常见停用词（中英文）
  const stopWords = [
    // 中文
    '请', '帮我', '我想', '请问', '给我', '查一下', '搜索', '查找',
    '有没有', '能不能', '可不可以', '想知道', '想了解',
    // 英文
    'please', 'help', 'i want', 'i need', 'show me',
    'search for', 'find', 'look for', 'tell me'
  ];

  for (const word of stopWords) {
    // 使用正则匹配完整词
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    processed = processed.replace(regex, '');
  }

  // 3. 去除无意义的标点符号（保留 URL 中的）
  processed = processed.replace(/[?!.,;:()""'']/g, '');

  // 4. URL 解码（如果包含%）
  if (processed.includes('%')) {
    try {
      processed = decodeURIComponent(processed);
    } catch (e) {
      // 忽略解码错误
    }
  }

  // 5. 全角转半角（中文标点）
  processed = processed.replace(/[\uFF01-\uFF5E]/g, (ch) => {
    return String.fromCharCode(ch.charCodeAt(0) - 0xFEE0);
  });

  // 6. 再次清理空格
  processed = processed.trim().replace(/\s+/g, ' ');

  // 7. 如果处理后为空，返回原始查询
  if (!processed || processed.length === 0) {
    return query.trim();
  }

  return processed;
}

/**
 * 检测查询语言
 */
function detectLanguage(query) {
  const chineseChars = query.match(/[\u4e00-\u9fa5]/g);
  const chineseRatio = chineseChars ? chineseChars.length / query.length : 0;

  if (chineseRatio > 0.5) {
    return 'zh';
  } else if (chineseRatio > 0.2) {
    return 'zh-en';
  } else {
    return 'en';
  }
}

/**
 * 提取查询中的 URL
 */
function extractUrls(query) {
  const urlPattern = /https?:\/\/[^\s]+/gi;
  return query.match(urlPattern) || [];
}

/**
 * 检测是否包含代码
 */
function containsCode(query) {
  // 检测代码相关符号
  const codePatterns = [
    /[{}<>()\[\].=;]/,  // 常见符号
    /\b(function|class|import|from|return|if|else|for|while)\b/i,  // 关键字
    /\b(var|let|const|def|public|private|protected)\b/i  // 变量声明
  ];

  return codePatterns.some(pattern => pattern.test(query));
}

module.exports = {
  preprocessQuery,
  detectLanguage,
  extractUrls,
  containsCode
};
