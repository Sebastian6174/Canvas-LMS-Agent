from src.state import CourseState
from src.tools.canvas_api import update_course_home_page
from src.routing import INTRO_MODULE_NAME
from src.utils.helpers import (
    resolve_html_links,
    build_home_page_nav_links,
    apply_home_page_nav_links,
)
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

<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="https://univallecolombia.instructure.com/courses/863/files/67711/preview" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67711" data-api-returntype="File" /></h2>
<table style="border-collapse: collapse; width: 60%; height: 343px; margin-left: auto; margin-right: auto;" border="1px">
    <caption><strong>FICHA T&Eacute;CNICA DEL CURSO</strong></caption>
    <tbody>
        <tr style="height: 53px;">
            <th style="background-color: #efefef; border: 1px solid #ffffff; width: 28.3155%; height: 53px; text-align: left;" scope="row">
                <p style="margin-left: 30px;"><strong>Nombre y c&oacute;digo del curso</strong></p>
            </th>
            <td style="background-color: #ffffff; border: 1px solid #efefef; width: 28.7531%; height: 53px;">
                <p style="margin-left: 30px;">Tecnolog&iacute;a en gesti&oacute;n del talento humano</p>
            </td>
        </tr>
        <tr style="height: 53px;">
            <th style="background-color: #efefef; border: 1px solid #ffffff; width: 28.3155%; height: 53px; text-align: left;" scope="row">
                <p style="margin-left: 30px;"><strong>Programa / unidad acad&eacute;micas</strong></p>
            </th>
            <td style="background-color: #ffffff; border: 1px solid #efefef; width: 28.7531%; height: 53px;">
                <p style="margin-left: 30px;">Negociaci&oacute;n y toma de decisiones</p>
            </td>
        </tr>
        <tr style="height: 53px;">
            <th style="background-color: #efefef; border: 1px solid #ffffff; width: 28.3155%; height: 53px; text-align: left;" scope="row">
                <p style="margin-left: 30px;"><strong>Nivel acad&eacute;mico y modalidad</strong></p>
            </th>
            <td style="background-color: #ffffff; border: 1px solid #efefef; width: 28.7531%; height: 53px;">
                <p style="margin-left: 30px;">Pregrado</p>
            </td>
        </tr>
        <tr style="height: 53px;">
            <th style="background-color: #efefef; border: 1px solid #ffffff; width: 28.3155%; height: 53px; text-align: left;" scope="row">
                <p style="margin-left: 30px;"><strong>Cr&eacute;ditos y duraci&oacute;n del curso</strong></p>
            </th>
            <td style="background-color: #ffffff; border: 1px solid #efefef; width: 28.7531%; height: 53px;">
                <p style="margin-left: 30px;">3 cr&eacute;ditos -144 horas</p>
            </td>
        </tr>
        <tr style="height: 53px;">
            <th style="background-color: #efefef; border: 1px solid #ffffff; width: 28.3155%; height: 14px; text-align: left;" scope="row">
                <p style="margin-left: 30px;"><strong>Pre-requisitos y co-requisitos</strong></p>
            </th>
            <td style="background-color: #ffffff; border: 1px solid #efefef; width: 28.7531%; height: 14px;">
                <p style="margin-left: 30px;">Ninguno</p>
            </td>
        </tr>
        <tr style="height: 11px;">
            <th style="background-color: #ffffff; border: 1px solid #efefef; width: 57.0686%; height: 11px;" colspan="2" scope="row">
                <p style="margin-left: 30px; text-align: left;"><strong><span style="font-size: 14pt;">Programa descargable</span></strong></p>
            </th>
        </tr>
    </tbody>
