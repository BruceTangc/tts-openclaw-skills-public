#!/usr/bin/env node
/**
 * 从官方文档更新
 */

const fs = require('fs');
const path = require('path');

/**
 * 更新 SKILL.md 中的文档链接
 */
function updateSkillDocs() {
  const skillPath = path.join(__dirname, '..', 'SKILL.md');
  
  try {
    let content = fs.readFileSync(skillPath, 'utf-8');
    
    // 更新 homepage 链接
    content = content.replace(
      /homepage: .*/,
      `homepage: https://openpyxl.readthedocs.io`
    );
    
    fs.writeFileSync(skillPath, content, 'utf-8');
    console.log('✅ 更新 SKILL.md 文档链接');
    
  } catch (error) {
    console.error('❌ 更新 SKILL.md 失败:', error.message);
  }
}

/**
 * 主函数
 */
async function updateFromDocs() {
  console.log('🔄 从 openpyxl/xlsxwriter 官方文档更新 Skill...\n');
  
  // 更新文档链接
  updateSkillDocs();
  
  console.log('\n✅ 更新完成！');
  console.log('\n提示：如需更新 Python 库，运行：');
  console.log('  pip install --upgrade openpyxl xlsxwriter');
}

// 运行
if (require.main === module) {
  updateFromDocs();
}

module.exports = { updateFromDocs };
