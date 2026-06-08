[English](README_en.md) | [中文](README.md)

---

<p align="center">
  <img src="PinPrompt.png" alt="PinPrompt" width="120" />
</p>

<h1 align="center">PinPrompt - Prompt 分类管理工具</h1>

一个轻量级的桌面 Prompt 管理工具，使用 PySide6 构建，支持二级分类嵌套、拖拽排序、回收站、窗口置顶、一键复制、关键词搜索、Markdown 渲染。

## ✨ 功能特性

- **二级分类树** — 支持顶级分类 + 子分类嵌套（最多 2 层），可折叠展开
- **Prompt 树节点** — 左侧分类树下直接展示 Prompt 列表，支持拖拽排序和跨分类移动
- **拖拽排序** — 自由调整分类和 Prompt 顺序，支持跨父级移动
- **回收站机制** — 分类和 Prompt 删除后进入回收站，支持恢复或永久删除
- **路径自动重建** — 恢复时若原父分类被删，按记录的层级路径自动重建空分类
- **递归视图** — 父分类可一键查看其自身和所有后代分类的 Prompt
- **Markdown 渲染** — Prompt 内容支持 Markdown 格式，卡片预览自动渲染；编辑器内置预览模式
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
python -m PyInstaller --noconfirm --onefile --windowed --icon "PinPrompt.ico" --add-data "PinPrompt.ico;." --name "PinPrompt" main_pyside.py
```

打包产物位于 `dist/PinPrompt.exe`（约 45MB）。

## 📖 使用说明

| 操作 | 说明 |
|------|------|
| 新建顶级分类 | 点击顶部「➕ 新建顶级分类」按钮，输入分类名称 |
| 新建子分类 | 右键某分类 →「新建子分类」，输入名称 |
| 选择分类 | 点击左侧分类树切换，支持折叠展开 |
| 拖拽排序 | 按住分类或 Prompt 拖动调整顺序，支持跨分类移动 |
| 递归显示 | 点击顶部「🌲 递归显示」，父分类展示所有后代 Prompt |
| 新建 Prompt | 选择分类后，点击「📝 新建Prompt」 |
| Markdown 编辑 | Prompt 内容支持 Markdown 语法，编辑时点击「预览」按钮查看渲染效果 |
| 复制 Prompt | 点击卡片上的「📋 复制」按钮 |
| 编辑 Prompt | 点击卡片上的「✏️ 编辑」按钮（弹窗内 Ctrl+S 保存） |
| 删除 Prompt | 点击卡片上的「🗑️ 删除」按钮 → 移入回收站 |
| 删除分类 | 右键分类 →「删除」→ 移入回收站（含所有子分类和 Prompt） |
| 恢复/清空回收站 | 点击左侧「🗑️ 回收站」节点，在右侧操作 |
| 搜索 Prompt | 在搜索框输入关键词，实时按标题和内容过滤 |
| 窗口置顶 | 勾选「📌 窗口置顶」复选框 |

## 📁 数据存储

数据保存在 `prompts.json` 文件中（已在 .gitignore 中排除），格式如下：

```json
{
  "version": 2,
  "categories": [
    {
      "name": "工作",
      "prompts": [],
      "expanded": true,
      "children": [
        {
          "name": "编程助手",
          "prompts": [
            {
              "title": "代码审查",
              "content": "请帮我审查以下代码...",
              "created": "2026-04-16 23:42",
              "modified": "2026-04-17 15:30"
            }
          ],
          "expanded": false,
          "children": []
        }
      ]
    }
  ],
  "trash": [
    {
      "id": 1,
      "type": "category",
      "payload": { ... },
      "origin_path": ["工作"],
      "deleted_at": "2026-05-05 14:30"
    }
  ]
}
```

> 旧版本 v1 数据会在首次启动时自动迁移到 v2，并生成 `prompts.json.v1.bak` 备份。
>
> exe 打包后，数据文件与 exe 同级目录；开发环境下，数据文件与脚本同级目录。

## 📂 项目结构

```
PinPrompt/
├── main_pyside.py             # PySide6 主程序
├── category_tree.py           # 自定义 QTreeWidget（拖拽校验）
├── data_ops.py                # 纯数据操作（迁移/路径/回收站逻辑）
├── tests/                     # pytest 单元测试
│   ├── conftest.py
│   └── test_data_ops.py
├── docs/superpowers/          # 设计文档与实现计划
├── PinPrompt.png              # 项目图标
├── PinPrompt.ico              # exe 图标（Windows）
├── prompts.json               # 数据文件（自动生成，不提交）
├── requirements.txt           # 依赖清单
├── README.md                  # 本文件（中文）
├── README_en.md               # 英文版本
└── .gitignore                 # Git 忽略规则
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
- **v3** — 分类树改造：QListWidget → QTreeWidget，支持二级嵌套、拖拽排序、折叠展开；新增回收站机制（删除→恢复→永久删除）；新增递归视图；v1→v2 数据迁移
- **v4** — 左侧树展示 Prompt 节点，支持拖拽排序和跨分类移动；Prompt 内容支持 Markdown 渲染，编辑器内置预览模式；修复打包后窗口图标不显示的问题
