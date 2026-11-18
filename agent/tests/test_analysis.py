from src.analysis.analyzer import analyze_course
from src.analysis.assembly import build_course_structure, clean_activity_title, unit_name
from src.analysis.extraction import _scrub
from src.analysis.schemas import ActivityDetail, CourseOverview, ModuleInfo, ScheduleRow
from src.analysis.sections import DocumentSections, find_activity_block, labeled_cell
from tests.fakes import BIO, RUBRIC, FakeAnalystLLM


def _table(rows):
    return {"type": "table", "rows": rows}


ACTIVITY_TABLE = _table([
    ["2. Tarea: Ensayo", "", ""],
    ["Descripción:", "Primer paso.\n• Viñeta", ""],
    ["Recursos:", "• Lectura 1", ""],
    ["Evaluación", "Si", "Rúbrica: Si"],
])

TABS = [
    {"title": "1. INFORMACIÓN BÁSICA", "blocks": [_table([["Curso", "Curso de Prueba"]])]},
    {"title": "2. ALINEACIÓN RA + AF + AE", "blocks": [_table([["RA. 1.", "Reconoce los textos."]])]},
    {"title": "3. SECUENCIA", "blocks": [_table([["Semana", "Actividad"], ["1", "1. Videoconferencia: Bienvenida"]])]},
    {"title": "4. ACTIVIDADES", "blocks": [
        _table([["1. Videoconferencia: Bienvenida", ""], ["Recursos:", "No aplica"]]),
        ACTIVITY_TABLE,
    ]},
    {"title": "5. RUBRICAS", "blocks": [_table([["Actividad No. 2", "Rúbrica de evaluación: Ensayo"]])]},
]


def test_sections_are_classified_by_tab_title():
    sections = DocumentSections(TABS)

    assert all(sections.has(name) for name in ("info", "alignment", "sequence", "activities", "rubrics"))
    assert "Curso de Prueba" in sections.text("info")
    assert "Bienvenida" not in sections.text("info")
    assert len(sections.tables("rubrics")) == 1


def test_missing_section_falls_back_to_full_document():
    sections = DocumentSections([{"title": "Documento", "blocks": TABS[0]["blocks"]}])

    assert sections.text("sequence") == sections.full_text()


def test_activity_table_found_by_number_and_description_taken_literally():
    tables = DocumentSections(TABS).tables("activities")
    block = find_activity_block(tables, 2, "Ensayo")

    assert block is ACTIVITY_TABLE
    assert labeled_cell(block, "Descripción") == "Primer paso.\n• Viñeta"


def test_scrub_removes_placeholders_and_br():
    assert _scrub({"a": "string", "b": ["x", "None"], "c": "uno <br> dos"}) == {"a": "", "b": ["x"], "c": "uno\ndos"}


def test_unit_and_title_cleanup():
    assert unit_name(2, "Nombre del Módulo 2. Comunicaciones sin enredos (Semanas 3 y 4)") == "Unidad 2. Comunicaciones sin enredos"
    assert unit_name(1, "Módulo 1: ¿Qué dicen los documentos?") == "Unidad 1. ¿Qué dicen los documentos?"
    assert clean_activity_title("9. Tarea: “Hay que planificar”", "Tarea") == "Hay que planificar"


def test_analyzer_orders_activities_by_sequence_number_and_links_rubric():
    llm = FakeAnalystLLM()
    teacher_tabs = [{"title": "Perfil", "blocks": [{"type": "paragraph", "text": "Bio"}]}]

    structure, bio, warnings = analyze_course(llm, TABS, teacher_tabs, max_workers=1)

    assert [a.name for a in structure.activities] == [
        "Actividad 1. Videoconferencia: Bienvenida",
        "Actividad 2. Tarea: Ensayo",
    ]
    first, second = structure.activities
    assert (first.evaluation_type, first.weight, first.duration, first.week) == ("Formativa", 0, 3, 1)
    assert (second.evaluation_type, second.weight, second.duration, second.week) == ("Evaluativa", 100, 9, 2)
    # La descripción de la actividad 2 sale literal de su tabla; la 1 no tiene celda de descripción.
    assert second.description == "Primer paso.\n• Viñeta"
    assert second.delivery_form == "Suba el ensayo en PDF."
    assert second.rubric == "Rúbrica - Actividad 2. Tarea: Ensayo"
    assert first.rubric is None
    assert [r.name for r in structure.rubrics] == [second.rubric]

    unit = structure.modules[0]
    assert unit.name == "Unidad 1. Inicio"
    assert unit.activities == [first.name, second.name]
    assert all(a.module_name == unit.name for a in structure.activities)
    assert structure.learning_outcomes == ["RA 1. Reconoce los textos."]
    assert structure.prerequisites == []
    assert structure.total_hours == 12
    assert bio == BIO
    assert warnings == []


def test_assembly_warns_on_weights_and_unmatched_rubric():
    overview = CourseOverview(name="C", academic_program="P")
    rows = [ScheduleRow(number=1, activity_type="Tarea", name="Uno", module_number=1, week=1,
                        evaluation_type="A. Evaluativa", weight=30)]
    stray = RUBRIC.model_copy(update={"activity_number": 9, "activity_title": "Algo totalmente distinto"})

    structure, warnings = build_course_structure(
        overview, [ModuleInfo(number=1, title="Uno")], rows, [ActivityDetail(description="d", delivery_form="x")], [stray]
    )

    assert structure.activities[0].rubric is None
    assert any("30 %" in w for w in warnings)
    assert any("no se pudo asociar" in w for w in warnings)
