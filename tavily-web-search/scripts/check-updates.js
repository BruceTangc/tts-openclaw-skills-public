/**
 * 检查更新
 */

const fetch = require('node-fetch');
const path = require('path');
const fs = require('fs');

const DOCS_URL = 'https://docs.tavily.com/llms.txt';
const PACKAGE_PATH = path.join(__dirname, '../package.json');

async function checkUpdates() {
  console.log('🔍 检查 Tavily 文档更新...\n');
  
  try {
    // 读取当前版本
    const pkg = JSON.parse(fs.readFileSync(PACKAGE_PATH, 'utf8'));
    const currentVersion = pkg.tavily?.docs_version || 'unknown';
    const lastUpdated = pkg.tavily?.last_updated || 'never';
    
    console.log(`当前文档版本：${currentVersion}`);
    console.log(`最后更新：${lastUpdated}`);
    console.log('');
    
    // 抓取最新文档
    const response = await fetch(DOCS_URL);
    
    if (!response.ok) {
      throw new Error(`文档抓取失败：${response.statusText}`);
    }
    
    const latestContent = await response.text();
    const latestVersion = latestContent.substring(0, 20);
    
    // 比较版本
    if (latestVersion === currentVersion) {
      console.log('✅ 已是最新版本，无需更新');
      return { hasUpdates: false };
    }
    
    console.log('🆕 发现新版本!');
    console.log(`最新文档版本：${latestVersion}`);
    console.log('');
    console.log('运行以下命令更新:');
    console.log('  npm run update');
    console.log('  或');
    console.log('  node scripts/update-from-docs.js');
    
    return {
      hasUpdates: true,
      currentVersion,
      latestVersion
    };
    
  } catch (error) {
    console.error('❌ 检查更新失败:', error.message);
    return {
      hasUpdates: false,
      error: error.message
    };
  }
}

// 运行
if (require.main === module) {
  checkUpdates();
}

module.exports = { checkUpdates };
