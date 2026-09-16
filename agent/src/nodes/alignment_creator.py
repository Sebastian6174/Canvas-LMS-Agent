from src.state import CourseState
from src.tools.canvas_api import create_page
from config import config
from langchain_core.messages import SystemMessage, HumanMessage

def alignment_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear y configurar la página de Alineación de Actividades del curso.
    """
    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    
    if not structure or not course_id:
        return {"errors": ["Faltan datos para crear la página de alineación"]}

    print(f"Generando página de alineación para el curso {course_id}...")
    
    llm = config.get_llm()
    
    system_prompt = """Eres un experto en diseño instruccional y Canvas LMS.
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
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        html_content = response.content.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"Error generando HTML de Alineación con LLM: {e}")
        return {"errors": [f"Error generando Alineación: {str(e)}"]}
    
    # Resolver URLs de archivos e imágenes
    from src.utils.helpers import resolve_html_links
    files_map = state.get("course_files_map") or {}
    html_content = resolve_html_links(html_content, files_map, config.domain, course_id)

    result = create_page.invoke({
        "title": "Alineación de actividades",
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
