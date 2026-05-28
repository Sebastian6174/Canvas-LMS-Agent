from src.utils.helpers import (
    resolve_html_links,
    build_course_files_map,
    build_home_page_nav_links,
    apply_home_page_nav_links,
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
