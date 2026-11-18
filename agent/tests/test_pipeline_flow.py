"""Recorrido completo del grafo con el LLM, Google Docs y Canvas simulados."""

import itertools

import pytest

from config import config
from src.graph import create_graph
from src.pipeline import initial_state
from src.tools import canvas_api
from tests.fakes import FakeAnalystLLM
from tests.test_analysis import TABS

canvas_payloads = []


@pytest.fixture
def canvas_calls(monkeypatch):
    calls = []
    canvas_payloads.clear()
    ids = itertools.count(1)

    def fake_request(method, endpoint, data=None, custom_course_id=None):
        calls.append((method, endpoint))
        canvas_payloads.append((method, endpoint, data))
        if method == "GET":
            return []
        new_id = next(ids)
        return {"id": new_id, "url": f"pagina-{new_id}"}

    monkeypatch.setattr(canvas_api, "_canvas_request", fake_request)
    monkeypatch.setattr("src.nodes.analyst.read_google_doc", lambda doc_id: TABS)
    monkeypatch.setattr(config, "course_id", "999")
    monkeypatch.setattr(config, "create_new_course", False)
    monkeypatch.setattr(config, "base_course_id", "")
    monkeypatch.setattr(config, "teacher_doc", "")
    monkeypatch.setattr(config, "get_llm", FakeAnalystLLM)
    return calls


def _posted(endpoint_suffix):
    return [data for method, endpoint, data in canvas_payloads if method == "POST" and endpoint.endswith(endpoint_suffix)]


def test_pipeline_runs_end_to_end(canvas_calls):
    final = create_graph().invoke(initial_state("doc"))

    assert final["errors"] == []
    assert final["is_valid"] is True
    assert final["canvas_course_id"] == "999"
    assert list(final["module_mapping"]) == ["Introducción al curso y ayuda", "Unidad 1. Inicio", "Créditos"]
    assert final["agenda_page_url"] and final["alignment_page_url"] and final["credits_page_url"]
    assert final["forum_discussion_id"]
    assert list(final["canvas_assignment_ids"]) == [
        "Actividad 1. Videoconferencia: Bienvenida",
        "Actividad 2. Tarea: Ensayo",
    ]
    assert final["syllabus_page_url"] == "/courses/999/assignments/syllabus"
    assert ("PUT", "/front_page") in canvas_calls

    assignments = [data["assignment"] for data in _posted("/assignments")]
    assert [a["name"] for a in assignments] == list(final["canvas_assignment_ids"])
    assert [a["position"] for a in assignments] == [1, 2]
    essay = assignments[1]["description"]
    assert "Primer paso." in essay and "Suba el ensayo en PDF." in essay and "Semana No. 2" in essay

    # Las actividades van después de las dos páginas y el encabezado de la unidad.
    activity_items = [d["module_item"] for d in _posted("/items") if d["module_item"]["type"] == "Assignment"]
    assert [item["position"] for item in activity_items] == [4, 5]

    # Rúbrica asociada a la actividad evaluativa.
    rubrics = _posted("/rubrics")
    assert len(rubrics) == 1 and rubrics[0]["rubric"]["title"] == "Actividad 2. Tarea: Ensayo"


def test_home_page_failure_is_reported_once(monkeypatch, canvas_calls):
    original = canvas_api._canvas_request

    def failing_front_page(method, endpoint, data=None, custom_course_id=None):
        if endpoint == "/front_page":
            return {"error": "boom", "status_code": 500}
        return original(method, endpoint, data, custom_course_id)

    monkeypatch.setattr(canvas_api, "_canvas_request", failing_front_page)

    final = create_graph().invoke(initial_state("doc"))

    assert final["errors"] == ["Error en page_creator"]
    assert not _posted("/assignments")
