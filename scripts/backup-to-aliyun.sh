#!/bin/bash
# 记忆系统阿里云盘备份脚本
# 使用方法：./backup-to-aliyun.sh [backup|restore|list]

MODE="${1:-status}"
WORKSPACE="/home/admin/.openclaw/workspace"
BACKUP_DIR="${BACKUP_DIR:-/home/admin/.openclaw/backups/aliyun}"
DATE=$(date +%Y%m%d_%H%M%S)

echo "☁️ 记忆系统阿里云盘备份"
echo "================================"
echo "模式：$MODE"
echo "备份目录：$BACKUP_DIR"
echo ""

# 创建本地备份目录
mkdir -p "$BACKUP_DIR"

if [ "$MODE" = "backup" ]; then
    # 创建备份
    echo "1. 创建记忆备份..."
    BACKUP_FILE="$BACKUP_DIR/memory_backup_$DATE.tar.gz"
    
    tar -czf "$BACKUP_FILE" \
        -C "$WORKSPACE" \
        MEMORY.md \
        memory/ \
        2>&1
    
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    
    echo "2. 备份文件：$BACKUP_FILE"
    echo "3. 备份大小：$BACKUP_SIZE"
    
    echo ""
    echo "4. 上传到阿里云盘（需要手动或配置 aliyun-cli）..."
    echo "   方法 1: 使用阿里云盘客户端手动上传"
    echo "   方法 2: 使用 aliyun-cli 工具"
    echo "   方法 3: 使用 WebDAV 挂载"
    echo ""
    echo "   示例（使用 aliyun-cli）:"
    echo "   aliyunpan upload '$BACKUP_FILE' /openclaw-backups/"
    
    echo ""
    echo "================================"
    echo "✅ 本地备份完成！"
    echo "文件：$BACKUP_FILE"
    echo "大小：$BACKUP_SIZE"
    
elif [ "$MODE" = "restore" ]; then
    # 恢复备份
    echo "1. 从阿里云盘下载备份..."
    echo "   请手动从阿里云盘下载最新的 memory_backup_*.tar.gz"
    echo "   或使用 aliyun-cli:"
    echo "   aliyunpan download /openclaw-backups/memory_backup_*.tar.gz '$BACKUP_DIR/'"
    echo ""
    
    echo "2. 选择要恢复的备份文件:"
    ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -5
    
    echo ""
    read -p "输入备份文件名（直接回车使用最新）: " BACKUP_FILE
    
    if [ -z "$BACKUP_FILE" ]; then
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -1)
    fi
    
    if [ -f "$BACKUP_FILE" ]; then
        echo "3. 恢复备份：$BACKUP_FILE"
        tar -xzf "$BACKUP_FILE" -C "$WORKSPACE" 2>&1
        
        echo ""
        echo "================================"
        echo "✅ 恢复完成！"
    else
        echo "❌ 未找到备份文件"
    fi
    
elif [ "$MODE" = "list" ]; then
    # 查看备份列表
    echo "本地备份列表:"
    ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -10 || echo "无备份文件"
    
    echo ""
    echo "阿里云盘备份（需要手动查看）:"
    echo "  1. 打开阿里云盘客户端"
    echo "  2. 进入 /openclaw-backups/ 目录"
    echo "  3. 查看 memory_backup_*.tar.gz 文件"
fi

echo ""
echo "使用说明："
echo "  备份：./backup-to-aliyun.sh backup"
echo "  恢复：./backup-to-aliyun.sh restore"
echo "  列表：./backup-to-aliyun.sh list"
