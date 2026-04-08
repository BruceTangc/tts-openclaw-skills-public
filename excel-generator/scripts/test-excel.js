#!/usr/bin/env node
/**
 * Excel Generator 测试脚本
 */

const fs = require('fs');
const path = require('path');

async function runTest() {
  console.log('🧪 Excel Generator 测试\n');
  
  const excel = require('../index.js');
  const testFile = path.join(__dirname, 'test-output.xlsx');
  
  try {
    // 测试 1: 简单创建
    console.log('📊 测试 1: 简单创建 Excel');
    const testData = [
      ['姓名', '年龄', '城市'],
      ['张三', 25, '北京'],
      ['李四', 30, '上海'],
      ['王五', 28, '广州']
    ];
    
    const result1 = await excel.run({
      command: 'create',
      file: testFile,
      data: testData
    });
    
    console.log(result1);
    console.log('✅ 测试 1 通过\n');
    
    // 测试 2: 带样式
    console.log('🎨 测试 2: 带样式创建');
    const styleResult = await excel.run({
      command: 'from-data',
      file: testFile.replace('.xlsx', '-styled.xlsx'),
      data: [
        ['工单号', '零件编号', '尺寸', '数量', '重量'],
        ['10332', 'DI003120005A', '107x336mm', 2, '1.75kg'],
        ['10332', 'DI003120038A', '107x336mm', 2, '1.75kg']
      ],
      style: {
        header: { bold: true, bgColor: '4472C4', color: 'FFFFFF' },
        border: true,
        autoWidth: true
      }
    });
    
    console.log(styleResult);
    console.log('✅ 测试 2 通过\n');
    
    // 清理测试文件
    if (fs.existsSync(testFile)) {
      fs.unlinkSync(testFile);
    }
    if (fs.existsSync(testFile.replace('.xlsx', '-styled.xlsx'))) {
      fs.unlinkSync(testFile.replace('.xlsx', '-styled.xlsx'));
    }
    
    console.log('✅ 所有测试通过！');
    
  } catch (error) {
    console.error('❌ 测试失败:', error.message);
    process.exit(1);
  }
}

// 运行测试
if (require.main === module) {
  runTest();
}

module.exports = { runTest };
