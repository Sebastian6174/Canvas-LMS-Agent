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
Tu tarea es generar el código HTML para la página de "Agenda de actividades" (cronograma) de un curso en Canvas, basándote en la plantilla y la información proporcionada.

Debes usar exactamente esta estructura HTML:

<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="https://univallecolombia.instructure.com/courses/862/files/66540/preview" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/862/files/66540" data-api-returntype="File" /></h2>

<table style="border-collapse: collapse; width: 75.5295%; border-color: #e1e4e7; border-style: solid; margin-left: auto; margin-right: auto;" border="1" cellspacing="1" cellpadding="0">
    <caption>ACTIVIDADES DE APRENDIZAJE</caption>
    <tbody>
        <tr style="height: 24.8px;">
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 11.9431%; height: 24.8px;" scope="col" align="center">UNIDAD</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 13.7899%; height: 24.8px;" scope="col" align="center">SEMANAS</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 27.3336%; height: 24.8px;" scope="col" align="center">ACTIVIDAD</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 11.5737%; height: 24.8px;" scope="col" align="center">TIPO</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 18.5918%; height: 24.8px;" scope="col" align="center">DEDICACIÓN</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 16.7449%; height: 24.8px;" scope="col" align="center">VALORACIÓN</th>
        </tr>
        <!-- Las filas se agrupan por UNIDAD (index de modulo) usando rowspan -->
        <!-- Dentro de la unidad, se agrupan por SEMANA usando rowspan si hay múltiples actividades en la misma semana -->
        <tr>
            <td style="text-align: center;" rowspan="3">1</td>
            <td style="text-align: center;" rowspan="2">1</td>
            <td>Actividad 1. [Nombre de actividad 1]</td>
            <td style="text-align: center;">[Formativa / Evaluativa]</td>
            <td style="text-align: center;">[Dedicación en horas, ej: 20]</td>
            <td style="text-align: center;">[Valoración en %, ej: N/A o 20%]</td>
        </tr>
        <!-- ... más filas ... -->
        <!-- Fila de total al final -->
        <tr style="height: 34.8px;">
            <td style="text-align: right; padding: 5px;" colspan="4">Total horas</td>
            <td style="text-align: center;">[Suma total de horas de dedicación de todas las actividades]</td>
            <td style="text-align: center;">100%</td>
        </tr>
    </tbody>
</table>

REGLAS DE GENERACIÓN:
1. "UNIDAD" se refiere al número del módulo (Unidad 1, 2, 3, etc.). Agrupa las actividades por su módulo correspondiente.
2. "SEMANAS" se refiere a la semana en la que se realiza la actividad (de acuerdo al cronograma). Si hay más de una actividad en la misma semana, usa 'rowspan' para esa celda de semana.
3. "VALORACIÓN" debe ser "N/A" si la actividad es Formativa o su ponderación/peso es 0. Si tiene peso/ponderación > 0, muestra el porcentaje correspondiente (ej: "20%").
4. Suma el total de horas de dedicación al final en la fila de "Total horas".
5. Tu respuesta SOLO debe contener código HTML válido. Sin markdown ticks de ```html.
"""

    # Construimos la información estructurada que necesita el LLM
    modules_info = ""
    for idx, mod in enumerate(structure.modules):
        modules_info += f"Unidad {idx+1}: {mod.name}\nActividades en esta unidad: {', '.join(mod.activities)}\n\n"
        
    activities_info = ""
    for act in structure.activities:
        activities_info += f"- Actividad: {act.name}\n  Tipo: {act.type}\n  Valoración (ponderación): {act.weight}%\n\n"
        
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
