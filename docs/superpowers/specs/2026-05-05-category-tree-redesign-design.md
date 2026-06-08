# 分类树重构与回收站设计

**日期**：2026-05-05
**作者**：基于头脑风暴会话整理
**目标**：解决 PinPrompt 分类管理的三个痛点——不能手动排序、不能折叠、类别多时拥挤；同时引入回收站避免误删

---

## 1. 背景与目标

当前 [main_pyside.py](../../../main_pyside.py) 使用 `QListWidget` 平铺展示所有分类，按字母序排序，无法体现使用频率或自定义结构。当分类数量超过十几个后，左侧面板显得拥挤且难以快速定位。

本次改造解决：

1. **手动排序** — 用户可以通过拖拽自由调整分类顺序
2. **折叠分组** — 支持父子两级嵌套，父分类可折叠隐藏子分类
3. **回收站** — 删除操作不再不可逆，先进入回收站，回收站内可恢复或永久删除

---

## 2. 数据结构（v2）

### 2.1 新格式

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
            { "title": "代码审查", "content": "...", "created": "2026-04-16 23:42" }
          ],
          "expanded": false,
          "children": []
        }
      ]
    },
    {
      "name": "写作",
      "prompts": [...],
      "expanded": false,
      "children": []
    }
  ],
  "trash": [
    {
      "id": 17,
      "type": "category",
      "payload": { "name": "...", "prompts": [...], "expanded": false, "children": [...] },
      "origin_path": ["工作"],
      "deleted_at": "2026-05-05 14:30"
    },
    {
      "id": 18,
      "type": "prompt",
      "payload": { "title": "...", "content": "...", "created": "..." },
      "origin_path": ["工作", "编程助手"],
      "deleted_at": "2026-05-05 14:35"
    }
  ]
}
```

### 2.2 字段约束

| 字段 | 说明 |
|---|---|
| `version` | 固定为 `2`，缺失视为 v1 旧格式触发迁移 |
| `categories` | 顶层数组，**顺序即显示顺序** |
| `name` | 分类名，**同级唯一**；不同父级下可重名 |
| `prompts` | Prompt 数组，结构与 v1 完全相同（兼容字段 `title`/`content`/`created`/`modified`）|
| `expanded` | 折叠状态；仅在 `closeEvent` 时持久化 |
| `children` | 子分类数组；**最多 2 层**，叶子分类的 `children` 永远是空数组 |
| `trash` | 回收站数组，永久保留直到手动清空 |
| `trash[].id` | 自增整数，用于 UI 列表的唯一标识 |
| `trash[].type` | `"category"` 或 `"prompt"` |
| `trash[].payload` | 被删项的完整快照 |
| `trash[].origin_path` | 原父级路径数组（顶层分类的 path 是 `[]`，子分类是 `[父名]`，prompt 是 `[父名]` 或 `[父名, 子名]`）|
| `trash[].deleted_at` | 删除时间戳，格式 `YYYY-MM-DD HH:MM` |

### 2.3 数据迁移

启动加载时调用 `migrate_v1_to_v2(data)`：

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
    return {"version": 2, "categories": new_cats, "trash": []}
```

迁移后立即 `save_data()` 落盘，之后再不会触发。

### 2.4 持久化时机

| 操作 | 写盘时机 |
|---|---|
| 新建 / 重命名 / 删除分类 | 立即 |
| 新建 / 编辑 / 删除 prompt | 立即 |
| 拖拽分类调整顺序或层级 | 立即 |
| 从回收站恢复 / 永久删除 / 清空 | 立即 |
| 折叠 / 展开父分类 | **不立即**，仅更新内存 |
| 程序关闭 | `closeEvent` 中统一 `save_data()`，刷新 `expanded` 状态 |

---

## 3. 控件升级

将左侧面板的 `QListWidget` 替换为 `QTreeWidget`：

