# Excel Generator - 安装说明

## 快速安装

### 1. 安装 Python 依赖

```bash
cd ~/.openclaw/workspace/skills/excel-generator

# 使用 pip 安装
pip install -r requirements.txt

# 或使用 python3 -m pip（如果 pip 不可用）
python3 -m pip install openpyxl xlsxwriter
```

### 2. 安装 Node.js 依赖

```bash
npm install
```

### 3. 验证安装

```bash
# 运行测试
npm test
```

如果看到类似以下输出，说明安装成功：

```
🧪 Excel Generator 综合测试

📊 测试 1: 简单创建 Excel
✅ 通过：{ success: true, ... }

🎨 测试 2: 带样式创建
✅ 通过：{ success: true, ... }

📈 测试 3: 图表创建
✅ 通过：{ success: true, ... }

✨ 测试 4: 完整样式（交替行）
✅ 通过：{ success: true, ... }

✅ 测试完成：4 通过，0 失败
🎉 所有测试通过！
```

## 故障排查

### 问题 1: pip 找不到

**错误信息**: `bash: pip: command not found`

**解决方案**:
```bash
# 使用 python3 -m pip
python3 -m pip install openpyxl xlsxwriter
```

### 问题 2: 网络超时

**错误信息**: `Read timed out`

**解决方案**:
```bash
# 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple openpyxl xlsxwriter
```

### 问题 3: 权限问题

**错误信息**: `Permission denied`

**解决方案**:
```bash
# 使用 --user 参数
pip install --user openpyxl xlsxwriter
```

### 问题 4: npm install 失败

**错误信息**: `npm ERR!`

**解决方案**:
```bash
# 清除 npm 缓存
npm cache clean --force

# 删除 node_modules 重新安装
rm -rf node_modules package-lock.json
npm install
```

## 验证安装

```bash
# 检查 Python 库
python3 -c "import openpyxl; print('openpyxl:', openpyxl.__version__)"
python3 -c "import xlsxwriter; print('xlsxwriter:', xlsxwriter.__version__)"

# 检查 Node.js 依赖
node -e "console.log('node-fetch:', require('node-fetch').default ? 'OK' : 'FAIL')"
```

## 使用示例

安装完成后，在 OpenClaw 中使用：

```javascript
excel-generator({
  command: "from-data",
  file: "测试.xlsx",
  data: [["姓名", "年龄"], ["张三", 25]],
  style: {
    header: { bold: true, bgColor: "4472C4", color: "FFFFFF" },
    border: true,
    autoWidth: true
  }
})
```

## 下一步

安装成功后，可以：
1. 查看 SKILL.md 了解完整功能
2. 运行 `npm test` 查看所有测试
3. 开始使用 Excel 生成功能
