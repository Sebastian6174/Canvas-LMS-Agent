from src.utils.helpers import resolve_html_links, build_course_files_map

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
