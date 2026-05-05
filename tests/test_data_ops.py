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

