/**
 * 简单的内存缓存（带 TTL + 最大条目限制）
 */

class Cache {
  constructor(ttlMinutes = 5, maxItems = 50) {
    this.store = new Map();
    this.ttl = ttlMinutes * 60 * 1000; // 转换为毫秒
    this.maxItems = maxItems;
  }

  /**
   * 生成缓存键
   */
  _makeKey(prefix, data) {
    return `${prefix}:${JSON.stringify(data)}`;
  }

  /**
   * 清理过期条目
   */
  _cleanExpired() {
    const now = Date.now();
    for (const [key, item] of this.store.entries()) {
      if (now - item.timestamp > this.ttl) {
        this.store.delete(key);
      }
    }
  }

  /**
   * 获取缓存
   */
  get(key) {
    const item = this.store.get(key);
    
    if (!item) {
      return null;
    }
    
    // 检查是否过期
    if (Date.now() - item.timestamp > this.ttl) {
      this.store.delete(key);
      return null;
    }
    
    return item.data;
  }

  /**
   * 设置缓存
   */
  set(key, data) {
    // 达到上限时清理过期条目，再删除最老的一条
    if (this.store.size >= this.maxItems) {
      this._cleanExpired();
      if (this.store.size >= this.maxItems) {
        const oldest = this.store.keys().next().value;
        this.store.delete(oldest);
      }
    }
    
    this.store.set(key, {
      data,
      timestamp: Date.now()
    });
  }

  /**
   * 删除缓存
   */
  delete(key) {
    return this.store.delete(key);
  }

  /**
   * 清空缓存
   */
  clear() {
    this.store.clear();
  }

  /**
   * 获取缓存统计
   */
  stats() {
    const now = Date.now();
    let valid = 0;
    let expired = 0;
    
    for (const [key, item] of this.store.entries()) {
      if (now - item.timestamp > this.ttl) {
        expired++;
      } else {
        valid++;
      }
    }
    
    return { valid, expired, total: this.store.size, maxItems: this.maxItems };
  }
}

// 创建全局缓存实例（5 分钟 TTL，最多 50 条）
const cache = new Cache(5, 50);

module.exports = {
  Cache,
  cache
};
