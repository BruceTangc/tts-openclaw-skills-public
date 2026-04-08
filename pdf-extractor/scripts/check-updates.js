#!/usr/bin/env node
/**
 * 检查 PyMuPDF 文档更新
 */

const fetch = require('node-fetch');
const fs = require('fs');
const path = require('path');

const PYMUPDF_DOCS_URL = 'https://pymupdf.readthedocs.io/en/latest/changelog.html';
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
  console.log('🔍 检查 PyMuPDF 文档更新...\n');
  
  const currentVersion = getCurrentVersion();
  console.log(`当前 Skill 版本：v${currentVersion}`);
  
  try {
    // 获取 PyMuPDF 最新版本信息
    const response = await fetch('https://pypi.org/pypi/pymupdf/json');
    const data = await response.json();
    const latestVersion = data.info.version;
    
    console.log(`PyMuPDF 最新版本：v${latestVersion}`);
    
    // 检查本地 pymupdf 版本
    const { execSync } = require('child_process');
    try {
      const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
      const installed = execSync(`${pythonCmd} -c "import fitz; print(fitz.__version__)"`, {
        encoding: 'utf-8'
      }).trim();
      console.log(`本地 PyMuPDF 版本：v${installed}`);
      
      if (installed !== latestVersion) {
        console.log('\n⚠️  发现新版本！');
        console.log(`   运行：pip install --upgrade pymupdf`);
      } else {
        console.log('\n✅ PyMuPDF 已是最新版本');
      }
    } catch (e) {
      console.log('\n⚠️  无法检查本地版本，请手动运行：pip show pymupdf');
    }
    
    // 检查 Skill 更新
    console.log('\n📦 检查 Skill 更新...');
    console.log('   请访问：https://github.com/BruceTangc/tts-openclaw-skills-public');
    
    return {
      skillVersion: currentVersion,
      pymupdfLatest: latestVersion,
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
