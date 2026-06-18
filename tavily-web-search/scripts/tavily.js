#!/usr/bin/env node
// 抑制 node-fetch 的 punycode 弃用警告
process.noDeprecation = true;

/**
 * Tavily Web Search CLI — 路径无关，从任意目录可调用
 *
 * 用法:
 *   node scripts/tavily.js search <query> [选项]
 *   node scripts/tavily.js extract <url> [<url2> ...]
 *   node scripts/tavily.js usage
 *   node scripts/tavily.js --help
 *
 * 选项 (search):
 *   --max-results N    结果数量 (1-20, 默认 5)
 *   --topic X          general | news | finance (默认 general)
 *   --time-range X     day | week | month | year
 *   --depth X          basic | advanced | fast | ultra-fast (默认 basic)
 *   --answer [basic|advanced] 包含 AI 答案
 *   --raw [markdown|text] 包含原始内容
 *   --images           包含图片
 *   --favicon          包含站点图标
 *   --usage            包含用量信息
 *   --country X        国家 (如 china)
 *   --exact-match      精确匹配模式
 *   --json             输出原始 JSON（适用于管道处理）
 *
 * 环境变量:
 *   TAVILY_API_KEY     Tavily API Key (必需)
 */

const path = require('path');
// __dirname 指向 scripts/，require 会自动向上查找 node_modules
const { handler } = require('../index');

const AVAILABLE_COMMANDS = ['search', 'extract', 'usage', '--help', '-h'];

function printHelp() {
  console.log(`
🔍 Tavily Web Search CLI

用法:
  node ${path.relative(process.cwd(), __filename)} search <query> [选项]
  node ${path.relative(process.cwd(), __filename)} extract <url> [<url2> ...]
  node ${path.relative(process.cwd(), __filename)} usage

选项 (search):
  --max-results N    结果数量 (1-20, 默认 5)
  --topic X          general | news | finance
  --time-range X     day | week | month | year
  --depth X          basic | advanced | fast | ultra-fast
  --answer [basic|advanced] 包含 AI 答案
  --raw [markdown|text] 包含原始内容
  --images           包含图片
  --favicon          包含站点图标
  --usage            包含用量信息
  --country X        国家 (如 china)
  --exact-match      精确匹配模式
  --json             输出原始 JSON（适用于管道处理）

环境变量:
  TAVILY_API_KEY     ❗ 必需 — 从 https://tavily.com 获取

示例:
  node scripts/tavily.js search "AI Agent 最新进展"
  node scripts/tavily.js search "油价" --topic news --time-range week --answer
  node scripts/tavily.js search "AI" --max-results 2 --json
  node scripts/tavily.js extract https://example.com
  node scripts/tavily.js usage
`);
}

function parseArgs(argv) {
  const args = argv.slice(2); // skip "node" and script path

  if (args.length === 0 || args[0] === '--help' || args[0] === '-h') {
    return { command: 'help' };
  }

  const command = args[0];
  if (!AVAILABLE_COMMANDS.includes(command)) {
    console.error(`❌ 未知命令: ${command}`);
    console.error(`可用命令: ${AVAILABLE_COMMANDS.filter(c => !c.startsWith('-')).join(', ')}`);
    process.exit(1);
  }

  if (command === 'usage') {
    return { command: 'usage' };
  }

  if (command === 'search') {
    // 收集所有非选项参数作为 query
    const queryParts = [];
    const opts = {};
    let jsonMode = false;
    for (let i = 1; i < args.length; i++) {
      const arg = args[i];
      if (arg === '--json') {
        jsonMode = true;
      } else if (arg.startsWith('--')) {
        const key = arg.replace(/^--/, '').replace(/-/g, '_');
        if (key === 'answer') {
          const nextVal = args[i + 1];
          if (nextVal && !nextVal.startsWith('--') && (nextVal === 'basic' || nextVal === 'advanced')) {
            opts.include_answer = nextVal;
            i++;
          } else {
            opts.include_answer = true;
          }
        } else if (key === 'raw') {
          const nextVal = args[i + 1];
          if (nextVal && !nextVal.startsWith('--') && (nextVal === 'markdown' || nextVal === 'text')) {
            opts.include_raw_content = nextVal;
            i++;
          } else {
            opts.include_raw_content = true;
          }
        } else if (key === 'images') {
          opts.include_images = true;
        } else if (key === 'favicon') {
          opts.include_favicon = true;
        } else if (key === 'usage') {
          opts.include_usage = true;
        } else if (key === 'exact_match') {
          opts.exact_match = true;
        } else if (key === 'country') {
          i++;
          opts.country = args[i];
        } else {
          i++;
          opts[key] = args[i];
        }
      } else {
        queryParts.push(arg);
      }
    }

    const query = queryParts.join(' ');
    if (!query) {
      console.error('❌ 缺少搜索关键词');
      console.error('用法: node scripts/tavily.js search <query> [选项]');
      process.exit(1);
    }

    return { command: 'search', query, ...opts, raw_output: jsonMode };
  }

  if (command === 'extract') {
    const urls = [];
    let jsonMode = false;
    for (let i = 1; i < args.length; i++) {
      if (args[i] === '--json') {
        jsonMode = true;
      } else if (args[i].startsWith('http://') || args[i].startsWith('https://')) {
        urls.push(args[i]);
      }
    }
    if (urls.length === 0) {
      console.error('❌ 缺少 URL');
      console.error('用法: node scripts/tavily.js extract <url> [<url2> ...]');
      process.exit(1);
    }
    return { command: 'extract', urls, raw_output: jsonMode };
  }

  return { command: 'help' };
}

async function main() {
  const parsed = parseArgs(process.argv);

  if (parsed.command === 'help') {
    printHelp();
    return;
  }

  try {
    const result = await handler(parsed);
    console.log(result);
  } catch (err) {
    console.error(`❌ 执行失败: ${err.message}`);
    process.exit(1);
  }
}

main();
