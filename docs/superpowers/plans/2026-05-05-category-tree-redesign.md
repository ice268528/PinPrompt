# 分类树重构与回收站 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把 PinPrompt 的左侧分类列表从平铺 `QListWidget` 升级为 2 层嵌套 `QTreeWidget`，支持拖拽排序、折叠、回收站和递归视图，同时把可纯函数化的逻辑抽到独立模块以便单元测试。

**架构：**
- `main_pyside.py` 保留 UI 主入口、`PinPromptApp` / `PromptCard` / `AddEditDialog`
- 新增 `data_ops.py` 承载纯数据操作（迁移、路径查找、回收站逻辑），无 Qt 依赖、可单元测试
- 新增 `category_tree.py` 承载 `CategoryTreeWidget(QTreeWidget)` 拖拽校验子类
- 新增 `tests/` 目录用 pytest 覆盖纯逻辑

**技术栈：** Python 3.13、PySide6 6.x、pyperclip、pytest（新增），conda 环境 PinPrompt

**设计文档参考：** [docs/superpowers/specs/2026-05-05-category-tree-redesign-design.md](../specs/2026-05-05-category-tree-redesign-design.md)

**所有 python / pip / pytest 命令前必须 `conda activate PinPrompt`，禁止用 base 环境。**

---

## 文件结构

| 文件 | 职责 | 状态 |
|---|---|---|
| `main_pyside.py` | 主入口、`PinPromptApp`、`PromptCard`、`AddEditDialog`、整体 UI 装配 | 修改 |
| `data_ops.py` | 数据迁移、路径查找、同级唯一性、回收站恢复/删除逻辑（纯函数）| **新建** |
| `category_tree.py` | `CategoryTreeWidget(QTreeWidget)` 拖拽校验子类 | **新建** |
| `tests/__init__.py` | pytest 包标记（空文件）| **新建** |
| `tests/conftest.py` | pytest fixtures（如样例数据）| **新建** |
| `tests/test_data_ops.py` | `data_ops` 模块单元测试 | **新建** |
| `prompts.json` | 数据文件（运行时生成） | 不动 |

---

## Phase 1：测试基础设施

### 任务 1：在 PinPrompt 环境安装 pytest

**文件：** 无（环境操作）

- [ ] **步骤 1：检查环境是否已激活并安装 pytest**

```bash
conda activate PinPrompt
pip install pytest
```

预期：pytest 安装成功；如已存在则提示 `Requirement already satisfied`。

- [ ] **步骤 2：验证 pytest 可用**

```bash
conda activate PinPrompt
pytest --version
```

预期：输出形如 `pytest 8.x.x`。

### 任务 2：创建 tests/ 目录骨架

**文件：**
- 创建：`tests/__init__.py`
- 创建：`tests/conftest.py`

- [ ] **步骤 1：创建空的 `tests/__init__.py`**

`tests/__init__.py` 内容：

```python
```

（空文件，仅作包标记）

- [ ] **步骤 2：创建 `tests/conftest.py` 提供样例数据 fixture**

`tests/conftest.py` 内容：

```python
import pytest


@pytest.fixture
def v1_data():
    """v1 旧格式样例数据"""
    return {
        "categories": {
            "写作": {
                "prompts": [
                    {"title": "邮件", "content": "...", "created": "2026-04-16 10:00"}
                ]
            },
            "编程": {
                "prompts": [
                    {"title": "代码审查", "content": "...", "created": "2026-04-17 11:00"}
                ]
            }
        }
    }


@pytest.fixture
def v2_data():
    """v2 新格式样例数据"""
    return {
        "version": 2,
        "categories": [
            {
                "name": "工作",
                "prompts": [],
                "expanded": True,
                "children": [
                    {
                        "name": "编程助手",
                        "prompts": [
                            {"title": "代码审查", "content": "...", "created": "2026-04-17 11:00"}
                        ],
                        "expanded": False,
                        "children": []
                    }
                ]
            },
            {
                "name": "写作",
                "prompts": [
                    {"title": "邮件", "content": "...", "created": "2026-04-16 10:00"}
                ],
                "expanded": False,
                "children": []
            }
        ],
        "trash": []
    }
```

- [ ] **步骤 3：跑 pytest 确认能识别空测试集**

```bash
conda activate PinPrompt
pytest tests/ -v
```

预期：`no tests ran` 或 `collected 0 items`，无报错。

- [ ] **步骤 4：Commit**

```bash
git add tests/__init__.py tests/conftest.py
git commit -m "test: 搭建 pytest 测试基础设施和样例数据 fixture"
```

---

## Phase 2：数据迁移（v1 → v2）

### 任务 3：编写 `migrate_v1_to_v2` 失败测试

**文件：**
- 创建：`tests/test_data_ops.py`

- [ ] **步骤 1：写测试**

`tests/test_data_ops.py` 内容：

```python
from data_ops import migrate_v1_to_v2


def test_migrate_v1_adds_version_field(v1_data):
    result = migrate_v1_to_v2(v1_data)
    assert result["version"] == 2


def test_migrate_v1_converts_dict_to_ordered_list(v1_data):
    result = migrate_v1_to_v2(v1_data)
    assert isinstance(result["categories"], list)
    # v1 dict keys 按字母序排序作为初始顺序：编程 < 写作（按 unicode 排序）
    names = [c["name"] for c in result["categories"]]
    assert names == sorted(["写作", "编程"])


def test_migrate_v1_preserves_prompts(v1_data):
    result = migrate_v1_to_v2(v1_data)
    name_to_cat = {c["name"]: c for c in result["categories"]}
    assert name_to_cat["写作"]["prompts"][0]["title"] == "邮件"
    assert name_to_cat["编程"]["prompts"][0]["title"] == "代码审查"


def test_migrate_v1_adds_default_fields_to_each_category(v1_data):
    result = migrate_v1_to_v2(v1_data)
    for cat in result["categories"]:
        assert cat["expanded"] is False
        assert cat["children"] == []


def test_migrate_v1_initializes_empty_trash(v1_data):
    result = migrate_v1_to_v2(v1_data)
    assert result["trash"] == []


def test_migrate_v2_is_noop(v2_data):
    result = migrate_v1_to_v2(v2_data)
    assert result is v2_data  # 同一对象，未触发迁移


def test_migrate_handles_empty_v1():
    result = migrate_v1_to_v2({"categories": {}})
    assert result == {"version": 2, "categories": [], "trash": []}


def test_migrate_handles_missing_categories_key():
    result = migrate_v1_to_v2({})
    assert result == {"version": 2, "categories": [], "trash": []}
```

- [ ] **步骤 2：运行测试验证失败**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py -v
```

预期：FAIL，报 `ModuleNotFoundError: No module named 'data_ops'`。

### 任务 4：实现 `migrate_v1_to_v2`

**文件：**
- 创建：`data_ops.py`

- [ ] **步骤 1：写最少实现**

`data_ops.py` 内容（仅含本任务相关函数）：

```python
"""
PinPrompt 纯数据操作模块

无 Qt 依赖，可独立单元测试。包含：
- 数据迁移（v1 → v2）
- 节点路径查找
- 同级唯一性校验
- 回收站逻辑（删除快照、恢复路径重建、ID 分配）
"""


def migrate_v1_to_v2(data):
    """把 v1 的无序 dict 结构迁移为 v2 的有序列表 + 回收站结构。

    v1: {"categories": {"name": {"prompts": [...]}}}
    v2: {"version": 2, "categories": [{"name", "prompts", "expanded", "children"}], "trash": []}

    已是 v2 直接返回原对象（同一引用），便于上层判断是否需要落盘。
    """
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

- [ ] **步骤 2：运行测试验证全部通过**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py -v
```

预期：8 个 PASS。

- [ ] **步骤 3：Commit**

```bash
git add data_ops.py tests/test_data_ops.py
git commit -m "feat(data): 实现 v1 → v2 数据迁移"
```

---

## Phase 3：路径查找与同级唯一性

### 任务 5：编写 `find_node_by_path` 失败测试

**文件：**
- 修改：`tests/test_data_ops.py`（追加测试）

- [ ] **步骤 1：在 `tests/test_data_ops.py` 末尾追加**

```python
from data_ops import find_node_by_path