</table>
<h3><strong>Introducci&oacute;n</strong></h3>
<div title="Page 2">
    <p style="text-align: justify;">En el mundo del siglo XXI, las organizaciones y las personas se enfrentan a conflictos, cambios r&aacute;pidos y situaciones complejas que requieren habilidades s&oacute;lidas para dialogar, negociar y tomar decisiones acertadas. En este contexto, la gesti&oacute;n del talento humano juega un papel estrat&eacute;gico: los profesionales del &aacute;rea necesitan comprender c&oacute;mo surgen los conflictos, c&oacute;mo transformarlos y c&oacute;mo conducir procesos de negociaci&oacute;n que generen acuerdos sostenibles.</p>
    <p style="text-align: justify;">Este curso ofrece una introducci&oacute;n pr&aacute;ctica y aplicada a los modelos contempor&aacute;neos de resoluci&oacute;n de conflictos y toma de decisiones, integrando aportes de la administraci&oacute;n, la econom&iacute;a, la psicolog&iacute;a y la gesti&oacute;n organizacional. A lo largo de seis semanas, van a conocer t&eacute;cnicas y herramientas que les permitir&aacute;n analizar problemas desde m&uacute;ltiples perspectivas para seleccionar m&eacute;todos adecuados e intervenir en situaciones reales.</p>
    <p style="text-align: justify;">El curso orienta la formaci&oacute;n de profesionales &nbsp;en la identificaci&oacute;n y comprensi&oacute;n de los conflictos presentes en la vida cotidiana, familiar, social y laboral. Asimismo, fortalecer&aacute; habilidades para participar y conducir procesos de negociaci&oacute;n dentro de las organizaciones, buscando la toma de decisiones fundamentadas, sobre las cuales deber&aacute; saber evaluar no solo la decisi&oacute;n y su racionalidad, como tal, sino las consecuencias y resultados de las mismas.</p>
    <p style="text-align: justify;">Estas capacidades son esenciales para su futuro desempe&ntilde;o como tecn&oacute;logo en Gesti&oacute;n del Talento Humano, ya que permiten aportar a la construcci&oacute;n de ambientes laborales colaborativos, productivos y orientados a la soluci&oacute;n de problemas.</p>
    <p>&nbsp;</p>
    <h3><strong><img id="12687" role="presentation" src="https://univallecolombia.instructure.com/courses/863/files/67126/preview" alt="" width="43" height="43" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67126" data-api-returntype="File" />Resultados de aprendizaje</strong><strong></strong></h3>
    <ul style="list-style-type: none;">
        <li><strong>RA1. </strong>Aplicar la t&eacute;cnica apropiada para resolver un conflicto.</li>
        <li><strong>RA2. </strong>Identificar el problema y el m&eacute;todo id&oacute;neo para su resoluci&oacute;n.</li>
        <li><strong>RA3. </strong>Reconocer el proceso de toma de decisiones y las distintas t&eacute;cnicas disponibles para tomar decisiones.</li>
        <li><span><strong>RA4. </strong>Utilizar la t&eacute;cnica apropiada para abordar cada negociaci&oacute;n.</span></li>
    </ul>
    <p style="text-align: justify;">&nbsp;</p>
