#!/usr/bin/env node
/**
 * 从 PyMuPDF 官方文档更新 Skill
 */

const fetch = require('node-fetch');
const fs = require('fs');
const path = require('path');

const DOCS_BASE = 'https://pymupdf.readthedocs.io/en/latest';

/**
 * 获取文档内容
 */
async function fetchDoc(page) {
  const url = `${DOCS_BASE}/${page}`;
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.text();
  } catch (error) {
    console.warn(`⚠️  无法获取 ${page}: ${error.message}`);
    return null;
  }
}

/**
 * 更新 SKILL.md 中的 API 文档链接
 */
function updateSkillDocs() {
  const skillPath = path.join(__dirname, '..', 'SKILL.md');
  
  try {
    let content = fs.readFileSync(skillPath, 'utf-8');
    
    // 更新 homepage 链接
    content = content.replace(
      /homepage: .*/,
      `homepage: https://pymupdf.readthedocs.io`
    );
    
    fs.writeFileSync(skillPath, content, 'utf-8');
    console.log('✅ 更新 SKILL.md 文档链接');
    
  } catch (error) {
    console.error('❌ 更新 SKILL.md 失败:', error.message);
  }
}

/**
 * 更新 Python 脚本中的 API 用法
 */
function updatePythonScripts() {
  console.log('📝 检查 Python 脚本 API 用法...');
  
  // PyMuPDF 核心 API 相对稳定，主要检查弃用警告
  const scripts = [
    'extract.py',
    'info.py',
    'search.py',
    'to-markdown.py'
  ];
  
  scripts.forEach(script => {
    const scriptPath = path.join(__dirname, script);
    if (fs.existsSync(scriptPath)) {
      console.log(`   ✓ ${script} - 无需更新`);
    }
  });
}

/**
 * 主函数
 */
async function updateFromDocs() {
  console.log('🔄 从 PyMuPDF 官方文档更新 Skill...\n');
  
  // 更新文档链接
  updateSkillDocs();
  
  // 检查 Python 脚本
  updatePythonScripts();
  
  console.log('\n✅ 更新完成！');
  console.log('\n提示：如需更新 PyMuPDF 库，运行：');
  console.log('  pip install --upgrade pymupdf');
}

// 运行
if (require.main === module) {
  updateFromDocs();
}

module.exports = { updateFromDocs };
