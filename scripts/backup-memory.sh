#!/bin/bash
# 记忆系统备份脚本
# 使用方法：./backup-memory.sh [full|quick]

BACKUP_DIR="${BACKUP_DIR:-/home/admin/.openclaw/backups}"
WORKSPACE="/home/admin/.openclaw/workspace"
MEMORY_DB="/home/admin/.openclaw/memory"
DATE=$(date +%Y%m%d_%H%M%S)
MODE="${1:-quick}"

echo "🧠 记忆系统备份"
echo "================================"
echo "备份模式：$MODE"
echo "备份目录：$BACKUP_DIR"
echo ""

# 创建备份目录
mkdir -p "$BACKUP_DIR"

if [ "$MODE" = "full" ]; then
    # 完整备份（包含索引数据库）
    echo "1. 备份长期记忆..."
    cp "$WORKSPACE/MEMORY.md" "$BACKUP_DIR/MEMORY_$DATE.md"
    
    echo "2. 备份日常记录..."
    cp -r "$WORKSPACE/memory/" "$BACKUP_DIR/memory_$DATE/"
    
    echo "3. 备份记忆索引..."
    cp -r "$MEMORY_DB/" "$BACKUP_DIR/memory-db_$DATE/"
    
    echo "4. 备份配置文件..."
    cp "$WORKSPACE/memory.config.json" "$BACKUP_DIR/memory.config_$DATE.json" 2>/dev/null || true
    
    echo "5. 导出 Markdown 备份..."
    cd "$WORKSPACE"
    node -e "const ms=require('./skills/memory-system/index.js'); ms.run({action:'export',format:'markdown',output:'$BACKUP_DIR/export_$DATE.md'}).then(r=>console.log(r.path));"
    
    BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
else
    # 快速备份（只备份 Markdown 文件）
    echo "1. 备份长期记忆..."
    cp "$WORKSPACE/MEMORY.md" "$BACKUP_DIR/MEMORY_$DATE.md"
    
    echo "2. 备份日常记录..."
    cp -r "$WORKSPACE/memory/" "$BACKUP_DIR/memory_$DATE/"
    
    BACKUP_SIZE=$(du -sh "$BACKUP_DIR/memory_$DATE" | cut -f1)
fi

# 清理旧备份（保留最近 7 个）
echo ""
echo "6. 清理旧备份..."
cd "$BACKUP_DIR"
ls -t MEMORY_*.md 2>/dev/null | tail -n +8 | xargs -r rm --
echo "保留最近 7 个备份"

echo ""
echo "================================"
echo "✅ 备份完成！"
echo "备份大小：$BACKUP_SIZE"
echo "备份位置：$BACKUP_DIR"
echo ""
echo "恢复方法："
echo "  cp $BACKUP_DIR/MEMORY_*.md $WORKSPACE/MEMORY.md"
echo "  cp -r $BACKUP_DIR/memory_*/ $WORKSPACE/memory/"
