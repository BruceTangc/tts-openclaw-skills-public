/**
 * 配置验证工具
 */

const fs = require('fs');
const path = require('path');

const CONFIG_PATH = path.join(__dirname, '../config/default.json');

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
  
  // 验证 Tavily 配置
  if (config.tavily?.enabled) {
    if (!config.tavily.api_key) {
      errors.push('Tavily 已启用但缺少 api_key');
    } else if (config.tavily.api_key === 'tvly-dev-xxx') {
      warnings.push('Tavily API Key 使用的是默认值');
    }
  }
  
  // 验证 SearXNG 配置
  if (config.searxng?.enabled) {
    if (!config.searxng.url) {
      errors.push('SearXNG 已启用但缺少 url');
    }
  }
  
  // 验证路由配置
  if (!config.routing) {
    errors.push('缺少 routing 配置');
  } else if (!config.routing.default_strategy) {
    warnings.push('未指定 default_strategy，使用默认值 auto');
  }
  
  // 验证至少有一个引擎启用
  const tavilyEnabled = config.tavily?.enabled;
  const searxngEnabled = config.searxng?.enabled;
  
  if (!tavilyEnabled && !searxngEnabled) {
    errors.push('至少需要启用一个引擎（Tavily 或 SearXNG）');
  }
  
  return {
    valid: errors.length === 0,
    errors,
    warnings,
    config
  };
}

function printValidation(result) {
  console.log('🔍 **Search Router 配置验证**\n');
  
  if (result.valid) {
    console.log('✅ 配置验证通过！\n');
  } else {
    console.log('❌ 配置验证失败\n');
  }
  
  if (result.errors.length > 0) {
    console.log('**错误**:');
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
  
  if (result.config) {
    console.log('**引擎状态**:');
    console.log(`  - 🔍 Tavily: ${result.config.tavily?.enabled ? '✅ 启用' : '❌ 禁用'}`);
    console.log(`  - 🌐 SearXNG: ${result.config.searxng?.enabled ? '✅ 启用' : '❌ 禁用'}`);
    console.log(`  - 路由策略：${result.config.routing?.default_strategy || '未配置'}`);
    console.log('');
  }
  
  if (result.valid && result.warnings.length === 0) {
    console.log('✅ 配置完美，可以直接使用');
  } else if (result.valid) {
    console.log('✅ 配置可用，建议修复警告');
  } else {
    console.log('❌ 请先修复错误再使用');
  }
}

if (require.main === module) {
  const result = validateConfig();
  printValidation(result);
  process.exit(result.valid ? 0 : 1);
}

module.exports = { validateConfig, printValidation };
