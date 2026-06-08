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

        # 禁止拖到自身
        if source_item is target_item:
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

        # ---- 手动实现 item 移动，避免 Qt 默认 dropEvent 可能丢失自定义 data ----
        old_parent = source_item.parent()
        if old_parent is None:
            old_parent = self.invisibleRootItem()
        old_index = old_parent.indexOfChild(source_item)

        if position == "on":
            # 变成 target_item 的子分类
            if old_index >= 0:
                old_parent.takeChild(old_index)
            target_item.addChild(source_item)
            source_item.setData(0, KIND_KEY, "child")
        else:
            # 同级排序
            target_parent = target_item.parent()
            if target_parent is None:
                target_parent = self.invisibleRootItem()
            target_index = target_parent.indexOfChild(target_item)

            if old_index >= 0:
                old_parent.takeChild(old_index)

            # 根据指示器微调插入位置
            if drop_indicator == QAbstractItemView.BelowItem:
                target_index += 1

            # 同源同父时，移除后目标索引需回退一位
            if old_parent is target_parent and old_index < target_index:
                target_index -= 1

            target_parent.insertChild(target_index, source_item)

            if target_parent is self.invisibleRootItem():
                source_item.setData(0, KIND_KEY, "top")
            else:
                source_item.setData(0, KIND_KEY, "child")

        event.setDropAction(Qt.MoveAction)
        event.accept()
        self.drop_completed.emit()
