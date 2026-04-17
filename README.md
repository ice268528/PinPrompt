[English](README_en.md) | [中文](README.md)

---

<p align="center">
  <img src="PinPrompt.png" alt="PinPrompt" width="120" />
</p>

<h1 align="center">PinPrompt - Prompt 分类管理工具</h1>

一个轻量级的桌面 Prompt 管理工具，使用 PySide6 构建，支持分类存储、窗口置顶、一键复制、关键词搜索。

## ✨ 功能特性

- **分类管理** — 创建多个分类，按类别组织 Prompt
- **一键复制** — 每个 Prompt 独立复制按钮，复制后显示 Toast 提示
- **窗口置顶** — 使用 Windows API 实现窗口置顶，不影响关闭按钮
- **关键词搜索** — 按标题和内容实时过滤 Prompt
- **编辑删除** — 支持 Prompt 的编辑和删除，记录创建/修改时间
- **数据持久化** — 数据保存在本地 JSON 文件中，exe 和开发环境均可正确读写
- **快捷操作** — 编辑弹窗内支持 Ctrl+S 快速保存

## 🚀 快速启动

### 下载 exe（推荐）

前往 [GitHub Releases](https://github.com/ice268528/PinPrompt/releases) 下载最新版本的 `PinPrompt.exe`，双击即可运行，无需安装 Python。

### 命令行启动

```bash
# 激活 PinPrompt conda 环境
conda activate PinPrompt
python main_pyside.py
```

## 📦 依赖安装

```bash
conda create -n PinPrompt python=3.13 -y
conda activate PinPrompt
pip install PySide6 pyperclip
```

## 🔨 打包为 exe

```bash
conda activate PinPrompt
python -m PyInstaller --noconfirm --onefile --windowed --icon "PinPrompt.ico" --name "PinPrompt" main_pyside.py
```

打包产物位于 `dist/PinPrompt.exe`（约 45MB）。

## 📖 使用说明

| 操作 | 说明 |
|------|------|
| 新建分类 | 点击顶部「➕ 新建分类」按钮，输入分类名称 |
| 选择分类 | 点击左侧分类列表切换 |
| 新建 Prompt | 选择分类后，点击「📝 新建Prompt」 |
| 复制 Prompt | 点击卡片上的「📋 复制」按钮 |
| 编辑 Prompt | 点击卡片上的「✏️ 编辑」按钮（弹窗内 Ctrl+S 保存） |
| 删除 Prompt | 点击卡片上的「🗑️ 删除」按钮，确认后删除 |
| 搜索 Prompt | 在搜索框输入关键词，实时按标题和内容过滤 |
| 窗口置顶 | 勾选「📌 窗口置顶」复选框 |
| 删除分类 | 选中分类后，点击「🗑️ 删除分类」，确认后删除（连同所有 Prompt） |

## 📁 数据存储

数据保存在 `prompts.json` 文件中（已在 .gitignore 中排除），格式如下：

```json
{
  "categories": {
    "编程助手": {
      "prompts": [
        {
          "title": "代码审查",
          "content": "请帮我审查以下代码...",
          "created": "2026-04-16 23:42",
          "modified": "2026-04-17 15:30"
        }
      ]
    }
  }
}
```

> exe 打包后，数据文件与 exe 同级目录；开发环境下，数据文件与脚本同级目录。

## 📂 项目结构

```
PinPrompt/
├── main_pyside.py    # PySide6 主程序
├── PinPrompt.png      # 项目图标
├── PinPrompt.ico      # exe 图标（Windows）
├── prompts.json       # 数据文件（自动生成，不提交）
├── requirements.txt   # 依赖清单
├── README.md          # 本文件（中文）
├── README_en.md       # 英文版本
└── .gitignore         # Git 忽略规则
```

## 🖥️ 系统要求

- **Windows** 10/11（推荐）
- Python 3.7+（开发环境）
- PySide6 6.x + pyperclip

## 🔧 技术栈

- **UI 框架**：PySide6（Qt for Python）
- **窗口置顶**：Windows API（SetWindowPos + ctypes），避免 Qt setWindowFlags 导致关闭按钮失效
- **剪贴板**：pyperclip
- **打包**：PyInstaller（单文件 + 无窗口模式）

## 📝 开发日志

- **v1** — tkinter 原型版本
- **v2** — PySide6 重写，解决 tkinter Canvas 滚动性能问题；新增搜索功能；使用 Windows API 实现窗口置顶；Toast 提示替代弹窗；打包为单文件 exe