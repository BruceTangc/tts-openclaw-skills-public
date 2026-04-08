#!/usr/bin/env node
/**
 * 获取 PDF 信息
 */

const { execSync } = require('child_process');
const path = require('path');

async function run(file) {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const scriptPath = path.join(__dirname, '..', 'scripts', 'info.py');
  
  try {
    const result = execSync(`${pythonCmd} "${scriptPath}" "${file}"`, {
      encoding: 'utf-8'
    });
    return JSON.parse(result);
  } catch (error) {
    throw new Error(`获取 PDF 信息失败：${error.message}`);
  }
}

module.exports = { run };
