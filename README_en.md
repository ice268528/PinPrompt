<p align="center">
  <img src="PinPrompt.png" alt="PinPrompt" width="120" />
</p>

<h1 align="center">PinPrompt - Prompt Classification Management Tool</h1>

A lightweight desktop Prompt management tool built with PySide6, supporting two-level nested categories, drag-and-drop sorting, trash bin, window always-on-top, one-click copy, keyword search, and Markdown rendering.

## ✨ Features

- **Two-Level Category Tree** — Support top-level categories + sub-categories (max 2 levels), collapsible/expandable
- **Prompt Tree Nodes** — Prompts displayed directly in the category tree, with drag-and-drop sorting and cross-category movement
- **Drag-and-Drop Sorting** — Freely reorder categories and Prompts, move sub-categories across parent categories
- **Trash Bin** — Categories and Prompts go to trash when deleted, with restore or permanent delete options
- **Auto Path Rebuild** — When restoring, if the original parent was deleted, automatically rebuild empty categories along the recorded path
- **Recursive View** — Parent category can display all descendant Prompts with one click
- **Markdown Rendering** — Prompt content supports Markdown format with auto-rendered preview; editor has built-in preview mode
- **One-Click Copy** — Each Prompt has an independent copy button with Toast notification
- **Always-on-Top** — Uses Windows API to keep window on top without affecting close button
- **Keyword Search** — Filter Prompts by title and content in real-time
- **Edit & Delete** — Support Prompt editing and deletion with created/modified timestamps
- **Data Persistence** — Data saved to local JSON file, works for both exe and dev environment
- **Keyboard Shortcut** — Ctrl+S to save in edit dialog

## 🚀 Quick Start

### Download exe (Recommended)

Go to [GitHub Releases](https://github.com/ice268528/PinPrompt/releases) to download the latest `PinPrompt.exe`, double-click to run, no Python installation required.

### Command Line

```bash
# Activate PinPrompt conda environment
conda activate PinPrompt
python main_pyside.py
```

## 📦 Dependencies

```bash
conda create -n PinPrompt python=3.13 -y
conda activate PinPrompt
pip install PySide6 pyperclip
```

## 🔨 Build exe

```bash
conda activate PinPrompt
python -m PyInstaller --noconfirm --onefile --windowed --icon "PinPrompt.ico" --add-data "PinPrompt.ico;." --name "PinPrompt" main_pyside.py
```

Output: `dist/PinPrompt.exe` (~45MB).

## 📖 User Guide

| Action | Description |
|--------|-------------|
| Create Top Category | Click "➕ 新建顶级分类" at top, enter category name |
| Create Sub-Category | Right-click a category → "新建子分类", enter name |
| Select Category | Click category in left sidebar, supports collapse/expand |
| Drag-and-Drop | Drag categories or Prompts to reorder, supports cross-category movement |
| Recursive View | Click "🌲 递归显示" to show all descendant Prompts of a parent |
| Create Prompt | Select a category, click "📝 新建Prompt" |
| Markdown Editing | Prompt content supports Markdown syntax; click "预览" button in editor to preview rendered output |
| Copy Prompt | Click "📋 复制" on the card |
| Edit Prompt | Click "✏️ 编辑" (Ctrl+S to save in dialog) |
| Delete Prompt | Click "🗑️ 删除" → moves to trash |
| Delete Category | Right-click category → "删除" → moves to trash (with all sub-categories and Prompts) |
| Restore/Clear Trash | Click "🗑️ 回收站" node on the left, operate on the right panel |
| Search Prompt | Enter keywords in search box to filter by title and content |
| Always-on-Top | Check "📌 窗口置顶" checkbox |

## 📁 Data Storage

Data is stored in `prompts.json` (already in .gitignore):

```json
{
  "version": 2,
  "categories": [
    {
      "name": "Work",
      "prompts": [],
      "expanded": true,
      "children": [
        {
          "name": "Programming",
          "prompts": [
            {
              "title": "Code Review",
              "content": "Please help me review the following code...",
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
      "origin_path": ["Work"],
      "deleted_at": "2026-05-05 14:30"
    }
  ]
}
```

> Legacy v1 data will be automatically migrated to v2 on first startup, with a `prompts.json.v1.bak` backup created.
>
> After packaging to exe, data file is in the same directory as exe; in dev environment, data file is in the same directory as script.

## 📂 Project Structure

```
PinPrompt/
├── main_pyside.py             # PySide6 main program
├── category_tree.py           # Custom QTreeWidget (drag-drop validation)
├── data_ops.py                # Pure data operations (migration/path/trash logic)
├── tests/                     # pytest unit tests
│   ├── conftest.py
│   └── test_data_ops.py
├── docs/superpowers/          # Design docs and implementation plans
├── PinPrompt.png              # Project icon
├── PinPrompt.ico              # exe icon (Windows)
├── prompts.json               # Data file (auto-generated, not committed)
├── requirements.txt           # Dependencies
├── README.md                  # This file (Chinese)
└── README_en.md               # English version
```

## 🖥️ System Requirements

- **Windows** 10/11 (recommended)
- Python 3.7+ (development)
- PySide6 6.x + pyperclip

## 🔧 Tech Stack

- **UI Framework**: PySide6 (Qt for Python)
- **Always-on-Top**: Windows API (SetWindowPos + ctypes), avoiding Qt setWindowFlags breaking close button
- **Clipboard**: pyperclip
- **Packaging**: PyInstaller (single file + windowless mode)

## 📝 Changelog

- **v1** — tkinter prototype
- **v2** — PySide6 rewrite, fix tkinter Canvas scroll performance; add search; implement window always-on-top via Windows API; Toast notification instead of dialog; packaged as single exe
- **v3** — Category tree overhaul: QListWidget → QTreeWidget, supporting two-level nesting, drag-and-drop sorting, collapse/expand; added trash bin (delete→restore→permanent delete); added recursive view; v1→v2 data migration
- **v4** — Prompt tree nodes in sidebar with drag-and-drop sorting and cross-category movement; Markdown rendering for Prompt content with built-in editor preview; fixed window icon not showing in packaged exe
