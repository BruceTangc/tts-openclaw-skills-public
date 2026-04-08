/**
 * 统一缓存层
 * 
 * 为所有搜索引擎提供缓存支持
 */

const fs = require('fs');
const path = require('path');

const CACHE_DIR = path.join(__dirname, '../.cache');
const CACHE_FILE = path.join(CACHE_DIR, 'search-cache.json');
const CACHE_TTL = 5 * 60 * 1000; // 5 分钟
const MAX_CACHE_SIZE = 1000; // 最多缓存 1000 条

// 确保缓存目录存在
if (!fs.existsSync(CACHE_DIR)) {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
}

/**
 * 缓存类
 */
class SearchCache {
  constructor() {
    this.cache = this._load();
    this._cleanup();
  }

  /**
   * 加载缓存
   */
  _load() {
    try {
      if (fs.existsSync(CACHE_FILE)) {
        const data = fs.readFileSync(CACHE_FILE, 'utf8');
        return JSON.parse(data);
      }
    } catch (error) {
      console.warn('⚠️  加载缓存失败:', error.message);
    }
    return {};
  }

  /**
   * 保存缓存
   */
  _save() {
    try {
      fs.writeFileSync(CACHE_FILE, JSON.stringify(this.cache, null, 2));
    } catch (error) {
      console.warn('⚠️  保存缓存失败:', error.message);
    }
  }

  /**
   * 生成缓存键
   */
  _makeKey(engine, query, options) {
    return `${engine}:${query}:${JSON.stringify(options || {})}`;
  }

  /**
   * 获取缓存
   */
  get(engine, query, options = {}) {
    const key = this._makeKey(engine, query, options);
    const item = this.cache[key];

    if (!item) {
      return null;
    }

    // 检查是否过期
    const age = Date.now() - item.timestamp;
    if (age > CACHE_TTL) {
      delete this.cache[key];
      this._save();
      return null;
    }

    return item.data;
  }

  /**
   * 设置缓存
   */
  set(engine, query, data, options = {}) {
    const key = this._makeKey(engine, query, options);

    this.cache[key] = {
      data,
      timestamp: Date.now(),
      engine,
      query
    };

    // 限制缓存大小
    const keys = Object.keys(this.cache);
    if (keys.length > MAX_CACHE_SIZE) {
      // 删除最旧的 10%
      const sortedKeys = keys.sort((a, b) => 
        this.cache[a].timestamp - this.cache[b].timestamp
      );
      const deleteCount = Math.floor(MAX_CACHE_SIZE * 0.1);
      for (let i = 0; i < deleteCount; i++) {
        delete this.cache[sortedKeys[i]];
      }
    }

    this._save();
  }

  /**
   * 清理过期缓存
   */
  _cleanup() {
    const now = Date.now();
    let cleaned = 0;

    for (const [key, item] of Object.entries(this.cache)) {
      if (now - item.timestamp > CACHE_TTL) {
        delete this.cache[key];
        cleaned++;
      }
    }

    if (cleaned > 0) {
      console.log(`🧹 清理了 ${cleaned} 条过期缓存`);
      this._save();
    }
  }

  /**
   * 清空缓存
   */
  clear() {
    this.cache = {};
    this._save();
    console.log('✅ 缓存已清空');
  }

  /**
   * 获取缓存统计
   */
  stats() {
    const now = Date.now();
    let valid = 0;
    let expired = 0;

    for (const item of Object.values(this.cache)) {
      if (now - item.timestamp > CACHE_TTL) {
        expired++;
      } else {
        valid++;
      }
    }

    return {
      valid,
      expired,
      total: this.cache.length,
      ttl: CACHE_TTL / 1000 / 60 + '分钟'
    };
  }
}

// 创建全局缓存实例
const cache = new SearchCache();

module.exports = {
  SearchCache,
  cache
};