```python
self.category_tree = QTreeWidget()
self.category_tree.setHeaderHidden(True)
self.category_tree.setDragDropMode(QAbstractItemView.InternalMove)
self.category_tree.setSelectionMode(QAbstractItemView.SingleSelection)
self.category_tree.setContextMenuPolicy(Qt.CustomContextMenu)
self.category_tree.customContextMenuRequested.connect(self.show_category_menu)
self.category_tree.itemExpanded.connect(self.on_item_expanded)
self.category_tree.itemCollapsed.connect(self.on_item_collapsed)
self.category_tree.currentItemChanged.connect(self.on_category_select)
```

`QTreeWidgetItem` 通过 `setData(0, Qt.UserRole, ref)` 关联到 `self.data["categories"]` 中对应节点的引用，避免每次操作都靠 name 路径查找。

---

## 4. 节点显示

| 节点类型 | 显示文本 | 说明 |
|---|---|---|
| 顶层父分类（有 children） | `📂 工作 [2]` | `[2]` 是子分类数 |
| 顶层叶子分类（无 children） | `📁 写作 (5)` | `(5)` 是该分类下 prompt 数 |
| 子分类 | `📁 编程助手 (12)` | `(12)` 是 prompt 数 |
| 回收站节点 | `🗑️ 回收站 (4)` | `(4)` 是回收站条目数；空则不显示括号 |
| 空分类 | `📁 写作 (0)` | 仍显示 `(0)`，区别于折叠状态 |

折叠/展开箭头由 `QTreeWidget` 自动绘制，不需要手动维护。

---

## 5. 拖拽规则

`QTreeWidget.dropEvent` 重写，校验后再调用 `super().dropEvent(event)`：

| 场景 | 处理 |
|---|---|
| 顶层叶子 → 顶层之间 | ✅ 重排顶层顺序 |
| 顶层叶子 → 拖到顶层身上 | ✅ 变成它的子分类 |
| 子分类 → 同父其它子分类之间 | ✅ 重排子分类顺序 |
| 子分类 → 顶层之间 | ✅ 提升为顶层 |
| 子分类 → 另一个父分类身上 | ✅ 转移父级 |
| 父分类（已有 children）→ 拖进另一父分类身上 | ❌ `event.ignore()`，状态栏提示"最多支持 2 层嵌套" |
| 任何节点 → 拖进回收站节点 | ❌ `event.ignore()`，状态栏提示"如需删除请用右键菜单" |
| 回收站节点 / 回收站子项 | ❌ 不可拖动 |

drop 完成后立即同步 `self.data["categories"]` 的顺序与嵌套结构，并 `save_data()`。

---

## 6. 右键菜单

| 节点类型 | 菜单项 |
|---|---|
| 顶层父分类（有 children） | 重命名 / 新建子分类 / **删除（级联进回收站）** / 移到顶部 |
| 顶层叶子分类 | 重命名 / 新建子分类 / 删除（进回收站）/ 移到顶部 |
| 子分类 | 重命名 / 删除（进回收站）/ 提升为顶级 |
| 回收站节点 | 清空回收站（确认弹窗，永久删除全部）|
| 回收站子项 | 恢复 / 永久删除 |

> Prompt 卡片本身没有右键菜单，本期不引入。

**删除父分类的确认弹窗**示例：

> 确定要删除分类「工作」吗？
> 该分类包含 2 个子分类、共 15 条 Prompt，将一并放入回收站。
> [取消] [删除]

**新建子分类**用 `QInputDialog.getText` 弹窗输入名字，确认后追加到父分类的 `children` 末尾，并自动展开父分类。

**重命名**用 `QInputDialog.getText` 弹窗，预填当前名字，校验同级唯一性。

---

## 7. 选中行为

### 7.1 普通模式（默认）

| 选中节点 | 右侧显示 |
|---|---|
| 顶层叶子分类 | 该分类的 prompts 列表（与现状一致）|
| 子分类 | 该分类的 prompts 列表 |
| 顶层父分类 | **仅显示该父分类自己的** prompts，不递归到子分类 |
| 父分类自己无 prompts | 显示空提示"暂无 Prompt（子分类中可能有，开启递归视图查看）"|
| 回收站节点 | 切换到回收站列表视图（见 §9）|

### 7.2 递归视图模式（toggle 开启时）

工具栏的 🌲 递归视图按钮按下后，选中**父分类**会按子分类分组显示：

