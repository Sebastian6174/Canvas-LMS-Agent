from src.nodes.syllabus_creator import syllabus_creator_node
from src.state import Activity, CourseStructure, Module, Rubric, ScheduleItem


def test_syllabus_creator_updates_canvas_syllabus_with_ordered_activities(monkeypatch):
    structure = CourseStructure(
        name="Curso de Prueba",
        academic_program="Ingenieria",
        semester=1,
        academic_level="Pregrado",
        credits=3,
        prerequisites=[],
        teacher="Docente Uno",
        description="Descripcion del curso",
        learning_outcomes=["RA1", "RA2"],
        modules=[
            Module(name="Unidad 1. Base", description="U1", activities=["Actividad 1", "Actividad 2"])
        ],
        activities=[
            Activity(
                name="Actividad 2",
                description="Segunda actividad",
                duration=4,
                activity_type="Tarea",
                evaluation_type="Evaluativa",
                number=2,
                rubric="Rubrica N. 1",
                related_learning_outcome="RA2",
                weight=30,
                module_name="Unidad 1. Base",
            ),
            Activity(
                name="Actividad 1",
                description="Primera actividad",
                duration=2,
                activity_type="Foro",
                evaluation_type="Formativa",
                number=1,
                rubric=None,
                related_learning_outcome="RA1",
                weight=0,
                module_name="Unidad 1. Base",
            ),
        ],
        schedule=[
            ScheduleItem(week=2, activity_name="Actividad 2", time_commitment="4 horas"),
            ScheduleItem(week=1, activity_name="Actividad 1", time_commitment="2 horas"),
        ],
        rubrics=[Rubric(name="Rubrica N. 1", criteria=[])],
    )

    captured = {}

    def mock_update_course_syllabus(self, kwargs):
        captured.update(kwargs)
        return {"id": 123}

    monkeypatch.setattr(
        "src.nodes.syllabus_creator.update_course_syllabus",
        type("T", (), {"invoke": mock_update_course_syllabus})(),
    )

    result = syllabus_creator_node(
        {
            "course_structure": structure,
            "canvas_course_id": "canvas_123",
            "errors": [],
            "course_files_map": {},
        }
    )

    assert result["errors"] == []
    assert result["syllabus_page_url"] == "/courses/canvas_123/assignments/syllabus"
    assert captured["course_id"] == "canvas_123"
    assert captured["make_default_view"] is False
    assert captured["show_course_summary"] is True
    assert "Programa del curso" in captured["body"]
    assert "generada automaticamente por Canvas" in captured["body"]
    assert "Actividad 1" not in captured["body"]
    assert "Actividad 2" not in captured["body"]
    assert "<ol" not in captured["body"]
    assert "<table" not in captured["body"]
