/**
 * Tavily API 封装
 */

const fetch = require('node-fetch');
const config = require('../config/default.json');

const API_KEY = process.env.TAVILY_API_KEY || config.api_key;
const BASE_URL = config.base_url;

// 验证 API Key
if (!API_KEY || API_KEY === 'tvly-dev-xxx' || API_KEY.startsWith('tvly-your')) {
  console.warn('⚠️  警告：Tavily API Key 未配置或使用默认值，请修改 config/default.json 或设置环境变量 TAVILY_API_KEY');
}

/**
 * 通用请求方法（带重试）
 */
async function request(endpoint, data = null, method = 'POST', retries = 2) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`
    }
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
        const retryAfter = response.headers.get('Retry-After') || Math.pow(2, attempt);
        console.log(`⏱️  速率限制，等待 ${retryAfter}秒后重试...`);
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
        continue;
      }
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(`Tavily API Error: ${error.detail?.error || response.statusText}`);
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
  
  // Usage API
  usage: () => request('/usage', null, 'GET')
};
