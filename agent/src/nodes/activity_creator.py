from src.state import CourseState
from src.tools.canvas_api import add_item_to_module, create_assignment, delete_assignment, list_assignments
from src.activity_types import wrap_activity_description_html
from src.utils.helpers import activities_for_unit
from config import config


def _normalize_assignment_name(name: str) -> str:
    return (name or "").strip().lower()


def _delete_stale_assignments(course_id: str, current_activity_names: set[str]) -> None:
    assignments = list_assignments.invoke({"course_id": course_id})
    if not isinstance(assignments, list):
        print("No se pudieron listar las actividades existentes para limpiar el Syllabus.")
        return

    for assignment in assignments:
        assignment_name = assignment.get("name", "")
        assignment_id = assignment.get("id")
        if not assignment_id or _normalize_assignment_name(assignment_name) in current_activity_names:
            continue

        print(f"Eliminando actividad antigua de Canvas: {assignment_name}")
        result = delete_assignment.invoke({"assignment_id": assignment_id, "course_id": course_id})
        if "error" in result:
            print(f"No se pudo eliminar la actividad antigua '{assignment_name}': {result['error']}")


def activity_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear las actividades y asignarlas a sus unidades (módulos Canvas).
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

    current_activity_names = {_normalize_assignment_name(act.name) for act in structure.activities}
    _delete_stale_assignments(course_id, current_activity_names)

    canvas_assignment_ids = {}
    for act in structure.activities:
        print(f"Creando actividad: {act.name}")
        description_html = wrap_activity_description_html(
            act.activity_type,
            act.description,
            act.related_learning_outcome,
            act.weight,
        )
        res = create_assignment.invoke({
            "name": act.name,
            "description": description_html,
            "points_possible": float(act.weight),
            "course_id": course_id
        })
        
        if "error" in res:
            print(f"Error al crear actividad {act.name}: {res['error']}")
            continue
            
        canvas_assignment_ids[act.name] = res.get("id")

    for mod in structure.modules:
        mod_id = module_mapping.get(mod.name)
        if not mod_id:
            print(f"No hay módulo Canvas para la unidad '{mod.name}'. Omitiendo actividades.")
            continue

        for act in activities_for_unit(structure.activities, mod.name):
            assign_id = canvas_assignment_ids.get(act.name)
            if not assign_id:
                print(
                    f"No se encontró assignment para '{act.name}' "
                    f"(unidad '{mod.name}'). Omitiendo."
                )
                continue

            print(f"Agregando {act.name} al módulo {mod.name}")
            add_item_to_module.invoke({
                "module_id": mod_id,
                "title": act.name,
                "type": "Assignment",
                "content_id": assign_id,
                "course_id": course_id,
            })

    return {**state, "canvas_assignment_ids": canvas_assignment_ids}
