<p align="center">
  <img src="PinPrompt.png" alt="PinPrompt" width="120" />
</p>

<h1 align="center">PinPrompt - Prompt Classification Management Tool</h1>

A lightweight desktop Prompt management tool built with PySide6, supporting category storage, window always-on-top, one-click copy, and keyword search.

## ✨ Features

- **Category Management** — Create multiple categories to organize Prompts
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
python -m PyInstaller --noconfirm --onefile --windowed --icon "PinPrompt.ico" --name "PinPrompt" main_pyside.py
```

Output: `dist/PinPrompt.exe` (~45MB).

## 📖 User Guide

| Action | Description |
|--------|-------------|
| Create Category | Click "➕ 新建分类" at top, enter category name |
| Select Category | Click category in left sidebar |
| Create Prompt | Select a category, click "📝 新建Prompt" |
| Copy Prompt | Click "📋 复制" on the card |
| Edit Prompt | Click "✏️ 编辑" (Ctrl+S to save in dialog) |
| Delete Prompt | Click "🗑️ 删除", confirm to delete |
| Search Prompt | Enter keywords in search box to filter |
| Always-on-Top | Check "📌 窗口置顶" checkbox |
| Delete Category | Select category, click "🗑️ 删除分类", confirm (deletes all Prompts) |

## 📁 Data Storage

Data is stored in `prompts.json` (already in .gitignore):

```json
{
  "categories": {
    "Programming Helper": {
      "prompts": [
        {
          "title": "Code Review",
          "content": "Please help me review the following code...",
          "created": "2026-04-16 23:42",
          "modified": "2026-04-17 15:30"
        }
      ]
    }
  }
}
```

> After packaging to exe, data file is in the same directory as exe; in dev environment, data file is in the same directory as script.

## 📂 Project Structure

```
PinPrompt/
├── main_pyside.py    # PySide6 main program
├── PinPrompt.png      # Project icon
├── PinPrompt.ico      # exe icon (Windows)
├── prompts.json      # Data file (auto-generated, not committed)
├── requirements.txt  # Dependencies
├── README.md         # This file (Chinese)
└── README_en.md      # English version
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