```
── 工作（本级）──
  [Prompt 卡片]
  [Prompt 卡片]

── 编程助手 ──
  [Prompt 卡片]
  [Prompt 卡片]
  ...

── 代码审查 ──
  [Prompt 卡片]
```

- 父分类自己的 prompts 放在最上方一组，标题为"父分类名（本级）"
- 每个子分类一个分组，标题为子分类名
- 空子分类不显示分组（避免视觉噪声）
- 选中**叶子分类**时递归视图无效，显示行为与普通模式相同

---

## 8. 顶部工具栏

```
[➕ 新建顶级分类] [📝 新建Prompt] [🌲 递归视图] [📌 窗口置顶] [🔍 搜索...]
```

| 按钮 | 行为 |
|---|---|
| ➕ 新建顶级分类 | 弹 `QInputDialog`，新建后追加到 `categories` 末尾 |
| 📝 新建Prompt | 选中分类后启用；弹 `AddEditDialog`（不变） |
| 🌲 递归视图 | `QPushButton.setCheckable(True)` 的 toggle 按钮；切换时刷新右侧显示 |
| 📌 窗口置顶 | 不变 |
| 🔍 搜索 | 不变（在当前选中分类的 prompts 内搜索；递归视图下跨子分类搜索）|

**移除**：现有的"🗑️ 删除分类"按钮（统一走右键菜单）。

---

## 9. 回收站

### 9.1 入口

回收站作为 `QTreeWidget` 的最底部固定节点呈现，与其他分类用一条分隔线（在节点上方插入一个 disabled 的 separator item）区分：

```
📂 工作 [2]
   📁 编程助手 (12)
   📁 代码审查 (3)
📁 写作 (5)
─────────────
🗑️ 回收站 (4)
```

### 9.2 选中回收站后的右侧视图

切换为"回收站列表视图"，每条目显示为一张卡片：

```
[类型图标] 编程助手
原位置：工作 / 编程助手
删除时间：2026-05-05 14:30
                      [🔄 恢复] [🗑️ 永久删除]
```

| 类型图标 | 含义 |
|---|---|
| 📁 | 被删的分类（连同其子分类与 prompts）|
| 📝 | 被删的单条 prompt |

### 9.3 恢复规则

恢复一条记录时，沿 `origin_path` 寻找原父级，**缺失节点自动重建**：

1. **沿路径逐层走**，对每一层：
   - 该名字的分类已存在 → 进入下一层
   - 该名字的分类不存在 → **自动创建一个空分类**（`prompts=[]`、`children=[]`、`expanded=false`），作为重建路径的一部分
2. 路径走完后，把被恢复的项追加到末尾：
   - `type=category` → 追加到目标位置的 `children`（或顶层 `categories`）末尾
   - `type=prompt` → 追加到目标分类的 `prompts` 末尾
3. **同级同名冲突**（仅作用于被恢复项自身的 name / title，不作用于路径重建出的中间分类）→ 在 name / title 前加 `[YYYY-MM-DD HH:MM] ` 时间前缀（取 `deleted_at` 而非"现在"，便于追溯）

**示例 1：路径完整存在**
- 待恢复 prompt，origin_path = `["工作", "编程助手"]`
- "工作"、"编程助手"都在 → 直接追加到 `工作 / 编程助手` 的 prompts 末尾

**示例 2：路径完全断裂**
- 待恢复 prompt，origin_path = `["工作", "编程助手"]`
- "工作"被永久删除 → 自动创建顶层"工作" → 在其 children 创建"编程助手" → 把 prompt 追加进去

**示例 3：路径部分断裂**
- 待恢复子分类"编程助手"，origin_path = `["工作"]`
- "工作"被永久删除 → 自动创建顶层"工作"（空）→ 把"编程助手"追加为它的 children

**示例 4：路径上某节点同名复用**
- 用户已经手动新建了一个名为"工作"的顶层分类
- 待恢复 prompt，origin_path = `["工作", "编程助手"]`
- 复用已有的顶层"工作"，在其 children 中（如不存在）创建"编程助手" → 把 prompt 追加进去

