/**
 * Extract 命令 - 内容提取
 */

const api = require('../utils/api');
const formatter = require('../utils/formatter');

/**
 * 执行提取
 */
async function run(params) {
  const {
    urls,
    query,
    chunks_per_source,
    extract_depth,
    format,
    include_images,
    include_favicon,
    timeout
  } = params;
  
  if (!urls || (Array.isArray(urls) && urls.length === 0) || (!Array.isArray(urls) && !urls.trim())) {
    throw new Error('缺少 URL 参数');
  }
  
  // 支持单个 URL 字符串或数组
  const urlList = Array.isArray(urls) ? urls : [urls];
  
  if (urlList.length === 0) {
    throw new Error('URL 列表不能为空');
  }
  
  if (urlList.length > 20) {
    throw new Error('最多支持 20 个 URL');
  }
  
  // 验证 URL 格式
  const urlRegex = /^https?:\/\/.+/i;
  for (const url of urlList) {
    if (!urlRegex.test(url)) {
      throw new Error(`无效的 URL 格式：${url}（需要 http:// 或 https:// 开头）`);
    }
  }
  
  // 构建请求参数
  const requestData = {
    urls: urlList,
    extract_depth: extract_depth || 'basic',
    format: format || 'markdown'
  };
  
  // 可选参数
  if (query) requestData.query = query;
  if (chunks_per_source) requestData.chunks_per_source = chunks_per_source;
  if (include_images !== undefined) requestData.include_images = include_images;
  if (include_favicon !== undefined) requestData.include_favicon = include_favicon;
  if (timeout) requestData.timeout = timeout;
  
  // 调用 API
  const result = await api.extract(requestData);
  
  // 格式化输出
  return formatter.formatExtractResults(result);
}

module.exports = { run };