def test_find_node_top_level(v2_data):
    node = find_node_by_path(v2_data["categories"], ["写作"])
    assert node is not None
    assert node["name"] == "写作"


def test_find_node_nested(v2_data):
    node = find_node_by_path(v2_data["categories"], ["工作", "编程助手"])
    assert node is not None
    assert node["name"] == "编程助手"


def test_find_node_missing_returns_none(v2_data):
    assert find_node_by_path(v2_data["categories"], ["不存在"]) is None
    assert find_node_by_path(v2_data["categories"], ["工作", "不存在"]) is None


def test_find_node_empty_path_returns_none(v2_data):
    # 空路径无定义，约定返回 None
    assert find_node_by_path(v2_data["categories"], []) is None
```

- [ ] **步骤 2：运行测试验证失败**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py::test_find_node_top_level -v
```

预期：FAIL，`ImportError: cannot import name 'find_node_by_path'`。

### 任务 6：实现 `find_node_by_path`

**文件：**
- 修改：`data_ops.py`（追加函数）

- [ ] **步骤 1：在 `data_ops.py` 末尾追加**

```python
def find_node_by_path(categories, path):
    """沿 path 在 categories 列表中逐层查找节点。

    categories: 顶层 list[dict]
    path: list[str]，如 ["工作", "编程助手"]
    返回: 找到的节点 dict，或 None
    """
    if not path:
        return None
    current_list = categories
    node = None
    for name in path:
        node = next((c for c in current_list if c["name"] == name), None)
        if node is None:
            return None
        current_list = node.get("children", [])
    return node
```

- [ ] **步骤 2：运行测试验证全部通过**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py -v
```

预期：之前的 8 个 + 新加的 4 个，全 PASS。

### 任务 7：编写 `is_name_unique_among_siblings` 失败测试

**文件：**
- 修改：`tests/test_data_ops.py`（追加测试）

- [ ] **步骤 1：在文件末尾追加**

```python
from data_ops import is_name_unique_among_siblings


def test_unique_name_at_top_level(v2_data):
    assert is_name_unique_among_siblings(v2_data["categories"], "新分类") is True
    assert is_name_unique_among_siblings(v2_data["categories"], "写作") is False


def test_unique_name_in_children(v2_data):
    work_children = v2_data["categories"][0]["children"]
    assert is_name_unique_among_siblings(work_children, "新子分类") is True
    assert is_name_unique_among_siblings(work_children, "编程助手") is False


def test_unique_name_excludes_self(v2_data):
    # 重命名时排除自身节点，避免"改成自己当前的名字"被判重名
    siblings = v2_data["categories"]
    self_node = siblings[0]  # "工作"
    assert is_name_unique_among_siblings(siblings, "工作", exclude=self_node) is True
    assert is_name_unique_among_siblings(siblings, "写作", exclude=self_node) is False
```

- [ ] **步骤 2：运行验证失败**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py::test_unique_name_at_top_level -v
```

预期：FAIL，`ImportError: cannot import name 'is_name_unique_among_siblings'`。

### 任务 8：实现 `is_name_unique_among_siblings`

**文件：**
- 修改：`data_ops.py`（追加函数）

- [ ] **步骤 1：在 `data_ops.py` 末尾追加**

```python
def is_name_unique_among_siblings(siblings, name, exclude=None):
    """检查 name 在 siblings 列表中是否唯一。

    siblings: list[dict]，同级分类列表
    name: str，待检查的名字
    exclude: dict 或 None，重命名场景下需要排除的当前节点
    返回: bool
    """
    for node in siblings:
        if node is exclude:
            continue
        if node["name"] == name:
            return False
    return True
```

- [ ] **步骤 2：运行所有测试**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py -v
```

预期：全 PASS（共 15 个测试）。

- [ ] **步骤 3：Commit**

```bash
git add data_ops.py tests/test_data_ops.py
git commit -m "feat(data): 添加路径查找和同级唯一性校验工具"
```

---

## Phase 4：回收站逻辑（核心）

### 任务 9：编写 `next_trash_id` 失败测试

**文件：**
- 修改：`tests/test_data_ops.py`（追加测试）

- [ ] **步骤 1：在文件末尾追加**

```python
from data_ops import next_trash_id


def test_next_trash_id_empty():
    assert next_trash_id([]) == 1


def test_next_trash_id_increments_from_max():
    trash = [{"id": 1}, {"id": 5}, {"id": 3}]
    assert next_trash_id(trash) == 6


def test_next_trash_id_after_purge():
    # 即使 trash 非连续（中间被永久删过），仍取 max+1
    trash = [{"id": 17}]
    assert next_trash_id(trash) == 18
```

- [ ] **步骤 2：运行验证失败**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py::test_next_trash_id_empty -v
```

预期：FAIL，`ImportError: cannot import name 'next_trash_id'`。

### 任务 10：实现 `next_trash_id`

**文件：**
- 修改：`data_ops.py`（追加函数）

- [ ] **步骤 1：在文件末尾追加**

```python
def next_trash_id(trash):
    """计算下一个可用的 trash 条目 id。空列表返回 1，否则返回 max(id)+1。"""
    if not trash:
        return 1
    return max(t["id"] for t in trash) + 1
```

- [ ] **步骤 2：运行验证通过**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py -v
```

预期：之前的 15 个 + 新增 3 个，全 PASS。

### 任务 11：编写 `ensure_path` 失败测试

**文件：**
- 修改：`tests/test_data_ops.py`

- [ ] **步骤 1：在文件末尾追加**

```python
from data_ops import ensure_path


def test_ensure_path_full_existing(v2_data):
    # 路径完整存在，不应新建任何节点
    parent, rebuilt = ensure_path(v2_data["categories"], ["工作"])
    assert parent["name"] == "工作"
    assert rebuilt == 0


def test_ensure_path_nested_existing(v2_data):
    parent, rebuilt = ensure_path(v2_data["categories"], ["工作", "编程助手"])
    assert parent["name"] == "编程助手"
    assert rebuilt == 0


def test_ensure_path_creates_top_level():
    cats = []
    parent, rebuilt = ensure_path(cats, ["新顶级"])
    assert parent["name"] == "新顶级"
    assert parent["prompts"] == []
    assert parent["children"] == []
    assert parent["expanded"] is False
    assert rebuilt == 1
    assert len(cats) == 1
    assert cats[0] is parent


def test_ensure_path_creates_full_chain():
    cats = []
    parent, rebuilt = ensure_path(cats, ["工作", "编程"])
    assert parent["name"] == "编程"
    assert rebuilt == 2
    assert cats[0]["name"] == "工作"
    assert cats[0]["children"][0] is parent


def test_ensure_path_partial_rebuild(v2_data):
    # "工作"已存在，但其下没有"测试"子分类 → 仅重建子分类
    cats = v2_data["categories"]
    parent, rebuilt = ensure_path(cats, ["工作", "测试"])
    assert parent["name"] == "测试"
    assert rebuilt == 1
    work = next(c for c in cats if c["name"] == "工作")
    assert any(c["name"] == "测试" for c in work["children"])
```

- [ ] **步骤 2：运行验证失败**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py::test_ensure_path_full_existing -v
```

预期：FAIL，`ImportError: cannot import name 'ensure_path'`。

### 任务 12：实现 `ensure_path`

**文件：**
- 修改：`data_ops.py`

- [ ] **步骤 1：在文件末尾追加**

```python
def ensure_path(categories, path):
    """沿 path 在 categories 中逐层走，缺失节点自动创建空分类。

    categories: 顶层 list[dict]（会被原地修改）
    path: list[str]，至少长度 1
    返回: (末端节点, 重建的节点数)

    用于回收站恢复时的路径重建。
    """
    if not path:
        raise ValueError("ensure_path 不接受空路径")
    current_list = categories
    parent = None
    rebuilt_count = 0
    for name in path:
        node = next((c for c in current_list if c["name"] == name), None)
        if node is None:
            node = {"name": name, "prompts": [], "expanded": False, "children": []}
            current_list.append(node)
            rebuilt_count += 1
        current_list = node["children"]
        parent = node
    return parent, rebuilt_count
```

- [ ] **步骤 2：运行验证通过**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py -v
```

预期：之前的 18 个 + 新增 5 个，全 PASS。

### 任务 13：编写 `restore_trash_entry` 失败测试

**文件：**
- 修改：`tests/test_data_ops.py`

- [ ] **步骤 1：在文件末尾追加**

```python
from data_ops import restore_trash_entry


