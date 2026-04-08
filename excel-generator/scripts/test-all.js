#!/usr/bin/env node
/**
 * Excel Generator 综合测试
 */

const fs = require('fs');
const path = require('path');

async function runAllTests() {
  console.log('🧪 Excel Generator 综合测试\n');
  console.log('=' .repeat(50));
  
  const excel = require('../index.js');
  const testDir = path.join(__dirname, 'test-output');
  
  // 创建测试目录
  if (!fs.existsSync(testDir)) {
    fs.mkdirSync(testDir);
  }
  
  let passed = 0;
  let failed = 0;
  
  try {
    // 测试 1: 简单创建
    console.log('\n📊 测试 1: 简单创建 Excel');
    try {
      const testData = [
        ['姓名', '年龄', '城市'],
        ['张三', 25, '北京'],
        ['李四', 30, '上海'],
        ['王五', 28, '广州']
      ];
      
      const result1 = await excel.run({
        command: 'create',
        file: path.join(testDir, 'test-simple.xlsx'),
        data: testData
      });
      
      console.log('✅ 通过:', result1);
      passed++;
    } catch (e) {
      console.log('❌ 失败:', e.message);
      failed++;
    }
    
    // 测试 2: 带样式创建
    console.log('\n🎨 测试 2: 带样式创建');
    try {
      const styleData = [
        ['工单号', '零件编号', '尺寸', '数量', '重量'],
        ['10332', 'DI003120005A', '107x336mm', 2, '1.75kg'],
        ['10332', 'DI003120038A', '107x336mm', 2, '1.75kg']
      ];
      
      const result2 = await excel.run({
        command: 'from-data',
        file: path.join(testDir, 'test-styled.xlsx'),
        data: styleData,
        style: {
          header: { bold: true, bgColor: '4472C4', color: 'FFFFFF' },
          border: true,
          autoWidth: true
        }
      });
      
      console.log('✅ 通过:', result2);
      passed++;
    } catch (e) {
      console.log('❌ 失败:', e.message);
      failed++;
    }
    
    // 测试 3: 图表创建
    console.log('\n📈 测试 3: 图表创建');
    try {
      const chartData = [
        ['月份', '销售额'],
        ['1 月', 10000],
        ['2 月', 15000],
        ['3 月', 12000],
        ['4 月', 18000]
      ];
      
      const result3 = await excel.run({
        command: 'chart',
        file: path.join(testDir, 'test-chart.xlsx'),
        data: chartData,
        chart_type: 'bar'
      });
      
      console.log('✅ 通过:', result3);
      passed++;
    } catch (e) {
      console.log('❌ 失败:', e.message);
      failed++;
    }
    
    // 测试 4: 完整样式
    console.log('\n✨ 测试 4: 完整样式（交替行）');
    try {
      const fullData = [
        ['产品', 'Q1', 'Q2', 'Q3', 'Q4'],
        ['产品 A', 100, 150, 200, 250],
        ['产品 B', 120, 140, 180, 220],
        ['产品 C', 90, 130, 170, 210],
        ['产品 D', 110, 160, 190, 240]
      ];
      
      const result4 = await excel.run({
        command: 'from-data',
        file: path.join(testDir, 'test-full-style.xlsx'),
        data: fullData,
        style: {
          header: { 
            bold: true, 
            bgColor: '4472C4', 
            color: 'FFFFFF',
            fontSize: 12
          },
          border: true,
          autoWidth: true,
          alternatingRows: true
        }
      });
      
      console.log('✅ 通过:', result4);
      passed++;
    } catch (e) {
      console.log('❌ 失败:', e.message);
      failed++;
    }
    
    // 总结
    console.log('\n' + '='.repeat(50));
    console.log(`\n✅ 测试完成：${passed} 通过，${failed} 失败`);
    
    if (failed === 0) {
      console.log('\n🎉 所有测试通过！');
    } else {
      console.log('\n⚠️  部分测试失败，请检查依赖安装');
      console.log('\n安装依赖：');
      console.log('  pip install openpyxl xlsxwriter');
      console.log('  npm install');
    }
    
    // 清理测试文件（可选）
    // if (fs.existsSync(testDir)) {
    //   fs.rmSync(testDir, { recursive: true, force: true });
    // }
    
  } catch (error) {
    console.error('\n❌ 测试执行失败:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

// 运行测试
if (require.main === module) {
  runAllTests();
}

module.exports = { runAllTests };
