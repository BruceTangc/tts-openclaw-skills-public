#!/usr/bin/env node
/**
 * Chart 命令封装
 */

const { execSync } = require('child_process');
const path = require('path');

async function run(file, data, chartType = 'bar') {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const scriptPath = path.join(__dirname, '..', 'scripts', 'chart.py');
  
  const args = [
    `--file "${file}"`,
    `--data '${JSON.stringify(data)}'`,
    `--chart-type "${chartType}"`
  ];
  
  try {
    const result = execSync(`${pythonCmd} "${scriptPath}" ${args.join(' ')}`, {
      encoding: 'utf-8'
    });
    return JSON.parse(result);
  } catch (error) {
    throw new Error(`创建图表失败：${error.message}`);
  }
}

module.exports = { run };
