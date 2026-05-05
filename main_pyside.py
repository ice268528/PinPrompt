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
    QLabel, QPushButton, QTreeWidgetItem, QTextEdit,
    QLineEdit, QDialog, QDialogButtonBox, QCheckBox, QScrollArea,
    QFrame, QSplitter, QMessageBox, QStatusBar, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut
import pyperclip

from category_tree import CategoryTreeWidget, ROLE_KEY, KIND_KEY
from data_ops import migrate_v1_to_v2

# 数据文件路径（exe 打包时放在 exe 同级目录，开发时放在脚本目录）
if getattr(sys, 'frozen', False):
    DATA_DIR = os.path.dirname(sys.executable)
else:
    DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(DATA_DIR, "prompts.json")


class PromptCard(QFrame):
    """Prompt 卡片组件"""
    
    def __init__(self, prompt_data, index, parent=None, prompt_owner=None):
        super().__init__(parent)
        self.prompt_data = prompt_data
        self.index = index
        self.parent_app = parent
        self.prompt_owner = prompt_owner if prompt_owner is not None else parent.current_category if parent else None
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
            self.parent_app.edit_prompt(self.index, prompt_owner=self.prompt_owner)

    def delete_prompt(self):
        """删除 Prompt"""
        if self.parent_app:
            self.parent_app.delete_prompt(self.index, prompt_owner=self.prompt_owner)


