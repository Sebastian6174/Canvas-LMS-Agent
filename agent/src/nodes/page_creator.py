from src.state import CourseState
from src.tools.canvas_api import update_course_home_page
from src.constants import INTRO_MODULE_NAME
from src.nodes.base import resolve_course_id
from src.utils.home_page import apply_home_page_nav_links, build_home_page_nav_links
from src.utils.llm_html import generate_course_html
from config import config

SYSTEM_PROMPT = """Eres un experto en diseño web y Canvas LMS.
Genera HTML válido para la página de inicio del curso usando la siguiente estructura mínima: banner (imagen centrada), ficha técnica (tabla con Nombre del curso, Programa, Nivel, Créditos, Pre-requisitos), introducción, resultados de aprendizaje y profesor.
Usa únicamente la información proporcionada en el `state`. Si falta algún dato, inserta en su lugar un mensaje claro indicando qué falta (p. ej. "Falta: créditos del curso").
No inventes datos ni enlaces. Los enlaces relativos serán resueltos posteriormente por la aplicación.
Respóndele al llamador SOLO con HTML válido (sin explicaciones ni marcas adicionales).
"""


def page_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear y configurar la página de inicio del curso.
    """
    structure = state.get("course_structure")
    course_id = resolve_course_id(state)
    teacher_info = state.get("teacher_info", "")
    
    if not structure or not course_id:
        return {"errors": ["Faltan datos para crear la página de inicio"]}

    print(f"Configurando página de inicio para el curso {course_id}...")
    
    human_prompt = f"Información del curso:\nPrograma Académico: {structure.academic_program}\nDescripción: {structure.description}\n\nInformación del/los Docente(s) extraída del documento adicional:\n{teacher_info}"

    try:
        html_content = generate_course_html(
            SYSTEM_PROMPT, human_prompt, state.get("course_files_map"), course_id
        )
    except Exception as e:
        print(f"Error generando HTML con LLM: {e}")
        return {"errors": [f"Error generando HTML con LLM: {str(e)}"]}

    module_mapping = state.get("module_mapping") or {}
    course_module_names = [mod.name for mod in structure.modules]
    nav_links = build_home_page_nav_links(
        course_id=course_id,
        domain=config.domain,
        module_mapping=module_mapping,
        course_module_names=course_module_names,
        agenda_page_url=state.get("agenda_page_url"),
        forum_discussion_id=state.get("forum_discussion_id"),
        intro_module_name=INTRO_MODULE_NAME,
    )
    html_content = apply_home_page_nav_links(
        html_content, nav_links, course_id, config.domain
    )

    result = update_course_home_page.invoke({
        "body": html_content,
        "course_id": course_id
    })
    
    if "error" in result:
        print(f"Error al actualizar la página de inicio: {result['error']}")
        return {"errors": ["Error en page_creator"]}

    return {}
