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
Tu tarea es generar el código HTML para la página de "Alineación de actividades" de un curso en Canvas, basándote estrictamente en la información de los Resultados de Aprendizaje (R.A.) y Actividades del curso proporcionadas.

Debes estructurar el HTML usando una tabla con clases de Canvas y que tenga un diseño muy similar al siguiente ejemplo:

<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="https://univallecolombia.instructure.com/courses/862/files/66540/preview" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/862/files/66540" data-api-returntype="File" /></h2>
<table style="border-collapse: collapse; width: 100.013%; border: 1px solid #e1e4e7; margin-left: auto; margin-right: auto;" border="1" cellspacing="1" cellpadding="0">
    <caption>ACTIVIDADES DE APRENDIZAJE</caption>
    <thead>
        <tr style="background-color: #f3f4f5; height: 25.3333px;">
            <th style="width: 5.25374%; height: 25.3333px;" scope="row">R.A.</th>
            <th style="width: 9.02827%; height: 25.3333px;" scope="row">Indicadores de logro</th>
            <th style="width: 41.3668%; height: 25.3333px;" scope="row">Descripción</th>
            <th style="width: 29.6862%; height: 25.3333px;" scope="row">Actividad</th>
            <th style="width: 14.6901%; height: 25.3333px;" scope="row">Tipo de actividad</th>
        </tr>
    </thead>
    <tbody>
        <!-- Las filas se agrupan por R.A. (usar rowspan para R.A. e indicadores cuando corresponda) -->
        <tr>
            <td style="padding: 5px; text-align: center;" rowspan="2">R.A. 1</td>
            <td style="padding: 5px; text-align: center;">1</td>
            <td style="padding: 5px;">[Breve indicador de logro extraído o redactado de forma coherente para el R.A. 1]</td>
            <td style="padding: 5px;">[Nombre de la Actividad relacionada (ej: A1: Foro - ...)]</td>
            <td style="padding: 5px; text-align: center;">[Formativa / Evaluativa]</td>
        </tr>
        <tr>
            <td style="padding: 5px; text-align: center;">2</td>
            <td style="padding: 5px;">[Otro indicador de logro para R.A. 1]</td>
            <td style="padding: 5px;">[Nombre de la Actividad relacionada]</td>
            <td style="padding: 5px; text-align: center;">[Formativa / Evaluativa]</td>
        </tr>
        <!-- Repetir para cada R.A. y sus actividades correspondientes -->
    </tbody>
</table>
<h3><strong><img id="12687" role="presentation" src="https://univallecolombia.instructure.com/courses/862/files/66539/preview" alt="" width="43" height="43" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/862/files/66539" data-api-returntype="File" />Resultados de aprendizaje</strong></h3>
<ul style="list-style-type: none;">
    <!-- Lista detallada de R.A.s del curso en formato: <li><strong>RA1. </strong>Texto del resultado...</li> -->
</ul>

REGLAS DE GENERACIÓN:
1. Agrupa la tabla por Resultados de Aprendizaje (R.A. 1, R.A. 2, etc.), usando correctamente 'rowspan' para la columna "R.A." de acuerdo al número de indicadores/actividades mapeados a dicho R.A.
2. Cada actividad tiene un campo 'related_learning_outcome'. Mapea las actividades de la lista a su respectivo R.A. 
3. Genera 1 o 2 'Indicadores de logro' lógicos y coherentes para cada R.A. basándote en la descripción de las actividades que están asignadas a dicho R.A. 
4. Si la actividad es evaluativa, pon "Evaluativa" en la columna Tipo de actividad. De lo contrario, pon "Formativa".
5. Al final, escribe la lista de todos los Resultados de aprendizaje (R.A.) de manera limpia.
6. Tu respuesta SOLO debe contener código HTML válido. Sin markdown ticks de ```html.
"""

    # Construimos la lista de R.A. y Actividades para pasarlas al LLM
    outcomes_str = "\n".join([f"RA {i+1}: {ra}" for i, ra in enumerate(structure.learning_outcomes)])
    
    activities_str = ""
    for act in structure.activities:
        activities_str += f"- Nombre: {act.name}\n  Descripción: {act.description}\n  Tipo: {act.type}\n  RA Relacionado: {act.related_learning_outcome}\n\n"

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
