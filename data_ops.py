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
