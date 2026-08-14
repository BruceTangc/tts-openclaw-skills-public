# tts-openclaw-skills-public

OpenClaw 公共 skills 集合 — 通用、可复用的 Agent 能力库。

本仓库包含 **4 个 skill**，每个 skill 都是一个独立目录，结构统一：

```
<skill-name>/
├── SKILL.md      # skill 定义（frontmatter + 使用指令）
├── _meta.json    # 元数据（可选）
└── scripts/      # 实现脚本（Node.js / Python）
```

## 📦 Skills 清单

| Skill | 说明 | 技术栈 |
|-------|------|--------|
| [excel-generator](excel-generator/) | 生成格式化 Excel 文件（创建、数据填充、图表、样式、模板） | openpyxl + xlsxwriter |
| [pdf-extractor](pdf-extractor/) | PDF 文本提取，支持从官方文档自动更新 | PyMuPDF |
| [self-improvement](self-improvement/) | 自主记忆与自我学习系统 V3.2（经验收集、知识图谱、多 Agent 学习、行为优化） | Python |
| [tavily-web-search](tavily-web-search/) | Tavily API 集成：网页搜索、内容提取、用量查询（自动更新） | Node.js |

## 🚀 快速使用

### 方式一：安装到 OpenClaw 工作区

```bash
# 把需要的 skill 复制到工作区 skills/ 目录
cp -r <skill-name> ~/.openclaw/workspace/skills/

# 验证加载
openclaw skills list
```

### 方式二：作为仓库直接 clone

```bash
git clone git@github.com:BruceTangc/tts-openclaw-skills-public.git
```

### 安装依赖

每个 skill 目录内有各自的依赖说明：

```bash
# Python 依赖（excel-generator / pdf-extractor）
pip install -r <skill-name>/requirements.txt

# Node 依赖（excel-generator / pdf-extractor / tavily-web-search）
cd <skill-name> && npm install
```

## 🔑 需要 API Key 的 skill

- **tavily-web-search**：需要 `TAVILY_API_KEY`，在 `config/default.json` 或环境变量中配置

## 📝 贡献 / 同步说明

本仓库是公开备份，与私有仓库 `tts-openclaw-skills-private` 分开管理。公开仓库放通用、无敏感信息的 skill；涉及个人数据、账号信息的 skill 只保留在私有仓库。

## 📄 License

本仓库内容为个人开发作品，供学习和参考使用。
