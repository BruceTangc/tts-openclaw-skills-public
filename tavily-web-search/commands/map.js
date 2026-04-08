/**
 * Map 命令 - 站点地图（已禁用）
 */

const api = require('../utils/api');

/**
 * 生成站点地图
 */
async function run(params) {
  const {
    url,
    instructions,
    max_depth,
    max_breadth,
    limit,
    select_paths,
    exclude_paths,
    select_domains,
    exclude_domains,
    allow_external,
    timeout
  } = params;
  
  if (!url) {
    throw new Error('缺少 URL 参数');
  }
  
  // 构建请求参数
  const requestData = {
    url,
    instructions: instructions || '',
    max_depth: max_depth || 1,
    max_breadth: max_breadth || 20,
    limit: limit || 50,
    allow_external: allow_external !== false,
    timeout: timeout || 150
  };
  
  // 可选参数
  if (select_paths) requestData.select_paths = select_paths;
  if (exclude_paths) requestData.exclude_paths = exclude_paths;
  if (select_domains) requestData.select_domains = select_domains;
  if (exclude_domains) requestData.exclude_domains = exclude_domains;
  
  // 调用 API
  const result = await api.map(requestData);
  
  return result;
}

module.exports = { run };
