#!/usr/bin/env node
/**
 * Excel Generator - 基于 openpyxl 和 xlsxwriter
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * 解析用户输入
 */
function parseInput(input) {
  if (typeof input === 'string') {
    return { command: 'create', file: input };
  }
  return input || {};
}

/**
 * 执行 Python 脚本
 */
function runPythonScript(script, args) {
  const scriptPath = path.join(__dirname, 'scripts', script);
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  
  try {
    const result = execSync(`${pythonCmd} "${scriptPath}" ${args.join(' ')}`, {
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024 // 10MB
    });
    return JSON.parse(result);
  } catch (error) {
    throw new Error(`Python 脚本执行失败：${error.message}`);
  }
}

/**
 * 格式化输出
 */
function formatOutput(result, command, file) {
  if (result.success) {
    return `✅ **Excel 生成成功**\n\n📄 文件：${file}\n📊 工作表：${result.sheet_count || 1}\n📝 行数：${result.row_count || 0}\n\n文件已保存到：${result.output_file}`;
  } else {
    throw new Error(result.error || '生成失败');
  }
}

/**
 * 主函数
 */
async function run(input) {
  const params = parseInput(input);
  const { 
    command = 'create', 
    file, 
    data, 
    sheet_name = 'Sheet1',
    style,
    chart_type
  } = params;
  
  // 验证参数
  if (!file) {
    throw new Error('缺少文件路径参数');
  }
  
  if (!file.toLowerCase().endsWith('.xlsx')) {
    throw new Error('文件必须是 .xlsx 格式');
  }
  
  // 确保输出目录存在
  const outputDir = path.dirname(file);
  if (outputDir && outputDir !== '.' && !fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  let result;
  
  switch (command) {
    case 'create':
      if (!data) {
        throw new Error('缺少 data 参数');
      }
      result = runPythonScript('create.js', [
        `--file "${file}"`,
        `--sheet "${sheet_name}"`,
        `--data '${JSON.stringify(data)}'`
      ]);
      break;
      
    case 'from-data':
      if (!data) {
        throw new Error('缺少 data 参数');
      }
      const styleArg = style ? `--style '${JSON.stringify(style)}'` : '';
      // 直接调用 create.py，传递样式参数
      result = runPythonScript('create.py', [
        `--file "${file}"`,
        `--sheet "${sheet_name}"`,
        `--data '${JSON.stringify(data)}'`,
        styleArg
      ]);
      break;
      
    case 'style':
      if (!file) {
        throw new Error('缺少 file 参数');
      }
      // style 命令直接调用 style.py，不需要 data
      result = runPythonScript('style.py', [
        `--file "${file}"`,
        `--style '${JSON.stringify(style || {})}'`
      ]);
      break;
      
    case 'chart':
      if (!data) {
        throw new Error('缺少 data 参数');
      }
      result = runPythonScript('chart.py', [
        `--file "${file}"`,
        `--data '${JSON.stringify(data)}'`,
        `--chart-type "${chart_type || 'bar'}"`
      ]);
      break;
      
    case 'template':
      const templateArgs = [
        `--template "${params.template}"`,
        `--output "${file}"`
      ];
      if (data) templateArgs.push(`--data '${JSON.stringify(data)}'`);
      if (params.replacements) templateArgs.push(`--replacements '${JSON.stringify(params.replacements)}'`);
      result = runPythonScript('template.py', templateArgs);
      break;
      
    default:
      throw new Error(`未知命令：${command}`);
  }
  
  return formatOutput(result, command, file);
}

module.exports = { run };
