/**
 * Search 命令 - 网页搜索
 */

const api = require('../utils/api');
const formatter = require('../utils/formatter');
const { cache } = require('../utils/cache');

// ── 常量 ──────────────────────────────────────────────
const VALID_SEARCH_DEPTH = ['basic', 'advanced', 'fast', 'ultra-fast'];
const VALID_TOPIC = ['general', 'news', 'finance'];
const VALID_TIME_RANGE = ['day', 'week', 'month', 'year', 'd', 'w', 'm', 'y'];
const VALID_INCLUDE_ANSWER = [true, false, 'basic', 'advanced'];
const VALID_INCLUDE_RAW = [true, false, 'markdown', 'text'];

// ── 工具 ──────────────────────────────────────────────

/** 兼容 CLI 传入的字符串 "true"/"false" */
function coerceBool(val) {
  if (val === 'true') return true;
  if (val === 'false') return false;
  return val;
}

/** 生成缓存键 */
function makeCacheKey(params) {
  return `search:${JSON.stringify(params)}`;
}

function fail(msg) { throw new Error(msg); }

// ── 执行 ──────────────────────────────────────────────

async function run(params) {
  let {
    query,
    search_depth = 'basic',
    max_results = 5,
    topic = 'general',
    time_range,
    start_date,
    end_date,
    include_answer,
    include_raw_content,
    include_images,
    include_image_descriptions,
    include_favicon,
    include_domains,
    exclude_domains,
    country,
    chunks_per_source,
    auto_parameters,
    exact_match,
    safe_search,
    include_usage,
    use_cache = true,
    raw_output
  } = params;

  if (!query || query.trim() === '')
    fail('缺少搜索关键词');

  // ── 字符串布尔值归一化 ──
  include_answer   = coerceBool(include_answer);
  include_raw_content = coerceBool(include_raw_content);
  include_images   = coerceBool(include_images);
  include_image_descriptions = coerceBool(include_image_descriptions);
  include_favicon  = coerceBool(include_favicon);
  auto_parameters  = coerceBool(auto_parameters);
  exact_match      = coerceBool(exact_match);
  safe_search      = coerceBool(safe_search);
  include_usage    = coerceBool(include_usage);

  // ── 枚举校验 ──
  if (!VALID_SEARCH_DEPTH.includes(search_depth))
    fail(`无效的 search_depth: ${search_depth}，可选值：${VALID_SEARCH_DEPTH.join(', ')}`);
  if (!VALID_TOPIC.includes(topic))
    fail(`无效的 topic: ${topic}，可选值：${VALID_TOPIC.join(', ')}`);
  if (time_range && !VALID_TIME_RANGE.includes(time_range))
    fail(`无效的 time_range: ${time_range}，可选值：${VALID_TIME_RANGE.join(', ')}`);
  if (include_answer !== undefined && !VALID_INCLUDE_ANSWER.includes(include_answer))
    fail(`无效的 include_answer，可选值：true/false/"basic"/"advanced"`);
  if (include_raw_content !== undefined && !VALID_INCLUDE_RAW.includes(include_raw_content))
    fail(`无效的 include_raw_content，可选值：true/false/"markdown"/"text"`);

  // ── 参数值域校验 ──
  if (chunks_per_source && (chunks_per_source < 1 || chunks_per_source > 3))
    fail('chunks_per_source 范围：1-3');

  // ── 组合约束（来自官方文档） ──

  // chunks_per_source 仅在 advanced 有效
  if (chunks_per_source && search_depth !== 'advanced')
    chunks_per_source = undefined;

  // finance topic 不支持 fast / ultra-fast
  if (topic === 'finance' && (search_depth === 'fast' || search_depth === 'ultra-fast'))
    fail(`topic="finance" 不支持 search_depth="${search_depth}"，请使用 basic 或 advanced`);

  // fast / ultra-fast 不支持 include_raw_content（它们只返回 NLP 摘要，无原始内容）
  if (include_raw_content && (search_depth === 'fast' || search_depth === 'ultra-fast'))
    fail(`include_raw_content 不支持 search_depth="${search_depth}"，请使用 basic 或 advanced`);

  // country 仅在 topic=general 时有效
  if (country && topic !== 'general')
    fail(`country 仅在 topic="general" 时有效，当前 topic="${topic}"`);

  // safe_search 不支持 fast/ultra-fast
  if (safe_search && (search_depth === 'fast' || search_depth === 'ultra-fast'))
    fail(`safe_search 不支持 search_depth="${search_depth}"，请使用 basic 或 advanced`);

  // ── 构建请求参数 ──
  const requestData = { query, search_depth, max_results, topic };

  if (time_range)               requestData.time_range = time_range;
  if (start_date)               requestData.start_date = start_date;
  if (end_date)                 requestData.end_date = end_date;
  if (include_answer !== undefined)       requestData.include_answer = include_answer;
  if (include_raw_content !== undefined)  requestData.include_raw_content = include_raw_content;
  if (include_images !== undefined)       requestData.include_images = include_images;
  if (include_image_descriptions !== undefined) requestData.include_image_descriptions = include_image_descriptions;
  if (include_favicon !== undefined)      requestData.include_favicon = include_favicon;
  if (include_domains?.length)            requestData.include_domains = include_domains;
  if (exclude_domains?.length)            requestData.exclude_domains = exclude_domains;
  if (country)                  requestData.country = country;
  if (chunks_per_source)        requestData.chunks_per_source = chunks_per_source;
  if (auto_parameters !== undefined)      requestData.auto_parameters = auto_parameters;
  if (exact_match !== undefined)          requestData.exact_match = exact_match;
  if (safe_search !== undefined)          requestData.safe_search = safe_search;
  if (include_usage !== undefined)        requestData.include_usage = include_usage;

  // ── 缓存 ──
  const cacheKey = makeCacheKey(requestData);
  if (use_cache) {
    const cachedResult = cache.get(cacheKey);
    if (cachedResult)
      return formatter.formatSearchResults(cachedResult);
  }

  // ── 调用 API ──
  const result = await api.search(requestData);

  if (use_cache)
    cache.set(cacheKey, result);

  return raw_output
    ? JSON.stringify(result, null, 2)
    : formatter.formatSearchResults(result);
}

module.exports = { run, makeCacheKey };
