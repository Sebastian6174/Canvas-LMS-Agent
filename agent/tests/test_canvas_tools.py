from src.tools import canvas_tools
from src.tools.canvas_api import (
    create_course,
    import_base_course_files,
    create_module,
    list_modules,
    create_assignment,
    list_assignments,
    delete_assignment,
    create_or_update_assignment_rubric,
    add_item_to_module,
    update_course_home_page,
    update_course_syllabus,
    create_page,
    create_discussion_topic,
    set_module_position,
    list_course_files,
)

EXPECTED_TOOLS = [
    create_course,
    import_base_course_files,
    create_module,
    list_modules,
    create_assignment,
    list_assignments,
    delete_assignment,
    create_or_update_assignment_rubric,
    add_item_to_module,
    update_course_home_page,
    update_course_syllabus,
    create_page,
    create_discussion_topic,
    set_module_position,
    list_course_files,
]


def test_canvas_tools_includes_all_api_tools():
    assert len(canvas_tools) == len(EXPECTED_TOOLS)
    for tool in EXPECTED_TOOLS:
        assert tool in canvas_tools


def test_canvas_tools_are_langchain_tools():
    for tool in canvas_tools:
        assert hasattr(tool, "invoke")
        assert callable(tool.invoke)


def test_import_base_course_files_selects_only_files(monkeypatch):
    from src.tools import canvas_api

    monkeypatch.setattr(
        canvas_api,
        "_list_all_course_files",
        lambda _cid: [{"id": 10}, {"id": 20}],
    )
    captured = {}

    def fake_request(method, endpoint, data=None, custom_course_id=None):
        if method == "POST" and endpoint == "/content_migrations":
            captured["payload"] = data
            return {"id": 99, "workflow_state": "running"}
        if method == "GET" and "/content_migrations/" in endpoint:
            return {"workflow_state": "completed"}
        return {}

    monkeypatch.setattr(canvas_api, "_canvas_request", fake_request)

    result = canvas_api.import_base_course_files.invoke({
        "target_course_id": "100",
        "source_course_id": "862",
    })

    assert result.get("workflow_state") == "completed"
    assert captured["payload"]["select"] == {"files": [10, 20]}
    assert "modules" not in captured["payload"].get("select", {})


def test_update_course_syllabus_updates_course_body(monkeypatch):
    from src.tools import canvas_api

    captured = {}

    def fake_request(method, endpoint, data=None, custom_course_id=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["payload"] = data
        captured["course_id"] = custom_course_id
        return {"id": custom_course_id}

    monkeypatch.setattr(canvas_api, "_canvas_request", fake_request)

    result = canvas_api.update_course_syllabus.invoke(
        {
            "body": "<h2>Programa del curso</h2>",
            "course_id": "100",
            "make_default_view": True,
            "show_course_summary": True,
        }
    )

    assert result == {"id": "100"}
    assert captured["method"] == "PUT"
    assert captured["endpoint"] == "/courses/100"
    assert captured["course_id"] == "100"
    assert captured["payload"]["course"]["syllabus_body"] == "<h2>Programa del curso</h2>"
    assert captured["payload"]["course"]["default_view"] == "syllabus"
    assert captured["payload"]["course"]["syllabus_course_summary"] is True
