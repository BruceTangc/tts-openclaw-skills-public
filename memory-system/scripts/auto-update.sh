#!/bin/bash
# OpenClaw 自动更新脚本
# 使用方法：./auto-update.sh [check|update]

MODE="${1:-check}"
CURRENT_VERSION=$(openclaw --version 2>&1 | grep -oP '\d{4}\.\d+\.\d+' | head -1)

echo "🔄 OpenClaw 自动更新"
echo "================================"
echo "当前版本：$CURRENT_VERSION"
echo ""

if [ "$MODE" = "check" ]; then
    echo "检查更新..."
    openclaw update --dry-run 2>&1 | head -20
    
elif [ "$MODE" = "update" ]; then
    echo "开始更新..."
    openclaw update 2>&1
    
    NEW_VERSION=$(openclaw --version 2>&1 | grep -oP '\d{4}\.\d+\.\d+' | head -1)
    echo ""
    echo "================================"
    echo "更新完成！"
    echo "新版本：$NEW_VERSION"
    
    # 备份记忆系统
    echo ""
    echo "备份记忆系统..."
    /home/admin/.openclaw/workspace/skills/memory-system/scripts/backup-memory.sh quick
fi
