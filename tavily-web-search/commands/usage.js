/**
 * Usage 命令 - 用量查询
 */

const api = require('../utils/api');
const formatter = require('../utils/formatter');

/**
 * 查询用量
 */
async function run(params) {
  const { project_id } = params || {};
  
  // 调用 API（支持按项目查询）
  const result = await api.usage({ project_id });
  
  // 格式化输出
  return formatter.formatUsage(result);
}

module.exports = { run };