def test_restore_top_level_category(v2_data):
    entry = {
        "id": 1, "type": "category",
        "payload": {"name": "新顶级", "prompts": [], "expanded": False, "children": []},
        "origin_path": [],
        "deleted_at": "2026-05-05 14:30",
    }
    restored, rebuilt, renamed = restore_trash_entry(v2_data["categories"], entry)
    assert restored["name"] == "新顶级"
    assert rebuilt == 0
    assert renamed is False
    assert v2_data["categories"][-1] is restored  # 追加到末尾


def test_restore_subcategory_full_path(v2_data):
    entry = {
        "id": 2, "type": "category",
        "payload": {"name": "新子级", "prompts": [], "expanded": False, "children": []},
        "origin_path": ["工作"],
        "deleted_at": "2026-05-05 14:30",
    }
    restored, rebuilt, renamed = restore_trash_entry(v2_data["categories"], entry)
    work = next(c for c in v2_data["categories"] if c["name"] == "工作")
    assert work["children"][-1] is restored
    assert rebuilt == 0
    assert renamed is False


def test_restore_prompt_to_existing_child(v2_data):
    entry = {
        "id": 3, "type": "prompt",
        "payload": {"title": "新 P", "content": "...", "created": "2026-04-20 10:00"},
        "origin_path": ["工作", "编程助手"],
        "deleted_at": "2026-05-05 14:30",
    }
    restored, rebuilt, renamed = restore_trash_entry(v2_data["categories"], entry)
    coding = v2_data["categories"][0]["children"][0]
    assert coding["prompts"][-1] is restored
    assert rebuilt == 0
    assert renamed is False


def test_restore_with_path_full_rebuild():
    cats = [{"name": "其它", "prompts": [], "expanded": False, "children": []}]
    entry = {
        "id": 4, "type": "prompt",
        "payload": {"title": "P", "content": "...", "created": "2026-04-20 10:00"},
        "origin_path": ["工作", "编程"],
        "deleted_at": "2026-05-05 14:30",
    }
    restored, rebuilt, renamed = restore_trash_entry(cats, entry)
    assert rebuilt == 2  # 重建了"工作"和"编程"
    work = next(c for c in cats if c["name"] == "工作")
    coding = next(c for c in work["children"] if c["name"] == "编程")
    assert coding["prompts"][-1] is restored


def test_restore_with_path_partial_rebuild(v2_data):
    # "工作"在，"测试"不在
    cats = v2_data["categories"]
    entry = {
        "id": 5, "type": "prompt",
        "payload": {"title": "P", "content": "...", "created": "2026-04-20 10:00"},
        "origin_path": ["工作", "测试"],
        "deleted_at": "2026-05-05 14:30",
    }
    restored, rebuilt, renamed = restore_trash_entry(cats, entry)
    assert rebuilt == 1
    test_cat = next(c for c in cats[0]["children"] if c["name"] == "测试")
    assert test_cat["prompts"][-1] is restored


def test_restore_category_name_collision_adds_prefix(v2_data):
    # 顶层已有"写作"，恢复一个同名顶层分类 → name 加时间前缀
    entry = {
        "id": 6, "type": "category",
        "payload": {"name": "写作", "prompts": [], "expanded": False, "children": []},
        "origin_path": [],
        "deleted_at": "2026-05-05 14:30",
    }
    restored, rebuilt, renamed = restore_trash_entry(v2_data["categories"], entry)
    assert renamed is True
    assert restored["name"] == "[2026-05-05 14:30] 写作"


def test_restore_prompt_title_collision_adds_prefix(v2_data):
    # 给"写作"先放一条同名 prompt
    v2_data["categories"][1]["prompts"].append(
        {"title": "邮件", "content": "first", "created": "2026-04-15 10:00"}
    )
    entry = {
        "id": 7, "type": "prompt",
        "payload": {"title": "邮件", "content": "restored", "created": "2026-04-10 10:00"},
        "origin_path": ["写作"],
        "deleted_at": "2026-05-05 14:30",
    }
    restored, rebuilt, renamed = restore_trash_entry(v2_data["categories"], entry)
    assert renamed is True
    assert restored["title"] == "[2026-05-05 14:30] 邮件"


def test_restore_reuses_existing_same_name_in_path():
    # 用户手动新建了同名"工作"，恢复 prompt 应复用而非另建
    cats = [{"name": "工作", "prompts": [], "expanded": False, "children": []}]
    entry = {
        "id": 8, "type": "prompt",
        "payload": {"title": "P", "content": "...", "created": "..."},
        "origin_path": ["工作", "编程"],
        "deleted_at": "2026-05-05 14:30",
    }
    restored, rebuilt, renamed = restore_trash_entry(cats, entry)
    assert rebuilt == 1  # 只重建了"编程"，"工作"被复用
    assert len(cats) == 1  # 顶层仍只有一个"工作"
```

- [ ] **步骤 2：运行验证失败**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py::test_restore_top_level_category -v
```

预期：FAIL，`ImportError: cannot import name 'restore_trash_entry'`。

### 任务 14：实现 `restore_trash_entry`

**文件：**
- 修改：`data_ops.py`

- [ ] **步骤 1：在文件末尾追加**

```python
def restore_trash_entry(categories, entry):
    """根据 entry 把回收站项恢复到 categories。沿 origin_path 自动重建缺失节点。

    categories: 顶层 list[dict]（会被原地修改，新增节点和被恢复项）
    entry: 回收站条目，含 type / payload / origin_path / deleted_at

    返回: (restored_node, rebuilt_count, renamed)
        restored_node: 被恢复并最终落入 categories 的节点（同 entry["payload"]，可能其 name/title 被改）
        rebuilt_count: 重建的中间节点数
        renamed: bool，是否因同级重名加了时间前缀
    """
    origin_path = entry["origin_path"]
    item_type = entry["type"]
    payload = entry["payload"]
    deleted_at = entry["deleted_at"]

    if item_type not in ("category", "prompt"):
        raise ValueError(f"未知 type: {item_type}")
    if item_type == "prompt" and not origin_path:
        raise ValueError("prompt 的 origin_path 不能为空")

    if item_type == "category" and not origin_path:
        target_list = categories
        rebuilt_count = 0
    else:
        parent_node, rebuilt_count = ensure_path(categories, origin_path)
        target_list = parent_node["children"] if item_type == "category" else parent_node["prompts"]

    name_field = "name" if item_type == "category" else "title"
    original_name = payload[name_field]
    renamed = False
    if any(item.get(name_field) == original_name for item in target_list):
        payload[name_field] = f"[{deleted_at}] {original_name}"
        renamed = True

    target_list.append(payload)
    return payload, rebuilt_count, renamed
```

- [ ] **步骤 2：运行所有测试**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py -v
```

预期：全 PASS（共 31 个测试）。

- [ ] **步骤 3：Commit**

```bash
git add data_ops.py tests/test_data_ops.py
git commit -m "feat(trash): 实现回收站 ID 分配、路径重建、恢复逻辑"
```

---

## Phase 5：拖拽校验（纯函数 + Qt 子类）

### 任务 15：编写 `is_drop_valid` 失败测试

**文件：**
- 修改：`tests/test_data_ops.py`

定义节点角色概念：
- 顶层节点：`role="top"`，无父级
- 子节点：`role="child"`，有父级
- 回收站节点：`role="trash"`，特殊不可参与拖拽
- 分隔符：`role="separator"`，不可拖

`drop_position` 概念：
- `"between"`：放在两节点之间（同级）
- `"on"`：放在节点身上（变成它的子节点）

- [ ] **步骤 1：在 `tests/test_data_ops.py` 末尾追加**

```python
from data_ops import is_drop_valid


def _make_node(name, role="top", has_children=False):
    return {"name": name, "role": role, "has_children": has_children}


def test_drop_top_leaf_between_top_levels():
    src = _make_node("A", role="top", has_children=False)
    tgt = _make_node("B", role="top")
    assert is_drop_valid(src, tgt, "between") == (True, "")


def test_drop_top_leaf_onto_top_becomes_child():
    src = _make_node("A", role="top", has_children=False)
    tgt = _make_node("B", role="top")
    assert is_drop_valid(src, tgt, "on") == (True, "")


