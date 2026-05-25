from src.state import CourseState
from src.tools.canvas_api import update_course_home_page
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
Tu tarea es generar el código HTML para la página de inicio de un curso en Canvas, basándote estrictamente en la información proporcionada.
Debes estructurar el HTML para que sea idéntico o muy similar a este formato de ejemplo:

<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="https://univallecolombia.instructure.com/courses/308/files/15594/preview" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/files/15594" data-api-returntype="File" /></h2>
<h2 style="text-align: center;"><strong>Apreciado Consejero y Consejera, una cordial bienvenida a este espacio de Formaci&oacute;n para la consejer&iacute;a virtual!!</strong></h2>
<p>&nbsp;</p>
<p style="text-align: center;"><iframe title="YouTube video player" src="https://www.youtube.com/embed/tPo6S6jPM8c" width="640" height="360" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"></iframe></p>
<p>&nbsp;</p>
<h3><strong>Introducci&oacute;n</strong></h3>
<div title="Page 2">
    <p style="text-align: justify;"><span>(Aquí va la descripción del curso de forma justificada)</span></p>
    <p style="text-align: justify;">&nbsp;</p>
</div>
<p style="text-align: center;"><a title="Foro- Preguntas y Respuestas del Curso" href="$CANVAS_OBJECT_REFERENCE$/discussion_topics/g99c2e432826b03bb13e3146a015d3439"> <img id="1000" src="https://univallecolombia.instructure.com/courses/308/files/15555/preview" alt="Boton Foro Dudas" width="224" height="58" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/files/15555" data-api-returntype="File" /></a><a title="Estudiante: Gu&iacute;a del Curso" href="https://univallecolombia.instructure.com/courses/308/pages/estudiante-guia-del-curso" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/pages/estudiante-guia-del-curso" data-api-returntype="Page"><img id="1001" src="https://univallecolombia.instructure.com/courses/308/files/15554/preview" alt="Boton Guia Curso" width="224" height="58" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/files/15554" data-api-returntype="File" /></a><a title="Estudiante: Ayuda" href="https://univallecolombia.instructure.com/courses/308/pages/estudiante-ayuda" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/pages/estudiante-ayuda" data-api-returntype="Page"><img id="1002" src="https://univallecolombia.instructure.com/courses/308/files/15556/preview" alt="Boton Ayuda" width="224" height="58" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/files/15556" data-api-returntype="File" /></a><a href="https://univallecolombia.instructure.com/courses/308/pages/estudiante-guia-del-curso" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/pages/estudiante-guia-del-curso" data-api-returntype="Page"></a></p>
<h3><strong>M&oacute;dulos de aprendizaje</strong></h3>
<p>&nbsp;</p>
<p style="text-align: center;"><a title="Unidad 1. Fundamentos de Estad&iacute;stica" href="$CANVAS_OBJECT_REFERENCE$/modules/gb25ca05745680e38de80f065b67277f8" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/146/modules/972" data-api-returntype="Module"><img src="https://univallecolombia.instructure.com/courses/308/files/15560/download?wrap=1" alt="Unidad 1" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/files/15560" data-api-returntype="File" /></a><a title="Unidad 2. Fundamentos de Administraci&oacute;n" href="$CANVAS_OBJECT_REFERENCE$/modules/gef364dbbbe1716d731b31c229a23f1b5" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/146/modules/224" data-api-returntype="Module"><img src="https://univallecolombia.instructure.com/courses/308/files/15559/download?wrap=1" alt="Unidad 2" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/files/15559" data-api-returntype="File" /></a><a title="Unidad 3. Fundamentos de Calidad" href="$CANVAS_OBJECT_REFERENCE$/modules/g27c57cd94d28e3c6c378e5b4a320e765" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/146/modules/225" data-api-returntype="Module"><img src="https://univallecolombia.instructure.com/courses/308/files/15558/download?wrap=1" alt="Unidad 3" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/308/files/15558" data-api-returntype="File" /></a></p>
<p style="text-align: center;">&nbsp;</p>
<table class="ic-Table ic-Table--hover-row ic-Table--striped" style="width: 100%; border-collapse: collapse; border-style: none;" border="0">
    <caption>
        <h3 style="text-align: left;"><strong>&nbsp;Profesoras consejeras</strong></h3>
    </caption>
    <tbody>
        <tr>
            <th style="width: 20.9895%; text-align: center; vertical-align: middle;" scope="row">
                <p>&nbsp;</p>
            </th>
            <th style="width: 22.9618%; text-align: center; vertical-align: middle;" scope="row">
                <p>&nbsp;</p>
                <p><span style="font-size: 14pt;">M&oacute;nica Chica</span></p>
            </th>
            <td style="width: 34.4674%; text-align: left; vertical-align: middle;">
                <p>Consejera estudiantil Virtual DINTEV-&nbsp; Universidad del Valle.</p>
            </td>
            <td style="width: 21.5812%; text-align: left; vertical-align: middle;">
                <p>&nbsp;</p>
            </td>
        </tr>
    </tbody>
</table>
<p>&nbsp;</p>

Ten en cuenta:
1. Reemplazar la descripción del curso en el apartado de Introducción usando EXACTAMENTE la descripción real proporcionada, sin omitir partes ni resumir el texto.
2. Adaptar el título de bienvenida ("Apreciado Consejero...", etc) al curso actual. Por ejemplo: 'Apreciado estudiante, una cordial bienvenida a este espacio de [Nombre del Curso]!!'. Asegúrate de reemplazar completamente el nombre del curso de la plantilla ('Formación para la consejería virtual') por el nombre del curso actual.
3. Usar los links y recursos de imágenes y el iframe tal cual están en el ejemplo, asumiendo que el nodo de configuración se encargará de ellos.
4. Para la tabla de docentes al final, usa la información detallada del docente proporcionada. Genera las filas de la tabla adaptándote a los docentes reales que vengan en la información extraída, con su nombre y una breve descripción de su perfil usando SOLO la información dada.
5. NO asumas ni inventes información. Si alguna información no está presente, inserta un mensaje para el usuario indicando qué falta, pero no inventes nada.
6. Tu respuesta SOLO debe contener código HTML válido. Sin markdown ticks de ```html.
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
    
    result = update_course_home_page.invoke({
        "body": html_content,
        "course_id": course_id
    })
    
    if "error" in result:
        print(f"Error al actualizar la página de inicio: {result['error']}")
        return {"errors": ["Error en page_creator"]}

    return {}