</div>
<p style="text-align: center;"><a title="Foro- Preguntas y Respuestas del Curso" href="https://univallecolombia.instructure.com/courses/863/discussion_topics/5426" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/discussion_topics/5426" data-api-returntype="Discussion"> <img id="1000" src="https://univallecolombia.instructure.com/courses/863/files/67114/preview" alt="Boton Foro Dudas" width="224" height="58" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67114" data-api-returntype="File" /></a></p>
<h3><strong>Unidades de aprendizaje</strong></h3>
<p>&nbsp;</p>
<p style="text-align: center;"><a title="Agenda de Actividades" href="https://univallecolombia.instructure.com/courses/863/pages/agenda-de-actividades" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/pages/agenda-de-actividades" data-api-returntype="Page"><img id="16295" src="https://univallecolombia.instructure.com/courses/863/files/67113/preview" alt="Agenda de Actividades" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67113" data-api-returntype="File" /></a><a title="Actividades de preparaci&oacute;n" href="$CANVAS_OBJECT_REFERENCE$/modules/g52c8579515fc6b411720eab9aeacf292" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/146/modules/971" data-api-returntype="Module"><img src="https://univallecolombia.instructure.com/courses/863/files/67119/download?wrap=1" alt="Actividades preliminares" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67119" data-api-returntype="File" /></a><a title="Unidad 1. El conflicto" href="https://univallecolombia.instructure.com/courses/863/modules/4156" data-course-type="modules" data-published="true" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/modules/4156" data-api-returntype="Module"><img src="https://univallecolombia.instructure.com/courses/863/files/67116/download?wrap=1" alt="Unidad 1" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67116" data-api-returntype="File" /></a><a title="Unidad 2. La negociaci&oacute;n" href="https://univallecolombia.instructure.com/courses/863/modules/4161" data-course-type="modules" data-published="true" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/modules/4161" data-api-returntype="Module"><img src="https://univallecolombia.instructure.com/courses/863/files/67117/download?wrap=1" alt="Unidad 2" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67117" data-api-returntype="File" /></a><a title="Unidad 3. Toma de decisiones" href="https://univallecolombia.instructure.com/courses/863/modules/4162" data-course-type="modules" data-published="true" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/modules/4162" data-api-returntype="Module"><img src="https://univallecolombia.instructure.com/courses/863/files/67118/download?wrap=1" alt="Unidad 3" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67118" data-api-returntype="File" /></a></p>
<p style="text-align: center;">&nbsp;</p>
<table class="ic-Table ic-Table--hover-row ic-Table--striped" style="width: 100%; border-collapse: collapse; border-style: none;" border="0">
    <caption>
        <h3 style="text-align: left;"><strong>&nbsp;Profesor</strong></h3>
    </caption>
    <tbody>
        <tr>
            <th style="width: 20.9895%; text-align: center; vertical-align: middle;" scope="row">
                <p>&nbsp;</p>
            </th>
            <th style="width: 22.9618%; text-align: center; vertical-align: middle;" scope="row">
                <p><img id="67128" src="https://univallecolombia.instructure.com/courses/863/files/67128/preview" alt="Profesor Holmes Sierra Cespedes" width="133" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67128" data-api-returntype="File" /></p>
                <p><span style="font-size: 14pt;">Holmes Sierra Cespedes</span></p>
            </th>
            <td style="width: 34.4674%; text-align: left; vertical-align: middle;">
                <p>Tiene como formaci&oacute;n b&aacute;sica, la econom&iacute;a y cuenta con una maestr&iacute;a en estudios pol&iacute;ticos, ha realizado estudios en pol&iacute;ticas p&uacute;blicas y en econom&iacute;a solidaria. Se ha desempe&ntilde;ado en el sector privado social como director de proyectos de desarrollo rurales y urbanos, y en sector p&uacute;blico, en &aacute;reas de planeaci&oacute;n territorial y gesti&oacute;n p&uacute;blica. Ha ejercido la docencia en procesos no formales de educaci&oacute;n y en procesos formales de educaci&oacute;n a nivel superior. Ha hecho parte de movimientos sociales y pol&iacute;ticos orientados a la justicia social y la equidad en los territorios.&nbsp;</p>
            </td>
            <td style="width: 21.5812%; text-align: left; vertical-align: middle;">
                <p>&nbsp;</p>
            </td>
        </tr>
    </tbody>
</table>

Ten en cuenta:

1. La página de inicio se compone del banner, la ficha técnica del curso (Tabla), la introducción, los resultados de aprendizaje y el profesor.
2. Los links del html de ejemplo no son los correctos. Por el contrario, debes usar los links de los archivos relativos al curso actual (Banner, botón guía del curso, botón foro de dudas, botón de las unidades, etc.).
3. Los enlaces (href) de los botones de foro, agenda y unidades pueden usar URLs de ejemplo; se reemplazarán automáticamente por las del curso actual.
4. NO asumas ni inventes información. Si alguna información no está presente, inserta un mensaje para el usuario indicando qué falta, pero no inventes nada.
5. Tu respuesta SOLO debe contener código HTML válido. Sin markdown ticks de ```html.
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
    
    files_map = state.get("course_files_map") or {}
    html_content = resolve_html_links(html_content, files_map, config.domain, course_id)

    module_mapping = state.get("module_mapping") or {}
    course_module_names = [mod.name for mod in structure.modules]
    nav_links = build_home_page_nav_links(
        course_id=course_id,
        domain=config.domain,
        module_mapping=module_mapping,
        course_module_names=course_module_names,
        agenda_page_url=state.get("agenda_page_url"),
        forum_discussion_id=state.get("forum_discussion_id"),
        intro_module_name=INTRO_MODULE_NAME,
    )
    html_content = apply_home_page_nav_links(
        html_content, nav_links, course_id, config.domain
    )

    result = update_course_home_page.invoke({
        "body": html_content,
        "course_id": course_id
    })
    
    if "error" in result:
        print(f"Error al actualizar la página de inicio: {result['error']}")
        return {"errors": ["Error en page_creator"]}

    return {}
