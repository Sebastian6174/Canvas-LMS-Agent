from config import config
from src.nodes.analyst import analyst_node
from src.nodes.rubrics_creator import rubrics_creator_node
from src.state import Activity, CourseStructure, Module, Rubric, RubricCriterion, ScheduleItem


class MockStructuredLLM:
    def __init__(self, return_value):
        self.return_value = return_value

    def invoke(self, messages):
        return self.return_value


class MockLLM:
    def __init__(self, return_value):
        self.return_value = return_value

    def with_structured_output(self, schema):
        return MockStructuredLLM(self.return_value)


def test_rubrics_workflow(monkeypatch):
    mock_rubric = Rubric(
        name="Rubrica N. 1",
        criteria=[
            RubricCriterion(
                name="Criterio 1: Calidad",
                points=20.0,
                excelente="Trabajo excelente",
                en_desarrollo="Trabajo en desarrollo",
                basico="Trabajo basico",
                insuficiente="Trabajo insuficiente",
            )
        ],
    )

    mock_structure = CourseStructure(
        name="Curso de Prueba",
        academic_program="Ingenieria",
        semester=1,
        academic_level="Pregrado",
        credits=3,
        prerequisites=[],
        teacher="Profesor de Prueba",
        description="Descripcion del curso",
        learning_outcomes=["RA1"],
        modules=[
            Module(name="Unidad 1. Introduccion", description="U1 desc", activities=["Actividad 3"])
        ],
        activities=[
            Activity(
                name="Actividad 3",
                description="Hacer un reel sobre el conflicto",
                duration=10,
                activity_type="Otros",
                evaluation_type="Evaluativa",
                related_learning_outcome="RA1",
                weight=20.0,
                module_name="Unidad 1. Introduccion",
                rubric="Rubrica N. 1",
            )
        ],
        schedule=[
            ScheduleItem(week=1, activity_name="Actividad 3", time_commitment="10 horas")
        ],
        rubrics=[mock_rubric],
    )

    monkeypatch.setattr(
        "src.nodes.analyst.read_google_doc",
        lambda doc_id: [
            {"title": "1. INFO", "content": "algun contenido"},
            {"title": "No1", "content": "tabla de rubrica"},
        ],
    )

    monkeypatch.setattr(config, "get_llm", lambda: MockLLM(mock_structure))

    analyst_result = analyst_node(
        {
            "doc_id": "mock_doc_id",
            "course_structure": None,
            "canvas_course_id": None,
            "module_mapping": None,
            "teacher_info": None,
            "is_valid": False,
            "errors": [],
        }
    )

    assert analyst_result["is_valid"] is True
    assert analyst_result["errors"] == []

    created_rubrics = []

    def mock_list_assignments(self, kwargs):
        return []

    def mock_create_or_update_assignment_rubric(self, kwargs):
        created_rubrics.append(kwargs)
        return {"rubric": {"id": 456}, "rubric_association": {"id": 789}}

    monkeypatch.setattr(
        "src.nodes.rubrics_creator.list_assignments",
        type("T", (), {"invoke": mock_list_assignments})(),
    )
    monkeypatch.setattr(
        "src.nodes.rubrics_creator.create_or_update_assignment_rubric",
        type("T", (), {"invoke": mock_create_or_update_assignment_rubric})(),
    )

    creator_result = rubrics_creator_node(
        {
            **analyst_result,
            "canvas_course_id": "canvas_123",
            "canvas_assignment_ids": {"Actividad 3": 333},
        }
    )

    assert creator_result["errors"] == []
    assert len(created_rubrics) == 1
    assert created_rubrics[0]["title"] == "Actividad 3"
    assert created_rubrics[0]["assignment_id"] == 333
    assert created_rubrics[0]["course_id"] == "canvas_123"
    assert created_rubrics[0]["use_for_grading"] is True
