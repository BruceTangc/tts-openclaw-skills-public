/**
 * Tavily Web Search - OpenClaw Skill
 * 
 * 完整的 Tavily API 集成，支持搜索、提取、爬取、地图、研究等功能
 */

const config = require('./config/default.json');
const formatter = require('./utils/formatter');

// 导入所有命令
const commands = {
  search: require('./commands/search'),
  extract: require('./commands/extract'),
  usage: require('./commands/usage'),
  crawl: require('./commands/crawl'),
  map: require('./commands/map'),
  research: require('./commands/research'),
  research_status: require('./commands/research-status')
};

/**
 * 解析输入
 */
function parseInput(input) {
  // 支持多种输入格式
  if (typeof input === 'string') {
    // 简单格式：直接是搜索词
    return { command: 'search', params: { query: input } };
  }
  
  if (typeof input === 'object') {
    const { command, ...params } = input;
    return { command: command || 'search', params };
  }
  
  throw new Error('无效的输入格式');
}

/**
 * 主处理函数
 */
async function handler(input) {
  let command;
  
  try {
    const parsed = parseInput(input);
    command = parsed.command;
    const params = parsed.params;
    
    // 检查命令是否存在
    if (!commands[command]) {
      return `❌ 未知命令：${command}\n\n可用命令：${Object.keys(commands).join(', ')}`;
    }
    
    // 检查命令是否启用
    const commandConfig = config.commands[command];
    if (!commandConfig?.enabled) {
      return `⚠️ 命令 "${command}" (${commandConfig?.description || command}) 暂未启用\n\n如需启用，请修改 config/default.json 中的配置`;
    }
    
    // 执行命令
    const result = await commands[command].run(params);
    
    // 如果结果已经是字符串，直接返回
    if (typeof result === 'string') {
      return result;
    }
    
    // 否则返回 JSON
    return JSON.stringify(result, null, 2);
    
  } catch (error) {
    return formatter.formatError(error, command || 'tavily');
  }
}

/**
 * 获取帮助信息
 */
function help() {
  const lines = [
    '🔍 **Tavily Web Search 帮助**',
    '',
    '**可用命令**:',
    ''
  ];
  
  // 分类显示命令
  const enabledCommands = [];
  const disabledCommands = [];
  
  Object.entries(config.commands).forEach(([cmd, cfg]) => {
    const line = `${cfg.enabled ? '✅' : '⏸️'} \`${cmd}\` - ${cfg.description}`;
    if (cfg.enabled) {
      enabledCommands.push(line);
    } else {
      disabledCommands.push(line);
    }
  });
  
  lines.push('**已启用**:');
  lines.push(...enabledCommands);
  
  if (disabledCommands.length > 0) {
    lines.push('');
    lines.push('**已实现但未启用**:');
    lines.push(...disabledCommands);
  }
  
  lines.push('');
  lines.push('**使用示例**:');
  lines.push('```');
  lines.push('// 搜索');
  lines.push('tavily("OpenClaw 文档")');
  lines.push('');
  lines.push('// 搜索（带参数）');
  lines.push('tavily({ command: "search", query: "AI", max_results: 10 })');
  lines.push('');
  lines.push('// 提取网页内容');
  lines.push('tavily({ command: "extract", urls: ["https://..."] })');
  lines.push('');
  lines.push('// 查看用量');
  lines.push('tavily({ command: "usage" })');
  lines.push('```');
  
  lines.push('');
  lines.push('**配置**: 编辑 `config/default.json` 或设置 `TAVILY_API_KEY` 环境变量');
  
  return lines.join('\n');
}

/**
 * 获取版本信息
 */
function version() {
  const pkg = require('./package.json');
  return {
    name: pkg.name,
    version: pkg.version,
    tavilyApiVersion: pkg.tavily?.api_version || 'unknown',
    docsVersion: pkg.tavily?.docs_version || 'unknown',
    lastUpdated: pkg.tavily?.last_updated || 'never'
  };
}

module.exports = {
  handler,
  help,
  version,
  commands,
  config
};
