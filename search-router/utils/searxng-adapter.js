/**
 * SearXNG 搜索引擎适配器
 */

const { exec } = require('child_process');
const path = require('path');

const SEARXNG_SCRIPT = path.join(__dirname, '../../searxng/scripts/searxng.py');

/**
 * 搜索 SearXNG
 */
async function search(query, options = {}) {
  const {
    limit = 5,
    category = 'general',
    language = 'auto',
    time_range
  } = options;
  
  return new Promise((resolve) => {
    // 构建命令
    let cmd = `cd ~/.openclaw/workspace/skills/searxng && uv run scripts/searxng.py search "${query.replace(/"/g, '\\"')}"`;
    cmd += ` -n ${limit}`;
    cmd += ` -c ${category}`;
    
    if (language !== 'auto') {
      cmd += ` -l ${language}`;
    }
    
    if (time_range) {
      cmd += ` -t ${time_range}`;
    }
    
    cmd += ' --format json';
    
    // 执行命令
    exec(cmd, { timeout: 30000 }, (error, stdout, stderr) => {
      if (error) {
        resolve({
          success: false,
          engine: 'searxng',
          error: error.message,
          results: []
        });
        return;
      }
      
      try {
        const data = JSON.parse(stdout);
        resolve({
          success: true,
          engine: 'searxng',
          results: parseResults(data),
          raw: data
        });
      } catch (parseError) {
        resolve({
          success: false,
          engine: 'searxng',
          error: `解析失败：${parseError.message}`,
          results: []
        });
      }
    });
  });
}

/**
 * 解析 SearXNG 结果
 */
function parseResults(data) {
  const results = [];
  
  if (!data || !data.results) {
    return results;
  }
  
  for (const item of data.results) {
    results.push({
      title: item.title || '无标题',
      url: item.url || '',
      content: item.content || '',
      engine: 'searxng',
      engines: item.engines || [],
      score: item.score || 0
    });
  }
  
  return results;
}

module.exports = {
  search,
  parseResults
};
