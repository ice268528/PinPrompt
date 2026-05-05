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
