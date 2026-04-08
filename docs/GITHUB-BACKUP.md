# 🧠 记忆系统 GitHub 备份配置

> 备份仓库：brucetangc/tts-openclaw-skills-private

---

## ✅ 配置完成

| 项目 | 状态 | 说明 |
|------|------|------|
| Git 初始化 | ✅ 完成 | `/home/admin/.openclaw/workspace/.git` |
| 远程仓库 | ✅ 配置 | `git@github.com:brucetangc/tts-openclaw-skills-private.git` |
| 首次推送 | ✅ 完成 | 2026-04-08 16:57 |
| 自动备份 | ✅ 配置 | 每天凌晨 2:00 |

---

## 📦 备份内容

| 文件/目录 | 说明 |
|-----------|------|
| `MEMORY.md` | 长期记忆 |
| `memory/` | 日常记录 |
| `skills/memory-system/` | 记忆系统 Skill |

---

## 🔧 管理命令

### 手动备份
```bash
cd /home/admin/.openclaw/workspace
git add MEMORY.md memory/
git commit -m "backup: $(date)"
git push
```

### 查看状态
```bash
cd /home/admin/.openclaw/workspace
git status
git log --oneline
git remote -v
```

### 查看自动备份
```bash
crontab -l
```

---

## 🌐 访问仓库

**HTTPS:**
```
https://github.com/brucetangc/tts-openclaw-skills-private
```

**SSH:**
```
git@github.com:brucetangc/tts-openclaw-skills-private.git
```

---

## 📝 恢复方法

### 从 GitHub 恢复

```bash
# 1. 克隆仓库
git clone git@github.com:brucetangc/tts-openclaw-skills-private.git /tmp/backup

# 2. 恢复文件
cp /tmp/backup/MEMORY.md /home/admin/.openclaw/workspace/
cp -r /tmp/backup/memory/ /home/admin/.openclaw/workspace/
cp -r /tmp/backup/skills/memory-system/ /home/admin/.openclaw/workspace/

# 3. 清理
rm -rf /tmp/backup
```

---

## 🔐 SSH Key 配置（如需要）

如果推送失败，需要配置 SSH Key：

```bash
# 1. 生成 SSH Key
ssh-keygen -t ed25519 -C "openclaw@local" -f ~/.ssh/github_openclaw -N ""

# 2. 查看公钥
cat ~/.ssh/github_openclaw.pub

# 3. 添加到 GitHub
# 访问：https://github.com/settings/keys
# 点击 "New SSH key"
# 粘贴公钥内容

# 4. 测试连接
ssh -T git@github.com
```

---

## 📊 备份历史

| 日期 | 提交 | 说明 |
|------|------|------|
| 2026-04-08 | 6208c44 | initial backup: 记忆系统 + Skill 初始化 |

---

## ⚠️ 注意事项

1. **隐私保护**：这是私人仓库，只有你能访问
2. **敏感信息**：不要在记忆中存储密码、API Key 等敏感信息
3. **定期验证**：定期检查 GitHub 仓库确保备份正常
4. **本地优先**：GitHub 是备份，本地文件是主要数据源

---

**配置时间：** 2026-04-08 16:57  
**配置者：** OpenClaw  
**仓库：** brucetangc/tts-openclaw-skills-private
