from src.state import CourseState
from src.tools.canvas_api import update_course_home_page
from config import config

def page_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear y configurar la página de inicio del curso.
    """
    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    
    if not structure or not course_id:
        return {**state, "errors": ["Faltan datos para crear la página de inicio"]}

    print(f"Configurando página de inicio para el curso {course_id}...")
    
    # Construimos el HTML de la página de inicio
    html_content = f"""
    <h1>Bienvenido al curso: {structure.academic_program}</h1>
    <p><strong>Docente:</strong> {structure.teacher}</p>
    <hr>
    <h3>Descripción del curso</h3>
    <p>{structure.description}</p>
    <h3>Resultados de Aprendizaje</h3>
    <ul>
    {" ".join([f"<li>{outcome}</li>" for outcome in structure.learning_outcomes])}
    </ul>
    """
    
    result = update_course_home_page.invoke({
        "body": html_content,
        "course_id": course_id
    })
    
    if "error" in result:
        print(f"Error al actualizar la página de inicio: {result['error']}")
        return {**state, "errors": state.get("errors", []) + ["Error en page_creator"]}

    return state
