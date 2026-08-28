from src.activity_types import (
    normalize_activity_type,
    format_activity_display_name,
    infer_evaluation_type,
    ACTIVITY_TYPE_DEFAULT,
    wrap_activity_description_html,
)
from src.nodes.analyst import _enrich_activity_titles_and_types
from src.state import Activity, CourseStructure, Module


def test_normalize_activity_type_defaults_to_otros():
    assert normalize_activity_type("desconocido") == ACTIVITY_TYPE_DEFAULT
    assert normalize_activity_type("taller") == ACTIVITY_TYPE_DEFAULT
    assert normalize_activity_type(None) == ACTIVITY_TYPE_DEFAULT


def test_format_activity_display_name():
    assert (
        format_activity_display_name(2, "Foro", "Debate sobre el tema")
        == "Actividad 2. Foro: Debate sobre el tema"
    )
    prefixed = "Actividad 2. Foro: Debate sobre el tema"
    assert format_activity_display_name(2, "Foro", prefixed) == prefixed


def test_infer_evaluation_type_from_weight():
    assert infer_evaluation_type(0) == "Formativa"
    assert infer_evaluation_type(20) == "Evaluativa"
    assert infer_evaluation_type(0, "Evaluativa") == "Evaluativa"


def test_enrich_activity_titles_and_types_updates_modules_and_schedule():
    structure = CourseStructure(
        name="Curso",
        academic_program="Prog",
        semester=1,
        academic_level="Pregrado",
        credits=3,
        prerequisites=[],
        teacher="Docente",
        description="Desc",
        learning_outcomes=["RA1"],
        modules=[
            Module(name="Unidad 1", description="U1", activities=["Tarea uno"]),
        ],
        activities=[
            Activity(
                name="Tarea uno",
                description="d",
                duration=4,
                activity_type="Tarea",
                related_learning_outcome="RA1",
                weight=10,
            )
        ],
        schedule=[],
    )
    enriched = _enrich_activity_titles_and_types(structure)
    assert enriched.activities[0].name == "Actividad 1. Tarea: Tarea uno"
    assert enriched.modules[0].activities[0] == "Actividad 1. Tarea: Tarea uno"
    assert enriched.activities[0].evaluation_type == "Evaluativa"


def test_wrap_activity_description_includes_type_guide():
    html = wrap_activity_description_html(
        activity_type="Quiz",
        description="Contenido",
        related_learning_outcome="RA1",
        weight=5,
    )
    assert "Tipo de actividad" in html
    assert "Contenido" in html
