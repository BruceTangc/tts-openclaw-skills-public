#!/bin/bash
# 混合备份方案：GitHub + 阿里云盘
# 使用方法：./backup-hybrid.sh

WORKSPACE="/home/admin/.openclaw/workspace"
GITHUB_REPO="${GITHUB_REPO:-https://github.com/YOUR_USERNAME/openclaw-memory.git}"
ALIYUN_DIR="/home/admin/.openclaw/backups/aliyun"
DATE=$(date +%Y%m%d_%H%M%S)

echo "🔄 记忆系统混合备份（GitHub + 阿里云盘）"
echo "================================"
echo "日期：$DATE"
echo ""

# ========== 1. GitHub 备份（MEMORY.md + memory/*.md）==========
echo "1️⃣ GitHub 备份（版本控制）"
echo "--------------------------------"
cd "$WORKSPACE"

git add MEMORY.md memory/ 2>&1
git commit -m "backup: 自动备份 $DATE" 2>&1
git push origin main 2>&1 || git push origin master 2>&1

if [ $? -eq 0 ]; then
    echo "✅ GitHub 备份成功"
else
    echo "⚠️ GitHub 备份失败（可能未配置 Git）"
fi

echo ""

# ========== 2. 阿里云盘备份（完整备份）==========
echo "2️⃣ 阿里云盘备份（完整归档）"
echo "--------------------------------"
mkdir -p "$ALIYUN_DIR"

BACKUP_FILE="$ALIYUN_DIR/memory_backup_$DATE.tar.gz"
tar -czf "$BACKUP_FILE" \
    -C "$WORKSPACE" \
    MEMORY.md \
    memory/ \
    memory.config.json \
    skills/memory-system/ \
    2>&1

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "备份文件：$BACKUP_FILE"
echo "备份大小：$BACKUP_SIZE"
echo ""
echo "⚠️ 请手动上传到阿里云盘，或配置 aliyun-cli 自动上传"
echo "   示例：aliyunpan upload '$BACKUP_FILE' /openclaw-backups/"

echo ""
echo "================================"
echo "✅ 混合备份完成！"
echo ""
echo "备份位置："
echo "  - GitHub: $GITHUB_REPO"
echo "  - 阿里云盘：$BACKUP_FILE ($BACKUP_SIZE)"
echo ""
echo "恢复方法："
echo "  - 从 GitHub: git clone $GITHUB_REPO && cp -r MEMORY.md memory/ $WORKSPACE/"
echo "  - 从阿里云盘：tar -xzf memory_backup_*.tar.gz -C $WORKSPACE/"
