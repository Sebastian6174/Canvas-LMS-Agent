from config import config
from src.nodes.base import resolve_course_id
from src.pages.home import build_home_html
from src.pages.html import CourseLinks
from src.state import CourseState
from src.tools.canvas_api import update_course_home_page


def page_creator_node(state: CourseState) -> dict:
    """
    Crea la página de inicio del curso. Corre después de la agenda, el foro y los
    módulos para enlazarlos con sus URLs reales.
    """
    structure = state.get("course_structure")
    course_id = resolve_course_id(state)
    if not structure or not course_id:
        return {"errors": ["Faltan datos para crear la página de inicio"]}

    print(f"Configurando página de inicio para el curso {course_id}...")
    html = build_home_html(
        structure,
        state.get("teacher_info") or "",
        CourseLinks(state.get("course_files_map"), config.domain, course_id),
        state.get("module_mapping") or {},
        agenda_page_url=state.get("agenda_page_url"),
        forum_discussion_id=state.get("forum_discussion_id"),
    )

    result = update_course_home_page.invoke({"body": html, "course_id": course_id})
    if "error" in result:
        print(f"Error al actualizar la página de inicio: {result['error']}")
        return {"errors": ["Error en page_creator"]}
    return {}
