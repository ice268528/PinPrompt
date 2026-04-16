# PinPrompt - Prompt 分类管理工具

一个轻量级的桌面 Prompt 管理工具，支持分类存储、窗口置顶、一键复制。

## 功能特性

- ✅ **分类管理**：创建多个分类，按类别组织 Prompt
- ✅ **一键复制**：每个 Prompt 都有独立的复制按钮
- ✅ **窗口置顶**：支持窗口置顶，方便随时查看
- ✅ **编辑删除**：支持 Prompt 的编辑和删除
- ✅ **数据持久化**：数据保存在本地 JSON 文件中

## 快速启动

### 推荐：无黑框启动 ⭐
```bash
# 双击此文件，无命令行黑框
.\start.vbs
```

> 💡 建议右键 `start.vbs` → 发送到 → 桌面快捷方式，方便启动

### 方式二：命令行启动
```bash
python main.py
```

### 方式三：无窗口命令行启动
```bash
pythonw main.py
```

## 依赖安装

```bash
pip install pyperclip
```

> 注：tkinter 是 Python 内置库，无需额外安装

## 使用说明

1. **创建分类**：点击「新建分类」按钮
2. **添加 Prompt**：选择分类后，点击「新建 Prompt」
3. **复制 Prompt**：点击 Prompt 卡片上的「复制」按钮
4. **窗口置顶**：勾选「窗口置顶」选项

## 数据存储

数据保存在 `prompts.json` 文件中，格式如下：

```json
{
  "categories": {
    "编程助手": {
      "prompts": [
        {
          "title": "代码审查",
          "content": "请帮我审查以下代码...",
          "created": "2026-04-16 23:42"
        }
      ]
    }
  }
}
```

## 系统要求

- Python 3.7+
- Windows / macOS / Linux
