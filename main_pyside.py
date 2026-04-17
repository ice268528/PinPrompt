"""
PinPrompt - Prompt 分类管理工具
使用 PySide6 重写，解决 tkinter 滚动性能问题
功能：分类存储 prompt、窗口置顶、一键复制
"""

import sys
import json
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QLineEdit, QDialog, QDialogButtonBox, QCheckBox, QScrollArea,
    QFrame, QSplitter, QMessageBox, QStatusBar
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut
import pyperclip

# 数据文件路径（exe 打包时放在 exe 同级目录，开发时放在脚本目录）
if getattr(sys, 'frozen', False):
    DATA_DIR = os.path.dirname(sys.executable)
else:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(DATA_DIR, "prompts.json")


class PromptCard(QFrame):
    """Prompt 卡片组件"""
    
    def __init__(self, prompt_data, index, parent=None):
        super().__init__(parent)
        self.prompt_data = prompt_data
        self.index = index
        self.parent_app = parent
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            PromptCard {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
            PromptCard:hover {
                border-color: #4a90d9;
                background-color: #f8f9fa;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 标题行
        title_layout = QHBoxLayout()
        
        self.title_label = QLabel(self.prompt_data.get("title", "无标题"))
        self.title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        # 按钮组
        copy_btn = QPushButton("📋 复制")
        copy_btn.setFixedWidth(80)
        copy_btn.clicked.connect(self.copy_content)
        title_layout.addWidget(copy_btn)
        
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.setFixedWidth(80)
        edit_btn.clicked.connect(self.edit_prompt)
        title_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.setFixedWidth(80)
        delete_btn.clicked.connect(self.delete_prompt)
        title_layout.addWidget(delete_btn)
        
        layout.addLayout(title_layout)
        
        # 内容预览
        content = self.prompt_data.get("content", "")
        preview = content[:150] + "..." if len(content) > 150 else content
        self.content_label = QLabel(preview)
        self.content_label.setWordWrap(True)
        self.content_label.setFont(QFont("Microsoft YaHei", 9))
        self.content_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.content_label)
        
        # 时间信息
        created = self.prompt_data.get("created", "")
        modified = self.prompt_data.get("modified", "")
        time_text = f"创建: {created}"
        if modified:
            time_text += f" | 修改: {modified}"
        self.time_label = QLabel(time_text)
        self.time_label.setFont(QFont("Microsoft YaHei", 8))
        self.time_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.time_label)
        
    def copy_content(self):
        """复制内容"""
        try:
            pyperclip.copy(self.prompt_data.get("content", ""))
            if self.parent_app:
                self.parent_app.show_toast("✅ 已复制到剪贴板")
        except Exception as e:
            if self.parent_app:
                self.parent_app.show_toast(f"❌ 复制失败: {e}")
    
    def edit_prompt(self):
        """编辑 Prompt"""
        if self.parent_app:
            self.parent_app.edit_prompt(self.index)
    
    def delete_prompt(self):
        """删除 Prompt"""
        if self.parent_app:
            self.parent_app.delete_prompt(self.index)


class AddEditDialog(QDialog):
    """添加/编辑 Prompt 对话框"""
    
    def __init__(self, parent=None, title="", content="", is_edit=False):
        super().__init__(parent)
        self.is_edit = is_edit
        self.setup_ui(title, content)
        
    def setup_ui(self, title, content):
        """设置UI"""
        self.setWindowTitle("编辑 Prompt" if self.is_edit else "新建 Prompt")
        self.setMinimumSize(500, 350)
        self.resize(550, 400)
        
        layout = QVBoxLayout(self)
        
        # 标题输入
        title_label = QLabel("标题:")
        title_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(title_label)
        
        self.title_edit = QLineEdit()
        self.title_edit.setFont(QFont("Microsoft YaHei", 10))
        self.title_edit.setText(title)
        layout.addWidget(self.title_edit)
        
        # 内容输入
        content_label = QLabel("内容:")
        content_label.setFont(QFont("Microsoft YaHei", 10))
        layout.addWidget(content_label)
        
        self.content_edit = QTextEdit()
        self.content_edit.setFont(QFont("Microsoft YaHei", 10))
        self.content_edit.setPlainText(content)
        self.content_edit.setAcceptRichText(False)
        layout.addWidget(self.content_edit)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # 设置按钮文本
        save_btn = button_box.button(QDialogButtonBox.Save)
        save_btn.setText("保存 (Ctrl+S)")
        
        layout.addWidget(button_box)
        
        # Ctrl+S 快捷键
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.accept)
        
        self.setWindowTitle("编辑 Prompt" if self.is_edit else "新建 Prompt")
        
    def get_data(self):
        """获取输入数据"""
        return {
            "title": self.title_edit.text().strip(),
            "content": self.content_edit.toPlainText().strip()
        }


