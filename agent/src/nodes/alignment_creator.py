from src.state import CourseState
from src.constants import ALIGNMENT_PAGE_TITLE
from src.tools.canvas_api import create_page
from src.nodes.base import resolve_course_id
from src.utils.llm_html import generate_course_html

SYSTEM_PROMPT = """Eres un experto en diseño instruccional y Canvas LMS.
Genera HTML válido para la página "Alineación de actividades".
Estructura mínima: banner seguido de una tabla con columnas [R.A., Indicadores de logro, Descripción, Actividad, Tipo de actividad].
Reglas:
- Agrupa por R.A. y usa `rowspan` en la columna R.A. según el número de filas relacionadas.
- Mapea cada actividad al `related_learning_outcome`.
- Genera 1–2 indicadores de logro coherentes por R.A. basados en las actividades asignadas.
- Pon "Evaluativa" o "Formativa" según `evaluation_type` o `weight`.
Usa sólo la información proporcionada; si falta algo, inserta un aviso claro.
Responde únicamente con HTML válido.
"""


def alignment_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear y configurar la página de Alineación de Actividades del curso.
    """
    structure = state.get("course_structure")
    course_id = resolve_course_id(state)
    
    if not structure or not course_id:
        return {"errors": ["Faltan datos para crear la página de alineación"]}

    print(f"Generando página de alineación para el curso {course_id}...")
    
    # Construimos la lista de R.A. y Actividades para pasarlas al LLM
    outcomes_str = "\n".join([f"RA {i+1}: {ra}" for i, ra in enumerate(structure.learning_outcomes)])
    
    activities_str = ""
    for act in structure.activities:
        activities_str += (
            f"- Nombre: {act.name}\n"
            f"  Descripción: {act.description}\n"
            f"  Tipo de actividad: {act.activity_type}\n"
            f"  Naturaleza: {act.evaluation_type}\n"
            f"  RA Relacionado: {act.related_learning_outcome}\n\n"
        )

    human_prompt = f"""Información para alinear:
Resultados de Aprendizaje (R.A.) del Curso:
{outcomes_str}

Actividades del Curso:
{activities_str}"""

    try:
        html_content = generate_course_html(
            SYSTEM_PROMPT, human_prompt, state.get("course_files_map"), course_id
        )
    except Exception as e:
        print(f"Error generando HTML de Alineación con LLM: {e}")
        return {"errors": [f"Error generando Alineación: {str(e)}"]}

    result = create_page.invoke({
        "title": ALIGNMENT_PAGE_TITLE,
        "body": html_content,
        "course_id": course_id
    })
    
    if "error" in result:
        print(f"Error al crear la página de alineación: {result['error']}")
        return {"errors": ["Error creando alineación"]}

    # El objeto retornado por Canvas contiene la propiedad 'url' que es el slug único de la página wiki
    page_url = result.get("url")
    print(f"Página de alineación creada exitosamente: {page_url}")
    
    return {"alignment_page_url": page_url}