def test_drop_child_to_top_level():
    src = _make_node("A", role="child")
    tgt = _make_node("B", role="top")
    assert is_drop_valid(src, tgt, "between") == (True, "")


def test_drop_parent_with_children_onto_other_top_rejected():
    # 把已有子分类的父分类拖到另一个分类身上 → 会形成 3 层，禁止
    src = _make_node("A", role="top", has_children=True)
    tgt = _make_node("B", role="top")
    ok, reason = is_drop_valid(src, tgt, "on")
    assert ok is False
    assert "2 层" in reason


def test_drop_anything_onto_trash_rejected():
    src = _make_node("A", role="top")
    tgt = _make_node("回收站", role="trash")
    ok, reason = is_drop_valid(src, tgt, "on")
    assert ok is False
    assert "右键菜单" in reason


def test_drop_anything_between_around_trash_rejected():
    src = _make_node("A", role="top")
    tgt = _make_node("回收站", role="trash")
    ok, reason = is_drop_valid(src, tgt, "between")
    assert ok is False


def test_drag_trash_node_rejected():
    src = _make_node("回收站", role="trash")
    tgt = _make_node("B", role="top")
    ok, _ = is_drop_valid(src, tgt, "between")
    assert ok is False


def test_drag_separator_rejected():
    src = _make_node("---", role="separator")
    tgt = _make_node("B", role="top")
    ok, _ = is_drop_valid(src, tgt, "between")
    assert ok is False
```

- [ ] **步骤 2：运行验证失败**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py::test_drop_top_leaf_between_top_levels -v
```

预期：FAIL，`ImportError: cannot import name 'is_drop_valid'`。

### 任务 16：实现 `is_drop_valid`

**文件：**
- 修改：`data_ops.py`

- [ ] **步骤 1：在文件末尾追加**

```python
def is_drop_valid(source, target, position):
    """校验拖拽是否合法。

    source / target: dict，至少含 "role" ∈ {"top","child","trash","separator"} 和 "has_children"（仅 source 用）
    position: "between" | "on"
    返回: (allowed: bool, reason: str)
        allowed=False 时 reason 是状态栏提示文案
    """
    if source.get("role") in ("trash", "separator"):
        return False, "该节点不可拖动"
    if target.get("role") in ("trash", "separator"):
        if target.get("role") == "trash":
            return False, "如需删除请用右键菜单"
        return False, "目标位置不可放置"
    # 已有 children 的父分类不能再被拖到其他分类身上（会形成 3 层）
    if position == "on" and source.get("has_children"):
        return False, "最多支持 2 层嵌套"
    return True, ""
```

- [ ] **步骤 2：运行所有测试**

```bash
conda activate PinPrompt
pytest tests/test_data_ops.py -v
```

预期：全 PASS（共 39 个测试）。

- [ ] **步骤 3：Commit**

```bash
git add data_ops.py tests/test_data_ops.py
git commit -m "feat(tree): 实现拖拽合法性校验纯函数"
```

### 任务 17：创建 `category_tree.py` 骨架

**文件：**
- 创建：`category_tree.py`

- [ ] **步骤 1：写 `CategoryTreeWidget` 子类初始版本**

`category_tree.py` 内容：

```python
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
```

- [ ] **步骤 2：导入冒烟测试**

运行：

```bash
conda activate PinPrompt
python -c "from category_tree import CategoryTreeWidget; print('ok')"
```

预期：输出 `ok`，无 ImportError。

- [ ] **步骤 3：Commit**

```bash
git add category_tree.py
git commit -m "feat(tree): 添加 CategoryTreeWidget 拖拽校验子类"
```

---

## Phase 6：主窗口集成数据迁移与树控件

### 任务 18：在 `load_data` 中接入迁移与备份

**文件：**
- 修改：`main_pyside.py`（`PinPromptApp.load_data`）

- [ ] **步骤 1：在 `main_pyside.py` 顶部新增 import**

在文件开头的 import 区域加：

```python
import shutil
from data_ops import migrate_v1_to_v2
```

- [ ] **步骤 2：替换 `load_data` 实现**

把现有的 `load_data` 整体替换为：

```python
    def load_data(self):
        """加载数据；旧 v1 格式自动迁移并备份原文件。"""
        if not os.path.exists(DATA_FILE):
            return {"version": 2, "categories": [], "trash": []}
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return {"version": 2, "categories": [], "trash": []}

        if data.get("version", 1) < 2:
            backup_path = DATA_FILE + ".v1.bak"
            try:
                shutil.copyfile(DATA_FILE, backup_path)
            except Exception:
                pass
            data = migrate_v1_to_v2(data)
            self._needs_post_load_save = True
        else:
            self._needs_post_load_save = False
        # 兼容遗漏字段
        data.setdefault("trash", [])
        return data
```

- [ ] **步骤 3：在 `__init__` 末尾根据 `_needs_post_load_save` 触发一次落盘**

定位到 `__init__` 方法中 `self.refresh_categories()` 之后追加：

```python
        if getattr(self, "_needs_post_load_save", False):
            self.save_data()
```

- [ ] **步骤 4：手动验证迁移**

准备一个 v1 格式的 prompts.json（如果不存在则跳过）：

```bash
conda activate PinPrompt
python -c "
import json, os
data = {'categories': {'测试': {'prompts': [{'title':'T','content':'C','created':'2026-01-01 00:00'}]}}}
with open('prompts.json','w',encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('v1 fixture written')
"
python main_pyside.py
```

预期：程序正常启动，且：
- 项目根目录出现 `prompts.json.v1.bak`
- `prompts.json` 已被改写为 v2 格式（含 `version: 2` 和 `trash: []`）

退出程序后查看：

```bash
cat prompts.json | head -20
```

确认含 `"version": 2`。

- [ ] **步骤 5：Commit**

```bash
git add main_pyside.py
git commit -m "feat(data): load_data 接入 v1→v2 迁移并备份原文件"
```

### 任务 19：把 `QListWidget` 替换为 `CategoryTreeWidget`

**文件：**
- 修改：`main_pyside.py`

- [ ] **步骤 1：在顶部 import 区域追加**

```python
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu
from category_tree import CategoryTreeWidget, ROLE_KEY, KIND_KEY
```

注意保留原有的 import（QListWidget 仍然可能被其他地方用到，但我们要去掉对它的依赖）。

- [ ] **步骤 2：替换 `create_category_panel` 实现**

定位到 `create_category_panel` 方法，把内部的 `QListWidget` 替换为 `CategoryTreeWidget`：

```python
    def create_category_panel(self):
        """创建分类面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("分类")
        title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(title)

        self.category_tree = CategoryTreeWidget()
        self.category_tree.setFont(QFont("Microsoft YaHei", 10))
        self.category_tree.currentItemChanged.connect(self.on_category_select)
        self.category_tree.itemExpanded.connect(self.on_item_expanded)
        self.category_tree.itemCollapsed.connect(self.on_item_collapsed)
        self.category_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_tree.customContextMenuRequested.connect(self.show_category_menu)
        self.category_tree.drop_rejected.connect(self._on_drop_rejected)
        self.category_tree.drop_completed.connect(self._on_drop_completed)
        layout.addWidget(self.category_tree)

        return panel

    def _on_drop_rejected(self, reason):
        self.status_bar.showMessage(reason, 3000)

    def _on_drop_completed(self):
        # drop 后由树状态重建 self.data["categories"]，并落盘
        self.data["categories"] = self._tree_to_categories()
        self.save_data()
        self.refresh_categories()
```

- [ ] **步骤 3：删除旧的 `category_list` 引用并替换 `refresh_categories`、`on_category_select`**

把 `refresh_categories` 替换为：

