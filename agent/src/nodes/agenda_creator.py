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

<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="https://univallecolombia.instructure.com/courses/863/files/67711/preview" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67711" data-api-returntype="File" /></h2>
<table style="border-collapse: collapse; width: 66.035%; border-color: #e1e4e7; border-style: solid; margin-left: auto; margin-right: auto;" border="1" cellspacing="1" cellpadding="0">
    <caption>ACTIVIDADES DE APRENDIZAJE</caption>
    <tbody>
        <tr>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 10%;" scope="col" align="center">UNIDAD</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 10%;" scope="col" align="center">SEMANAS</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 50%;" scope="col" align="center">ACTIVIDAD</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 13%;" scope="col" align="center">TIPO</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 12%;" scope="col" align="center">DEDICACI&Oacute;N</th>
            <th style="vertical-align: middle; background-color: #f3f4f5; width: 11%;" scope="col" align="center">VALORACI&Oacute;N</th>
        </tr>
        <tr>
            <td style="text-align: center;" rowspan="3">1</td>
            <td style="text-align: center;" rowspan="2">1</td>
            <td>Actividad 1. Comprender la dificultad: el conflicto como punto de partida.</td>
            <td style="text-align: center;">Formativa</td>
            <td style="text-align: center;">20</td>
            <td style="text-align: center;"></td>
        </tr>
        <tr>
            <td>Actividad 2. El conflicto en perspectiva humana, social y psicol&oacute;gica.</td>
            <td style="text-align: center;">Formativa</td>
            <td style="text-align: center;">4</td>
            <td style="text-align: center;"></td>
        </tr>
        <tr>
            <td style="text-align: center;">2</td>
            <td>Actividad 3. Miradas al conflicto: expresarlo, pensarlo y transformarlo.</td>
            <td style="text-align: center;">Evaluativa</td>
            <td style="text-align: center;">24</td>
            <td style="text-align: center;">20%</td>
        </tr>
        <tr>
            <td style="text-align: center;" rowspan="3">2</td>
            <td style="text-align: center;">3</td>
            <td>Actividad 4. Mecanismos alternativos de negociaci&oacute;n.</td>
            <td style="text-align: center;">Evaluativa</td>
            <td style="text-align: center;">24</td>
            <td style="text-align: center;">20%</td>
        </tr>
        <tr>
            <td style="text-align: center;" rowspan="2">4</td>
            <td>Actividad 5. La negociaci&oacute;n como puente: identificar intereses y posiciones.</td>
            <td style="text-align: center;">Evaluativa</td>
            <td style="text-align: center;">20</td>
            <td style="text-align: center;">20%</td>
        </tr>
        <tr>
            <td>Actividad 6. Valoraci&oacute;n del proceso de negociaci&oacute;n.</td>
            <td style="text-align: center;">Formativa</td>
            <td style="text-align: center;">4</td>
            <td style="text-align: center;"></td>
        </tr>
        <tr>
            <td style="text-align: center;" rowspan="2">3</td>
            <td style="text-align: center;" rowspan="2">5</td>
            <td>Actividad 7. Decidir con prop&oacute;sito: t&eacute;cnicas para resolver problemas.</td>
            <td style="text-align: center;">Evaluativa</td>
            <td style="text-align: center;">24</td>
            <td style="text-align: center;">20%</td>
        </tr>
        <tr>
            <td>Actividad 8. Integrar para transformar: an&aacute;lisis final.</td>
            <td style="text-align: center;">Evaluativa</td>
            <td style="text-align: center;">24</td>
            <td style="text-align: center;">20%</td>
        </tr>
        <tr>
            <td style="text-align: right; padding: 5px;" colspan="4">Total horas</td>
            <td style="text-align: center;">144</td>
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
