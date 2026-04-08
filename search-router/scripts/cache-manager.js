#!/usr/bin/env node
/**
 * 缓存管理工具
 */

const { cache } = require('../utils/cache');

const command = process.argv[2];

switch (command) {
  case 'stats':
    const stats = cache.stats();
    console.log('📊 缓存统计:');
    console.log(`  有效缓存：${stats.valid}`);
    console.log(`  过期缓存：${stats.expired}`);
    console.log(`  总计：${stats.total}`);
    console.log(`  TTL: ${stats.ttl}`);
    break;
    
  case 'clear':
    cache.clear();
    console.log('✅ 缓存已清空');
    break;
    
  case 'help':
  default:
    console.log('缓存管理工具');
    console.log('');
    console.log('用法:');
    console.log('  npm run cache stats   - 查看缓存统计');
    console.log('  npm run cache clear   - 清空缓存');
    console.log('');
    console.log('配置:');
    console.log('  TTL: 5 分钟');
    console.log('  最大缓存数：1000 条');
    break;
}
