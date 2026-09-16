from src.state import CourseState
from src.tools.canvas_api import update_course_home_page
from src.routing import INTRO_MODULE_NAME
from src.utils.helpers import (
    resolve_html_links,
    build_home_page_nav_links,
    apply_home_page_nav_links,
)
from config import config
from langchain_core.messages import SystemMessage, HumanMessage

def page_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear y configurar la página de inicio del curso.
    """
    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    teacher_info = state.get("teacher_info", "")
    
    if not structure or not course_id:
        return {"errors": ["Faltan datos para crear la página de inicio"]}

    print(f"Configurando página de inicio para el curso {course_id}...")
    
    llm = config.get_llm()
    
    system_prompt = """Eres un experto en diseño web y Canvas LMS.
Genera HTML válido para la página de inicio del curso usando la siguiente estructura mínima: banner (imagen centrada), ficha técnica (tabla con Nombre del curso, Programa, Nivel, Créditos, Pre-requisitos), introducción, resultados de aprendizaje y profesor.
Usa únicamente la información proporcionada en el `state`. Si falta algún dato, inserta en su lugar un mensaje claro indicando qué falta (p. ej. "Falta: créditos del curso").
No inventes datos ni enlaces. Los enlaces relativos serán resueltos posteriormente por la aplicación.
Respóndele al llamador SOLO con HTML válido (sin explicaciones ni marcas adicionales).
"""

    human_prompt = f"Información del curso:\nPrograma Académico: {structure.academic_program}\nDescripción: {structure.description}\n\nInformación del/los Docente(s) extraída del documento adicional:\n{teacher_info}"

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        html_content = response.content.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"Error generando HTML con LLM: {e}")
        return {"errors": [f"Error generando HTML con LLM: {str(e)}"]}
    
    files_map = state.get("course_files_map") or {}
    html_content = resolve_html_links(html_content, files_map, config.domain, course_id)

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
