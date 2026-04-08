---
name: excel-generator
description: Create formatted Excel files with openpyxl and xlsxwriter
author: brucetangc
version: 1.0.0
homepage: https://openpyxl.readthedocs.io
triggers:
  - "Excel"
  - "excel"
  - "表格"
  - "生成"
  - "create"
  - "spreadsheet"
  - "xlsx"
metadata: {
  "clawdbot": {
    "emoji": "📊",
    "requires": {
      "bins": ["python3"],
      "pip": ["openpyxl", "xlsxwriter"]
    },
    "config": {
      "env": {
        "EXCEL_OUTPUT_DIR": {
          "description": "Excel 文件默认输出目录（可选）",
          "default": "",
          "required": false
        }
      }
    }
  }
}
---

# Excel Generator

基于 openpyxl 和 xlsxwriter 的 Excel 文件生成工具，支持创建格式化的 .xlsx 文件。

## 功能列表

| 功能 | 状态 | 说明 |
|------|------|------|
| 📊 `create` | ✅ 启用 | 创建 Excel 文件 |
| 📝 `from-data` | ✅ 启用 | 从数据数组生成（带样式） |
| 🎨 `style` | ✅ 启用 | 应用样式到现有文件 |
| 📈 `chart` | ✅ 启用 | 添加图表（柱状/折线/饼图） |
| 📋 `template` | ✅ 启用 | 填充 Excel 模板 |

## 安装依赖

```bash
pip install openpyxl xlsxwriter
```

或使用 requirements.txt：
```bash
pip install -r requirements.txt
```

## 使用示例

### 创建简单 Excel
```javascript
excel-generator({
  command: "create",
  file: "report.xlsx",
  data: [["姓名", "年龄"], ["张三", 25], ["李四", 30]]
})
```

### 带样式的 Excel
```javascript
excel-generator({
  command: "style",
  file: "formatted.xlsx",
  data: [["工单号", "材料", "数量"]],
  style: {
    header: { bold: true, bgColor: "FFFF00" },
    border: true,
    autoWidth: true
  }
})
```

### 从工单数据生成
```javascript
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

### 填充模板
```javascript
excel-generator({
  command: "template",
  template: "工单模板.xlsx",
  file: "工单 -10332.xlsx",
  replacements: {
    "{工单号}": "10332",
    "{日期}": "2026-03-25"
  },
  data: [
    ["DI003120005A", "107x336mm", 2, "1.75kg"]
  ]
})
```

## 参数说明

### Create
- `file` - 输出文件路径（必填）
- `data` - 2D 数组数据（必填）
- `sheet_name` - 工作表名称（可选，默认 Sheet1）

### Style
- `file` - 输出文件路径（必填）
- `data` - 2D 数组数据（必填）
- `style` - 样式配置
  - `header.bold` - 标题加粗
  - `header.bgColor` - 标题背景色
  - `header.color` - 标题文字颜色
  - `border` - 添加边框
  - `autoWidth` - 自动列宽

### Chart
- `file` - 输出文件路径（必填）
- `data` - 数据（第一行标题，第二行开始数据）
- `chart_type` - 图表类型：bar（柱状）/line（折线）/pie（饼图）

### Template
- `template` - 模板文件路径（必填）
- `file` - 输出文件路径（必填）
- `data` - 要追加的数据数组（可选）
- `replacements` - 替换规则对象（可选）
  - 例如：`{"{name}": "张三", "{date}": "2026-04-07"}`

## 样式配置示例

```javascript
{
  "header": {
    "bold": true,
    "bgColor": "4472C4",
    "color": "FFFFFF",
    "fontSize": 12
  },
  "border": true,
  "autoWidth": true,
  "alternatingRows": true
}
```

## 颜色代码

常用颜色（RGB 十六进制）：
- 蓝色：`4472C4`
- 绿色：`70AD47`
- 红色：`ED7D31`
- 灰色：`A5A5A5`
- 黄色：`FFC000`

## 自动更新

本 Skill 支持从官方文档自动更新：

```bash
# 检查更新
npm run check-updates

# 应用更新
npm run update
```

## 完整示例

### 工单报表生成
```javascript
// 从 PDF 提取数据后生成 Excel
const pdfData = [
  ["工单号", "零件编号", "尺寸", "数量", "切割时间", "重量"],
  ["10332", "DI003120005A", "107x336mm", 2, "0.93min", "1.75kg"],
  ["10332", "DI003120038A", "107x336mm", 2, "0.93min", "1.75kg"],
  ["10332", "DI003120021A", "84x313mm", 2, "0.86min", "1.19kg"],
  ["10332", "DI003120039A", "84x314mm", 2, "0.86min", "1.19kg"]
];

excel-generator({
  command: "from-data",
  file: "工单 -10332.xlsx",
  data: pdfData,
  style: {
    header: { 
      bold: true, 
      bgColor: "4472C4", 
      color: "FFFFFF",
      fontSize: 11
    },
    border: true,
    autoWidth: true,
    alternatingRows: true
  }
});
```

### 销售数据图表
```javascript
const salesData = [
  ["月份", "销售额"],
  ["1 月", 10000],
  ["2 月", 15000],
  ["3 月", 12000],
  ["4 月", 18000]
];

excel-generator({
  command: "chart",
  file: "销售报表.xlsx",
  data: salesData,
  chart_type: "bar"  // 或 "line", "pie"
});
```

## 更新日志

### v1.0.0 (2026-04-07)
- 初始版本
- 支持 create、from-data、style、chart、template 命令
- 集成 openpyxl（读写）和 xlsxwriter（图表）
- 实现完整样式支持（边框、颜色、对齐、交替行）
- 实现自动更新功能
