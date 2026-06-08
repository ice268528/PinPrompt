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
