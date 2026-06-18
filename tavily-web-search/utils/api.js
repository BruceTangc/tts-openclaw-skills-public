/**
 * Tavily API 封装
 */

const fetch = require('node-fetch');
const config = require('../config/default.json');

const BASE_URL = config.base_url;

// 只从环境变量读取 API Key — config 中不存储任何 key（防止意外上传泄露）
const API_KEY = process.env.TAVILY_API_KEY;

// 验证 API Key — 延迟到首次请求时检查（避免 --help 等操作也被拦截）
function validateApiKey() {
  if (!API_KEY) {
    const msg = [
      '❌ Tavily API Key 未配置',
      '',
      '本 Skill 依赖 Tavily API，需要有效的 API Key 才能使用。',
      '获取地址: https://tavily.com',
      '',
      '设置方式:',
      '  export TAVILY_API_KEY="你的 key"',
      '',
      '（注意: 请勿将 API Key 写入 config 文件，使用环境变量更安全。）',
      ''
    ].join('\n');
    throw new Error(msg);
  }
}

/**
 * 解析 Retry-After 头（支持秒数或 HTTP-date）
 */
function parseRetryAfter(retryAfter) {
  if (!retryAfter) return null;
  
  // 如果是纯数字，当作秒数
  const seconds = parseInt(retryAfter, 10);
  if (!isNaN(seconds)) return seconds;
  
  // 尝试解析 HTTP-date
  const date = new Date(retryAfter);
  if (!isNaN(date.getTime())) {
    return Math.max(1, Math.ceil((date.getTime() - Date.now()) / 1000));
  }
  
  return null;
}

/**
 * 通用请求方法（带重试）
 */
async function request(endpoint, data = null, method = 'POST', retries = 2, extraHeaders = null) {
  // 延迟验证 API Key（确保 --help 不受影响）
  validateApiKey();
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`
  };
  if (extraHeaders) {
    Object.assign(headers, extraHeaders);
  }
  
  const options = {
    method,
    headers
  };
  
  if (data && method === 'POST') {
    options.body = JSON.stringify(data);
  }
  
  // 重试逻辑
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        timeout: 30000 // 30 秒超时
      });
      
      // 处理速率限制
      if (response.status === 429) {
        const retryAfterHeader = response.headers.get('Retry-After');
        const retrySeconds = parseRetryAfter(retryAfterHeader) || Math.pow(2, attempt);
        console.log(`⏱️  速率限制，等待 ${retrySeconds}秒后重试...`);
        await new Promise(resolve => setTimeout(resolve, retrySeconds * 1000));
        continue;
      }
      
      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        // Tavily API 错误格式：detail 可能是字符串或对象
        let errorMsg = response.statusText;
        if (errorBody.detail) {
          errorMsg = typeof errorBody.detail === 'string' ? errorBody.detail : errorBody.detail?.error || response.statusText;
        } else if (errorBody.message) {
          errorMsg = errorBody.message;
        }
        throw new Error(`Tavily API Error (${response.status}): ${errorMsg}`);
      }
      
      return await response.json();
      
    } catch (error) {
      if (attempt === retries) {
        throw error;
      }
      console.log(`⚠️  请求失败，重试 ${attempt + 1}/${retries}: ${error.message}`);
      await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
    }
  }
}

module.exports = {
  API_KEY,
  BASE_URL,
  
  // Search API
  search: (params) => request('/search', params),
  
  // Extract API
  extract: (params) => request('/extract', params),
  
  // Crawl API
  crawl: (params) => request('/crawl', params),
  
  // Map API
  map: (params) => request('/map', params),
  
  // Research API
  research: (params) => request('/research', params),
  
  // Research Status API
  researchStatus: (requestId) => request(`/research/${requestId}`, null, 'GET'),
  
  // Usage API（支持 project_id 作为 header）
  usage: (options = {}) => {
    const { project_id } = options;
    if (project_id) {
      return request('/usage', null, 'GET', 2, { 'X-Project-ID': project_id });
    }
    return request('/usage', null, 'GET');
  }
};
