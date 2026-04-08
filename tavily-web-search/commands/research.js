/**
 * Research 命令 - 深度研究（已禁用）
 */

const api = require('../utils/api');

/**
 * 执行深度研究
 */
async function run(params) {
  const {
    input,
    model,
    stream,
    output_schema,
    citation_format
  } = params;
  
  if (!input) {
    throw new Error('缺少研究主题 (input)');
  }
  
  // 构建请求参数
  const requestData = {
    input,
    model: model || 'auto',
    stream: stream || false,
    citation_format: citation_format || 'numbered'
  };
  
  // 可选参数
  if (output_schema) requestData.output_schema = output_schema;
  
  // 调用 API
  const result = await api.research(requestData);
  
  return result;
}

module.exports = { run };