class PinPromptApp(QMainWindow):
    """主应用"""
    
    def __init__(self):
        super().__init__()
        self.data = self.load_data()
        self.current_category = None
        self.setup_ui()
        # 启动时刷新分类列表
        self.refresh_categories()
        
    def load_data(self):
        """加载数据"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"categories": {}}
        return {"categories": {}}
    
    def save_data(self):
        """保存数据"""
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("PinPrompt - Prompt管理工具")
        self.resize(900, 650)
        self.setMinimumSize(600, 400)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 顶部工具栏
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # 内容区域（分割器）
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：分类列表
        left_panel = self.create_category_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：Prompt 列表
        right_panel = self.create_prompt_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([200, 700])
        
        main_layout.addWidget(splitter, 1)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        
        # 新建分类按钮
        add_cat_btn = QPushButton("➕ 新建分类")
        add_cat_btn.clicked.connect(self.add_category)
        toolbar_layout.addWidget(add_cat_btn)
        
        # 新建 Prompt 按钮
        add_prompt_btn = QPushButton("📝 新建Prompt")
        add_prompt_btn.clicked.connect(self.add_prompt)
        toolbar_layout.addWidget(add_prompt_btn)
        
        # 删除分类按钮
        del_cat_btn = QPushButton("🗑️ 删除分类")
        del_cat_btn.clicked.connect(self.delete_category)
        toolbar_layout.addWidget(del_cat_btn)
        
        # 分隔符
        toolbar_layout.addSpacing(20)
        
        # 窗口置顶复选框
        self.always_on_top_cb = QCheckBox("📌 窗口置顶")
        self.always_on_top_cb.stateChanged.connect(self.toggle_on_top)
        toolbar_layout.addWidget(self.always_on_top_cb)
        
        # 搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 搜索...")
        self.search_edit.setFixedWidth(180)
        self.search_edit.textChanged.connect(self.on_search_changed)
        toolbar_layout.addWidget(self.search_edit)
        
        toolbar_layout.addStretch()
        
        # Toast 提示标签
        self.toast_label = QLabel("")
        self.toast_label.setStyleSheet("""
            QLabel {
                background-color: #2ed573;
                color: white;
                padding: 5px 15px;
                border-radius: 4px;
                font-family: 'Microsoft YaHei';
            }
        """)
        self.toast_label.setVisible(False)
        toolbar_layout.addWidget(self.toast_label)
        
        return toolbar
    
    def create_category_panel(self):
        """创建分类面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title = QLabel("分类")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(title)
        
        # 分类列表
        self.category_list = QListWidget()
        self.category_list.setFont(QFont("Microsoft YaHei", 10))
        self.category_list.currentItemChanged.connect(self.on_category_select)
        layout.addWidget(self.category_list)
        
        return panel
    
    def create_prompt_panel(self):
        """创建 Prompt 面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title = QLabel("Prompts")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(title)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #f5f5f5;
            }
        """)
        
        # 滚动内容容器
        self.prompt_container = QWidget()
        self.prompt_layout = QVBoxLayout(self.prompt_container)
        self.prompt_layout.setAlignment(Qt.AlignTop)
        self.prompt_layout.setSpacing(5)
        
        scroll_area.setWidget(self.prompt_container)
        layout.addWidget(scroll_area)
        
        return panel
    
    def refresh_categories(self):
        """刷新分类列表"""
        self.category_list.clear()
        for cat in sorted(self.data["categories"].keys()):
            item = QListWidgetItem(f"📁 {cat}")
            item.setData(Qt.UserRole, cat)
            self.category_list.addItem(item)
    
    def on_category_select(self, current, previous):
        """选择分类"""
        if current:
            cat_name = current.data(Qt.UserRole)
            self.current_category = cat_name
            self.refresh_prompts()
            self.status_bar.showMessage(f"当前分类: {cat_name}")
    
    def on_search_changed(self, text):
        """搜索框内容变化"""
        self.refresh_prompts()
    
    def refresh_prompts(self):
        """刷新 Prompt 列表"""
        # 清空现有内容
        while self.prompt_layout.count():
            item = self.prompt_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.current_category or self.current_category not in self.data["categories"]:
            return
        
        prompts = self.data["categories"][self.current_category].get("prompts", [])
        
        # 搜索过滤
        search_text = self.search_edit.text().strip().lower()
        
        if search_text:
            prompts = [p for p in prompts 
                      if search_text in p.get("title", "").lower() 
                      or search_text in p.get("content", "").lower()]
        
        if not prompts:
            empty_label = QLabel("暂无 Prompt" if not search_text else "没有匹配的搜索结果")
            empty_label.setFont(QFont("Microsoft YaHei", 10))
            empty_label.setStyleSheet("color: #999999; padding: 20px;")
            self.prompt_layout.addWidget(empty_label)
            return
        
        for i, prompt in enumerate(prompts):
            card = PromptCard(prompt, i, self)
            self.prompt_layout.addWidget(card)
    
    def add_category(self):
        """添加分类"""
        from PySide6.QtWidgets import QInputDialog
        
        text, ok = QInputDialog.getText(
            self, "新建分类", "分类名称:"
        )
        
        if ok and text.strip():
            cat_name = text.strip()
            if cat_name in self.data["categories"]:
                QMessageBox.warning(self, "警告", "分类已存在！")
                return
            
            self.data["categories"][cat_name] = {"prompts": []}
            self.save_data()
            self.refresh_categories()
            self.status_bar.showMessage(f"已添加分类: {cat_name}")
    
    def delete_category(self):
        """删除分类"""
        if not self.current_category:
            QMessageBox.warning(self, "警告", "请先选择要删除的分类！")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除分类「{self.current_category}」及其所有 Prompt 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.data["categories"][self.current_category]
            self.save_data()
            self.current_category = None
            self.refresh_categories()
            self.refresh_prompts()
            self.status_bar.showMessage("分类已删除")
    
    def add_prompt(self):
        """添加 Prompt"""
        if not self.current_category:
            QMessageBox.warning(self, "警告", "请先选择分类！")
            return
        
        dialog = AddEditDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data["title"] or not data["content"]:
                QMessageBox.warning(self, "警告", "标题和内容不能为空！")
                return
            
            self.data["categories"][self.current_category]["prompts"].append({
                "title": data["title"],
                "content": data["content"],
                "created": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            self.save_data()
            self.refresh_prompts()
            self.status_bar.showMessage(f"已添加 Prompt: {data['title']}")
    
    def edit_prompt(self, index):
        """编辑 Prompt"""
        prompts = self.data["categories"][self.current_category]["prompts"]
        prompt = prompts[index]
        
        dialog = AddEditDialog(
            self,
            title=prompt.get("title", ""),
            content=prompt.get("content", ""),
            is_edit=True
        )
        
        if dialog.exec():
            data = dialog.get_data()
            if not data["title"] or not data["content"]:
                QMessageBox.warning(self, "警告", "标题和内容不能为空！")
                return
            
            prompts[index] = {
                "title": data["title"],
                "content": data["content"],
                "created": prompt.get("created", ""),
                "modified": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            self.save_data()
            self.refresh_prompts()
            self.status_bar.showMessage(f"已更新 Prompt: {data['title']}")
    
    def delete_prompt(self, index):
        """删除 Prompt"""
        prompts = self.data["categories"][self.current_category]["prompts"]
        prompt = prompts[index]
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 Prompt「{prompt.get('title')}」吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del prompts[index]
            self.save_data()
            self.refresh_prompts()
            self.status_bar.showMessage("Prompt 已删除")
    
    def toggle_on_top(self, state):
        """切换窗口置顶 - 使用 Windows API 强制置顶"""
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_SHOWWINDOW = 0x0040
        HWND_TOPMOST = wintypes.HWND(-1)
        HWND_NOTOPMOST = wintypes.HWND(-2)
        
        hwnd = wintypes.HWND(self.winId())
        
        if state == Qt.Checked:
            # 先设置扩展样式添加 TOPMOST
            ex_style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
            user32.SetWindowLongW(hwnd, -20, ex_style | 8)  # 8 = WS_EX_TOPMOST
            # 然后用 SetWindowPos 确保生效
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 
                              SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            user32.BringWindowToTop(hwnd)
            self.status_bar.showMessage("已置顶")
        else:
            # 移除 TOPMOST
            ex_style = user32.GetWindowLongW(hwnd, -20)
            user32.SetWindowLongW(hwnd, -20, ex_style & ~8)
            user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                              SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            self.status_bar.showMessage("取消置顶")
        
        self.raise_()
        self.activateWindow()
    
    def show_toast(self, message, duration=1500):
        """显示 Toast 提示"""
        self.toast_label.setText(message)
        self.toast_label.setVisible(True)
        
        # 自动隐藏
        QTimer.singleShot(duration, lambda: self.toast_label.setVisible(False))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    window = PinPromptApp()
    # 居中显示
    screen = app.primaryScreen().geometry()
    window.move(
        (screen.width() - window.width()) // 2,
        (screen.height() - window.height()) // 2
    )
    window.show()
    window.raise_()
    window.activateWindow()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
