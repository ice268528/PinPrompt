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
