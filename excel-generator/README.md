# Excel Generator Skill

基于 openpyxl 和 xlsxwriter 的 Excel 文件生成工具，为 OpenClaw 提供 Excel 创建和格式化能力。

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
// 简单创建
excel-generator({
  command: "create",
  file: "report.xlsx",
  data: [["姓名", "年龄"], ["张三", 25], ["李四", 30]]
})

// 带样式
excel-generator({
  command: "style",
  file: "formatted.xlsx",
  data: [["工单号", "材料", "数量"]],
  style: {
    header: { bold: true, bgColor: "4472C4", color: "FFFFFF" },
    border: true,
    autoWidth: true
  }
})

// 工单报表
excel-generator({
  command: "from-data",
  file: "切割工单.xlsx",
  data: [
    ["工单号", "零件编号", "尺寸", "数量", "重量"],
    ["10332", "DI003120005A", "107x336mm", 2, "1.75kg"]
  ],
  style: {
    header: { bold: true, bgColor: "4472C4", color: "FFFFFF" },
    border: true,
    autoWidth: true
  }
})
```

## 功能说明

### Create（创建）
- 创建基础 Excel 文件
- 支持 2D 数组数据
- 可指定工作表名称

### From-Data（数据生成）
- 从数据数组生成 Excel
- 支持样式配置
- 自动调整列宽

### Style（样式）
- 标题样式（加粗、背景色、文字颜色）
- 边框样式
- 交替行样式

### Chart（图表）
- 支持柱状图、折线图、饼图
- 自动数据系列

## 样式配置

```javascript
{
  "header": {
    "bold": true,          // 加粗
    "bgColor": "4472C4",   // 背景色（RGB 十六进制）
    "color": "FFFFFF",     // 文字颜色
    "fontSize": 12         // 字体大小
  },
  "border": true,          // 添加边框
  "autoWidth": true,       // 自动列宽
  "alternatingRows": true  // 交替行样式
}
```

## 常用颜色

| 颜色 | 代码 | 效果 |
|------|------|------|
| 蓝色 | `4472C4` | 🔵 专业商务 |
| 绿色 | `70AD47` | 🟢 成功/完成 |
| 红色 | `ED7D31` | 🟠 警告/重要 |
| 灰色 | `A5A5A5` | ⚪ 中性/辅助 |
| 黄色 | `FFC000` | 🟡 高亮/注意 |

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
excel-generator/
├── SKILL.md              # Skill 说明文档
├── index.js              # 主入口
├── package.json          # Node.js 配置
├── requirements.txt      # Python 依赖
├── _meta.json            # 元数据
├── README.md             # 本文件
└── scripts/
    ├── create.py         # Excel 创建（Python）
    ├── from-data.js      # From-Data 封装
    ├── check-updates.js  # 检查更新
    └── update-from-docs.js # 从文档更新
```

### 测试

```bash
npm test
```

## 技术栈

- **openpyxl** - Excel 读写、样式处理
- **xlsxwriter** - 高级格式化、图表支持
- **Node.js** - OpenClaw Skill 封装

## 许可证

MIT
