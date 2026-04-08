/**
 * Search 命令 - 网页搜索
 */

const api = require('../utils/api');
const formatter = require('../utils/formatter');
const { cache } = require('../utils/cache');

/**
 * 生成缓存键
 */
function makeCacheKey(params) {
  return `search:${JSON.stringify(params)}`;
}

/**
 * 执行搜索
 */
async function run(params) {
  const {
    query,
    search_depth,
    max_results,
    topic,
    time_range,
    start_date,
    end_date,
    include_answer,
    include_raw_content,
    include_images,
    include_domains,
    exclude_domains,
    country,
    chunks_per_source,
    use_cache = true  // 默认启用缓存
  } = params;
  
  if (!query || query.trim() === '') {
    throw new Error('缺少搜索关键词');
  }
  
  // 构建请求参数
  const requestData = {
    query,
    search_depth: search_depth || 'basic',
    max_results: max_results || 5,
    topic: topic || 'general'
  };
  
  // 可选参数
  if (time_range) requestData.time_range = time_range;
  if (start_date) requestData.start_date = start_date;
  if (end_date) requestData.end_date = end_date;
  if (include_answer !== undefined) requestData.include_answer = include_answer;
  if (include_raw_content !== undefined) requestData.include_raw_content = include_raw_content;
  if (include_images !== undefined) requestData.include_images = include_images;
  if (include_domains && include_domains.length > 0) requestData.include_domains = include_domains;
  if (exclude_domains && exclude_domains.length > 0) requestData.exclude_domains = exclude_domains;
  if (country) requestData.country = country;
  if (chunks_per_source) requestData.chunks_per_source = chunks_per_source;
  
  // 检查缓存
  const cacheKey = makeCacheKey(requestData);
  if (use_cache) {
    const cachedResult = cache.get(cacheKey);
    if (cachedResult) {
      console.log('✅ 使用缓存结果');
      return formatter.formatSearchResults(cachedResult);
    }
  }
  
  // 调用 API
  const result = await api.search(requestData);
  
  // 存入缓存
  if (use_cache) {
    cache.set(cacheKey, result);
  }
  
  // 格式化输出
  return formatter.formatSearchResults(result);
}

module.exports = { run, makeCacheKey };
