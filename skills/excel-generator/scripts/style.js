#!/usr/bin/env node
/**
 * Style 命令封装
 */

const { execSync } = require('child_process');
const path = require('path');

async function run(file, style) {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const scriptPath = path.join(__dirname, '..', 'scripts', 'style.py');
  
  const args = [
    `--file "${file}"`,
    `--style '${JSON.stringify(style)}'`
  ];
  
  try {
    const result = execSync(`${pythonCmd} "${scriptPath}" ${args.join(' ')}`, {
      encoding: 'utf-8'
    });
    return JSON.parse(result);
  } catch (error) {
    throw new Error(`应用样式失败：${error.message}`);
  }
}

module.exports = { run };