> 复用同名节点而非另建带时间前缀的副本，是因为用户主动建了同名分类多半是想把相关内容聚到一起；如不想合并，恢复后用户可以手动改名分离。

恢复成功后状态栏显示提示信息（如"已恢复，路径上重建了 1 个分类节点"），从 `trash` 数组移除该项。

### 9.4 永久删除 / 清空

- 单项永久删除：从 `trash` 移除该项，立即 `save_data()`，无需弹窗（已经在回收站里了，再点删除属于二次确认）
- 清空回收站：弹确认框"确定要清空回收站吗？这将永久删除 N 条记录，无法恢复。" → 清空 `trash` 数组

### 9.5 ID 分配

`trash[].id` 是自增整数，由内存中维护的 `self._next_trash_id` 提供：

- 启动加载时：`_next_trash_id = max([t["id"] for t in trash], default=0) + 1`
- 每次新增删除条目时：分配当前 `_next_trash_id`，然后 `+=1`
- 即首次删除时 id 从 1 开始；清空回收站后下次删除仍从 1 开始

---

## 10. 类与函数变化

### 10.1 `PinPromptApp` 主要新增/修改

| 函数 | 变化 |
|---|---|
| `load_data()` | 新增迁移逻辑、初始化 `_next_trash_id` |
| `save_data()` | 不变 |
| `closeEvent()` | **新增**：保存当前所有节点的 `expanded` 状态后写盘 |
| `setup_ui()` | 把 `QListWidget` 换成 `QTreeWidget`，新增递归视图按钮 |
| `refresh_categories()` | 重构为递归构建 `QTreeWidgetItem`；末尾添加分隔符与回收站节点 |
| `on_category_select()` | 区分回收站节点 vs 普通分类；递归模式下走分组视图 |
| `refresh_prompts()` | 拆为 `refresh_prompts_normal()` 和 `refresh_prompts_recursive()` |
| `refresh_trash_view()` | **新增**：渲染回收站列表 |
| `add_category()` | 在 `categories` 末尾追加 |
| `add_subcategory(parent_node)` | **新增**：在指定父分类的 `children` 末尾追加 |
| `rename_category(node)` | **新增**：右键入口；同级唯一性校验 |
| `delete_category(node)` | **修改**：移到 `trash`，记录 `origin_path` 和 `deleted_at` |
| `delete_prompt(node, index)` | **修改**：移到 `trash` |
| `restore_trash_item(trash_id)` | **新增**：按规则恢复 |
| `purge_trash_item(trash_id)` | **新增**：永久删除单项 |
| `clear_trash()` | **新增**：清空回收站 |
| `move_to_top(node)` | **新增**：右键入口 |
| `promote_to_top(node)` | **新增**：把子分类提升为顶级 |
| `toggle_recursive_view()` | **新增**：toggle 按钮回调，刷新右侧 |
| `on_item_expanded/collapsed()` | **新增**：仅更新内存的 `expanded` 字段 |

### 10.2 `QTreeWidget` 子类（拖拽校验）

新增 `CategoryTreeWidget(QTreeWidget)`，重写 `dropEvent` 实现 §5 的规则校验。

### 10.3 `PromptCard` 与 `AddEditDialog`

不变。`PromptCard` 在递归视图下复用，只是分组容器是新的（用 `QLabel` + `QFrame` 实现简单分组标题）。

---

## 11. 错误处理

| 场景 | 处理 |
|---|---|
| 迁移时旧 prompts.json 损坏 / 格式异常 | 沿用现有 `try/except` 兜底，回退到空数据结构 |
| 重命名同级冲突 | 弹 `QMessageBox.warning` + 阻止保存 |
| 同级新建重名 | 同上 |
| 拖拽违规 | `event.ignore()` + 状态栏提示 |
| 恢复时父级链断裂 | 沿 `origin_path` 自动重建缺失的空分类节点（详见 §9.3） |
| `closeEvent` 期间 `save_data()` 失败 | 弹错误对话框（不中止关闭，允许用户手动备份） |

---

## 12. 测试计划

由于项目目前没有自动化测试基础设施（无 pytest、无测试文件），手动验证场景如下：

