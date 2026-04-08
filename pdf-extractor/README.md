# PDF Extractor Skill

基于 PyMuPDF 的 PDF 文本提取工具，为 OpenClaw 提供 PDF 处理能力。

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Node.js 依赖
npm install
```

### 2. 使用示例

```javascript
// 提取 PDF 文本
pdf-extractor("document.pdf")

// 获取 PDF 信息
pdf-extractor({ command: "info", file: "document.pdf" })

// 搜索关键词
pdf-extractor({ command: "search", file: "document.pdf", query: "关键词" })

// 转换为 Markdown
pdf-extractor({ command: "to-markdown", file: "document.pdf", output: "output.md" })
```

## 功能说明

### Extract（提取）
- 提取 PDF 全部或部分页面的文本
- 支持 Markdown 或纯文本格式输出

### Info（信息）
- 获取 PDF 页数、标题、作者等元数据

### Search（搜索）
- 在 PDF 中搜索关键词
- 返回匹配位置和上下文

### To-Markdown（转换）
- 将整个 PDF 转换为 Markdown 格式
- 可选择保存到文件

## 自动更新

```bash
# 检查更新
npm run check-updates

# 应用更新
npm run update
```

## 开发

### 目录结构
```
pdf-extractor/
├── SKILL.md              # Skill 说明文档
├── index.js              # 主入口
├── package.json          # Node.js 配置
├── requirements.txt      # Python 依赖
├── _meta.json            # 元数据
├── README.md             # 本文件
└── scripts/
    ├── extract.py        # 文本提取
    ├── info.py           # 获取信息
    ├── search.py         # 搜索
    ├── to-markdown.py    # Markdown 转换
    ├── info.js           # Info 命令封装
    ├── search.js         # Search 命令封装
    ├── to-markdown.js    # To-Markdown 命令封装
    ├── check-updates.js  # 检查更新
    └── update-from-docs.js # 从文档更新
```

### 测试

```bash
npm test
```

## 许可证

MIT
