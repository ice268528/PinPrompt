"""自定义 QTreeWidget：拖拽校验 + 信号通知。"""

from PySide6.QtWidgets import QTreeWidget, QAbstractItemView
from PySide6.QtCore import Qt, Signal

from data_ops import is_drop_valid


# 在 QTreeWidgetItem 的 UserRole 上挂载的数据键
ROLE_KEY = Qt.UserRole          # 指向 data dict 的引用（叶子分类、子分类、父分类）
KIND_KEY = Qt.UserRole + 1      # str: "top" / "child" / "trash" / "separator"


class CategoryTreeWidget(QTreeWidget):
    """支持拖拽 + 校验的分类树。drop 完成后发信号给主窗口同步数据。"""

    drop_rejected = Signal(str)   # 参数: 状态栏提示文案
    drop_completed = Signal()     # 参数: 无；主窗口需重新从树构造 self.data

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def dropEvent(self, event):
        source_item = self.currentItem()
        target_item = self.itemAt(event.pos())
        if source_item is None or target_item is None:
            event.ignore()
            return

        drop_indicator = self.dropIndicatorPosition()
        if drop_indicator == QAbstractItemView.OnItem:
            position = "on"
        else:
            position = "between"

        source_view = {
            "role": source_item.data(0, KIND_KEY) or "top",
            "has_children": source_item.childCount() > 0,
        }
        target_view = {
            "role": target_item.data(0, KIND_KEY) or "top",
            "has_children": target_item.childCount() > 0,
        }

        ok, reason = is_drop_valid(source_view, target_view, position)
        if not ok:
            self.drop_rejected.emit(reason)
            event.ignore()
            return

        super().dropEvent(event)
        self.drop_completed.emit()
