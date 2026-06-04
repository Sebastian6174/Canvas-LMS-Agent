from src.state import Activity, CourseStructure, Module
from src.nodes.analyst import _enrich_activity_unit_links
from src.utils.helpers import (
    resolve_html_links,
    build_course_files_map,
    build_home_page_nav_links,
    apply_home_page_nav_links,
    unit_intro_page_title,
    unit_materials_page_title,
    collect_unit_resources,
    build_unit_materials_page_body,
    activity_belongs_to_unit,
    activities_for_unit,
    resolve_canonical_module_name,
    canonical_unit_names_by_number,
)

def test_resolve_html_links():
    files = [
        {"id": 111, "filename": "Bannercurso.png", "display_name": "Bannercurso.png"},
        {"id": 222, "filename": "Boton_ForoDudas.png", "display_name": "Boton_ForoDudas.png"}
    ]
    
    files_map = build_course_files_map(files, "canvas.test", "999")
    
    # Test replacement of old template IDs
    html = '<img src="https://univallecolombia.instructure.com/courses/863/files/67711/preview" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67711">'
    resolved = resolve_html_links(html, files_map, "canvas.test", "999")
    
    assert "/files/111" in resolved
    assert "courses/999" in resolved
    assert "courses/863" not in resolved
    assert "67711" not in resolved

    # Test replacement of local/filename src
    html2 = '<img src="images/template/banner.png">'
    resolved2 = resolve_html_links(html2, files_map, "canvas.test", "999")
    assert "https://canvas.test/courses/999/files/111/preview" in resolved2


def test_apply_home_page_nav_links():
    nav = build_home_page_nav_links(
        course_id="999",
        domain="canvas.test",
        module_mapping={
            "Introducción al curso y ayuda": 10,
            "Unidad 1. El conflicto": 201,
            "Unidad 2. La negociación": 202,
        },
        course_module_names=["Unidad 1. El conflicto", "Unidad 2. La negociación"],
        agenda_page_url="agenda-de-actividades",
        forum_discussion_id=5426,
        intro_module_name="Introducción al curso y ayuda",
    )
    html = (
        '<p><a title="Foro" href="https://old.instructure.com/courses/863/discussion_topics/1">'
        '<img src="https://old.instructure.com/courses/863/files/67114/preview" alt="Boton Foro Dudas"></a></p>'
        '<p><a title="Agenda de Actividades" href="https://old.instructure.com/courses/863/pages/agenda-vieja">'
        '<img alt="Agenda de Actividades" src="agenda.png"></a></p>'
        '<p><a title="Unidad 1. El conflicto" href="https://old.instructure.com/courses/863/modules/4156" '
        'data-api-returntype="Module"><img src="Boton_U1.png" alt="Unidad 1"></a>'
        '<a title="Unidad 2" href="https://old.instructure.com/courses/863/modules/4161" '
        'data-api-returntype="Module"><img src="Boton_U2.png" alt="Unidad 2"></a></p>'
    )
    resolved = apply_home_page_nav_links(html, nav, "999", "canvas.test")

    assert "https://canvas.test/courses/999/discussion_topics/5426" in resolved
    assert "https://canvas.test/courses/999/pages/agenda-de-actividades" in resolved
    assert "https://canvas.test/courses/999/modules/201" in resolved
    assert "https://canvas.test/courses/999/modules/202" in resolved
    assert 'href="https://canvas.test/courses/999/discussion_topics/5426"' in resolved
    assert "courses/863/modules" not in resolved


def test_activities_for_unit_groups_by_module_name():
    activities = [
        Activity(
            name="Actividad 1. Tarea: A",
            description="d",
            duration=1,
            activity_type="Tarea",
            number=1,
            module_name="Unidad 1. El conflicto",
            related_learning_outcome="r",
            weight=0,
        ),
        Activity(
            name="Actividad 4. Tarea: B",
            description="d",
            duration=1,
            activity_type="Tarea",
            number=4,
            module_name="Unidad 2. La negociación",
            related_learning_outcome="r",
            weight=0,
        ),
    ]
    unit1 = activities_for_unit(activities, "Unidad 1. El conflicto")
    unit2 = activities_for_unit(activities, "Unidad 2. La negociación")
    assert [a.number for a in unit1] == [1]
    assert [a.number for a in unit2] == [4]


def test_activity_belongs_to_unit_by_number():
    unit = "Unidad 2. La negociación"
    assert activity_belongs_to_unit("Unidad 2", unit)
    assert activity_belongs_to_unit(unit, unit)
    assert not activity_belongs_to_unit("Unidad 1", unit)


def test_resolve_canonical_module_name():
    canonical = canonical_unit_names_by_number(
        [
            type("M", (), {"name": "Unidad 1. El conflicto"})(),
            type("M", (), {"name": "Unidad 2. La negociación"})(),
        ]
    )
    assert (
        resolve_canonical_module_name("Unidad 2", canonical)
        == "Unidad 2. La negociación"
    )


def test_unit_page_titles():
    assert unit_intro_page_title(2) == "Unidad 2 Introducción y Resultados de Aprendizaje"
    assert unit_materials_page_title(3) == "Unidad 3 Materiales de estudio"


def test_collect_unit_resources_deduplicates():
    activities = [
        Activity(
            name="Act 1",
            description="d",
            duration=1,
            activity_type="Tarea",
            evaluation_type="Formativa",
            related_learning_outcome="ra",
            weight=0,
            module_name="Unidad 1. Tema",
            resources=["Libro A", "Artículo B"],
        ),
        Activity(
            name="Act 2",
            description="d",
            duration=1,
            activity_type="Foro",
            evaluation_type="Formativa",
            related_learning_outcome="ra",
            weight=0,
            module_name="Unidad 1. Tema",
            resources=["Artículo B", "Video C"],
        ),
    ]
    resources = collect_unit_resources(activities, "Unidad 1. Tema")
    assert resources == ["Libro A", "Artículo B", "Video C"]


def test_build_unit_materials_page_body_includes_banner_and_list():
    body = build_unit_materials_page_body("<banner/>", ["Recurso 1"])
    assert "<banner/>" in body
    assert "<li>Recurso 1</li>" in body


def test_enrich_activity_unit_links_fills_missing_module_name():
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
            Module(
                name="Unidad 1. Tema",
                description="U1",
                activities=["Act 1"],
            )
        ],
        activities=[
            Activity(
                name="Act 1",
                description="d",
                duration=1,
                activity_type="Otros",
                related_learning_outcome="ra",
                weight=0,
            )
        ],
        schedule=[],
    )
    enriched = _enrich_activity_unit_links(structure)
    assert enriched.activities[0].module_name == "Unidad 1. Tema"
