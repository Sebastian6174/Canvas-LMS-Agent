from src.tools import canvas_tools
from src.tools.canvas_api import (
    create_course,
    import_base_course_content,
    create_module,
    list_modules,
    create_assignment,
    add_item_to_module,
    update_course_home_page,
    create_page,
    create_discussion_topic,
    set_module_position,
)

EXPECTED_TOOLS = [
    create_course,
    import_base_course_content,
    create_module,
    list_modules,
    create_assignment,
    add_item_to_module,
    update_course_home_page,
    create_page,
    create_discussion_topic,
    set_module_position,
]


def test_canvas_tools_includes_all_api_tools():
    assert len(canvas_tools) == len(EXPECTED_TOOLS)
    for tool in EXPECTED_TOOLS:
        assert tool in canvas_tools


def test_canvas_tools_are_langchain_tools():
    for tool in canvas_tools:
        assert hasattr(tool, "invoke")
        assert callable(tool.invoke)
