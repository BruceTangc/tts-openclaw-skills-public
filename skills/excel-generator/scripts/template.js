#!/usr/bin/env node
/**
 * Template 命令封装
 */

const { execSync } = require('child_process');
const path = require('path');

async function run(template, output, data = null, replacements = null) {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const scriptPath = path.join(__dirname, '..', 'scripts', 'template.py');
  
  const args = [
    `--template "${template}"`,
    `--output "${output}"`
  ];
  
  if (data) {
    args.push(`--data '${JSON.stringify(data)}'`);
  }
  
  if (replacements) {
    args.push(`--replacements '${JSON.stringify(replacements)}'`);
  }
  
  try {
    const result = execSync(`${pythonCmd} "${scriptPath}" ${args.join(' ')}`, {
      encoding: 'utf-8'
    });
    return JSON.parse(result);
  } catch (error) {
    throw new Error(`填充模板失败：${error.message}`);
  }
}

module.exports = { run };
