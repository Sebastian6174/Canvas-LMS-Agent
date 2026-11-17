from src.state import CourseState
from src.constants import CREDITS_PAGE_TITLE
from src.tools.canvas_api import create_page
from src.nodes.base import resolve_course_id
from src.utils.llm_html import generate_course_html

SYSTEM_PROMPT = """Eres un experto en diseño instruccional y Canvas LMS.
Tu tarea es generar el código HTML para la página de "Créditos" de un curso virtual, basándote en la plantilla y la información proporcionada.

Debes usar exactamente esta estructura HTML:

<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="https://univallecolombia.instructure.com/courses/863/files/67711/preview" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67711" data-api-returntype="File" /></h2>
<table class="ic-Table ic-Table--hover-row ic-Table--striped" style="width: 100%; border-collapse: collapse; border-style: none;" border="0">
    <caption>
        <h3 style="text-align: left;"><strong>&nbsp;Profesor autor</strong></h3>
    </caption>
    <tbody>
        <tr>
            <th style="width: 27.2394%; text-align: center; vertical-align: middle;" scope="row">
                <p><img id="67128" src="https://univallecolombia.instructure.com/courses/863/files/67128/preview" alt="Profesor Holmes Sierra Cespedes" width="133" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67128" data-api-returntype="File" /></p>
                <p><span style="font-size: 14pt;">Holmes Sierra Cespedes</span></p>
            </th>
            <td style="width: 66.8502%; text-align: left; vertical-align: middle;">
                <p>Tiene como formaci&oacute;n b&aacute;sica, la econom&iacute;a y cuenta con una maestr&iacute;a en estudios pol&iacute;ticos, ha realizado estudios en pol&iacute;ticas p&uacute;blicas y en econom&iacute;a solidaria. Se ha desempe&ntilde;ado en el sector privado social como director de proyectos de desarrollo rurales y urbanos, y en sector p&uacute;blico, en &aacute;reas de planeaci&oacute;n territorial y gesti&oacute;n p&uacute;blica. Ha ejercido la docencia en procesos no formales de educaci&oacute;n y en procesos formales de educaci&oacute;n a nivel superior. Ha hecho parte de movimientos sociales y pol&iacute;ticos orientados a la justicia social y la equidad en los territorios.&nbsp;</p>
            </td>
            <td style="width: 5.9104%; text-align: left; vertical-align: middle;">
                <p style="padding-left: 40px;">&nbsp;</p>
            </td>
        </tr>
    </tbody>
</table>
<h4><strong>Asesor&iacute;a Metodol&oacute;gica:</strong></h4>
<p>Constanza Loaiza Meneses.</p>
<h4><strong>Dise&ntilde;o gr&aacute;fico, producci&oacute;n audiovisual y montaje:</strong></h4>
<p>&Aacute;rea de medios educativos - DINTEV.</p>

REGLAS DE GENERACIÓN:
1. Reemplaza [Nombre del profesor] con el docente real.
2. Si viene información del perfil del docente en el 'teacher_info' de la entrada, utilízala de forma íntegra sin resumir para llenar la biografía/perfil.
3. Tu respuesta SOLO debe contener código HTML válido. Sin markdown ticks de ```html.
"""


def credits_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear y configurar la página de Créditos del curso.
    """
    structure = state.get("course_structure")
    course_id = resolve_course_id(state)
    
    if not structure or not course_id:
        return {"errors": ["Faltan datos para crear la página de créditos"]}

    print(f"Generando página de créditos para el curso {course_id}...")
    
    human_prompt = f"""Docente del curso: {structure.teacher}
Programa Académico: {structure.academic_program}
Nivel Académico: {structure.academic_level}
Créditos del Curso: {structure.credits}
Información adicional del docente (teacher_info): {state.get('teacher_info', 'No disponible')}"""

    try:
        html_content = generate_course_html(
            SYSTEM_PROMPT, human_prompt, state.get("course_files_map"), course_id
        )
    except Exception as e:
        print(f"Error generando HTML de Créditos con LLM: {e}")
        return {"errors": [f"Error generando Créditos: {str(e)}"]}

    result = create_page.invoke({
        "title": CREDITS_PAGE_TITLE,
        "body": html_content,
        "course_id": course_id
    })
    
    if "error" in result:
        print(f"Error al crear la página de créditos: {result['error']}")
        return {"errors": ["Error creando créditos"]}

    page_url = result.get("url")
    print(f"Página de créditos creada exitosamente: {page_url}")
    
    return {"credits_page_url": page_url}
