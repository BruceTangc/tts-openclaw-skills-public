/**
 * Research Status 命令 - 研究状态查询（已禁用）
 */

const api = require('../utils/api');

/**
 * 查询研究状态
 */
async function run(params) {
  const { request_id } = params;
  
  if (!request_id) {
    throw new Error('缺少 request_id 参数');
  }
  
  // 调用 API
  const result = await api.researchStatus(request_id);
  
  return {
    request_id: result.request_id,
    status: result.status,
    input: result.input,
    report: result.report,
    sources: result.sources,
    citations: result.citations
  };
}

module.exports = { run };
