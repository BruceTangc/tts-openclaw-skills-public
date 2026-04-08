#!/bin/bash
# GitHub 仓库配置脚本
# 使用方法：./setup-github-repo.sh

WORKSPACE="/home/admin/.openclaw/workspace"
REPO_NAME="openclaw-memory"

echo "🐙 GitHub 私人仓库配置"
echo "================================"
echo ""

# 1. 检查 Git
if ! command -v git &> /dev/null; then
    echo "❌ Git 未安装，请先安装：sudo apt install git"
    exit 1
fi

echo "1️⃣ 初始化 Git 仓库"
echo "--------------------------------"
cd "$WORKSPACE"
git init
git config user.email "your-email@example.com"
git config user.name "Your Name"
echo "✅ Git 初始化完成"
echo ""

# 2. 添加远程仓库
echo "2️⃣ 配置远程仓库"
echo "--------------------------------"
echo "请选择远程仓库方式："
echo "  1. HTTPS（需要 Token）"
echo "  2. SSH（推荐，需要 SSH Key）"
read -p "选择 [1/2]: " CHOICE

if [ "$CHOICE" = "2" ]; then
    # SSH 方式
    echo ""
    echo "生成 SSH Key..."
    ssh-keygen -t ed25519 -C "your-email@example.com" -f ~/.ssh/github_openclaw -N ""
    
    echo ""
    echo "✅ SSH Key 已生成："
    echo "   公钥：~/.ssh/github_openclaw.pub"
    echo ""
    echo "📋 请复制以下公钥内容，然后添加到 GitHub："
    echo "   https://github.com/settings/keys"
    echo ""
    cat ~/.ssh/github_openclaw.pub
    echo ""
    
    read -p "添加完成后按回车继续..."
    
    git remote add origin git@github.com:YOUR_USERNAME/$REPO_NAME.git
else
    # HTTPS 方式
    read -p "输入你的 GitHub 用户名：" GITHUB_USER
    git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git
fi

echo ""
echo "3️⃣ 首次备份"
echo "--------------------------------"
git add MEMORY.md memory/
git commit -m "initial backup: 记忆系统初始化"
git branch -M main
git push -u origin main

echo ""
echo "================================"
echo "✅ 配置完成！"
echo ""
echo "仓库地址：https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""
echo "下次备份："
echo "  cd $WORKSPACE"
echo "  git add MEMORY.md memory/"
echo "  git commit -m \"backup: \$(date)\""
echo "  git push"
echo ""
echo "自动备份（可选）："
echo "  (crontab -l 2>/dev/null; echo \"0 2 * * * cd $WORKSPACE && git add MEMORY.md memory/ && git commit -m 'auto backup' && git push\") | crontab -"