class TrashItemCard(QFrame):
    """回收站中的单个条目卡片（可能是分类或 prompt）。"""
    def __init__(self, entry, app):
        super().__init__()
        self.entry = entry
        self.app = app
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(
            "TrashItemCard { background: #fafafa; border: 1px solid #ddd; "
            "border-radius: 6px; padding: 8px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        # 左侧：类型 + 名称 + 元信息
        info_layout = QVBoxLayout()
        kind = entry["type"]
        if kind == "category":
            cat = entry["payload"]
            name = cat.get("name", "(未命名)")
            child_n = len(cat.get("children", []))
            prompt_n = self.app._count_prompts_recursive(cat)
            title_text = f"📁 分类：{name}"
            meta = f"子分类 {child_n} / Prompt {prompt_n}"
        else:
            p = entry["payload"]
            title_text = f"📄 Prompt：{p.get('title', '(未命名)')}"
            meta = ""

        title_lbl = QLabel(title_text)
        title_lbl.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(title_lbl)

        path_str = " / ".join(entry.get("origin_path", [])) or "(顶级)"
        path_lbl = QLabel(f"原位置：{path_str}")
        path_lbl.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(path_lbl)

        if meta:
            meta_lbl = QLabel(meta)
            meta_lbl.setStyleSheet("color: #666; font-size: 11px;")
            info_layout.addWidget(meta_lbl)

        time_lbl = QLabel(f"删除于：{entry.get('deleted_at', '')}")
        time_lbl.setStyleSheet("color: #999; font-size: 11px;")
        info_layout.addWidget(time_lbl)

        layout.addLayout(info_layout, stretch=1)

        # 右侧：恢复 / 永久删除按钮
        btn_layout = QVBoxLayout()
        restore_btn = QPushButton("恢复")
        restore_btn.clicked.connect(lambda: self.app._restore_trash_item(self.entry["id"]))
        btn_layout.addWidget(restore_btn)
        purge_btn = QPushButton("永久删除")
        purge_btn.setStyleSheet("color: #c00;")
        purge_btn.clicked.connect(lambda: self.app._purge_trash_item(self.entry["id"]))
        btn_layout.addWidget(purge_btn)
        layout.addLayout(btn_layout)


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
        self.current_view = "normal"
        self.recursive_view = False
        self.setup_ui()
        # 启动时刷新分类列表
        self.refresh_categories()
        
    def load_data(self):
        """加载数据，v1 自动迁移到 v2，并保留 .v1.bak 备份。"""
        if not os.path.exists(DATA_FILE):
            return {"version": 2, "categories": [], "trash": []}
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except Exception:
            return {"version": 2, "categories": [], "trash": []}

        if raw.get("version", 1) < 2:
            # 备份 v1
            bak_path = DATA_FILE + ".v1.bak"
            try:
                with open(bak_path, 'w', encoding='utf-8') as bf:
                    json.dump(raw, bf, ensure_ascii=False, indent=2)
            except Exception:
                pass
            raw = migrate_v1_to_v2(raw)
            self.save_data(raw)
        else:
            raw.setdefault("trash", [])
        return raw
    
    def save_data(self, data=None):
        """保存数据"""
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data if data is not None else self.data, f, ensure_ascii=False, indent=2)
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("PinPrompt - Prompt管理工具")
        self.resize(900, 650)
        self.setMinimumSize(600, 400)

        # 设置窗口图标
        icon_path = os.path.join(DATA_DIR, "PinPrompt.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
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
        
        # 设置分割比例（左侧给分类树更多空间，缓解拥挤感）
        splitter.setSizes([260, 640])
        
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
        
        # 新建顶级分类按钮
        add_cat_btn = QPushButton("➕ 新建顶级分类")
        add_cat_btn.clicked.connect(self.add_category)
        toolbar_layout.addWidget(add_cat_btn)

        # 新建 Prompt 按钮
        add_prompt_btn = QPushButton("📝 新建Prompt")
        add_prompt_btn.clicked.connect(self.add_prompt)
        toolbar_layout.addWidget(add_prompt_btn)

        # 分隔符
        toolbar_layout.addSpacing(20)

        # 递归视图开关
        self.recursive_btn = QPushButton("🌲 递归显示")
        self.recursive_btn.setCheckable(True)
        self.recursive_btn.setChecked(False)
        self.recursive_btn.setToolTip("开启后，父分类显示其本身和所有后代分类的 Prompt")
        self.recursive_btn.toggled.connect(self.on_recursive_toggled)
        toolbar_layout.addWidget(self.recursive_btn)

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
        """创建分类面板（使用 QTreeWidget 支持折叠与拖拽）。"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        title = QLabel("分类")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(title)

        # 搜索 + 折叠控制
        ctrl_layout = QHBoxLayout()

        self.cat_search_edit = QLineEdit()
        self.cat_search_edit.setPlaceholderText("🔍 搜索分类...")
        self.cat_search_edit.setClearButtonEnabled(True)
        self.cat_search_edit.textChanged.connect(self.on_cat_search_changed)
        ctrl_layout.addWidget(self.cat_search_edit)

        self.collapse_all_btn = QPushButton("⏷")
        self.collapse_all_btn.setFixedWidth(28)
        self.collapse_all_btn.setToolTip("全部折叠")
        self.collapse_all_btn.clicked.connect(self.collapse_all_categories)
        ctrl_layout.addWidget(self.collapse_all_btn)

        self.expand_all_btn = QPushButton("⏵")
        self.expand_all_btn.setFixedWidth(28)
        self.expand_all_btn.setToolTip("全部展开")
        self.expand_all_btn.clicked.connect(self.expand_all_categories)
        ctrl_layout.addWidget(self.expand_all_btn)

        layout.addLayout(ctrl_layout)

        # 分类树
        self.category_tree = CategoryTreeWidget()
        self.category_tree.setFont(QFont("Microsoft YaHei", 10))
        self.category_tree.currentItemChanged.connect(self.on_category_select)
        self.category_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_tree.customContextMenuRequested.connect(self.show_category_menu)
        self.category_tree.drop_rejected.connect(self._on_drop_rejected)
        self.category_tree.drop_completed.connect(self._on_drop_completed)
        layout.addWidget(self.category_tree)

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
    
    def _make_category_item(self, cat_dict, role="top"):
        """根据分类 dict 创建 QTreeWidgetItem。"""
        prompt_count = len(cat_dict.get("prompts", []))
        child_count = len(cat_dict.get("children", []))
        if child_count > 0:
            text = f"📂 {cat_dict['name']} [{child_count}]"
        else:
            text = f"📁 {cat_dict['name']} ({prompt_count})"
        item = QTreeWidgetItem([text])
        item.setData(0, ROLE_KEY, cat_dict)
        item.setData(0, KIND_KEY, role)
        item.setFlags(
            Qt.ItemIsEnabled | Qt.ItemIsSelectable |
            Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
        )
        return item

    def refresh_categories(self):
        """刷新分类树，支持搜索过滤。"""
        selected_path = None
        current = self.category_tree.currentItem()
        if current:
            cat = current.data(0, ROLE_KEY)
            if cat:
                selected_path = self._path_of_category(cat)

        self.category_tree.blockSignals(True)
        self.category_tree.clear()

        search_text = self.cat_search_edit.text().strip().lower() if hasattr(self, 'cat_search_edit') else ""

        for cat in self.data["categories"]:
            if search_text:
                cat_match = search_text in cat["name"].lower()
                child_matches = [c for c in cat.get("children", [])
                                 if search_text in c["name"].lower()]
                if not cat_match and not child_matches:
                    continue

            top_item = self._make_category_item(cat, role="top")
            self.category_tree.addTopLevelItem(top_item)

            children_to_show = cat.get("children", [])
            if search_text and not cat_match:
                children_to_show = child_matches

            for child in children_to_show:
                child_item = self._make_category_item(child, role="child")
                top_item.addChild(child_item)

            if search_text:
                top_item.setExpanded(True)
            else:
                top_item.setExpanded(cat.get("expanded", False))

        # 分隔符（不可选中、不可拖拽）
        sep = QTreeWidgetItem(["────────"])
        sep.setFlags(Qt.NoItemFlags)
        sep.setData(0, KIND_KEY, "separator")
        self.category_tree.addTopLevelItem(sep)

        # 回收站节点
        trash_count = len(self.data.get("trash", []))
        trash_item = QTreeWidgetItem([f"🗑️ 回收站 ({trash_count})"])
        trash_item.setData(0, KIND_KEY, "trash")
        trash_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.category_tree.addTopLevelItem(trash_item)

        if selected_path:
            item = self._find_item_by_path(selected_path)
            if item:
                self.category_tree.setCurrentItem(item)

        self.category_tree.blockSignals(False)

    def _path_of_category(self, cat):
        """根据 dict 引用返回其在 data 中的路径 [name] 或 [parent_name, name]。"""
        for top in self.data["categories"]:
            if top is cat:
                return [top["name"]]
            for child in top.get("children", []):
                if child is cat:
                    return [top["name"], child["name"]]
        return []

    def _find_item_by_path(self, path):
        """在 QTreeWidget 中按路径查找对应的 QTreeWidgetItem。"""
        if not path:
            return None
        root = self.category_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            cat = item.data(0, ROLE_KEY)
            if cat and cat.get("name") == path[0]:
                if len(path) == 1:
                    return item
                for j in range(item.childCount()):
                    child_item = item.child(j)
                    child_cat = child_item.data(0, ROLE_KEY)
                    if child_cat and child_cat.get("name") == path[1]:
                        return child_item
        return None

    def on_cat_search_changed(self, text):
        """分类搜索框内容变化时刷新树。"""
        self.refresh_categories()

    def collapse_all_categories(self):
        """全部折叠分类树。"""
        root = self.category_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.data(0, KIND_KEY) in ("top", "child"):
                item.setExpanded(False)
                self._persist_expanded_for_item(item)
        self.save_data()

    def expand_all_categories(self):
        """全部展开分类树。"""
        root = self.category_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.data(0, KIND_KEY) in ("top", "child"):
                item.setExpanded(True)
                self._persist_expanded_for_item(item)
        self.save_data()

    def _persist_expanded_for_item(self, item):
        """把单个 item 及其子项的展开状态写回 self.data。"""
        cat = item.data(0, ROLE_KEY)
        if cat is not None:
            cat["expanded"] = item.isExpanded()
        for j in range(item.childCount()):
            child_item = item.child(j)
            child_cat = child_item.data(0, ROLE_KEY)
            if child_cat is not None:
                child_cat["expanded"] = child_item.isExpanded()

    def on_category_select(self, current, previous):
        """选择分类树节点。"""
        if current is None:
            self.current_category = None
            self.current_view = "normal"
            self.refresh_prompts()
            return
        kind = current.data(0, KIND_KEY)
        if kind == "separator":
            return
        if kind == "trash":
            self.current_category = None
            self.current_view = "trash"
            self.refresh_trash_view()
            return
        cat = current.data(0, ROLE_KEY)
        if cat is None:
            return
        self.current_category = cat
        self.current_view = "normal"
        self.refresh_prompts()
        self.status_bar.showMessage(f"当前分类: {cat['name']}")

    def _on_drop_rejected(self, reason):
        self.status_bar.showMessage(reason, 3000)

    def _on_drop_completed(self):
        self.data["categories"] = self._tree_to_categories()
        # 同步 KIND_KEY 以反映实际层级（拖放后节点位置可能改变）
        root = self.category_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            kind = item.data(0, KIND_KEY)
            if kind in ("top", "child"):
                item.setData(0, KIND_KEY, "top")
                for j in range(item.childCount()):
                    item.child(j).setData(0, KIND_KEY, "child")
        self.save_data()
        self.refresh_categories()

    def _tree_to_categories(self):
        """遍历 QTreeWidget，把分类节点按当前层级结构重新序列化为 list[dict]。"""
        result = []
        root = self.category_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            kind = item.data(0, KIND_KEY)
            if kind not in ("top", "child"):
                continue
            cat = item.data(0, ROLE_KEY)
            if cat is None:
                continue
            cat["expanded"] = item.isExpanded()
            cat["children"] = []
            for j in range(item.childCount()):
                child_item = item.child(j)
                child_cat = child_item.data(0, ROLE_KEY)
                if child_cat is not None:
                    cat["children"].append(child_cat)
            result.append(cat)
        return result

    def on_search_changed(self, text):
        """搜索框内容变化"""
        self.refresh_prompts()

    def refresh_prompts(self):
        """根据 recursive_view 分发到普通或递归视图。"""
        if self.current_view == "trash":
            self.refresh_trash_view()
            return
        if self.current_category is None:
            self._clear_prompt_layout()
            return
        if self.recursive_view and self.current_category.get("children"):
            self._refresh_prompts_recursive()
        else:
            self._refresh_prompts_normal()

    def _clear_prompt_layout(self):
        while self.prompt_layout.count():
            child = self.prompt_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _refresh_prompts_normal(self):
        """只显示 self.current_category.prompts（带搜索过滤）。"""
        self._clear_prompt_layout()
        cat = self.current_category
        prompts = cat.get("prompts", [])
        kw = self.search_edit.text().strip().lower()
        if kw:
            prompts = [p for p in prompts
                       if kw in p.get("title", "").lower()
                       or kw in p.get("content", "").lower()]
        if not prompts:
            empty_label = QLabel("暂无 Prompt" if not kw else "没有匹配的搜索结果")
            empty_label.setFont(QFont("Microsoft YaHei", 10))
            empty_label.setStyleSheet("color: #999999; padding: 20px;")
            self.prompt_layout.addWidget(empty_label)
            self.prompt_layout.addStretch()
            return
        for idx, p in enumerate(prompts):
            card = PromptCard(p, idx, self)
            self.prompt_layout.addWidget(card)
        self.prompt_layout.addStretch()

    def _refresh_prompts_recursive(self):
        """父分类视图：按子分类分组显示所有后代 prompts。"""
        self._clear_prompt_layout()
        cat = self.current_category
        kw = self.search_edit.text().strip().lower()

        def filtered(pts):
            if not kw:
                return list(enumerate(pts))
            return [(i, p) for i, p in enumerate(pts)
                    if kw in p.get("title", "").lower() or kw in p.get("content", "").lower()]

        # 1. 当前分类自己的 prompts
        own = filtered(cat.get("prompts", []))
        if own:
            self._add_section_header(f"── {cat['name']} ──")
            for idx, p in own:
                self.prompt_layout.addWidget(PromptCard(p, idx, self))

        # 2. 每个子分类一个标题段
        for child in cat.get("children", []):
            child_prompts = filtered(child.get("prompts", []))
            if not child_prompts:
                continue
            self._add_section_header(f"── {child['name']} ──")
            for idx, p in child_prompts:
                self.prompt_layout.addWidget(PromptCard(p, idx, self, prompt_owner=child))

        self.prompt_layout.addStretch()

    def _add_section_header(self, text):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #888; padding: 6px 0; font-size: 12px;")
        self.prompt_layout.addWidget(lbl)

    def on_recursive_toggled(self, checked):
        self.recursive_view = checked
        if self.current_view == "normal":
            self.refresh_prompts()
    
    def add_category(self):
        """添加顶级分类。"""
        text, ok = QInputDialog.getText(self, "新建顶级分类", "分类名称:")
        if ok and text.strip():
            name = text.strip()
            if any(c["name"] == name for c in self.data["categories"]):
                QMessageBox.warning(self, "警告", "顶层已存在同名分类！")
                return
            self.data["categories"].append({
                "name": name, "prompts": [], "expanded": False, "children": []
            })
            self.save_data()
            self.refresh_categories()
            self.status_bar.showMessage(f"已添加分类: {name}")
    
    # ── 分类右键菜单 ──

    def show_category_menu(self, pos):
        """分类树右键菜单。"""
        item = self.category_tree.itemAt(pos)
        if item is None:
            return
        kind = item.data(0, KIND_KEY)
        menu = QMenu(self)
        if kind == "trash":
            act_clear = menu.addAction("清空回收站")
            chosen = menu.exec(self.category_tree.viewport().mapToGlobal(pos))
            if chosen == act_clear:
                self._clear_trash()
            return
        if kind == "separator":
            return

        cat = item.data(0, ROLE_KEY)
        is_top = (kind == "top")
        is_child = (kind == "child")

        if is_top:
            act_rename = menu.addAction("重命名")
            act_new_child = menu.addAction("新建子分类")
            act_move_top = menu.addAction("移到顶部")
            act_del = menu.addAction("删除")
            chosen = menu.exec(self.category_tree.viewport().mapToGlobal(pos))
            if chosen == act_rename:
                self._rename_category(cat, kind, item)
            elif chosen == act_new_child:
                self._add_subcategory(cat)
            elif chosen == act_move_top:
                self._move_to_top(cat, kind, item)
            elif chosen == act_del:
                self._delete_category_to_trash(cat, kind, item)
        elif is_child:
            act_rename = menu.addAction("重命名")
            act_promote = menu.addAction("提升为顶级分类")
            act_del = menu.addAction("删除")
            chosen = menu.exec(self.category_tree.viewport().mapToGlobal(pos))
            if chosen == act_rename:
                self._rename_category(cat, kind, item)
            elif chosen == act_promote:
                self._promote_to_top(cat, kind, item)
            elif chosen == act_del:
                self._delete_category_to_trash(cat, kind, item)

    def _rename_category(self, cat, kind, item):
        from data_ops import is_name_unique_among_siblings
        new_name, ok = QInputDialog.getText(self, "重命名分类", "新名称:", text=cat["name"])
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        siblings = self._siblings_of(cat, kind, item)
        if not is_name_unique_among_siblings(siblings, new_name, exclude=cat):
            QMessageBox.warning(self, "警告", "同级已存在同名分类！")
            return
        cat["name"] = new_name
        self.save_data()
        self.refresh_categories()
        self.status_bar.showMessage(f"已重命名为: {new_name}")

    def _siblings_of(self, cat, kind, item):
        if kind == "top":
            return self.data["categories"]
        # 直接扫描数据：不依赖 item.parent()，防止拖放后树结构与实际数据不一致
        for top in self.data["categories"]:
            if any(c is cat or c == cat for c in top.get("children", [])):
                return top["children"]
        # 兜底：如果扫描不到（理论上不应发生），按顶级处理
        return self.data["categories"]

    def _add_subcategory(self, parent_cat):
        from data_ops import is_name_unique_among_siblings
        text, ok = QInputDialog.getText(self, "新建子分类", "子分类名称:")
        if not ok or not text.strip():
            return
        name = text.strip()
        siblings = parent_cat.get("children", [])
        if not is_name_unique_among_siblings(siblings, name):
            QMessageBox.warning(self, "警告", "该分类下已存在同名子分类！")
            return
        new_child = {"name": name, "prompts": [], "expanded": False, "children": []}
        parent_cat.setdefault("children", []).append(new_child)
        self.save_data()
        self.refresh_categories()
        self.status_bar.showMessage(f"已添加子分类: {name}")

    def _move_to_top(self, cat, kind, item):
        from data_ops import is_name_unique_among_siblings
        if not is_name_unique_among_siblings(self.data["categories"], cat["name"]):
            QMessageBox.warning(self, "警告", "顶级分类已存在同名！")
            return
        # 防御：从所有子分类列表和顶级列表中彻底移除 cat，再插入到顶级
        for top in self.data["categories"]:
            top["children"] = [c for c in top.get("children", []) if not (c is cat or c == cat)]
        self.data["categories"] = [c for c in self.data["categories"] if not (c is cat or c == cat)]
        self.data["categories"].insert(0, cat)
        self.save_data()
        self.refresh_categories()
        self.status_bar.showMessage("已移到顶部")

    def _promote_to_top(self, cat, kind, item):
        from data_ops import is_name_unique_among_siblings
        if not is_name_unique_among_siblings(self.data["categories"], cat["name"]):
            QMessageBox.warning(self, "警告", "顶级分类已存在同名！")
            return
        # 防御：从所有子分类列表和顶级列表中彻底移除 cat，再添加到顶级
        for top in self.data["categories"]:
            top["children"] = [c for c in top.get("children", []) if not (c is cat or c == cat)]
        self.data["categories"] = [c for c in self.data["categories"] if not (c is cat or c == cat)]
        self.data["categories"].append(cat)
        self.save_data()
        self.refresh_categories()
        self.status_bar.showMessage("已提升为顶级分类")

    def _count_prompts_recursive(self, cat):
        total = len(cat.get("prompts", []))
        for child in cat.get("children", []):
            total += self._count_prompts_recursive(child)
        return total

    def _origin_path_of(self, cat, kind, item):
        if kind == "top":
            return [cat["name"]]
        parent_item = item.parent()
        parent_cat = parent_item.data(0, ROLE_KEY) if parent_item else None
        if parent_cat:
            return [parent_cat["name"], cat["name"]]
        return [cat["name"]]

    def _path_of_current_category(self):
        cat = self.current_category
        if cat is None:
            return []
        for top in self.data["categories"]:
            if top is cat:
                return [top["name"]]
            for child in top.get("children", []):
                if child is cat:
                    return [top["name"], child["name"]]
        return []

    def _delete_category_to_trash(self, cat, kind, item):
        from data_ops import next_trash_id
        prompt_count = self._count_prompts_recursive(cat)
        child_count = len(cat.get("children", []))
        msg = f"确定要删除分类「{cat['name']}」吗？\n"
        if child_count > 0:
            msg += f"包含 {child_count} 个子分类、共 {prompt_count} 条 Prompt。\n"
        else:
            msg += f"包含 {prompt_count} 条 Prompt。\n"
        msg += "删除后将放入回收站。"
        reply = QMessageBox.question(self, "确认删除", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        origin_path = self._origin_path_of(cat, kind, item)
        # 防御：从所有子分类列表和顶级列表中彻底移除 cat
        for top in self.data["categories"]:
            top["children"] = [c for c in top.get("children", []) if not (c is cat or c == cat)]
        self.data["categories"] = [c for c in self.data["categories"] if not (c is cat or c == cat)]
        entry = {
            "id": next_trash_id(self.data["trash"]),
            "type": "category",
            "payload": cat,
            "origin_path": origin_path,
            "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.data["trash"].append(entry)
        self.save_data()
        self.refresh_categories()
        self.refresh_prompts()
        self.status_bar.showMessage("分类已移入回收站")

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
            
            self.current_category["prompts"].append({
                "title": data["title"],
                "content": data["content"],
                "created": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            self.save_data()
            self.refresh_prompts()
            self.status_bar.showMessage(f"已添加 Prompt: {data['title']}")
    
    def edit_prompt(self, index, prompt_owner=None):
        """编辑 Prompt"""
        owner = prompt_owner if prompt_owner is not None else self.current_category
        if owner is None:
            return
        prompts = owner["prompts"]
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
    
    def delete_prompt(self, index, prompt_owner=None):
        """删除 Prompt 进回收站（prompt_owner 用于递归视图下指定所属分类）。"""
        from data_ops import next_trash_id
        owner = prompt_owner if prompt_owner is not None else self.current_category
        if owner is None:
            return
        prompts = owner["prompts"]
        prompt = prompts[index]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除 Prompt「{prompt.get('title')}」？\n将放入回收站。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        del prompts[index]
        entry = {
            "id": next_trash_id(self.data["trash"]),
            "type": "prompt",
            "payload": prompt,
            "origin_path": self._path_of_current_category() if prompt_owner is None else self._path_of_owner(prompt_owner),
            "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.data["trash"].append(entry)
        self.save_data()
        self.refresh_categories()
        self.refresh_prompts()
        self.status_bar.showMessage("Prompt 已移入回收站")

    def _path_of_owner(self, owner):
        """返回任意分类节点的完整路径。"""
        for top in self.data["categories"]:
            if top is owner:
                return [top["name"]]
            for child in top.get("children", []):
                if child is owner:
                    return [top["name"], child["name"]]
        return []

    # ── 回收站操作 ──

    def refresh_trash_view(self):
        """渲染回收站列表为卡片。"""
        while self.prompt_layout.count():
            child = self.prompt_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        trash = self.data.get("trash", [])
        if not trash:
            empty = QLabel("回收站为空")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color: #888; padding: 40px;")
            self.prompt_layout.addWidget(empty)
            self.prompt_layout.addStretch()
            return

        # 头部操作区：清空回收站按钮
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 8)
        title = QLabel(f"回收站（{len(trash)} 项）")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        clear_btn = QPushButton("清空回收站")
        clear_btn.clicked.connect(self._clear_trash)
        header_layout.addWidget(clear_btn)
        self.prompt_layout.addWidget(header)

        for entry in sorted(trash, key=lambda e: e.get("deleted_at", ""), reverse=True):
            card = TrashItemCard(entry, self)
            self.prompt_layout.addWidget(card)
        self.prompt_layout.addStretch()

    def _restore_trash_item(self, trash_id):
        """根据 id 还原回收站条目。委托 data_ops.restore_trash_entry 处理核心逻辑。"""
        from data_ops import restore_trash_entry
        entry = next((e for e in self.data["trash"] if e["id"] == trash_id), None)
        if entry is None:
            QMessageBox.warning(self, "失败", "找不到要恢复的条目。")
            return
        try:
            restored, rebuilt_count, renamed = restore_trash_entry(
                self.data["categories"], entry
            )
        except ValueError as e:
            QMessageBox.warning(self, "恢复失败", str(e))
            return
        if rebuilt_count > 0:
            QMessageBox.information(
                self, "已恢复",
                f"原父分类已被永久删除，已自动重建 {rebuilt_count} 个空分类。"
            )
        if renamed:
            self.status_bar.showMessage(f"同名冲突，已重命名为 {restored.get('name') or restored.get('title')}")
        self.data["trash"] = [e for e in self.data["trash"] if e["id"] != trash_id]
        self.save_data()
        self.refresh_categories()
        self.refresh_trash_view()
        self.status_bar.showMessage("已恢复")

    def _purge_trash_item(self, trash_id):
        """从回收站永久删除某条目。"""
        entry = next((e for e in self.data["trash"] if e["id"] == trash_id), None)
        if entry is None:
            return
        if entry["type"] == "category":
            cat = entry["payload"]
            n = self._count_prompts_recursive(cat)
            msg = f"将永久删除分类「{cat.get('name')}」及其下 {n} 条 Prompt，无法恢复。"
        else:
            p = entry["payload"]
            msg = f"将永久删除 Prompt「{p.get('title')}」，无法恢复。"
        reply = QMessageBox.question(self, "确认永久删除", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        self.data["trash"] = [e for e in self.data["trash"] if e["id"] != trash_id]
        self.save_data()
        self.refresh_categories()
        self.refresh_trash_view()
        self.status_bar.showMessage("已永久删除")

    def _clear_trash(self):
        """清空回收站。"""
        if not self.data.get("trash"):
            return
        n = len(self.data["trash"])
        reply = QMessageBox.question(
            self, "确认清空回收站",
            f"将永久删除回收站中全部 {n} 项，无法恢复。",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self.data["trash"] = []
        self.save_data()
        self.refresh_categories()
        self.refresh_trash_view()
        self.status_bar.showMessage("回收站已清空")

    def toggle_on_top(self, state):
        """切换窗口置顶 - 优先使用 Qt flags，并提供 WinAPI 回退，已移除调试日志"""
        # 兼容 state 既可能是 int（stateChanged）也可能是 bool（toggled）
        try:
            checked = (state == Qt.Checked) or bool(state)
        except Exception:
            checked = bool(state)

        # 使用 setWindowFlags 更新 flags，保留系统按钮
        try:
            flags = self.windowFlags()
            if checked:
                flags |= Qt.WindowStaysOnTopHint
                flags |= (Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
            else:
                flags &= ~Qt.WindowStaysOnTopHint
                flags |= (Qt.WindowCloseButtonHint | Qt.WindowSystemMenuHint)

            self.setWindowFlags(flags)
            self.show()
            self.raise_()
            self.activateWindow()
        except Exception:
            # 忽略 UI 修改错误，继续尝试 WinAPI 回退
            pass

        # WinAPI 回退（兼容 32/64 位）
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            SetWindowPos = user32.SetWindowPos
            SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND,
                                     ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_uint]
            SetWindowPos.restype = wintypes.BOOL

            SetForegroundWindow = user32.SetForegroundWindow
            SetForegroundWindow.argtypes = [wintypes.HWND]
            SetForegroundWindow.restype = wintypes.BOOL

            BringWindowToTop = user32.BringWindowToTop
            BringWindowToTop.argtypes = [wintypes.HWND]
            BringWindowToTop.restype = wintypes.BOOL

            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_SHOWWINDOW = 0x0040
            SWP_FRAMECHANGED = 0x0020
            HWND_TOPMOST = wintypes.HWND(-1)
            HWND_NOTOPMOST = wintypes.HWND(-2)

            hwnd = wintypes.HWND(int(self.winId()))

            if checked:
                SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            else:
                SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)

            # 尝试刷新框架并置前
            try:
                SetWindowPos(hwnd, HWND_TOPMOST if checked else HWND_NOTOPMOST, 0, 0, 0, 0,
                             SWP_NOMOVE | SWP_NOSIZE | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
                BringWindowToTop(hwnd)
                SetForegroundWindow(hwnd)
            except Exception:
                pass

            self.status_bar.showMessage("已置顶" if checked else "取消置顶")
        except Exception:
            self.status_bar.showMessage("已置顶" if checked else "取消置顶")

        # 确保激活
        self.raise_()
        self.activateWindow()
    
    def show_toast(self, message, duration=1500):
        """显示 Toast 提示"""
        self.toast_label.setText(message)
        self.toast_label.setVisible(True)

        # 自动隐藏
        QTimer.singleShot(duration, lambda: self.toast_label.setVisible(False))

    def _persist_expanded_states(self):
        """遍历树，把所有分类节点的展开状态写回 self.data。"""
        root = self.category_tree.invisibleRootItem()
        for i in range(root.childCount()):
            top_item = root.child(i)
            kind = top_item.data(0, KIND_KEY)
            if kind not in ("top", "child"):
                continue
            cat = top_item.data(0, ROLE_KEY)
            if cat is None:
                continue
            cat["expanded"] = top_item.isExpanded()
            for j in range(top_item.childCount()):
                child_item = top_item.child(j)
                child_cat = child_item.data(0, ROLE_KEY)
                if child_cat is not None:
                    child_cat["expanded"] = child_item.isExpanded()

    def closeEvent(self, event):
        try:
            self._persist_expanded_states()
            self.save_data()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"关闭时保存数据失败：{e}")
        super().closeEvent(event)


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
