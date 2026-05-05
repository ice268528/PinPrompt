# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

PinPrompt 是一个 Windows 桌面端的 Prompt 分类管理工具。**当前活跃版本是 PySide6 实现，入口为 [main_pyside.py](main_pyside.py)**；[main.py](main.py) 是 v1 tkinter 原型，因 Canvas 滚动性能问题被弃用但保留在仓库中以备参考——**修改功能时应改 `main_pyside.py`，而不是 `main.py`**。

## 常用命令

### 开发环境

```bash
conda activate PinPrompt
python main_pyside.py
```

环境一次性创建：

```bash
conda create -n PinPrompt python=3.13 -y
conda activate PinPrompt
pip install PySide6 pyperclip
```

### 打包 exe

```bash
conda activate PinPrompt
python -m PyInstaller --noconfirm --onefile --windowed --icon "PinPrompt.ico" --name "PinPrompt" main_pyside.py
```

产物在 `dist/PinPrompt.exe`（约 45MB）。**不要使用 [PinPrompt.spec](PinPrompt.spec) 直接打包**——它的 datas 是空的、没有把 `PinPrompt.ico` 作为运行时资源打入，必须用上面的命令行参数确保图标和单文件模式正确。

### 图标维护

- [gen_ico.py](gen_ico.py)：从 `PinPrompt.png` 生成多尺寸（16/32/48/64/128/256）的 `PinPrompt.ico`，需要 Pillow
- [check_icon.py](check_icon.py)：用 `pefile` 检查 exe 中实际内嵌的图标资源（路径硬编码为 `dist2/PinPrompt.exe`，按需修改）

## 架构要点

### 单文件结构

[main_pyside.py](main_pyside.py) 由三个类组成：

- `PromptCard`（QFrame）——单条 Prompt 的卡片视图，承载复制/编辑/删除按钮
- `AddEditDialog`（QDialog）——新建/编辑共用同一个弹窗，通过 `is_edit` 区分；内置 Ctrl+S 快捷键
- `PinPromptApp`（QMainWindow）——主窗口，持有数据 `self.data` 和当前分类 `self.current_category`

### 数据持久化

数据是单个 JSON 文件 `prompts.json`，结构为 `{"categories": {分类名: {"prompts": [...]}}}`。**路径在开发和打包后不一样**：

```python
if getattr(sys, 'frozen', False):
    DATA_DIR = os.path.dirname(sys.executable)  # exe 同级目录
else:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))  # 脚本同级目录
```

任何涉及读写 `prompts.json` 或加载 `PinPrompt.ico` 的逻辑都必须走 `DATA_DIR`，否则 exe 运行时会找错位置。

### 窗口置顶（toggle_on_top）

[main_pyside.py:527](main_pyside.py#L527) 的实现刻意走"Qt flags + WinAPI"双路径，是踩坑后的结果，**改动时要小心**：

- 单纯用 `setWindowFlags(Qt.WindowStaysOnTopHint)` 会导致 Windows 标题栏的关闭/最小化按钮失效，所以同时显式补上 `WindowCloseButtonHint | WindowSystemMenuHint | WindowMinimizeButtonHint | WindowMaximizeButtonHint`
- 同时调用 Windows API `SetWindowPos(HWND_TOPMOST/HWND_NOTOPMOST)` 作为兜底，覆盖 Qt flags 在某些情况下不生效的场景
- 两条路径都要保留，去掉任意一条都可能在某种 Windows 版本上失效

### Prompt 卡片刷新

`refresh_prompts` 通过 `while self.prompt_layout.count(): ... deleteLater()` 全量重建卡片。这是有意为之——比起增量更新，全量重建简单可靠，搜索过滤直接复用同一路径（`search_text` 为空时显示全部）。

## 分支约定

- `pyside6` 为当前开发分支
- `main` 为主分支（PR 默认目标）

## 已知遗留物

- [main.py](main.py)：v1 tkinter 版本，**不再维护**，保留作历史参考
- [PinPrompt_old.ico](PinPrompt_old.ico)：旧图标，参考用
- [PinPrompt.spec](PinPrompt.spec)：默认生成的 spec，**不可用于打包**，见上文