```python
    def refresh_categories(self):
        """刷新分类树。包含末尾的回收站节点。"""
        self.category_tree.blockSignals(True)
        self.category_tree.clear()

        for cat in self.data["categories"]:
            top_item = self._make_category_item(cat, role="top")
            self.category_tree.addTopLevelItem(top_item)
            for child in cat.get("children", []):
                child_item = self._make_category_item(child, role="child")
                top_item.addChild(child_item)
            top_item.setExpanded(cat.get("expanded", False))

        # 分隔符（disabled item）
        sep = QTreeWidgetItem(["─" * 12])
        sep.setFlags(Qt.NoItemFlags)
        sep.setData(0, KIND_KEY, "separator")
        self.category_tree.addTopLevelItem(sep)

        # 回收站节点
        trash_count = len(self.data.get("trash", []))
        trash_label = f"🗑️ 回收站 ({trash_count})" if trash_count else "🗑️ 回收站"
        trash_item = QTreeWidgetItem([trash_label])
        trash_item.setData(0, KIND_KEY, "trash")
        self.category_tree.addTopLevelItem(trash_item)

        self.category_tree.blockSignals(False)

    def _make_category_item(self, cat_dict, role):
        """构造分类节点；显示文本含图标和计数。"""
        if cat_dict.get("children"):
            text = f"📂 {cat_dict['name']} [{len(cat_dict['children'])}]"
        else:
            text = f"📁 {cat_dict['name']} ({len(cat_dict.get('prompts', []))})"
        item = QTreeWidgetItem([text])
        item.setData(0, ROLE_KEY, cat_dict)
        item.setData(0, KIND_KEY, role)
        return item

    def _tree_to_categories(self):
        """从当前树状态构造一个新的 categories 列表（保持引用不变以保留 prompts/expanded）。"""
        new_top = []
        for i in range(self.category_tree.topLevelItemCount()):
            item = self.category_tree.topLevelItem(i)
            kind = item.data(0, KIND_KEY)
            if kind in ("trash", "separator"):
                continue
            cat = item.data(0, ROLE_KEY)
            cat["children"] = []
            for j in range(item.childCount()):
                child_item = item.child(j)
                child_cat = child_item.data(0, ROLE_KEY)
                child_cat["children"] = []  # 子级不应再有子，强制清空
                cat["children"].append(child_cat)
            cat["expanded"] = item.isExpanded()
            new_top.append(cat)
        return new_top
```

把 `on_category_select` 替换为：

```python
    def on_category_select(self, current, previous):
        if current is None:
            self.current_category = None
            self.refresh_prompts()
            return
        kind = current.data(0, KIND_KEY)
        if kind == "trash":
            self.current_category = None
            self.refresh_trash_view()
            self.status_bar.showMessage("回收站")
            return
        if kind == "separator":
            return
        cat = current.data(0, ROLE_KEY)
        self.current_category = cat
        self.refresh_prompts()
        self.status_bar.showMessage(f"当前分类: {cat['name']}")
```

把 `refresh_prompts` 中所有用到 `self.current_category` 字符串名字的地方改为读取 `cat` dict（因为现在 `self.current_category` 已是 dict 引用）。具体改动：

```python
    def refresh_prompts(self):
        """刷新 Prompt 列表。"""
        while self.prompt_layout.count():
            item = self.prompt_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cat = self.current_category
        if cat is None:
            return

        prompts = cat.get("prompts", [])
        search_text = self.search_edit.text().strip().lower()
        if search_text:
            prompts = [p for p in prompts
                       if search_text in p.get("title", "").lower()
                       or search_text in p.get("content", "").lower()]

        if not prompts:
            empty = QLabel("暂无 Prompt" if not search_text else "没有匹配的搜索结果")
            empty.setFont(QFont("Microsoft YaHei", 10))
            empty.setStyleSheet("color: #999999; padding: 20px;")
            self.prompt_layout.addWidget(empty)
            return

        for i, prompt in enumerate(prompts):
            card = PromptCard(prompt, i, self)
            self.prompt_layout.addWidget(card)
```

注意 `add_prompt` / `edit_prompt` / `delete_prompt` / `delete_category` 等需要随之更新，统一改为通过 `self.current_category`（dict 引用）访问。下面任务里逐个处理。

- [ ] **步骤 4：先添加占位的 `refresh_trash_view`、`on_item_expanded`、`on_item_collapsed`、`show_category_menu`，避免本任务编译失败**

在 `PinPromptApp` 类中添加：

```python
    def refresh_trash_view(self):
        """暂时占位，Phase 7 实现完整版。"""
        while self.prompt_layout.count():
            item = self.prompt_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        label = QLabel("（回收站视图将在 Phase 7 完整实现）")
        label.setStyleSheet("color: #999; padding: 20px;")
        self.prompt_layout.addWidget(label)

    def on_item_expanded(self, item):
        cat = item.data(0, ROLE_KEY)
        if cat is not None:
            cat["expanded"] = True

    def on_item_collapsed(self, item):
        cat = item.data(0, ROLE_KEY)
        if cat is not None:
            cat["expanded"] = False

    def show_category_menu(self, pos):
        """暂时占位，Phase 7 实现完整版。"""
        pass
```

- [ ] **步骤 5：临时改造 `add_prompt` / `delete_category` 等方法的字符串引用**

`add_prompt` 改为：

```python
    def add_prompt(self):
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
            self.refresh_categories()
            self.refresh_prompts()
            self.status_bar.showMessage(f"已添加 Prompt: {data['title']}")
```

`edit_prompt` 改为：

```python
    def edit_prompt(self, index):
        if not self.current_category:
            return
        prompts = self.current_category["prompts"]
        prompt = prompts[index]
        dialog = AddEditDialog(self, title=prompt.get("title", ""),
                               content=prompt.get("content", ""), is_edit=True)
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
            self.refresh_categories()
            self.refresh_prompts()
            self.status_bar.showMessage(f"已更新 Prompt: {data['title']}")
```

`delete_prompt(index)` 改为（Phase 7 会再升级为"进回收站"，这里先保持现状即直接删）：

```python
    def delete_prompt(self, index):
        if not self.current_category:
            return
        prompts = self.current_category["prompts"]
        prompt = prompts[index]
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除 Prompt「{prompt.get('title')}」吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            del prompts[index]
            self.save_data()
            self.refresh_categories()
            self.refresh_prompts()
            self.status_bar.showMessage("Prompt 已删除")
```

旧的 `delete_category` / `add_category` 暂保留（Phase 7 会重写），但去掉对 `self.data["categories"]` 是 dict 的假设——本任务只要不 crash 即可。把工具栏的"🗑️ 删除分类"按钮临时禁用：

定位到 `create_toolbar` 中：

```python
        del_cat_btn = QPushButton("🗑️ 删除分类")
        del_cat_btn.clicked.connect(self.delete_category)
        toolbar_layout.addWidget(del_cat_btn)
```

替换为：

```python
        # 删除分类已迁移到右键菜单（Phase 7）
```

把 `add_category` 改为：

```python
    def add_category(self):
        from PySide6.QtWidgets import QInputDialog
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
```

把工具栏按钮文字 `"➕ 新建分类"` 改为 `"➕ 新建顶级分类"`。

- [ ] **步骤 6：手动启动验证**

```bash
conda activate PinPrompt
python main_pyside.py
```

预期：
- 程序正常启动
- 左侧显示分类树（v1 数据已迁移）
- 顶部分类节点带 `📁 名字 (N)` 计数
- 树底部出现 `─────────` 分隔符 + `🗑️ 回收站`
- 选中分类，右侧显示 prompts
- 选中"回收站"，右侧显示占位文字
- 拖拽分类可重排（drop 后顺序变化、计数刷新）
- 把一个分类拖到另一个分类身上 → 变子分类，父侧显示 `📂 名字 [1]`

- [ ] **步骤 7：Commit**

```bash
git add main_pyside.py
git commit -m "feat(ui): 用 CategoryTreeWidget 替换 QListWidget，支持拖拽和折叠"
```

---

## Phase 7：右键菜单与回收站删除

### 任务 20：右键菜单：重命名 / 新建子分类 / 提升 / 移到顶部

**文件：**
- 修改：`main_pyside.py`

- [ ] **步骤 1：在 `main_pyside.py` 顶部加 import**

```python
from data_ops import is_name_unique_among_siblings, next_trash_id
```

- [ ] **步骤 2：完整实现 `show_category_menu`**

替换前面 Phase 6 中占位的 `show_category_menu`：

