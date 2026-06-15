from config import config
from src.state import CourseState
from src.tools.canvas_api import update_course_syllabus


def _build_syllabus_html() -> str:
    return """
<h2>Programa del curso</h2>
<p>Este programa se reemplaza en cada ejecucion del flujo. La lista de actividades que aparece a continuacion es generada automaticamente por Canvas y contiene solo las actividades actuales del curso.</p>
""".strip()


def syllabus_creator_node(state: CourseState) -> CourseState:
    """
    Actualiza el Syllabus de Canvas con una introduccion breve y las actividades actuales.
    """
    if state.get("errors"):
        return state

    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id

    if not structure or not course_id:
        return {**state, "errors": ["Faltan datos para crear el programa del curso"]}

    print(f"Creando Syllabus / Programa del curso para el curso {course_id}...")

    result = update_course_syllabus.invoke(
        {
            "body": _build_syllabus_html(),
            "course_id": course_id,
            "make_default_view": False,
            "show_course_summary": True,
        }
    )

    if "error" in result:
        print(f"Error al crear el programa del curso: {result['error']}")
        return {**state, "errors": ["Error creando programa del curso"]}

    print("Syllabus / Programa del curso actualizado exitosamente.")
    return {**state, "syllabus_page_url": f"/courses/{course_id}/assignments/syllabus"}
