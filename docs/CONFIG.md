# 🧠 记忆系统 - 完整配置指南

> 备份 · 恢复 · 自动更新 · 开机自启

---

## 📦 1. 记忆备份

### 当前状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 自动备份 | ❌ 无 | 需要手动或配置 cron |
| 备份脚本 | ✅ 已创建 | `scripts/backup-memory.sh` |
| 备份位置 | ⚠️ 未配置 | 默认 `~/.openclaw/backups` |

### 使用方法

#### 快速备份（推荐）
```bash
# 备份 Markdown 文件（约 10 KB）
./skills/memory-system/scripts/backup-memory.sh quick
```

#### 完整备份
```bash
# 备份所有数据（包含索引数据库，约 100 KB）
./skills/memory-system/scripts/backup-memory.sh full
```

#### 自动备份（推荐配置）
```bash
# 添加到 crontab，每天凌晨 2 点备份
crontab -e

# 添加这行：
0 2 * * * /home/admin/.openclaw/workspace/skills/memory-system/scripts/backup-memory.sh quick
```

### 备份内容

**快速备份：**
- ✅ MEMORY.md（长期记忆）
- ✅ memory/*.md（日常记录）

**完整备份：**
- ✅ 快速备份所有内容
- ✅ main.sqlite（记忆索引数据库）
- ✅ memory.config.json（配置文件）
- ✅ Markdown 导出文件

### 恢复方法

```bash
# 1. 停止 OpenClaw
openclaw gateway stop

# 2. 恢复备份
cp ~/.openclaw/backups/MEMORY_*.md ~/.openclaw/workspace/MEMORY.md
cp -r ~/.openclaw/backups/memory_*/ ~/.openclaw/workspace/memory/

# 3. 重启 OpenClaw
openclaw gateway start
```

---

## 🔄 2. 自动更新

### 当前状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 自动检查 | ✅ 有 | `update-check.json` |
| 自动安装 | ❌ 无 | 需要手动确认 |
| 更新脚本 | ✅ 已创建 | `scripts/auto-update.sh` |

### 使用方法

#### 检查更新
```bash
./skills/memory-system/scripts/auto-update.sh check
```

#### 更新（含备份）
```bash
./skills/memory-system/scripts/auto-update.sh update
```

#### 自动更新（可选）
```bash
# 添加到 crontab，每周一 9 点检查更新
crontab -e

# 添加这行：
0 9 * * 1 /home/admin/.openclaw/workspace/skills/memory-system/scripts/auto-update.sh update
```

### 更新流程

1. 检查可用版本
2. 备份记忆系统（自动）
3. 下载并安装更新
4. 重启 Gateway 服务

---

## ⚡ 3. 开机自启

### 当前状态

| 项目 | 状态 | 说明 |
|------|------|------|
| systemd 服务 | ❌ 未配置 | 需要手动配置 |
| Gateway 运行 | ✅ 正常 | PID 1013（手动启动） |
| 自启脚本 | ✅ 已创建 | `scripts/openclaw-gateway.service` |

### 配置开机自启

#### 方法 1：systemd（推荐）
```bash
# 1. 复制服务文件
sudo cp scripts/openclaw-gateway.service /etc/systemd/system/

# 2. 重载 systemd
sudo systemctl daemon-reload

# 3. 启用服务
sudo systemctl enable openclaw-gateway

# 4. 启动服务
sudo systemctl start openclaw-gateway

# 5. 查看状态
sudo systemctl status openclaw-gateway
```

#### 方法 2：rc.local（简单）
```bash
# 编辑 rc.local
sudo nano /etc/rc.local

# 添加这行（在 exit 0 之前）：
su - admin -c 'openclaw gateway &'

# 赋予执行权限
sudo chmod +x /etc/rc.local
```

### 管理命令

```bash
# 查看状态
sudo systemctl status openclaw-gateway

# 停止服务
sudo systemctl stop openclaw-gateway

# 重启服务
sudo systemctl restart openclaw-gateway

# 查看日志
sudo journalctl -u openclaw-gateway -f
```

---

## 📊 4. 完整配置清单

### 必须配置 ⭐⭐⭐

| 配置 | 命令 | 优先级 |
|------|------|--------|
| **记忆备份** | `crontab -e` → 每天 2:00 | ⭐⭐⭐ |
| **开机自启** | `systemctl enable openclaw-gateway` | ⭐⭐⭐ |

### 推荐配置 ⭐⭐

| 配置 | 命令 | 优先级 |
|------|------|--------|
| **每周更新** | `crontab -e` → 每周一 9:00 | ⭐⭐ |
| **完整备份** | 每月手动执行一次 | ⭐⭐ |

### 可选配置 ⭐

| 配置 | 命令 | 优先级 |
|------|------|--------|
| **远程备份** | 同步到云存储 | ⭐ |
| **监控告警** | 配置健康检查 | ⭐ |

---

## 🚀 一键配置脚本

创建 `setup-complete.sh`：

```bash
#!/bin/bash
# 完整配置脚本

echo "🧠 OpenClaw 完整配置"
echo "================================"

# 1. 配置记忆备份
echo "1. 配置记忆备份（每天 2:00）..."
(crontab -l 2>/dev/null; echo "0 2 * * * /home/admin/.openclaw/workspace/skills/memory-system/scripts/backup-memory.sh quick") | crontab -

# 2. 配置开机自启
echo "2. 配置开机自启..."
sudo cp /home/admin/.openclaw/workspace/scripts/openclaw-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable openclaw-gateway
sudo systemctl restart openclaw-gateway

# 3. 测试备份
echo "3. 测试备份..."
/home/admin/.openclaw/workspace/skills/memory-system/scripts/backup-memory.sh quick

echo ""
echo "================================"
echo "✅ 配置完成！"
echo ""
echo "验证："
echo "  crontab -l                    # 查看定时任务"
echo "  systemctl status openclaw-gateway  # 查看服务状态"
echo "  ls -la ~/.openclaw/backups/   # 查看备份"
```

---

## 📝 总结

### 当前状态

| 功能 | 状态 | 脚本位置 |
|------|------|----------|
| 记忆备份 | ⚠️ 需配置 | `scripts/backup-memory.sh` |
| 自动更新 | ⚠️ 需配置 | `scripts/auto-update.sh` |
| 开机自启 | ⚠️ 需配置 | `scripts/openclaw-gateway.service` |

### 立即执行（推荐）

```bash
# 1. 赋予执行权限
chmod +x scripts/*.sh scripts/*.service

# 2. 运行一键配置
./scripts/setup-complete.sh
```

### 手动执行（按需）

```bash
# 备份记忆
./scripts/backup-memory.sh quick

# 检查更新
./scripts/auto-update.sh check

# 配置自启
sudo systemctl enable openclaw-gateway
```

---

**创建时间：** 2026-04-08  
**版本：** 1.0.0  
**维护：** 记忆系统 Skill 团队
