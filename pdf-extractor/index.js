#!/usr/bin/env node
/**
 * PDF Extractor - PyMuPDF 文本提取
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * 解析用户输入
 */
function parseInput(input) {
  if (typeof input === 'string') {
    return { command: 'extract', file: input };
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
function formatOutput(result, command) {
  if (command === 'info') {
    return formatInfo(result);
  } else if (command === 'search') {
    return formatSearch(result);
  } else {
    return formatExtract(result);
  }
}

/**
 * 格式化 PDF 信息
 */
function formatInfo(info) {
  let output = '📄 **PDF 信息**\n\n';
  output += `文件：${info.file}\n`;
  output += `页数：${info.page_count}\n`;
  
  if (info.metadata) {
    if (info.metadata.title) output += `标题：${info.metadata.title}\n`;
    if (info.metadata.author) output += `作者：${info.metadata.author}\n`;
    if (info.metadata.creationDate) output += `创建时间：${info.metadata.creationDate}\n`;
    if (info.metadata.modificationDate) output += `修改时间：${info.metadata.modificationDate}\n`;
  }
  
  return output;
}

/**
 * 格式化搜索结果
 */
function formatSearch(result) {
  let output = `🔍 **找到 ${result.matches.length} 个匹配**\n\n`;
  
  if (result.matches.length === 0) {
    output += '未找到匹配内容。';
    return output;
  }
  
  result.matches.forEach((match, idx) => {
    output += `**匹配 ${idx + 1}** (第 ${match.page} 页)\n`;
    output += `\`${match.text}\`\n\n`;
  });
  
  return output;
}

/**
 * 格式化提取结果
 */
function formatExtract(result) {
  return result.content;
}

/**
 * 主函数
 */
async function run(input) {
  const params = parseInput(input);
  const { command = 'extract', file, pages, query, case_sensitive, output, format = 'markdown' } = params;
  
  // 验证文件存在
  if (!file) {
    throw new Error('缺少文件路径参数');
  }
  
  if (!fs.existsSync(file)) {
    throw new Error(`文件不存在：${file}`);
  }
  
  // 验证文件扩展名
  if (!file.toLowerCase().endsWith('.pdf')) {
    throw new Error('只支持 PDF 文件');
  }
  
  let result;
  
  switch (command) {
    case 'extract':
      const pageArgs = pages ? `--pages ${pages.join(',')}` : '';
      result = runPythonScript('extract.py', [`"${file}"`, pageArgs, `--format ${format}`]);
      break;
      
    case 'info':
      result = runPythonScript('info.js', [`"${file}"`]);
      break;
      
    case 'search':
      if (!query) {
        throw new Error('缺少搜索关键词');
      }
      const caseArg = case_sensitive ? '--case-sensitive' : '';
      result = runPythonScript('search.py', [`"${file}"`, `--query "${query}"`, caseArg]);
      break;
      
    case 'to-markdown':
      const outputArgs = output ? `--output "${output}"` : '';
      result = runPythonScript('to-markdown.js', [`"${file}"`, outputArgs]);
      break;
      
    default:
      throw new Error(`未知命令：${command}`);
  }
  
  return formatOutput(result, command);
}

module.exports = { run };
