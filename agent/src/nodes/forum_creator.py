from src.state import CourseState
from src.tools.canvas_api import create_discussion_topic
from config import config
from langchain_core.messages import SystemMessage, HumanMessage

def forum_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear el foro de dudas y consultas en el curso.
    """
    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    
    if not structure or not course_id:
        return {"errors": ["Faltan datos para crear el foro de dudas"]}

    print(f"Generando foro de dudas para el curso {course_id}...")
    
    llm = config.get_llm()
    
    system_prompt = """Eres un experto en diseño instruccional y Canvas LMS.
Tu tarea es escribir el mensaje HTML de bienvenida para el "Foro de dudas y consultas" del curso, basándote en el siguiente html de ejemplo:

<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="https://univallecolombia.instructure.com/courses/863/files/67711/preview" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67711" data-api-returntype="File" /></h2>
<h2><strong><img style="float: right;" src="https://univallecolombia.instructure.com/courses/863/files/67124/download" alt="" width="145" height="203" data-api-endpoint="https://univallecolombia.instructure.com/api/v1/courses/863/files/67124" data-api-returntype="File" data-decorative="true" />Foro de dudas</strong></h2>
<p><em><strong>Este foro de discusi&oacute;n es utilizado para recopilar y responder las preguntas de estudiantes.&nbsp;</strong></em></p>
<p>Este es un foro sin calificaci&oacute;n usado para publicar preguntas generales de la clase. Si no est&aacute; seguro de las instrucciones, tareas, etc., no dude en publicar sus preguntas a continuaci&oacute;n.</p>
<p><strong>Tenga en cuenta:</strong> si su pregunta est&aacute; relacionada con una calificaci&oacute;n que recibi&oacute; u otro asunto personal, no la publique aqu&iacute;. Para esto, p&oacute;ngase en contacto conmigo directamente a trav&eacute;s del correo o dir&iacute;jase a su consejero.</p>

REGLAS DE GENERACIÓN:
1. Usa formato HTML limpio (párrafos, negritas, listas si es necesario).
2. Usa el nombre del docente real proporcionado.
3. Tu respuesta SOLO debe contener código HTML válido. Sin markdown ticks de ```html.
"""

    human_prompt = f"""Docente del curso: {structure.teacher}
Curso: {structure.academic_program}"""

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ])
        message_content = response.content.replace("```html", "").replace("```", "").strip()
    except Exception as e:
        print(f"Error generando mensaje del foro con LLM: {e}")
        return {"errors": [f"Error generando Foro: {str(e)}"]}
    
    # Resolver URLs de archivos e imágenes
    from src.utils.helpers import resolve_html_links
    files_map = state.get("course_files_map") or {}
    message_content = resolve_html_links(message_content, files_map, config.domain, course_id)

    result = create_discussion_topic.invoke({
        "title": "Foro de dudas",
        "message": message_content,
        "course_id": course_id
    })
    
    if "error" in result:
        print(f"Error al crear el foro de dudas: {result['error']}")
        return {"errors": ["Error creando foro"]}

    discussion_id = result.get("id")
    print(f"Foro de dudas creado exitosamente con ID: {discussion_id}")
    
    return {"forum_discussion_id": discussion_id}
