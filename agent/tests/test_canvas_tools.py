from src.tools import canvas_tools
from src.tools.canvas_api import (
    create_course,
    import_base_course_files,
    create_module,
    list_modules,
    publish_module,
    create_assignment,
    list_assignments,
    list_assignment_groups,
    enable_assignment_group_weights,
    create_or_update_assignment_group,
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
    publish_module,
    create_assignment,
    list_assignments,
    list_assignment_groups,
    enable_assignment_group_weights,
    create_or_update_assignment_group,
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


def test_create_module_publishes_module(monkeypatch):
    from src.tools import canvas_api

    captured = {}

    def fake_request(method, endpoint, data=None, custom_course_id=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["payload"] = data
        captured["course_id"] = custom_course_id
        return {"id": 10}

    monkeypatch.setattr(canvas_api, "_canvas_request", fake_request)

    result = canvas_api.create_module.invoke({"name": "Unidad 1", "course_id": "100"})

    assert result == {"id": 10}
    assert captured["method"] == "POST"
    assert captured["endpoint"] == "/modules"
    assert captured["course_id"] == "100"
    assert captured["payload"]["module"]["name"] == "Unidad 1"
    assert captured["payload"]["module"]["published"] is True


def test_add_subheader_to_module_uses_text_only_payload(monkeypatch):
    from src.tools import canvas_api

    requests = []

    def fake_request(method, endpoint, data=None, custom_course_id=None):
        requests.append((method, endpoint, data, custom_course_id))
        if method == "GET":
            return []
        return {"id": 99}

    monkeypatch.setattr(canvas_api, "_canvas_request", fake_request)

    result = canvas_api.add_item_to_module.invoke({
        "module_id": 10,
        "title": "Actividades",
        "type": "SubHeader",
        "course_id": "100",
    })

    assert result == {"id": 99}
    post_payload = requests[-1][2]
    assert post_payload == {"module_item": {"title": "Actividades", "type": "SubHeader"}}


def test_enable_assignment_group_weights_updates_course(monkeypatch):
    from src.tools import canvas_api

    captured = {}

    def fake_request(method, endpoint, data=None, custom_course_id=None):
        captured["method"] = method
        captured["endpoint"] = endpoint
        captured["payload"] = data
        captured["course_id"] = custom_course_id
        return {"id": custom_course_id}

    monkeypatch.setattr(canvas_api, "_canvas_request", fake_request)

    result = canvas_api.enable_assignment_group_weights.invoke({"course_id": "100"})

    assert result == {"id": "100"}
    assert captured["method"] == "PUT"
    assert captured["endpoint"] == "/courses/100"
    assert captured["course_id"] == "100"
    assert captured["payload"] == {"course": {"apply_assignment_group_weights": True}}


def test_create_assignment_sends_assignment_group_id(monkeypatch):
    from src.tools import canvas_api

    requests = []

    def fake_request(method, endpoint, data=None, custom_course_id=None):
        requests.append((method, endpoint, data, custom_course_id))
        if method == "GET":
            return []
        return {"id": 10}

    monkeypatch.setattr(canvas_api, "_canvas_request", fake_request)

    result = canvas_api.create_assignment.invoke({
        "name": "Actividad 1",
        "description": "<p>Contenido</p>",
        "points_possible": 5.0,
        "assignment_group_id": 7,
        "course_id": "100",
    })

    assert result == {"id": 10}
    post_payload = requests[-1][2]
    assert post_payload["assignment"]["points_possible"] == 5.0
    assert post_payload["assignment"]["assignment_group_id"] == 7
    assert post_payload["assignment"]["grading_type"] == "points"
    assert post_payload["assignment"]["omit_from_final_grade"] is False


def test_create_or_update_assignment_group_updates_existing_group(monkeypatch):
    from src.tools import canvas_api

    requests = []

    def fake_request(method, endpoint, data=None, custom_course_id=None):
        requests.append((method, endpoint, data, custom_course_id))
        if method == "GET":
            return [{"id": 3, "name": "Evaluativas 10% c/u"}]
        return {"id": 3}

    monkeypatch.setattr(canvas_api, "_canvas_request", fake_request)

    result = canvas_api.create_or_update_assignment_group.invoke({
        "name": "Evaluativas 10% c/u",
        "group_weight": 20.0,
        "course_id": "100",
    })

    assert result == {"id": 3}
    assert requests[-1][0] == "PUT"
    assert requests[-1][1] == "/assignment_groups/3"
    assert requests[-1][2] == {
        "name": "Evaluativas 10% c/u",
        "group_weight": 20.0,
    }
