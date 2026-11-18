from src.nodes.rubrics_creator import rubrics_creator_node
from src.state import (
    Activity,
    CourseStructure,
    Module,
    Rubric,
    RubricCriterion,
    ScheduleItem,
)


def test_rubrics_creator_skips_formative_activities(monkeypatch):
    structure = CourseStructure(
        name="Curso de Prueba",
        academic_program="Ingenieria",
        semester=1,
        academic_level="Pregrado",
        credits=3,
        prerequisites=[],
        teacher="Profesor de Prueba",
        description="Descripcion del curso",
        learning_outcomes=["RA1"],
        modules=[Module(name="Unidad 1", description="U1", activities=[])],
        activities=[
            Activity(
                name="Actividad formativa",
                description="Participar",
                duration=2,
                activity_type="Foro",
                evaluation_type="Formativa",
                related_learning_outcome="RA1",
                weight=0,
                module_name="Unidad 1",
                rubric="Rubrica formativa",
            )
        ],
        schedule=[],
        rubrics=[
            Rubric(
                name="Rubrica formativa",
                criteria=[
                    RubricCriterion(
                        name="Criterio",
                        points=5,
                        excelente="Excelente",
                        en_desarrollo="En desarrollo",
                        basico="Basico",
                        insuficiente="Insuficiente",
                    )
                ],
            )
        ],
    )
    created_rubrics = []

    monkeypatch.setattr(
        "src.nodes.rubrics_creator.list_assignments",
        type("T", (), {"invoke": lambda self, kwargs: [{"id": 1, "name": "Actividad formativa"}]})(),
    )
    monkeypatch.setattr(
        "src.nodes.rubrics_creator.create_or_update_assignment_rubric",
        type("T", (), {"invoke": lambda self, kwargs: created_rubrics.append(kwargs) or {"id": 1}})(),
    )

    result = rubrics_creator_node(
        {
            "course_structure": structure,
            "canvas_course_id": "canvas_123",
            "canvas_assignment_ids": {"Actividad formativa": 1},
            "errors": [],
        }
    )

    assert result["errors"] == []
    assert created_rubrics == []
