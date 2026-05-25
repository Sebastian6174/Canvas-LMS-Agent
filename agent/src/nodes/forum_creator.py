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
Tu tarea es escribir el mensaje HTML de bienvenida para el "Foro de dudas y consultas" del curso.

El mensaje debe ser:
1. Muy profesional, claro y acogedor.
2. Explicar brevemente que este espacio está dedicado a resolver inquietudes sobre las actividades, contenidos y lecturas.
3. Mencionar al docente como el moderador del espacio.

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
