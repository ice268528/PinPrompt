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


def next_trash_id(trash):
    """计算下一个可用的 trash 条目 id。空列表返回 1，否则返回 max(id)+1。"""
    if not trash:
        return 1
    return max(t["id"] for t in trash) + 1


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
