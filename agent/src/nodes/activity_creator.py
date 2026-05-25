from src.state import CourseState
from src.tools.canvas_api import create_assignment, add_item_to_module
from config import config

def activity_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear las actividades y asignarlas a los módulos.
    """
    if state.get("errors"):
        return state

    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    module_mapping = state.get("module_mapping", {})

    if not structure or not course_id:
        return {**state, "errors": ["Faltan datos para crear las actividades"]}

    if not module_mapping:
        return {**state, "errors": ["No hay módulos creados para asignar actividades"]}

    print(f"Creando actividades para el curso {course_id}...")
    
    # Mapeo temporal para encontrar actividades por nombre
    activities_by_name = {act.name: act for act in structure.activities}
    
    # Primero creamos todas las actividades y guardamos sus IDs
    assignment_mapping = {}
    for act in structure.activities:
        print(f"Creando actividad: {act.name}")
        res = create_assignment.invoke({
            "name": act.name,
            "description": f"{act.description}<br><br><strong>Resultado de aprendizaje:</strong> {act.related_learning_outcome}<br><strong>Puntos:</strong> {act.weight}",
            "points_possible": float(act.weight),
            "course_id": course_id
        })
        
        if "error" in res:
            print(f"Error al crear actividad {act.name}: {res['error']}")
            continue
            
        assignment_mapping[act.name] = res.get("id")

    # Luego las asignamos a los módulos según la estructura
    for mod in structure.modules:
        mod_id = module_mapping.get(mod.name)
        if not mod_id:
            continue
            
        for act_name in mod.activities:
            assign_id = assignment_mapping.get(act_name)
            if not assign_id:
                continue
                
            print(f"Agregando {act_name} al módulo {mod.name}")
            add_item_to_module.invoke({
                "module_id": mod_id,
                "title": act_name,
                "type": "Assignment",
                "content_id": assign_id,
                "course_id": course_id
            })

    return state
