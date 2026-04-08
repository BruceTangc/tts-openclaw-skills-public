#!/bin/bash
# 记忆系统 GitHub 备份脚本
# 使用方法：./backup-to-github.sh [push|pull|status]

MODE="${1:-status}"
WORKSPACE="/home/admin/.openclaw/workspace"
BACKUP_REPO="${BACKUP_REPO:-https://github.com/YOUR_USERNAME/openclaw-memory.git}"
BACKUP_DIR="/tmp/openclaw-memory-backup"

echo "🐙 记忆系统 GitHub 备份"
echo "================================"
echo "仓库：$BACKUP_REPO"
echo "模式：$MODE"
echo ""

if [ "$MODE" = "status" ]; then
    # 检查 Git 状态
    cd "$WORKSPACE"
    echo "1. 检查 Git 状态..."
    git status 2>&1 | head -10 || echo "未初始化 Git 仓库"
    
    echo ""
    echo "2. 查看最近提交..."
    git log --oneline -5 2>&1 || echo "无提交历史"
    
elif [ "$MODE" = "push" ]; then
    # 推送到 GitHub
    cd "$WORKSPACE"
    
    echo "1. 添加更改..."
    git add MEMORY.md memory/ 2>&1
    
    echo "2. 提交更改..."
    git commit -m "backup: 记忆系统自动备份 $(date '+%Y-%m-%d %H:%M:%S')" 2>&1
    
    echo "3. 推送到 GitHub..."
    git push origin main 2>&1 || git push origin master 2>&1
    
    echo ""
    echo "================================"
    echo "✅ 备份完成！"
    echo "仓库：$BACKUP_REPO"
    
elif [ "$MODE" = "pull" ]; then
    # 从 GitHub 恢复
    echo "1. 克隆备份仓库..."
    git clone "$BACKUP_REPO" "$BACKUP_DIR" 2>&1
    
    echo "2. 恢复记忆文件..."
    cp "$BACKUP_DIR/MEMORY.md" "$WORKSPACE/MEMORY.md" 2>&1
    cp -r "$BACKUP_DIR/memory/" "$WORKSPACE/memory/" 2>&1
    
    echo "3. 清理临时文件..."
    rm -rf "$BACKUP_DIR"
    
    echo ""
    echo "================================"
    echo "✅ 恢复完成！"
fi

echo ""
echo "使用说明："
echo "  手动备份：./backup-to-github.sh push"
echo "  恢复备份：./backup-to-github.sh pull"
echo "  查看状态：./backup-to-github.sh status"
