# 📦 记忆系统备份方案选择

> GitHub vs 阿里云盘 vs 混合备份

---

## 🎯 推荐方案

### 🏆 方案 A：混合备份（推荐 ⭐⭐⭐⭐⭐）

**配置：**
- **GitHub** → MEMORY.md + memory/*.md（版本控制）
- **阿里云盘** → 完整备份（含索引、Skill 文件）

**优点：**
- ✅ 版本控制 + 快速恢复
- ✅ 异地容灾
- ✅ 免费无限存储

**缺点：**
- ⚠️ 需要配置两个地方

---

### 🥈 方案 B：仅 GitHub（推荐 ⭐⭐⭐⭐）

**适合：**
- ✅ 技术文档为主
- ✅ 需要版本历史
- ✅ 不介意国内访问慢

**优点：**
- ✅ 版本控制完善
- ✅ 自动备份（GitHub Actions）
- ✅ 免费无限存储

**缺点：**
- ⚠️ 国内访问慢
- ⚠️ 敏感信息需脱敏

---

### 🥉 方案 C：仅阿里云盘（推荐 ⭐⭐⭐）

**适合：**
- ✅ 大文件备份
- ✅ 快速恢复
- ✅ 隐私要求高

**优点：**
- ✅ 国内访问快速
- ✅ 私密存储
- ✅ 支持大文件

**缺点：**
- ⚠️ 无版本控制
- ⚠️ 需要手动上传

---

## 🔧 配置方法

### 方案 A：混合备份

```bash
# 1. 配置 Git 仓库
cd /home/admin/.openclaw/workspace
git init
git remote add origin https://github.com/YOUR_USERNAME/openclaw-memory.git

# 2. 首次备份
./skills/memory-system/scripts/backup-hybrid.sh

# 3. 配置自动备份（每天凌晨 2 点）
(crontab -l 2>/dev/null; echo "0 2 * * * /home/admin/.openclaw/workspace/skills/memory-system/scripts/backup-hybrid.sh") | crontab -
```

---

### 方案 B：GitHub 备份

```bash
# 1. 创建 GitHub 仓库
# 访问 https://github.com/new 创建私有仓库

# 2. 配置本地 Git
cd /home/admin/.openclaw/workspace
git init
git remote add origin https://github.com/YOUR_USERNAME/openclaw-memory.git

# 3. 首次备份
./skills/memory-system/scripts/backup-to-github.sh push

# 4. 配置自动备份
(crontab -l 2>/dev/null; echo "0 2 * * * /home/admin/.openclaw/workspace/skills/memory-system/scripts/backup-to-github.sh push") | crontab -
```

**GitHub Actions 自动备份（可选）：**

创建 `.github/workflows/backup.yml`：
```yaml
name: Memory Backup
on:
  schedule:
    - cron: '0 2 * * *'  # 每天 2:00 UTC
  push:
    paths:
      - 'MEMORY.md'
      - 'memory/**'

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add MEMORY.md memory/
          git commit -m "auto backup" || echo "No changes"
          git push
```

---

### 方案 C：阿里云盘备份

```bash
# 1. 安装 aliyun-cli（可选）
# 访问 https://github.com/tickstep/aliyunpan 下载

# 2. 配置阿里云盘
aliyunpan login

# 3. 首次备份
./skills/memory-system/scripts/backup-to-aliyun.sh backup

# 4. 上传到阿里云盘
aliyunpan upload /home/admin/.openclaw/backups/aliyun/memory_backup_*.tar.gz /openclaw-backups/

# 5. 配置自动备份
(crontab -l 2>/dev/null; echo "0 2 * * * /home/admin/.openclaw/workspace/skills/memory-system/scripts/backup-to-aliyun.sh backup") | crontab -
```

---

## 📊 备份内容对比

| 内容 | GitHub | 阿里云盘 | 混合备份 |
|------|--------|----------|----------|
| MEMORY.md | ✅ | ✅ | ✅ 两者 |
| memory/*.md | ✅ | ✅ | ✅ 两者 |
| main.sqlite | ❌ | ✅ | ✅ 阿里云盘 |
| Skill 文件 | ✅ | ✅ | ✅ 阿里云盘 |
| 配置文件 | ✅ | ✅ | ✅ 阿里云盘 |

---

## 🚀 快速开始

### 我帮你选择！

**如果你想要：**

- **最佳方案** → 混合备份（GitHub + 阿里云盘）
- **简单方案** → GitHub 备份
- **快速恢复** → 阿里云盘备份

---

### 立即执行（混合备份）

```bash
# 1. 初始化 Git
cd /home/admin/.openclaw/workspace
git init
git config user.email "your@email.com"
git config user.name "Your Name"

# 2. 创建 GitHub 仓库（手动）
# 访问 https://github.com/new 创建私有仓库

# 3. 配置远程仓库
git remote add origin https://github.com/YOUR_USERNAME/openclaw-memory.git

# 4. 首次备份
./skills/memory-system/scripts/backup-hybrid.sh

# 5. 配置自动备份
(crontab -l 2>/dev/null; echo "0 2 * * * /home/admin/.openclaw/workspace/skills/memory-system/scripts/backup-hybrid.sh") | crontab -
```

---

## 📝 恢复方法

### 从 GitHub 恢复

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/openclaw-memory.git /tmp/backup

# 2. 恢复文件
cp /tmp/backup/MEMORY.md /home/admin/.openclaw/workspace/
cp -r /tmp/backup/memory/ /home/admin/.openclaw/workspace/

# 3. 清理
rm -rf /tmp/backup
```

### 从阿里云盘恢复

```bash
# 1. 下载备份
aliyunpan download /openclaw-backups/memory_backup_*.tar.gz /tmp/

# 2. 解压恢复
tar -xzf /tmp/memory_backup_*.tar.gz -C /home/admin/.openclaw/workspace/
```

---

## 🎯 我的建议

**推荐：混合备份（GitHub + 阿里云盘）**

**配置：**
- **每天 2:00** → GitHub 自动备份（版本控制）
- **每周日 3:00** → 阿里云盘完整备份（归档）
- **每月 1 号** → 手动验证备份可恢复

**理由：**
- ✅ 版本控制 + 快速恢复
- ✅ 异地容灾
- ✅ 免费方案
- ✅ 自动化程度高

---

**需要我帮你配置哪个方案？** 🚀
