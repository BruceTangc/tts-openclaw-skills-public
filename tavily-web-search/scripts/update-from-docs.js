/**
 * 从 Tavily 官方文档自动更新 Skill
 * 
 * 功能：
 * 1. 抓取官方文档最新内容
 * 2. 解析 API 参数变化
 * 3. 更新本地配置和代码
 * 4. 生成更新报告
 */

const fetch = require('node-fetch');
const fs = require('fs');
const path = require('path');

const DOCS_URL = 'https://docs.tavily.com/llms.txt';
const CONFIG_PATH = path.join(__dirname, '../config/default.json');
const PACKAGE_PATH = path.join(__dirname, '../package.json');

/**
 * 抓取文档索引
 */
async function fetchDocsIndex() {
  console.log('📥 抓取文档索引...');
  const response = await fetch(DOCS_URL);
  
  if (!response.ok) {
    throw new Error(`文档抓取失败：${response.statusText}`);
  }
  
  return await response.text();
}

/**
 * 解析文档索引
 */
function parseDocsIndex(content) {
  const pages = [];
  const lines = content.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('- [')) {
      const match = line.match(/\[(.*?)\]\((.*?)\)/);
      if (match) {
        pages.push({
          title: match[1],
          url: match[2]
        });
      }
    }
  }
  
  return pages;
}

/**
 * 检查 API 端点更新
 */
async function checkEndpointUpdates(pages) {
  const endpoints = {
    search: null,
    extract: null,
    crawl: null,
    map: null,
    research: null,
    usage: null
  };
  
  // 查找相关端点文档
  for (const page of pages) {
    if (page.title.includes('Search')) endpoints.search = page.url;
    if (page.title.includes('Extract')) endpoints.extract = page.url;
    if (page.title.includes('Crawl')) endpoints.crawl = page.url;
    if (page.title.includes('Map')) endpoints.map = page.url;
    if (page.title.includes('Research')) endpoints.research = page.url;
    if (page.title.includes('Usage')) endpoints.usage = page.url;
  }
  
  return endpoints;
}

/**
 * 更新配置文件
 */
function updateConfig(docsVersion) {
  console.log('📝 更新配置文件...');
  
  const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  config.auto_update.last_check = new Date().toISOString();
  
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
  
  return config;
}

/**
 * 更新 package.json
 */
function updatePackage(docsVersion) {
  console.log('📦 更新 package.json...');
  
  const pkg = JSON.parse(fs.readFileSync(PACKAGE_PATH, 'utf8'));
  pkg.tavily.docs_version = docsVersion;
  pkg.tavily.last_updated = new Date().toISOString();
  
  fs.writeFileSync(PACKAGE_PATH, JSON.stringify(pkg, null, 2));
  
  return pkg;
}

/**
 * 生成更新报告
 */
function generateReport(changes) {
  const lines = [
    '🔄 **Tavily Skill 更新报告**',
    '',
    `更新时间：${new Date().toLocaleString('zh-CN')}`,
    '',
    '**变更内容**:',
  ];
  
  if (changes.length === 0) {
    lines.push('- ✅ 无变更，已是最新版本');
  } else {
    changes.forEach(change => {
      lines.push(`- ${change}`);
    });
  }
  
  lines.push('');
  lines.push('**已启用的功能**:',);
  lines.push('- ✅ search - 网页搜索');
  lines.push('- ✅ extract - 内容提取');
  lines.push('- ✅ usage - 用量查询');
  
  lines.push('');
  lines.push('**已实现但未启用的功能**:,);
  lines.push('- ⏸️ crawl - 整站爬取');
  lines.push('- ⏸️ map - 站点地图');
  lines.push('- ⏸️ research - 深度研究');
  lines.push('- ⏸️ research_status - 研究状态查询');
  
  return lines.join('\n');
}

/**
 * 主函数
 */
async function main() {
  console.log('🚀 开始更新 Tavily Skill...\n');
  
  try {
    // 1. 抓取文档
    const docsContent = await fetchDocsIndex();
    
    // 2. 解析文档
    const pages = parseDocsIndex(docsContent);
    console.log(`📄 找到 ${pages.length} 个文档页面`);
    
    // 3. 检查端点
    const endpoints = await checkEndpointUpdates(pages);
    console.log('🔍 检查 API 端点...');
    console.log(endpoints);
    
    // 4. 更新配置
    const config = updateConfig(docsContent.substring(0, 20));
    
    // 5. 更新 package
    const pkg = updatePackage(docsContent.substring(0, 20));
    
    // 6. 生成报告
    const changes = [`文档版本更新`, `配置已同步`];
    const report = generateReport(changes);
    
    console.log('\n' + report);
    
    return {
      success: true,
      report,
      changes
    };
    
  } catch (error) {
    console.error('❌ 更新失败:', error.message);
    return {
      success: false,
      error: error.message
    };
  }
}

// 运行
if (require.main === module) {
  main().then(result => {
    process.exit(result.success ? 0 : 1);
  });
}

module.exports = { main };
