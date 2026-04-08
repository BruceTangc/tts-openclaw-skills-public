#!/usr/bin/env node
/**
 * PDF 转 Excel 集成测试
 * 使用之前的两个 Bystronic 切割工单 PDF
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

async function testPDFToExcel() {
  console.log('🧪 PDF 转 Excel 集成测试\n');
  console.log('=' .repeat(60));
  
  const outputDir = path.join(__dirname, 'test-output');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }
  
  // PDF 文件路径
  const pdf8mm = '/home/admin/.openclaw/media/inbound/8mm---655a50f5-34f1-4e6b-b883-8445fcf7ecf2.pdf';
  const pdf4mm = '/home/admin/.openclaw/media/inbound/4mm---8701ca21-bc63-44d2-9f44-f3b438036bff.pdf';
  
  // 从 PDF 提取的数据（根据之前的提取结果）
  const data8mm = {
    jobNo: '10332',
    date: '2026-03-25',
    material: '8mm 钢板',
    sheetSize: '3000x1510mm',
    sheetWeight: '20.86 kg',
    cuttingTime: '7.13 min',
    utilization: '43.6%',
    parts: [
      ['DI003120005A-A-q235-8mm-1j', '107x336mm', 2, '0.93min', '1.75kg'],
      ['DI003120038-A-q235-8mm-1j', '107x336mm', 2, '0.93min', '1.75kg'],
      ['DI003120021A-A-q235-8mm-1j', '84x313mm', 2, '0.86min', '1.19kg'],
      ['DI003120039-A-q235-8mm-1j', '84x314mm', 2, '0.86min', '1.19kg']
    ]
  };
  
  const data4mm = {
    jobNo: '10332',
    date: '2026-03-25',
    material: '4mm 钢板',
    sheetSize: '3000x1510mm',
    sheetWeight: '2.82 kg',
    cuttingTime: '2.41 min',
    utilization: '28.8%',
    parts: [
      ['SBS99020495-q235-4mm-', '105x105mm', 6, '0.41min', '0.33kg']
    ]
  };
  
  const excel = require('../index.js');
  
  try {
    // 测试 1: 创建 8mm 工单报表
    console.log('\n📊 测试 1: 创建 8mm 工单 Excel 报表');
    const data8mmRows = [
      ['工单号', '日期', '材料', '板材尺寸', '板材重量', '切割时间', '利用率'],
      [data8mm.jobNo, data8mm.date, data8mm.material, data8mm.sheetSize, data8mm.sheetWeight, data8mm.cuttingTime, data8mm.utilization],
      [],
      ['零件编号', '尺寸', '数量', '切割时间', '重量'],
      ...data8mm.parts
    ];
    
    const result1 = await excel.run({
      command: 'from-data',
      file: path.join(outputDir, '工单 -10332-8mm.xlsx'),
      data: data8mmRows,
      style: {
        header: { 
          bold: true, 
          bgColor: '4472C4', 
          color: 'FFFFFF',
          fontSize: 11
        },
        border: true,
        autoWidth: true,
        alternatingRows: true
      }
    });
    
    console.log('✅ 8mm 工单创建成功:', result1.output_file);
    
    // 测试 2: 创建 4mm 工单报表
    console.log('\n📊 测试 2: 创建 4mm 工单 Excel 报表');
    const data4mmRows = [
      ['工单号', '日期', '材料', '板材尺寸', '板材重量', '切割时间', '利用率'],
      [data4mm.jobNo, data4mm.date, data4mm.material, data4mm.sheetSize, data4mm.sheetWeight, data4mm.cuttingTime, data4mm.utilization],
      [],
      ['零件编号', '尺寸', '数量', '切割时间', '重量'],
      ...data4mm.parts
    ];
    
    const result2 = await excel.run({
      command: 'from-data',
      file: path.join(outputDir, '工单 -10332-4mm.xlsx'),
      data: data4mmRows,
      style: {
        header: { 
          bold: true, 
          bgColor: '70AD47', 
          color: 'FFFFFF',
          fontSize: 11
        },
        border: true,
        autoWidth: true,
        alternatingRows: true
      }
    });
    
    console.log('✅ 4mm 工单创建成功:', result2.output_file);
    
    // 测试 3: 创建合并报表
    console.log('\n📊 测试 3: 创建合并报表（两个工单对比）');
    const combinedData = [
      ['工单号', '材料', '板材重量', '切割时间', '利用率', '零件种类', '总数量'],
      ['10332', '8mm 钢板', data8mm.sheetWeight, data8mm.cuttingTime, data8mm.utilization, `${data8mm.parts.length}种`, '8 件'],
      ['10332', '4mm 钢板', data4mm.sheetWeight, data4mm.cuttingTime, data4mm.utilization, `${data4mm.parts.length}种`, '6 件']
    ];
    
    const result3 = await excel.run({
      command: 'from-data',
      file: path.join(outputDir, '工单 -10332-合并报表.xlsx'),
      data: combinedData,
      style: {
        header: { 
          bold: true, 
          bgColor: 'ED7D31', 
          color: 'FFFFFF',
          fontSize: 12
        },
        border: true,
        autoWidth: true,
        alternatingRows: true
      }
    });
    
    console.log('✅ 合并报表创建成功:', result3.output_file);
    
    // 测试 4: 创建图表
    console.log('\n📈 测试 4: 创建利用率对比图表');
    const chartData = [
      ['工单', '利用率 (%)'],
      ['8mm 工单', 43.6],
      ['4mm 工单', 28.8]
    ];
    
    const result4 = await excel.run({
      command: 'chart',
      file: path.join(outputDir, '工单 -10332-利用率对比.xlsx'),
      data: chartData,
      chart_type: 'bar'
    });
    
    console.log('✅ 利用率对比图表创建成功:', result4.output_file);
    
    // 总结
    console.log('\n' + '='.repeat(60));
    console.log('\n✅ 所有测试完成！\n');
    console.log('📁 生成的文件：');
    console.log('   1. 工单 -10332-8mm.xlsx');
    console.log('   2. 工单 -10332-4mm.xlsx');
    console.log('   3. 工单 -10332 - 合并报表.xlsx');
    console.log('   4. 工单 -10332 - 利用率对比.xlsx');
    console.log(`\n📂 文件位置：${outputDir}`);
    
    // 列出文件
    const files = fs.readdirSync(outputDir);
    console.log('\n📄 实际文件列表:');
    files.forEach(file => {
      const stat = fs.statSync(path.join(outputDir, file));
      console.log(`   - ${file} (${(stat.size / 1024).toFixed(2)} KB)`);
    });
    
  } catch (error) {
    console.error('\n❌ 测试失败:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

// 运行测试
if (require.main === module) {
  testPDFToExcel();
}

module.exports = { testPDFToExcel };
