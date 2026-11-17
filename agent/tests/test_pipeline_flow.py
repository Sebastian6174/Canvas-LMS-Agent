"""Recorrido completo del grafo con el LLM, Google Docs y Canvas simulados."""

import itertools

import pytest

from config import config
from src.activities.content import ActivityContent
from src.graph import create_graph
from src.pipeline import initial_state
from src.state import Activity, CourseStructure, Module, ScheduleItem
from src.tools import canvas_api


def _structure() -> CourseStructure:
    return CourseStructure(
        name="Curso de Prueba",
        academic_program="Ingenieria",
        semester=1,
        academic_level="Pregrado",
        credits=3,
        prerequisites=[],
        teacher="Docente",
        description="Descripcion",
        learning_outcomes=["RA1"],
        modules=[Module(name="Unidad 1. Inicio", description="", activities=["Ensayo"])],
        activities=[
            Activity(
                name="Ensayo",
                description="Escribir un ensayo",
                duration=2,
                activity_type="Tarea",
                evaluation_type="Evaluativa",
                related_learning_outcome="RA1",
                weight=100,
                module_name="Unidad 1. Inicio",
            )
        ],
        schedule=[ScheduleItem(week=3, activity_name="Ensayo", time_commitment="2 horas")],
    )


class _Structured:
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, messages):
        if self.schema is ActivityContent:
            return ActivityContent(
                description_html="<p><span>Redacte el ensayo.</span></p>",
                delivery_form="Envíe el documento en Canvas.",
                resources=["Lectura 1"],
            )
        return _structure()


class _FakeLLM:
    def __init__(self, fail_on: str | None = None):
        self.fail_on = fail_on

    def with_structured_output(self, schema):
        return _Structured(schema)

    def invoke(self, messages):
        if self.fail_on and self.fail_on in messages[0].content:
            raise RuntimeError("boom")
        return type("Response", (), {"content": "```html<p>contenido</p>```"})()


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
    monkeypatch.setattr(
        "src.nodes.analyst.read_google_doc",
        lambda doc_id: [{"title": "Programa", "content": "contenido del curso"}],
    )
    monkeypatch.setattr(config, "course_id", "999")
    monkeypatch.setattr(config, "create_new_course", False)
    monkeypatch.setattr(config, "base_course_id", "")
    monkeypatch.setattr(config, "teacher_doc", "")
    return calls


def test_pipeline_runs_end_to_end(monkeypatch, canvas_calls):
    monkeypatch.setattr(config, "get_llm", lambda: _FakeLLM())

    final = create_graph().invoke(initial_state("doc"))

    assert final["errors"] == []
    assert final["is_valid"] is True
    assert final["canvas_course_id"] == "999"
    assert set(final["module_mapping"]) == {
        "Introducción al curso y ayuda",
        "Créditos",
        "Unidad 1. Inicio",
    }
    assert final["agenda_page_url"] and final["alignment_page_url"] and final["credits_page_url"]
    assert final["forum_discussion_id"]
    assert list(final["canvas_assignment_ids"]) == ["Actividad 1. Tarea: Ensayo"]
    assert final["syllabus_page_url"] == "/courses/999/assignments/syllabus"
    assert ("PUT", "/front_page") in canvas_calls
    assert ("POST", "/assignments") in canvas_calls
    description = next(data for method, endpoint, data in canvas_payloads if endpoint == "/assignments")
    assert "Redacte el ensayo." in description["assignment"]["description"]
    assert "Envíe el documento en Canvas." in description["assignment"]["description"]
    assert "Semana No. 3" in description["assignment"]["description"]


def test_home_page_failure_is_reported_once(monkeypatch, canvas_calls):
    monkeypatch.setattr(config, "get_llm", lambda: _FakeLLM(fail_on="página de inicio"))

    final = create_graph().invoke(initial_state("doc"))

    assert final["errors"] == ["Error generando HTML con LLM: boom"]
    assert ("POST", "/assignments") not in canvas_calls
