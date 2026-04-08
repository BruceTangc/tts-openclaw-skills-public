#!/usr/bin/env node
/**
 * 检查更新
 */

const fetch = require('node-fetch');
const fs = require('fs');
const path = require('path');

const VERSION_FILE = path.join(__dirname, '..', '_meta.json');

/**
 * 获取当前版本
 */
function getCurrentVersion() {
  try {
    const meta = JSON.parse(fs.readFileSync(VERSION_FILE, 'utf-8'));
    return meta.version || '1.0.0';
  } catch {
    return '1.0.0';
  }
}

/**
 * 检查更新
 */
async function checkUpdates() {
  console.log('🔍 检查 Excel Generator 更新...\n');
  
  const currentVersion = getCurrentVersion();
  console.log(`当前 Skill 版本：v${currentVersion}`);
  
  try {
    // 检查 openpyxl 版本
    const { execSync } = require('child_process');
    try {
      const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
      const openpyxlVer = execSync(`${pythonCmd} -c "import openpyxl; print(openpyxl.__version__)"`, {
        encoding: 'utf-8'
      }).trim();
      console.log(`openpyxl 版本：v${openpyxlVer}`);
      
      // 检查 PyPI 最新版本
      const response = await fetch('https://pypi.org/pypi/openpyxl/json');
      const data = await response.json();
      const latest = data.info.version;
      console.log(`openpyxl 最新版本：v${latest}`);
      
      if (openpyxlVer !== latest) {
        console.log('\n⚠️  发现新版本！');
        console.log(`   运行：pip install --upgrade openpyxl`);
      } else {
        console.log('\n✅ openpyxl 已是最新版本');
      }
      
      // 检查 xlsxwriter
      const xlsxVer = execSync(`${pythonCmd} -c "import xlsxwriter; print(xlsxwriter.__version__)"`, {
        encoding: 'utf-8'
      }).trim();
      console.log(`\nxlsxwriter 版本：v${xlsxVer}`);
      
      const xlsxResponse = await fetch('https://pypi.org/pypi/xlsxwriter/json');
      const xlsxData = await xlsxResponse.json();
      const xlsxLatest = xlsxData.info.version;
      console.log(`xlsxwriter 最新版本：v${xlsxLatest}`);
      
      if (xlsxVer !== xlsxLatest) {
        console.log(`   运行：pip install --upgrade xlsxwriter`);
      }
      
    } catch (e) {
      console.log('\n⚠️  无法检查版本，请手动运行：pip show openpyxl xlsxwriter');
    }
    
    // 检查 Skill 更新
    console.log('\n📦 检查 Skill 更新...');
    console.log('   请访问：https://github.com/BruceTangc/tts-openclaw-skills-public');
    
    return {
      skillVersion: currentVersion,
      hasUpdate: false
    };
    
  } catch (error) {
    console.error('❌ 检查更新失败:', error.message);
    return null;
  }
}

// 运行
if (require.main === module) {
  checkUpdates();
}

module.exports = { checkUpdates };
