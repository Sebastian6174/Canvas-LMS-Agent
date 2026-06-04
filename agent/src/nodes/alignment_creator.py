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

<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="https://univallecolombia.instructure.com/courses/863/files/67711/preview" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67711" data-api-returntype="File" /></h2>
<table style="border-collapse: collapse; width: 100.013%; border: 1px solid #e1e4e7; margin-left: auto; margin-right: auto;" border="1" cellspacing="1" cellpadding="0">
    <caption>ACTIVIDADES DE APRENDIZAJE</caption>
    <thead>
        <tr style="background-color: #f3f4f5;">
            <th style="width: 5.25374%; padding: 5px;" scope="row">R.A.</th>
            <th style="width: 9.02827%; padding: 5px;" scope="row">Indicadores de logro</th>
            <th style="width: 41.3668%; padding: 5px;" scope="row">Descripci&oacute;n</th>
            <th style="width: 29.6862%; padding: 5px;" scope="row">Actividad</th>
            <th style="width: 14.6901%; padding: 5px;" scope="row">Tipo de actividad</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="padding: 5px; text-align: center; width: 5.25374%;" rowspan="3">R.A. 1</td>
            <td style="padding: 5px; text-align: center; width: 9.02827%;">1</td>
            <td style="padding: 5px; width: 41.3668%;">Analiza las ideas centrales de la lectura y el video con claridad conceptual en un foro acad&eacute;mico sobre la naturaleza del conflicto humano.</td>
            <td style="padding: 5px; width: 29.6862%;">Comprender la dificultad: el conflicto como punto de partida.</td>
            <td style="padding: 5px; text-align: center; width: 14.6901%;">Formativa</td>
        </tr>
        <tr>
            <td style="padding: 5px; text-align: center;">2</td>
            <td style="padding: 5px;">Reconoce las dimensiones humana, social y psicol&oacute;gica del conflicto con precisi&oacute;n argumentativa en un entorno de aprendizaje colaborativo.</td>
            <td style="padding: 5px;">El conflicto en perspectiva humana, social y psicol&oacute;gica.</td>
            <td style="padding: 5px; text-align: center;">Formativa</td>
        </tr>
        <tr>
            <td style="padding: 5px; text-align: center;">3</td>
            <td style="padding: 5px;">Representa un aspecto relevante de la lectura sobre el conflicto con s&iacute;ntesis y creatividad mediante un video tipo reel compartido en el foro.</td>
            <td style="padding: 5px;">Miradas al conflicto: expresarlo, pensarlo y transformarlo.</td>
            <td style="padding: 5px; text-align: center;">Evaluativa</td>
        </tr>
        <tr>
            <td style="padding: 5px; text-align: center;" rowspan="3">R.A. 2</td>
            <td style="padding: 5px; text-align: center;">4</td>
            <td style="padding: 5px;">Explica los elementos de la negociaci&oacute;n y su relaci&oacute;n con casos reales con argumentaci&oacute;n pertinente en un podcast individual.</td>
            <td style="padding: 5px;">Mecanismos alternativos de negociaci&oacute;n.</td>
            <td style="padding: 5px; text-align: center;">Evaluativa</td>
        </tr>
        <tr>
            <td style="padding: 5px; text-align: center;">5</td>
            <td style="padding: 5px;">Analiza un caso de negociaci&oacute;n seleccionado con profundidad y aplicaci&oacute;n adecuada del marco te&oacute;rico en una presentaci&oacute;n grupal.</td>
            <td style="padding: 5px;">Negociar en acci&oacute;n: an&aacute;lisis de casos reales en distintos &aacute;mbitos.</td>
            <td style="padding: 5px; text-align: center;">Evaluativa</td>
        </tr>
        <tr>
            <td style="padding: 5px; text-align: center;">6</td>
            <td style="padding: 5px;">Eval&uacute;a el progreso en el uso de t&eacute;cnicas de negociaci&oacute;n con reflexi&oacute;n cr&iacute;tica durante el encuentro sincr&oacute;nico de seguimiento.</td>
            <td style="padding: 5px;">Valoraci&oacute;n del proceso de negociaci&oacute;n.</td>
            <td style="padding: 5px; text-align: center;">Formativa</td>
        </tr>
        <tr>
            <td style="padding: 5px; text-align: center;">R.A. 3</td>
            <td style="padding: 5px; text-align: center;">7</td>
            <td style="padding: 5px;">Identifica problemas, alternativas y t&eacute;cnicas de decisi&oacute;n con rigor metodol&oacute;gico al analizar situaciones propias de la gesti&oacute;n del talento humano.</td>
            <td style="padding: 5px;">Decidir con prop&oacute;sito: t&eacute;cnicas para resolver problemas.</td>
            <td style="padding: 5px; text-align: center;">Evaluativa</td>
        </tr>
        <tr>
            <td style="padding: 5px; text-align: center;">R.A. 4</td>
            <td style="padding: 5px; text-align: center;">8</td>
            <td style="padding: 5px;">Integra los aprendizajes sobre conflicto, negociaci&oacute;n y decisi&oacute;n con articulaci&oacute;n coherente en la presentaci&oacute;n final sincr&oacute;nica o grabada.</td>
            <td style="padding: 5px;">Integrar para transformar: an&aacute;lisis final.</td>
            <td style="padding: 5px; text-align: center;">Evaluativa</td>
        </tr>
    </tbody>
</table>

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
