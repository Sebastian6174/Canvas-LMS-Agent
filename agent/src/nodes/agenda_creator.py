from src.state import CourseState
from src.tools.canvas_api import create_page
from config import config
from langchain_core.messages import SystemMessage, HumanMessage

def agenda_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear y configurar la página de Agenda de Actividades del curso.
    """
    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    
    if not structure or not course_id:
        return {"errors": ["Faltan datos para crear la página de agenda"]}

    print(f"Generando página de agenda para el curso {course_id}...")
    
    llm = config.get_llm()
    
    system_prompt = """Eres un experto en diseño instruccional y Canvas LMS.
Genera HTML válido para la página "Agenda de actividades" (cronograma) del curso.
Usa la siguiente estructura mínima: banner, tabla con columnas [UNIDAD, SEMANAS, ACTIVIDAD, TIPO, DEDICACIÓN, VALORACIÓN] y una fila final con el total de horas.
Reglas importantes:
- Agrupa actividades por módulo/unidad.
- Si una actividad es Formativa o su ponderación es 0, muestra "N/A" en VALORACIÓN.
- Calcula la suma de horas en la fila "Total horas".
Usa sólo la información en `state`. No inventes datos; si falta algo, inserta un texto claro indicando qué falta.
Respondé SOLO con HTML válido (sin explicación adicional).
"""

    from src.utils.helpers import activities_for_unit

    # Construimos la información estructurada que necesita el LLM
    modules_info = ""
    for idx, mod in enumerate(structure.modules):
        unit_activity_names = [a.name for a in activities_for_unit(structure.activities, mod.name)]
        modules_info += (
            f"Unidad {idx+1}: {mod.name}\n"
            f"Actividades en esta unidad: {', '.join(unit_activity_names)}\n\n"
        )
        
    activities_info = ""
    for act in structure.activities:
        activities_info += (
            f"- Actividad: {act.name}\n"
            f"  Tipo de actividad: {act.activity_type}\n"
            f"  Naturaleza: {act.evaluation_type}\n"
            f"  Valoración (ponderación): {act.weight}%\n\n"
        )
        
    schedule_info = ""
    for item in structure.schedule:
        schedule_info += f"- Actividad: {item.activity_name}\n  Semana: {item.week}\n  Dedicación: {item.time_commitment}\n\n"

    human_prompt = f"""Estructura del curso para la Agenda:

Módulos / Unidades:
{modules_info}

Detalles de Actividades:
{activities_info}

Cronograma / Dedicación:
{schedule_info}"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        html_content = response.content.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"Error generando HTML de Agenda con LLM: {e}")
        return {"errors": [f"Error generando Agenda: {str(e)}"]}
    
    # Resolver URLs de archivos e imágenes
    from src.utils.helpers import resolve_html_links
    files_map = state.get("course_files_map") or {}
    html_content = resolve_html_links(html_content, files_map, config.domain, course_id)

    result = create_page.invoke({
        "title": "Agenda de actividades",
        "body": html_content,
        "course_id": course_id
    })
    
    if "error" in result:
        print(f"Error al crear la página de agenda: {result['error']}")
        return {"errors": ["Error creando agenda"]}

    page_url = result.get("url")
    print(f"Página de agenda creada exitosamente: {page_url}")
    
    return {"agenda_page_url": page_url}
