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

        # 名称唯一性预检
        source_cat = source_item.data(0, ROLE_KEY)
        if source_cat and source_cat.get("name"):
            name = source_cat["name"]
            if position == "on" and target_item:
                for j in range(target_item.childCount()):
                    sib = target_item.child(j)
                    if sib is source_item:
                        continue
                    sib_cat = sib.data(0, ROLE_KEY)
                    if sib_cat and sib_cat.get("name") == name:
                        self.drop_rejected.emit("目标分类下已存在同名子分类")
                        event.ignore()
                        return
            elif position == "between":
                target_parent = target_item.parent()
                if target_parent is None:
                    root = self.invisibleRootItem()
                    for i in range(root.childCount()):
                        sib = root.child(i)
                        if sib is source_item:
                            continue
                        if sib.data(0, KIND_KEY) not in ("top", "child"):
                            continue
                        sib_cat = sib.data(0, ROLE_KEY)
                        if sib_cat and sib_cat.get("name") == name:
                            self.drop_rejected.emit("顶级分类已存在同名")
                            event.ignore()
                            return
                else:
                    for j in range(target_parent.childCount()):
                        sib = target_parent.child(j)
                        if sib is source_item:
                            continue
                        sib_cat = sib.data(0, ROLE_KEY)
                        if sib_cat and sib_cat.get("name") == name:
                            self.drop_rejected.emit("同级分类已存在同名")
                            event.ignore()
                            return

        event.setDropAction(Qt.MoveAction)
        super().dropEvent(event)
        self.drop_completed.emit()
