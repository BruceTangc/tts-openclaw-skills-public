/**
 * Extract 命令 - 内容提取
 */

const api = require('../utils/api');
const formatter = require('../utils/formatter');

const VALID_EXTRACT_DEPTH = ['basic', 'advanced'];
const VALID_FORMAT = ['markdown', 'text'];

/** 兼容 CLI 传入的字符串 "true"/"false" */
function coerceBool(val) {
  if (val === 'true') return true;
  if (val === 'false') return false;
  return val;
}

function fail(msg) { throw new Error(msg); }

async function run(params) {
  let {
    urls,
    query,
    chunks_per_source,
    extract_depth = 'basic',
    format = 'markdown',
    include_images,
    include_favicon,
    include_usage,
    timeout,
    raw_output
  } = params;

  if (!urls || (Array.isArray(urls) && urls.length === 0) || (!Array.isArray(urls) && !urls.trim()))
    fail('缺少 URL 参数');

  const urlList = Array.isArray(urls) ? urls : [urls];

  if (urlList.length === 0) fail('URL 列表不能为空');
  if (urlList.length > 20)  fail('最多支持 20 个 URL');

  const urlRegex = /^https?:\/\/.+/i;
  for (const url of urlList)
    if (!urlRegex.test(url))
      fail(`无效的 URL 格式：${url}（需要 http:// 或 https:// 开头）`);

  // 归一化布尔值
  include_images   = coerceBool(include_images);
  include_favicon  = coerceBool(include_favicon);
  include_usage    = coerceBool(include_usage);

  // 枚举校验
  if (!VALID_EXTRACT_DEPTH.includes(extract_depth))
    fail(`无效的 extract_depth: ${extract_depth}，可选值：${VALID_EXTRACT_DEPTH.join(', ')}`);
  if (!VALID_FORMAT.includes(format))
    fail(`无效的 format: ${format}，可选值：${VALID_FORMAT.join(', ')}`);
  if (chunks_per_source && (chunks_per_source < 1 || chunks_per_source > 5))
    fail('chunks_per_source 范围：1-5');
  if (timeout && (timeout < 1 || timeout > 60))
    fail('timeout 范围：1-60 秒');

  const requestData = { urls: urlList, extract_depth, format };

  if (query)             requestData.query = query;
  if (chunks_per_source) requestData.chunks_per_source = chunks_per_source;
  if (include_images !== undefined)  requestData.include_images = include_images;
  if (include_favicon !== undefined) requestData.include_favicon = include_favicon;
  if (include_usage !== undefined)   requestData.include_usage = include_usage;
  if (timeout)           requestData.timeout = timeout;

  const result = await api.extract(requestData);

  return raw_output
    ? JSON.stringify(result, null, 2)
    : formatter.formatExtractResults(result);
}

module.exports = { run };