```python
    def show_category_menu(self, pos):
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
        # 注：回收站子项渲染在右侧卡片区，不在树里，因此无 "trash_item" 分支
        if kind == "separator":
            return

        # 普通分类菜单
        cat = item.data(0, ROLE_KEY)
        is_top = (kind == "top")
        is_child = (kind == "child")

        act_rename = menu.addAction("重命名")
        act_add_child = menu.addAction("新建子分类") if is_top else None
        act_delete = menu.addAction("删除")
        act_move_top = menu.addAction("移到顶部") if is_top else None
        act_promote = menu.addAction("提升为顶级") if is_child else None

        chosen = menu.exec(self.category_tree.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == act_rename:
            self._rename_category(cat, kind, item)
        elif chosen == act_add_child:
            self._add_subcategory(cat, item)
        elif chosen == act_delete:
            self._delete_category_to_trash(cat, kind, item)
        elif chosen == act_move_top:
            self._move_to_top(cat)
        elif chosen == act_promote:
            self._promote_to_top(cat, item)
```

- [ ] **步骤 3：实现 `_rename_category`**

```python
    def _rename_category(self, cat, kind, item):
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "重命名分类", "新名字:", text=cat["name"])
        if not ok:
            return
        new_name = new_name.strip()
        if not new_name or new_name == cat["name"]:
            return
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
        # child: 找父节点
        parent_item = item.parent()
        parent_cat = parent_item.data(0, ROLE_KEY) if parent_item else None
        return parent_cat["children"] if parent_cat else []
```

- [ ] **步骤 4：实现 `_add_subcategory`**

```python
    def _add_subcategory(self, parent_cat, parent_item):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "新建子分类", "子分类名称:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if any(c["name"] == name for c in parent_cat["children"]):
            QMessageBox.warning(self, "警告", "同级已存在同名子分类！")
            return
        parent_cat["children"].append({
            "name": name, "prompts": [], "expanded": False, "children": []
        })
        parent_cat["expanded"] = True
        self.save_data()
        self.refresh_categories()
        self.status_bar.showMessage(f"已新建子分类: {name}")
```

- [ ] **步骤 5：实现 `_move_to_top` 和 `_promote_to_top`**

```python
    def _move_to_top(self, cat):
        self.data["categories"].remove(cat)
        self.data["categories"].insert(0, cat)
        self.save_data()
        self.refresh_categories()
        self.status_bar.showMessage(f"已移到顶部: {cat['name']}")

    def _promote_to_top(self, cat, item):
        parent_item = item.parent()
        if parent_item is None:
            return
        parent_cat = parent_item.data(0, ROLE_KEY)
        parent_cat["children"].remove(cat)
        if any(c["name"] == cat["name"] for c in self.data["categories"]):
            from datetime import datetime
            cat["name"] = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {cat['name']}"
        self.data["categories"].append(cat)
        self.save_data()
        self.refresh_categories()
        self.status_bar.showMessage(f"已提升为顶级: {cat['name']}")
```

- [ ] **步骤 6：手动验证菜单可用**

```bash
conda activate PinPrompt
python main_pyside.py
```

测试：
- 右键顶层叶子分类 → 看到"重命名 / 新建子分类 / 删除 / 移到顶部"
- 重命名校验同级唯一
- 新建子分类后该顶层自动展开
- 移到顶部把分类放第一位
- 右键子分类 → 看到"重命名 / 删除 / 提升为顶级"
- 提升后子分类成为顶层

注意"删除"菜单项还连着旧的（占位空函数 `_delete_category_to_trash` 还没定义），下一步任务实现。

- [ ] **步骤 7：Commit**

```bash
git add main_pyside.py
git commit -m "feat(menu): 添加分类右键菜单（重命名/新建子分类/移到顶部/提升）"
```

### 任务 21：实现 "删除→进回收站" 与回收站节点展示

**文件：**
- 修改：`main_pyside.py`

- [ ] **步骤 1：实现 `_delete_category_to_trash`**

```python
    def _delete_category_to_trash(self, cat, kind, item):
        # 统计将影响的数量
        child_count = len(cat.get("children", []))
        prompt_count = self._count_prompts_recursive(cat)
        msg = f"确定要删除分类「{cat['name']}」吗？\n"
        if child_count or prompt_count:
            msg += f"该分类包含 {child_count} 个子分类、共 {prompt_count} 条 Prompt，将一并放入回收站。"
        else:
            msg += "将放入回收站。"
        reply = QMessageBox.question(self, "确认删除", msg,
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        origin_path = self._origin_path_of(cat, kind, item)
        siblings = self._siblings_of(cat, kind, item)
        siblings.remove(cat)

        from datetime import datetime
        entry = {
            "id": next_trash_id(self.data["trash"]),
            "type": "category",
            "payload": cat,
            "origin_path": origin_path,
            "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.data["trash"].append(entry)
        if self.current_category is cat:
            self.current_category = None
        self.save_data()
        self.refresh_categories()
        self.refresh_prompts()
        self.status_bar.showMessage(f"已移入回收站: {cat['name']}")

    def _count_prompts_recursive(self, cat):
        total = len(cat.get("prompts", []))
        for child in cat.get("children", []):
            total += len(child.get("prompts", []))
        return total

    def _origin_path_of(self, cat, kind, item):
        """返回 cat 的父级路径。顶层 → []，子级 → [父名]。"""
        if kind == "top":
            return []
        parent_item = item.parent()
        if parent_item is None:
            return []
        parent_cat = parent_item.data(0, ROLE_KEY)
        return [parent_cat["name"]]
```

- [ ] **步骤 2：升级 `delete_prompt` 让单条 prompt 也进回收站**

替换 Phase 6 中的 `delete_prompt`：

```python
    def delete_prompt(self, index):
        if not self.current_category:
            return
        prompts = self.current_category["prompts"]
        prompt = prompts[index]
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除 Prompt「{prompt.get('title')}」？\n将放入回收站。",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        del prompts[index]
        from datetime import datetime
        entry = {
            "id": next_trash_id(self.data["trash"]),
            "type": "prompt",
            "payload": prompt,
            "origin_path": self._path_of_current_category(),
            "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.data["trash"].append(entry)
        self.save_data()
        self.refresh_categories()
        self.refresh_prompts()
        self.status_bar.showMessage("Prompt 已移入回收站")

    def _path_of_current_category(self):
        """返回当前 self.current_category 的完整路径（含自身）。"""
        cat = self.current_category
        if cat is None:
            return []
        # 在 self.data["categories"] 中找到 cat 的路径
        for top in self.data["categories"]:
            if top is cat:
                return [top["name"]]
            for child in top.get("children", []):
                if child is cat:
                    return [top["name"], child["name"]]
        return []
```

- [ ] **步骤 3：手动验证**

```bash
conda activate PinPrompt
python main_pyside.py
```

操作：
- 右键某顶层分类 → 删除 → 弹窗写明数量 → 确认
- 该分类从树消失，回收站节点计数 +1
- 删除带子分类和 prompts 的父分类，弹窗显示如"包含 2 个子分类、共 5 条 Prompt"
- 删除单条 prompt，回收站计数 +1
- 重启程序，回收站内容仍在（已落盘）

- [ ] **步骤 4：Commit**

```bash
git add main_pyside.py
git commit -m "feat(trash): 删除分类/prompt 进回收站，弹窗显示影响数量"
```

---

## Phase 8：回收站 UI

### 任务 22：回收站节点渲染与卡片

**文件：**
- 修改：`main_pyside.py`（`refresh_categories` 末尾添加分隔符与回收站节点；新增 `refresh_trash_view`、`TrashItemCard`；更新 `on_category_select` 增加 trash 分支）

- [ ] **步骤 1：在 refresh_categories 末尾追加分隔符与回收站节点**

定位 Phase 6 任务 19 实现的 `refresh_categories`，在 `for cat in self.data["categories"]` 循环之后追加以下逻辑：

```python
    def refresh_categories(self):
        self.category_tree.blockSignals(True)
        self.category_tree.clear()
        for cat in self.data["categories"]:
            top_item = self._make_category_item(cat)
            self.category_tree.addTopLevelItem(top_item)
            for child in cat.get("children", []):
                child_item = self._make_category_item(child)
                top_item.addChild(child_item)
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

        self.category_tree.blockSignals(False)
```

注意 `setFlags(Qt.NoItemFlags)` 会让分隔符不参与拖拽与选中。回收站去掉了 `ItemIsDragEnabled` / `ItemIsDropEnabled`，使其无法被拖、也不能放东西进去。

- [ ] **步骤 2：更新 `on_category_select` 增加 trash 分支与 `current_view` 追踪**

