/**
 * 配置验证工具
 * 
 * 验证配置文件的完整性和正确性
 */

const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, '../config/default.json');
const PACKAGE_PATH = path.join(__dirname, '../package.json');

/**
 * 验证配置
 */
function validateConfig() {
  const errors = [];
  const warnings = [];
  
  // 读取配置
  let config;
  try {
    config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  } catch (error) {
    errors.push(`配置文件读取失败：${error.message}`);
    return { valid: false, errors, warnings };
  }
  
  // 验证必填字段
  if (!config.api_key) {
    errors.push('缺少必填字段：api_key');
  } else if (config.api_key === 'tvly-dev-xxx' || config.api_key.startsWith('tvly-your')) {
    warnings.push('API Key 使用的是默认值，请替换为真实的 Tavily API Key');
  } else if (!config.api_key.startsWith('tvly-')) {
    warnings.push('API Key 格式可能不正确（应该以 tvly- 开头）');
  }
  
  if (!config.base_url) {
    errors.push('缺少必填字段：base_url');
  }
  
  // 验证命令配置
  if (!config.commands) {
    errors.push('缺少命令配置：commands');
  } else {
    const requiredCommands = ['search', 'extract', 'usage'];
    for (const cmd of requiredCommands) {
      if (!config.commands[cmd]) {
        errors.push(`缺少必需命令配置：${cmd}`);
      } else if (typeof config.commands[cmd].enabled !== 'boolean') {
        warnings.push(`命令 ${cmd} 的 enabled 字段应该是布尔值`);
      }
    }
  }
  
  // 验证默认参数
  if (config.defaults) {
    if (config.defaults.max_results && (config.defaults.max_results < 1 || config.defaults.max_results > 20)) {
      errors.push('defaults.max_results 必须在 1-20 之间');
    }
    
    const validDepths = ['basic', 'advanced', 'fast', 'ultra-fast'];
    if (config.defaults.search_depth && !validDepths.includes(config.defaults.search_depth)) {
      errors.push(`defaults.search_depth 必须是以下值之一：${validDepths.join(', ')}`);
    }
  }
  
  // 验证自动更新配置
  if (config.auto_update) {
    if (config.auto_update.check_interval_hours && config.auto_update.check_interval_hours < 1) {
      warnings.push('auto_update.check_interval_hours 应该大于 0');
    }
  }
  
  // 验证 package.json
  try {
    const pkg = JSON.parse(fs.readFileSync(PACKAGE_PATH, 'utf8'));
    
    if (!pkg.name) {
      warnings.push('package.json 缺少 name 字段');
    }
    
    if (!pkg.version) {
      warnings.push('package.json 缺少 version 字段');
    }
    
    if (!pkg.tavily) {
      warnings.push('package.json 缺少 tavily 配置字段');
    }
  } catch (error) {
    warnings.push(`package.json 读取失败：${error.message}`);
  }
  
  return {
    valid: errors.length === 0,
    errors,
    warnings,
    config
  };
}

/**
 * 打印验证结果
 */
function printValidation(result) {
  console.log('🔍 **配置验证报告**\n');
  
  if (result.valid) {
    console.log('✅ 配置验证通过！\n');
  } else {
    console.log('❌ 配置验证失败\n');
  }
  
  if (result.errors.length > 0) {
    console.log('**错误**:',);
    result.errors.forEach(err => {
      console.log(`  ❌ ${err}`);
    });
    console.log('');
  }
  
  if (result.warnings.length > 0) {
    console.log('**警告**:');
    result.warnings.forEach(warn => {
      console.log(`  ⚠️  ${warn}`);
    });
    console.log('');
  }
  
  // 显示配置摘要
  if (result.config) {
    console.log('**配置摘要**:');
    console.log(`  - API Key: ${result.config.api_key.substring(0, 15)}...`);
    console.log(`  - Base URL: ${result.config.base_url}`);
    
    const enabled = Object.entries(result.config.commands || {})
      .filter(([_, cfg]) => cfg.enabled)
      .map(([name, _]) => name)
      .join(', ');
    
    console.log(`  - 已启用命令：${enabled || '无'}`);
    console.log('');
  }
  
  console.log('**建议**:');
  if (result.valid && result.warnings.length === 0) {
    console.log('  ✅ 配置完美，可以直接使用');
  } else if (result.valid) {
    console.log('  ✅ 配置可用，但建议修复警告');
  } else {
    console.log('  ❌ 请先修复错误再使用');
  }
}

// 命令行运行
if (require.main === module) {
  const result = validateConfig();
  printValidation(result);
  process.exit(result.valid ? 0 : 1);
}

module.exports = { validateConfig, printValidation };
