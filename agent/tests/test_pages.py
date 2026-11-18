from src.activities.template import render_activity_html
from src.pages.agenda import build_agenda_html
from src.pages.alignment import build_alignment_html
from src.pages.credits import build_credits_html
from src.pages.home import build_home_html
from src.pages.html import CourseLinks, linkify, split_indicator, text_to_html
from src.pages.unit import build_unit_intro_html, build_unit_materials_html
from src.state import Activity, CourseStructure, Module
from src.utils.course_files import build_course_files_map, file_id_from_url

UNIT_1 = "Unidad 1. Inicio"
UNIT_2 = "Unidad 2. Cierre"


def _activity(number, name, unit, week, weight, hours, **extra):
    return Activity(
        number=number, name=name, module_name=unit, week=week, weight=weight, duration=hours,
        evaluation_type="Evaluativa" if weight else "Formativa", **extra,
    )


STRUCTURE = CourseStructure(
    name="Curso de Prueba",
    academic_program="Tecnología",
    academic_level="Tecnológico",
    credits=2,
    total_hours=20,
    program_url="https://drive.example/programa",
    teacher="Ana Pérez",
    description="Bienvenida.\n• Punto uno",
    learning_outcomes=["RA 1. Reconoce textos.", "RA 2. Escribe textos."],
    modules=[
        Module(number=1, name=UNIT_1, description="Presentación U1.", learning_outcomes=["RA 1"],
               indicators=["1.1 Distingue documentos.", "1.2 Identifica términos."]),
        Module(number=2, name=UNIT_2, learning_outcomes=["RA 2"], indicators=["IL 2. Redacta."]),
    ],
    activities=[
        _activity(1, "Actividad 1. Videoconferencia: Hola", UNIT_1, 1, 0, 3),
        _activity(2, "Actividad 2. Tarea: Ensayo", UNIT_1, 1, 40, 9,
                  resources=["Guía.pdf", "Lectura (https://ejemplo.org/l)"], description="Paso 1.\n• a\n• b"),
        _activity(3, "Actividad 3. Tarea: Informe", UNIT_2, 2, 60, 8),
    ],
)

FILES = build_course_files_map(
    [
        {"id": 10, "filename": "Bannercurso.png"},
        {"id": 11, "filename": "Boton_U1.png"},
        {"id": 12, "filename": "Ana Pérez.png"},
        {"id": 13, "filename": "Guía.pdf"},
    ],
    "canvas.test",
    "5",
)
LINKS = CourseLinks(FILES, "canvas.test", "5")


def test_text_to_html_groups_bullets_and_links():
    html = text_to_html("Intro con https://a.org\n• uno\n• dos (https://b.org)\nFinal")

    assert html.splitlines() == [
        '<p><span>Intro con <a href="https://a.org" target="_blank" rel="noopener">https://a.org</a></span></p>',
        '<ul><li>uno</li><li><a href="https://b.org" target="_blank" rel="noopener">dos</a></li></ul>',
        "<p><span>Final</span></p>",
    ]
    assert linkify("a < b") == "a &lt; b"


def test_split_indicator_codes():
    assert split_indicator("1.1 Distingue.") == ("1.1", "Distingue.")
    assert split_indicator("IL 2. Describe.") == ("2", "Describe.")
    assert split_indicator("Sin código") == ("", "Sin código")


def test_agenda_groups_units_and_weeks_with_totals():
    html = build_agenda_html(STRUCTURE, LINKS)

    assert 'src="https://canvas.test/courses/5/files/10/preview"' in html
    assert '<td style="text-align: center;" rowspan="2">1</td><td style="text-align: center;" rowspan="2">1</td>' in html
    assert html.index("Actividad 1.") < html.index("Actividad 2.") < html.index("Actividad 3.")
    assert "<strong>20</strong>" in html and "<strong>100%</strong>" in html


def test_alignment_lists_outcomes_indicators_and_activities_per_unit():
    html = build_alignment_html(STRUCTURE, LINKS)

    assert 'rowspan="2">R.A. 1</td>' in html
    assert "1.1<br />1.2" in html
    assert "<p><span>Distingue documentos.</span></p><p><span>Identifica términos.</span></p>" in html
    assert 'rowspan="1">R.A. 2</td>' in html
    assert html.count("Evaluativa") == 2 and html.count("Formativa") == 1


def test_home_page_has_fact_sheet_navigation_and_teacher():
    html = build_home_html(STRUCTURE, "Biografía.", LINKS, {UNIT_1: 101, UNIT_2: 102}, "agenda-de-actividades", 77)

    assert "2 cr&eacute;ditos - 20 horas" in html
    assert "<p style=\"margin-left: 30px;\">Ninguno</p>" in html
    assert 'href="https://drive.example/programa"' in html
    assert "<li><strong>RA1. </strong>Reconoce textos.</li>" in html
    assert 'href="https://canvas.test/courses/5/discussion_topics/77"' in html
    assert 'href="https://canvas.test/courses/5/pages/agenda-de-actividades"' in html
    # La unidad 1 tiene imagen de botón; la 2 no, así que se enlaza con su nombre.
    assert 'files/11/preview" alt="Unidad 1"' in html
    assert "<strong>Unidad 2. Cierre</strong></a>" in html
    assert 'files/12/preview" alt="Profesor Ana Pérez"' in html
    assert "<p><span>Biografía.</span></p>" in html


def test_credits_page_includes_teacher_and_production():
    html = build_credits_html("Ana Pérez", "Biografía.", LINKS)

    assert "Profesor autor" in html and "Ana Pérez" in html and "DINTEV" in html


def test_unit_pages_use_presentation_outcomes_and_resources():
    intro = build_unit_intro_html(STRUCTURE, STRUCTURE.modules[0], LINKS)
    materials = build_unit_materials_html(STRUCTURE, STRUCTURE.modules[0], LINKS)

    assert "<h2>Unidad 1. Inicio</h2>" in intro and "Presentación U1." in intro
    assert "<li>RA 1. Reconoce textos.</li>" in intro and "<li>1.1 Distingue documentos.</li>" in intro
    assert 'href="https://canvas.test/courses/5/files/13?wrap=1"' in materials
    assert '<a href="https://ejemplo.org/l" target="_blank" rel="noopener">Lectura</a>' in materials


def test_activity_template_matches_example_structure():
    html = render_activity_html(STRUCTURE.activities[1], LINKS)

    assert html.startswith('<h2><img id="13808"')
    assert "</strong></span>&nbsp;</span>40%</p>" in html
    assert "    <p><span>Paso 1.</span></p>\n    <ul><li>a</li><li>b</li></ul>" in html
    # Sin forma de entrega en el estado se usa la habitual para el tipo.
    assert "<p>Desarrolle la actividad según las indicaciones y entréguela en Canvas.</p>" in html
    assert html.count("Semana No. 1") == 2
    assert '<td style="text-align: center; border-style: dotted;">9</td>' in html


def test_file_id_from_url():
    assert file_id_from_url("https://x/courses/1/files/42/preview") == "42"
    assert file_id_from_url("https://x/courses/1/files/42?wrap=1") == "42"
    assert file_id_from_url(None) is None
