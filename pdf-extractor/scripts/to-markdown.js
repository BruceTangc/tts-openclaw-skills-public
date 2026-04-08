#!/usr/bin/env node
/**
 * PDF 转 Markdown
 */

const { execSync } = require('child_process');
const path = require('path');

async function run(file, output = null) {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const scriptPath = path.join(__dirname, '..', 'scripts', 'to-markdown.py');
  
  const args = [`"${file}"`];
  if (output) {
    args.push(`--output "${output}"`);
  }
  
  try {
    const result = execSync(`${pythonCmd} "${scriptPath}" ${args.join(' ')}`, {
      encoding: 'utf-8'
    });
    return JSON.parse(result);
  } catch (error) {
    throw new Error(`转换失败：${error.message}`);
  }
}

module.exports = { run };
