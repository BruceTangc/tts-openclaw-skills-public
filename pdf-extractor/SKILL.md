---
name: pdf-extractor
description: PyMuPDF-based PDF text extraction with auto-update from official docs
author: brucetangc
version: 1.0.0
homepage: https://pymupdf.readthedocs.io
triggers:
  - "PDF"
  - "pdf"
  - "提取"
  - "extract"
  - "读取"
  - "read"
metadata: {
  "clawdbot": {
    "emoji": "📄",
    "requires": {
      "bins": ["python3"],
      "pip": ["pymupdf"]
    },
    "config": {
      "env": {
        "PYMUPDF_FONT_DIR": {
          "description": "PyMuPDF 自定义字体目录（可选）",
          "default": "",
          "required": false
        }
      }
    }
  }
}
---

# PDF Extractor

基于 PyMuPDF 的 PDF 文本提取工具，支持提取本地 PDF 文件内容并输出 Markdown 格式。

## 功能列表

| 功能 | 状态 | 说明 |
|------|------|------|
| 📄 `extract` | ✅ 启用 | 提取 PDF 文本 |
| 📊 `info` | ✅ 启用 | 获取 PDF 元数据 |
| 🔍 `search` | ✅ 启用 | 搜索关键词 |
| 📝 `to-markdown` | ✅ 启用 | 转换为 Markdown |
| 🔄 `update` | ✅ 启用 | 自动更新 |

## 安装依赖

```bash
pip install pymupdf
```

或使用 requirements.txt：
```bash
pip install -r requirements.txt
```

## 使用示例

### 提取 PDF 文本
```javascript
pdf-extractor("file.pdf")
pdf-extractor({ command: "extract", file: "document.pdf" })
pdf-extractor({ command: "extract", file: "doc.pdf", pages: [1, 2, 3] })
```

### 获取 PDF 信息
```javascript
pdf-extractor({ command: "info", file: "document.pdf" })
```

### 搜索关键词
```javascript
pdf-extractor({ command: "search", file: "document.pdf", query: "关键词" })
```

### 转换为 Markdown
```javascript
pdf-extractor({ command: "to-markdown", file: "document.pdf", output: "output.md" })
```

## 参数说明

### Extract
- `file` - PDF 文件路径（必填）
- `pages` - 页码数组（可选，默认全部）
- `format` - 输出格式：text/markdown（默认 markdown）

### Info
- `file` - PDF 文件路径（必填）

### Search
- `file` - PDF 文件路径（必填）
- `query` - 搜索关键词（必填）
- `case_sensitive` - 是否区分大小写（默认 false）

### To-Markdown
- `file` - PDF 文件路径（必填）
- `output` - 输出文件路径（可选）

## 自动更新

本 Skill 支持从 PyMuPDF 官方文档自动更新：

```bash
# 检查更新
npm run check-updates

# 应用更新
npm run update
```

更新内容：
- API 用法同步
- 配置更新
- 代码优化

## 输出示例

### Info 输出
```
📄 PDF 信息

文件：document.pdf
页数：10
标题：示例文档
作者：张三
创建时间：2024-01-01
```

### Extract 输出
```
# 文档标题

## 第一章

这里是正文内容...
```

## 错误处理

所有错误都会返回友好的错误信息：
```
❌ **提取失败**

文件不存在：/path/to/file.pdf
```

## 更新日志

### v1.0.0 (2026-04-07)
- 初始版本
- 支持 extract、info、search、to-markdown
- 实现自动更新功能