替换 Phase 6 任务 19 的 `on_category_select` 实现：

```python
    def on_category_select(self, current, previous):
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
```

并在 `__init__` 顶部初始化 `self.current_view = "normal"`（用于区分当前是普通分类视图还是回收站视图）。

- [ ] **步骤 3：实现 refresh_trash_view**

在 `PinPromptApp` 中新增：

```python
    def refresh_trash_view(self):
        """渲染回收站列表为卡片。"""
        # 复用 prompt_layout 的容器，先清空
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

        # 按 deleted_at 倒序：最近删除的排在最前面
        for entry in sorted(trash, key=lambda e: e.get("deleted_at", ""), reverse=True):
            card = TrashItemCard(entry, self)
            self.prompt_layout.addWidget(card)
        self.prompt_layout.addStretch()
```

- [ ] **步骤 4：实现 TrashItemCard**

在 `PromptCard` 类定义之后、`AddEditDialog` 之前新增：

```python
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
```

- [ ] **步骤 5：手动验证**

```bash
conda activate PinPrompt
python main_pyside.py
```

操作：
- 删除若干分类和 prompt 进回收站
- 点击回收站节点，右侧切换为回收站列表
- 每张卡片显示类型、原路径、删除时间
- 类型为分类的卡片额外显示子分类和 prompt 数量
- 卡片右侧有"恢复"和"永久删除"按钮（点击后续步骤实现）
- 列表头部有"清空回收站"按钮

- [ ] **步骤 6：Commit**

```bash
git add main_pyside.py
git commit -m "feat(trash): 回收站节点 + 卡片视图 + 顶部操作区"
```

---

### 任务 23：回收站操作（恢复 / 永久删除 / 清空）

**文件：**
- 修改：`main_pyside.py`（新增 `_restore_trash_item`、`_purge_trash_item`、`_clear_trash`；扩展 `show_category_menu` 的 trash / trash_item 分支）

- [ ] **步骤 1：实现 _restore_trash_item**

在 `PinPromptApp` 中新增：

```python
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
```

- [ ] **步骤 2：实现 _purge_trash_item**

```python
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
```

- [ ] **步骤 3：实现 _clear_trash**

```python
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
```

- [ ] **步骤 4：扩展 show_category_menu 的 trash / trash_item 分支**

更新 Phase 7 任务 20 的 `show_category_menu` 代码（trash 节点已有"清空回收站"），仅需新增 trash_item 分支（如果将来在树里展开回收站子项；当前设计回收站节点不展开，子项渲染在右侧卡片区，所以这里不需额外动作。但为了显式确认设计：在 `show_category_menu` 顶部 `kind == "trash"` 分支保持原样即可）。

确认无需新增菜单：树里点击回收站节点直接进入卡片视图，所有操作在卡片按钮上完成。

- [ ] **步骤 5：手动验证**

```bash
conda activate PinPrompt
python main_pyside.py
```

操作：
1. **基础恢复**：删除一个顶级分类 → 进回收站 → 点恢复 → 顶级分类回到原位
2. **路径完整恢复**：父分类存在时删除子分类 → 恢复 → 子分类回到原父下
3. **路径自动重建**：删父分类（带子）→ 单独永久删除子分类的回收站 entry（不可能，因为父删时 children 一起进）；重新构造场景：先删某子分类 A，再删其父 B 进回收站，然后 purge 父 B；再恢复 A → 应自动重建空的父分类 → 弹"已自动重建 1 个空分类"
4. **同名冲突**：顶级删除"工作"→ 新建同名"工作"分类 → 恢复回收站中的"工作"→ 名字变为 `[2026-05-05 14:30] 工作`（由 restore_trash_entry 按 deleted_at 加前缀）
5. **Prompt 恢复同名**：删 prompt → 新建同名 → 恢复 → 标题变为 `[deleted_at] 原标题`
6. **永久删除单条**：点卡片"永久删除"→ 弹窗确认 → 该条消失
7. **清空回收站**：点头部"清空回收站"→ 弹窗确认 → 全部消失，回收站节点变 `🗑️ 回收站 (0)`
8. **空回收站**：进入回收站视图显示"回收站为空"

- [ ] **步骤 6：Commit**

```bash
git add main_pyside.py
git commit -m "feat(trash): 恢复/永久删除/清空回收站，路径自动重建"
```

---

## Phase 9：递归视图

### 任务 24：父分类递归显示后代 prompts

**文件：**
- 修改：`main_pyside.py`（顶部工具栏新增 toggle 按钮 + `refresh_prompts` 内分发到 `_refresh_prompts_normal` / `_refresh_prompts_recursive`）

- [ ] **步骤 1：在工具栏添加"递归显示"开关**

定位 `__init__` 中创建顶部工具栏的位置，在搜索框旁边新增按钮：

```python
        self.recursive_btn = QPushButton("递归显示")
        self.recursive_btn.setCheckable(True)
        self.recursive_btn.setChecked(False)
        self.recursive_btn.setToolTip("开启后，父分类显示其本身和所有后代分类的 Prompt")
        self.recursive_btn.toggled.connect(self.on_recursive_toggled)
        toolbar_layout.addWidget(self.recursive_btn)
```

并在 `__init__` 中初始化：

```python
        self.recursive_view = False
```

- [ ] **步骤 2：实现 on_recursive_toggled**

```python
    def on_recursive_toggled(self, checked):
        self.recursive_view = checked
        if self.current_view == "normal":
            self.refresh_prompts()
```

- [ ] **步骤 3：升级 refresh_prompts 分发到递归视图**

替换原 `refresh_prompts`：

```python
    def refresh_prompts(self):
        """根据 recursive_view 分发到普通或递归视图。"""
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
        kw = self.search_input.text().strip().lower()
        for idx, p in enumerate(prompts):
            if kw and kw not in p.get("title", "").lower() and kw not in p.get("content", "").lower():
                continue
            card = PromptCard(p, idx, self)
            self.prompt_layout.addWidget(card)
        self.prompt_layout.addStretch()

    def _refresh_prompts_recursive(self):
        """父分类视图：按子分类分组显示所有后代 prompts。"""
        self._clear_prompt_layout()
        cat = self.current_category
        kw = self.search_input.text().strip().lower()

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
            # 注意：递归视图下卡片的 index 仍指向其所属分类的 prompts 列表
            # 但 PromptCard 通过 self.parent.current_category 取列表会有歧义
            # 解决：让 PromptCard 在递归视图下使用 prompt_owner 参数（见步骤 4）
            for idx, p in child_prompts:
                self.prompt_layout.addWidget(PromptCard(p, idx, self, prompt_owner=child))

        self.prompt_layout.addStretch()

    def _add_section_header(self, text):
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #888; padding: 6px 0; font-size: 12px;")
        self.prompt_layout.addWidget(lbl)
```

- [ ] **步骤 4：调整 PromptCard 接受 prompt_owner 参数**

更新 `PromptCard.__init__`：

```python
class PromptCard(QFrame):
    def __init__(self, prompt, index, parent, prompt_owner=None):
        super().__init__()
        self.prompt = prompt
        self.index = index
        self.parent = parent
        # 该 prompt 实际归属于哪个分类（递归视图下可能不是 parent.current_category）
        self.prompt_owner = prompt_owner if prompt_owner is not None else parent.current_category
        # ... 其余 UI 构建逻辑保持不变
```

并升级 `PromptCard` 中编辑/删除按钮的回调，使用 `self.prompt_owner` 而不是 `self.parent.current_category`：

```python
    def edit_prompt(self):
        # 用 prompt_owner 而不是 current_category
        # 旧：self.parent.current_category["prompts"][self.index]
        # 新：self.prompt_owner["prompts"][self.index]
        ...

    def delete_prompt(self):
        # 同理
        ...
```

具体：定位现有 `PromptCard` 中所有 `self.parent.current_category` 的使用，统一改为 `self.prompt_owner`。`PinPromptApp.delete_prompt` 入参的 prompt_owner 也要从卡片传入：

```python
    def delete_prompt(self, index, prompt_owner=None):
        owner = prompt_owner if prompt_owner is not None else self.current_category
        if owner is None:
            return
        prompts = owner["prompts"]
        # ... 其余按 Phase 7 任务 21 的实现，但用 owner
```

并把 origin_path 改为 owner 的路径：

