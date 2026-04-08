#!/usr/bin/env node
/**
 * From-Data 命令封装
 */

const { execSync } = require('child_process');
const path = require('path');

async function run(file, data, sheetName = 'Sheet1', style = null) {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const scriptPath = path.join(__dirname, '..', 'scripts', 'create.py');
  
  const args = [
    `--file "${file}"`,
    `--sheet "${sheetName}"`,
    `--data '${JSON.stringify(data)}'`
  ];
  
  if (style) {
    args.push(`--style '${JSON.stringify(style)}'`);
  }
  
  try {
    const result = execSync(`${pythonCmd} "${scriptPath}" ${args.join(' ')}`, {
      encoding: 'utf-8'
    });
    return JSON.parse(result);
  } catch (error) {
    throw new Error(`生成 Excel 失败：${error.message}`);
  }
}

module.exports = { run };
