from src.state import CourseState
from src.tools.canvas_api import create_course, import_base_course_content
from config import config

def setup_course_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear el curso en Canvas e importar la estructura base.
    """
    structure = state.get("course_structure")
    if not structure:
        return {**state, "errors": ["No se encontró la estructura del curso"]}

    print(f"Creando curso: {structure.academic_program} - {structure.semester}")
    
    # Creamos el curso
    if (config.create_new_course):
        course_name = f"{structure.academic_program} - Semestre {structure.semester}"
        course_code = f"{structure.academic_program[:3].upper()}-{structure.semester}"
        
        new_course = create_course.invoke({
            "name": course_name,
            "course_code": course_code
        })
        
        if "error" in new_course:
            return {**state, "errors": [f"Error al crear curso: {new_course['error']}"]}
        
        course_id = str(new_course.get("id"))
        print(f"Curso creado con ID: {course_id}")
    else:
        course_id = config.course_id
        if not course_id:
            return {**state, "errors": ["COURSE_ID no configurado en .env"]}
        print(f"Usando curso existente con ID: {course_id}")

    # Importamos estructura base si existe un BASE_COURSE_ID configurado
    base_course_id = config.base_course_id
    if base_course_id:
        print(f"Importando contenido del curso base {base_course_id}...")
        import_res = import_base_course_content.invoke({
            "target_course_id": course_id,
            "source_course_id": base_course_id
        })
        if "error" in import_res:
            print(f"Advertencia: No se pudo importar la estructura base: {import_res['error']}")

    return {
        **state,
        "canvas_course_id": course_id
    }