```python
    def _path_of_owner(self, owner):
        """返回任意分类节点的完整路径。"""
        for top in self.data["categories"]:
            if top is owner:
                return [top["name"]]
            for child in top.get("children", []):
                if child is owner:
                    return [top["name"], child["name"]]
        return []
```

并在 `delete_prompt` 中将 `origin_path` 设为 `self._path_of_owner(owner)`。

- [ ] **步骤 5：手动验证**

```bash
conda activate PinPrompt
python main_pyside.py
```

操作：
1. 选中一个有子分类的父分类（如"工作"下面有"编程助手"、"邮件"）
2. 点击工具栏"递归显示" → 右侧依次显示：
   - `── 工作 ──`（如果工作自身有 prompt）
   - 工作的 prompt 卡片
   - `── 编程助手 ──`
   - 编程助手的 prompt 卡片
   - `── 邮件 ──`
   - ...
3. 在递归视图下编辑某子分类的 prompt → 修改后回到子分类视图确认变更生效
4. 在递归视图下删除某子分类的 prompt → 该 prompt 进回收站，回收站显示原路径为子分类
5. 关闭递归显示 → 回到只显示当前分类自己的 prompt
6. 选中无子分类的叶子分类时 → 即使开启递归，也只显示自己的 prompt（不显示空标题）

- [ ] **步骤 6：Commit**

```bash
git add main_pyside.py
git commit -m "feat(view): 父分类递归显示后代 prompts，按子分类分组"
```

---

## Phase 10：closeEvent + 展开状态持久化

### 任务 25：closeEvent 落盘 expanded 状态

**文件：**
- 修改：`main_pyside.py`（新增 / 升级 `closeEvent`、`_persist_expanded_states`）

- [ ] **步骤 1：实现 _persist_expanded_states**

将 QTreeWidget 中每个节点的当前 `isExpanded()` 写回数据 dict 的 `expanded` 字段。

```python
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
            # 子节点也持久化（虽然当前只有 2 层，子层一般无 expanded 意义，但保持一致）
            for j in range(top_item.childCount()):
                child_item = top_item.child(j)
                child_cat = child_item.data(0, ROLE_KEY)
                if child_cat is not None:
                    child_cat["expanded"] = child_item.isExpanded()
```

- [ ] **步骤 2：实现/升级 closeEvent**

如果 `PinPromptApp` 已有 `closeEvent`（早期版本可能没有），合并以下逻辑；否则新增：

```python
    def closeEvent(self, event):
        try:
            self._persist_expanded_states()
            self.save_data()
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"关闭时保存数据失败：{e}")
        super().closeEvent(event)
```

- [ ] **步骤 3：手动验证**

```bash
conda activate PinPrompt
python main_pyside.py
```

操作：
1. 展开"工作"分类（看到子分类）→ 关闭程序
2. 重新启动 → "工作"仍处于展开状态
3. 折叠"工作"→ 关闭 → 重启 → "工作"折叠
4. 用文本编辑器查看 `prompts.json` → 顶级分类对象有 `"expanded": true/false`

- [ ] **步骤 4：Commit**

```bash
git add main_pyside.py
git commit -m "feat(persist): 关闭时保存分类展开状态"
```

---

## Phase 11：手动测试清单与回归

### 任务 26：覆盖设计文档 §12 的全部测试场景

**目标：** 在所有功能上线后，按设计文档 §12 列出的场景手动跑一轮，记录任何回归。

- [ ] **步骤 1：生成测试用 prompts.json**

准备一个手工编辑的 v1 数据（用于验证迁移）和一个相对完整的 v2 数据。

v1 测试数据（保存为 `prompts.json`，启动前备份）：

```json
{
  "categories": {
    "工作": {"prompts": [
      {"title": "周报", "content": "请写一份周报"},
      {"title": "会议总结", "content": "总结会议要点"}
    ]},
    "学习": {"prompts": [
      {"title": "Python", "content": "解释 GIL"}
    ]},
    "测试": {"prompts": []}
  }
}
```

- [ ] **步骤 2：跑 §12.1 数据迁移验证**

```bash
conda activate PinPrompt
python main_pyside.py
```

验证：
- [ ] 启动后无报错
- [ ] 看到生成的 `prompts.json.v1.bak` 与 v1 内容一致
- [ ] `prompts.json` 现在结构为 `{"version": 2, "categories": [...], "trash": []}`
- [ ] 顶级分类按字母序排列：工作、学习、测试
- [ ] 每个分类的 `prompts` 与 v1 一致；`children` 为 `[]`；`expanded` 为 false

- [ ] **步骤 3：跑 §12.2 树控件交互**

- [ ] 点击顶级分类 → 右侧显示其 prompts
- [ ] 双击或单击展开图标 → 子分类列表展开
- [ ] 右键顶级分类 → 出现菜单（重命名、新建子分类、删除）
- [ ] 右键子分类 → 出现菜单（重命名、提升为顶级、删除；不出现"新建子分类"）
- [ ] 拖拽某子分类移到另一个父分类下 → 视觉到位 + 数据 children 列表对应变更
- [ ] 拖拽顶级分类调整顺序 → 数据 categories 顺序变更
- [ ] 尝试拖拽到回收站节点 → 被拒绝（drop_rejected 信号触发，状态栏提示）
- [ ] 尝试拖拽 3 层嵌套 → 被拒绝
- [ ] 拖拽到分隔符 → 被拒绝

- [ ] **步骤 4：跑 §12.3 同级唯一性**

- [ ] 在"工作"下新建子分类"测试" → 成功（顶级有"测试"但子级没有）
- [ ] 再次在"工作"下新建子分类"测试" → 失败提示
- [ ] 重命名某子分类与同级冲突 → 失败提示

- [ ] **步骤 5：跑 §12.4 回收站与路径重建**

按 Phase 8 任务 23 步骤 5 的 8 个场景再跑一遍。

- [ ] **步骤 6：跑 §12.5 递归视图**

按 Phase 9 任务 24 步骤 5 的场景跑。

- [ ] **步骤 7：跑 §12.6 持久化**

- [ ] 展开/折叠多个节点 → 关闭程序 → 重启 → 状态保留
- [ ] 排序变化 → 重启 → 顺序保留
- [ ] 拖拽到子级 → 重启 → 仍在子级

- [ ] **步骤 8：跑 §12.7 v1 兼容旧数据**

把 `prompts.json` 替换回原始 v1（不带 version 字段）→ 启动 → 仍能成功迁移。

- [ ] **步骤 9：打包验证**

```bash
conda activate PinPrompt
python -m PyInstaller --noconfirm --onefile --windowed --icon "PinPrompt.ico" --name "PinPrompt" main_pyside.py
```

- [ ] `dist/PinPrompt.exe` 启动正常
- [ ] 在 exe 同级目录读写 `prompts.json`（开发期数据不污染）
- [ ] 关闭再开,数据完整

- [ ] **步骤 10：Commit 测试结果记录（可选）**

如果跑测试发现并修了 bug，按各 phase 的 commit 风格补一次：

```bash
git add <files>
git commit -m "fix(...): <具体问题>"
```

如果完全无回归，无需新增 commit。

---

## 总结

完成本计划后，PinPrompt 将具备：

1. **二级分类树**（顶级 + 子级）支持折叠展开
2. **拖拽排序与移动**（同级排序、跨父级移动、3 层嵌套被拒绝）
3. **回收站机制**（删除分类/Prompt 进回收站、恢复时按 origin_path 自动重建路径、永久删除、清空回收站）
4. **递归视图**（父分类查看时按子分类分组显示所有后代 Prompt）
5. **数据迁移**（v1 dict → v2 list，自动备份 `prompts.json.v1.bak`）
6. **同级唯一命名**约束
7. **关闭时持久化**展开状态

**预估提交数：** ≈ 12 次小步骤 commit（参考各 Phase 末尾的 commit 步骤）

**关键原则：**
- TDD：每个 data_ops 函数先写测试再写实现
- DRY：路径解析、ensure_path、字符串转义统一在 data_ops
- YAGNI：不做拖拽预览高亮、不做自动清理回收站、不做撤销栈、不引入数据库
- 频繁 commit：每个步骤独立可回滚

**开发环境约定：** 所有 `python` / `pip` / `pyinstaller` 命令必须先 `conda activate PinPrompt`。