### 12.1 数据迁移
- [ ] 用旧 `prompts.json`（v1 格式）启动，确认自动转换为 v2 且不丢数据
- [ ] 第二次启动确认不再触发迁移

### 12.2 拖拽
- [ ] 顶层之间互拖：顺序变化
- [ ] 顶层叶子拖到顶层身上：变子级
- [ ] 子分类拖出到顶层之间：提升
- [ ] 子分类在不同父级间转移：父级正确变化
- [ ] 父分类（有 children）拖进另一父分类：被拒绝 + 提示
- [ ] 拖进回收站节点：被拒绝 + 提示

### 12.3 折叠
- [ ] 折叠/展开父分类，关闭程序后重启，状态保留

### 12.4 删除与恢复
- [ ] 删除顶层叶子分类 → 进回收站 → 恢复 → 回到顶层末尾
- [ ] 删除子分类 → 进回收站 → 恢复 → 回到原父级
- [ ] 删除父分类（含 2 个子分类、共 5 条 prompt）→ 弹窗写明数量 → 进回收站 → 恢复 → 完整还原结构
- [ ] 删除子分类 A（origin_path=["工作"]）→ 永久删除"工作" → 恢复 A → 自动重建顶层"工作"（空）→ A 进入"工作"的 children
- [ ] 删除 prompt P（origin_path=["工作", "编程"]）→ 永久删除"工作"（含"编程"）→ 恢复 P → 自动重建"工作"+"编程"两层 → P 在"编程"中
- [ ] 删除 prompt P（origin_path=["工作", "编程"]）→ 永久删除"工作" → 用户手动新建同名"工作"顶层分类 → 恢复 P → 复用已有"工作"，在其下新建"编程"，P 进入
- [ ] 删除某分类 → 同级新建同名分类 → 恢复原分类 → 名字加时间前缀
- [ ] 删除单条 prompt → 进回收站 → 恢复 → 回到原父分类末尾
- [ ] 永久删除单项 → 从回收站移除
- [ ] 清空回收站 → 弹窗确认 → trash 清空

### 12.5 递归视图
- [ ] 选中父分类 → 普通模式只显示自己 prompts
- [ ] 切换递归视图 → 按子分类分组显示
- [ ] 父分类自己无 prompts → 不显示"本级"组
- [ ] 选中叶子分类 → 递归视图无效

### 12.6 计数显示
- [ ] 父分类显示 `[N]` = 子分类数
- [ ] 叶子分类显示 `(N)` = prompt 数
- [ ] 删除/新增 prompt 后计数同步刷新

### 12.7 回归
- [ ] 窗口置顶（[main_pyside.py:527](../../../main_pyside.py#L527)）功能不受影响
- [ ] 复制/编辑/删除 prompt 卡片功能不受影响
- [ ] 搜索框过滤 prompt 不受影响（递归视图下应跨子分类搜索）
- [ ] 打包 exe 后路径处理（`DATA_DIR`）正常

---

## 13. 开发环境约定

所有 python / pyinstaller 命令前必须激活 conda 的 PinPrompt 环境，不要用 base：

```bash
conda activate PinPrompt
python main_pyside.py
```

---

## 14. 不在本期范围（YAGNI）

- 跨设备同步 / 云端备份
- 拖拽 prompt 卡片到其他分类（保留"编辑→另存"思路供未来）
- 回收站搜索 / 筛选 / 时间排序
- 自动清理（按时间或数量）
- 多选删除 / 多选拖拽
- 三级及以上嵌套
- 撤销 / 重做（Ctrl+Z）

---

## 15. 实施风险

| 风险 | 缓解 |
|---|---|
| `QTreeWidget` 拖拽默认行为与我们的约束有冲突 | 完整测试 §5 的 7 种场景；必要时在 `dropEvent` 里手工调整目标位置 |
| 迁移期间用户已经手动改过 prompts.json | 迁移前先 `prompts.json.bak` 备份一份在同目录 |
| 大量分类（50+）时 `refresh_categories()` 全量重建可能卡顿 | 现状下应该够用；若实测有问题再考虑增量更新 |
| `closeEvent` 写盘失败导致 `expanded` 丢失 | 弹错误对话框；用户至少可以手动复制数据 |
