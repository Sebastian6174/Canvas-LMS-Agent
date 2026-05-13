from src.state import CourseState
from src.tools.canvas_api import create_module

def module_generator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear los módulos en el curso de Canvas.
    """
    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id")
    
    if not structure or not course_id:
        return {**state, "errors": ["Faltan datos para crear los módulos"]}

    print(f"Generando módulos para el curso {course_id}...")
    
    module_mapping = {}
    
    for mod in structure.modules:
        print(f"Creando módulo: {mod.name}")
        result = create_module.invoke({
            "name": mod.name,
            "course_id": course_id
        })
        
        if "error" in result:
            print(f"Error al crear el módulo {mod.name}: {result['error']}")
            continue
            
        module_mapping[mod.name] = result.get("id")

    return {
        **state,
        "module_mapping": module_mapping
    }
