# PinPrompt 分类树优化设计

## 背景

当前分类列表使用 `QListWidget` 平铺展示，按字母排序，存在三个痛点：
1. 无法手动调整分类顺序
2. 无法折叠，分类一多就拥挤
3. 缺乏层级能力，只能扁平管理

## 目标

将分类列表升级为**支持手动排序和最多 2 层嵌套折叠的树形结构**，并在右侧提供**可选的递归显示子分类 prompts** 的能力。

## 数据结构

### 旧格式（v1）

```json
{
  "categories": {
    "编程助手": {
      "prompts": [{ "title": "...", "content": "...", "created": "..." }]
    },
    "写作": { "prompts": [...] }
  }
}
```

### 新格式（v2）

```json
{
  "version": 2,
  "categories": [
    {
      "name": "工作",
      "prompts": [],
      "expanded": true,
      "children": [
        { "name": "编程助手", "prompts": [...], "expanded": false, "children": [] },
        { "name": "代码审查", "prompts": [...], "expanded": false, "children": [] }
      ]
    },
    {
      "name": "写作",
      "prompts": [...],
      "expanded": false,
      "children": []
    }
  ]
}
```

字段说明：
- `version: 2` — 格式版本标记，旧文件缺少此字段时自动迁移
- `categories: []` — 顶层有序数组，**顺序即显示顺序**
- `name` — 分类名，**同级唯一**即可，不同父级下允许重名
- `prompts` — 结构不变
- `expanded` — 折叠状态，随 `save_data()` 持久化（不单独实时写盘）
- `children` — 子分类数组，叶子分类始终为空数组

### 迁移逻辑

```python
def migrate_v1_to_v2(data):
    if data.get("version", 1) >= 2:
        return data
    new_cats = []
    for name in sorted(data.get("categories", {}).keys()):
        old = data["categories"][name]
        new_cats.append({
            "name": name,
            "prompts": old.get("prompts", []),
            "expanded": False,
            "children": []
        })
    return {"version": 2, "categories": new_cats}
```

启动加载时自动调用，迁移后立刻 `save_data()` 落盘，之后不再触发。

## UI 行为

### 1. 控件升级

左侧 [main_pyside.py:328](main_pyside.py#L328) 的 `QListWidget` 替换为 `QTreeWidget`：
- `setHeaderHidden(True)`
- `setDragDropMode(QTreeWidget.InternalMove)`
- `setSelectionMode(QTreeWidget.SingleSelection)`
- `setIndentation(18)` — 紧凑缩进

### 2. 拖拽规则（限制 2 层）

重载 `dropEvent`，对落点做深度校验：

| 拖拽源 | 落点在两节点之间（同级排序） | 落点在目标节点身上（嵌套） |
|---|---|---|
| 顶层分类 | ✅ 允许 | 目标是子级 → ❌ 拒绝；目标是顶层 → ✅ 变成其子分类 |
| 子分类 | ✅ 允许 | ❌ 任何目标都拒绝（已达 2 层上限） |

拒绝时 `status_bar.showMessage("子分类无法继续嵌套")`。

### 3. 折叠 / 展开

- 原生 `▶/▼` 箭头点击切换
- 父分类选中时，右侧默认**只显示该父分类自己的 prompts**
- 子分类选中时显示其自己的 prompts
- `expanded` 状态存在 `self.data` 中，程序退出或增删改分类时统一 `save_data()`

### 4. 右键菜单

选中分类右键弹出：
```
新建子分类
重命名
────────
移到顶部
移到底部
────────
删除分类
```

- **新建子分类**：仅顶层分类可用，子分类项不显示或置灰
- **重命名**：检查同级唯一，重名时 `QMessageBox.warning`
- **删除分类**：连带删除该分类下所有 prompts 及所有子分类和子分类的 prompts，弹确认框

### 5. 计数显示

树节点文本带计数，缓解拥挤感：

| 分类类型 | 显示格式 | 例子 |
|---|---|---|
| 有子分类的父分类 | `分类名 (子分类数, prompt总数)` | `工作 (2, 15)` |
| 无子分类的分类 | `分类名 (prompt数)` | `编程助手 (8)` |
| 空的分类 | `分类名` | `待整理` |

`prompt总数` = 自身 prompts 数 + 递归子分类 prompts 数。

### 6. 递归显示子分类 prompts（可选）

右侧 Prompt 面板标题行增加一个复选框：`☐ 包含子分类`

- 默认 unchecked
- 仅当选中**有子分类的父分类**时 enabled
- 选中后，右侧列表递归汇总该父分类下所有 prompts 显示
- 状态不持久化，每次启动默认 off

## 影响面

需修改的文件：**仅 [main_pyside.py](main_pyside.py)**

需要改动的函数：
- `load_data` — 增加 v1→v2 迁移
- `save_data` — 不变，格式已经体现在 self.data 中
- `setup_ui` — 左侧 `QListWidget` → `QTreeWidget`
- `create_category_panel` — 改为 QTreeWidget 初始化
- `refresh_categories` — 改为递归构建 QTreeWidgetItem
- `on_category_select` — 从 tree item 的 data 中解析路径
- `add_category` — 改为在顶层追加新分类节点
- `delete_category` — 改为按路径递归删除
- `refresh_prompts` — 根据"包含子分类"复选框决定是否递归汇总 prompts
- **新增** `add_child_category`、`rename_category`、`move_to_top`、`move_to_bottom` 等
- **新增** `dropEvent` 重载（内部类或外部函数）

不需要改动的：
- `PromptCard`、`AddEditDialog` — 完全复用
- `toggle_on_top` — 不受影响
- `show_toast` — 不受影响
- `main.py`、`gen_ico.py`、`check_icon.py` — 不受影响
