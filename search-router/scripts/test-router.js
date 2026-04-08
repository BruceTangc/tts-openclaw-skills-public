/**
 * 路由测试脚本
 */

const router = require('../index.js');

async function runTests() {
  console.log('╔════════════════════════════════════════════════════════╗');
  console.log('║        Search Router - 智能路由测试                    ║');
  console.log('╚════════════════════════════════════════════════════════╝\n');
  
  const tests = [
    {
      name: '技术查询（应该使用 Tavily）',
      query: 'OpenClaw 安装教程',
      expected: 'tavily'
    },
    {
      name: '新闻查询（应该使用 SearXNG）',
      query: '最新 AI 新闻',
      expected: 'searxng'
    },
    {
      name: '实时查询（应该使用 SearXNG）',
      query: '刚刚发生的科技事件',
      expected: 'searxng'
    },
    {
      name: '研究查询（应该使用 Tavily）',
      query: 'AI 框架对比分析',
      expected: 'tavily'
    },
    {
      name: '通用查询（应该使用双引擎）',
      query: '人工智能',
      expected: 'both'
    }
  ];
  
  let passed = 0;
  let failed = 0;
  
  for (const test of tests) {
    console.log(`📋 测试：${test.name}`);
    console.log(`查询："${test.query}"`);
    
    try {
      // 测试分类
      const classification = router.classifyQuery(test.query);
      console.log(`分类结果：${classification.type} (${(classification.confidence * 100).toFixed(1)}%)`);
      console.log(`预期引擎：${test.expected}`);
      console.log(`实际引擎：${classification.engine}`);
      
      if (classification.engine === test.expected || 
          (test.expected === 'both' && classification.engine === 'both')) {
        console.log('✅ 通过\n');
        passed++;
      } else {
        console.log('⚠️  结果不符（可能是置信度低）\n');
        failed++;
      }
    } catch (error) {
      console.log(`❌ 失败：${error.message}\n`);
      failed++;
    }
  }
  
  console.log('═══════════════════════════════════════════════════════');
  console.log(`测试结果：${passed} 通过，${failed} 失败，成功率 ${(passed / tests.length * 100).toFixed(1)}%`);
  console.log('═══════════════════════════════════════════════════════\n');
  
  // 测试帮助信息
  console.log('❓ 帮助信息:');
  console.log('───────────────────────────────────────────────────────');
  console.log(router.help());
}

runTests().catch(console.error);
