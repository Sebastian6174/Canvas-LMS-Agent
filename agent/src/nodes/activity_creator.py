from src.state import CourseState
from src.tools.canvas_api import (
    add_item_to_module,
    create_assignment,
    create_or_update_assignment_group,
    delete_assignment,
    enable_assignment_group_weights,
    list_assignments,
)
from src.activity_types import wrap_activity_description_html
from src.utils.helpers import activities_for_unit
from config import config

ASSIGNMENT_POINTS = 5.0
FORMATIVE_POINTS = 0.0
FORMATIVE_GROUP_NAME = "Formativas"
EVALUATIVE_TOTAL_TARGET = 100.0


def _normalize_assignment_name(name: str) -> str:
    return (name or "").strip().lower()


def _weight_key(weight: float) -> float:
    value = float(weight or 0)
    if 0 < abs(value) < 1:
        value *= 100
    return round(value, 4)


def _format_weight(weight: float) -> str:
    weight = _weight_key(weight)
    return str(int(weight)) if weight.is_integer() else str(weight).rstrip("0").rstrip(".")


def _is_evaluative(activity) -> bool:
    evaluation_type = (getattr(activity, "evaluation_type", "") or "").strip().lower()
    if evaluation_type == "formativa":
        return False
    return evaluation_type == "evaluativa" or _weight_key(getattr(activity, "weight", 0)) > 0


def _evaluative_group_name(weight: float) -> str:
    return f"Evaluativas {_format_weight(weight)}% c/u"


def _build_assignment_group_specs(activities) -> dict[tuple[str, float | None], dict[str, float | str]]:
    specs: dict[tuple[str, float | None], dict[str, float | str]] = {}
    has_formative = any(not _is_evaluative(act) for act in activities)
    if has_formative:
        specs[("formative", None)] = {"name": FORMATIVE_GROUP_NAME, "group_weight": 0.0}

    for act in activities:
        if not _is_evaluative(act):
            continue
        weight = _weight_key(getattr(act, "weight", 0))
        key = ("evaluative", weight)
        if key not in specs:
            specs[key] = {
                "name": _evaluative_group_name(weight),
                "group_weight": 0.0,
            }
        specs[key]["group_weight"] = float(specs[key]["group_weight"]) + weight

    return specs


def _create_assignment_groups(course_id: str, activities) -> dict[tuple[str, float | None], int]:
    enable_result = enable_assignment_group_weights.invoke({"course_id": course_id})
    if "error" in enable_result:
        print(f"No se pudo activar la ponderacion por grupos: {enable_result['error']}")

    evaluative_total = sum(
        _weight_key(getattr(act, "weight", 0))
        for act in activities
        if _is_evaluative(act)
    )
    if abs(evaluative_total - EVALUATIVE_TOTAL_TARGET) > 0.01:
        print(
            "Advertencia: la suma de ponderaciones evaluativas es "
            f"{_format_weight(evaluative_total)}%, no {int(EVALUATIVE_TOTAL_TARGET)}%."
        )

    group_ids: dict[tuple[str, float | None], int] = {}
    for key, spec in _build_assignment_group_specs(activities).items():
        result = create_or_update_assignment_group.invoke({
            "name": spec["name"],
            "group_weight": float(spec["group_weight"]),
            "course_id": course_id,
        })
        if "error" in result:
            print(f"Error creando grupo de actividades '{spec['name']}': {result['error']}")
            continue
        group_id = result.get("id")
        if group_id:
            group_ids[key] = group_id

    return group_ids


def _assignment_group_id_for_activity(activity, group_ids: dict[tuple[str, float | None], int]) -> int | None:
    if not _is_evaluative(activity):
        return group_ids.get(("formative", None))
    return group_ids.get(("evaluative", _weight_key(getattr(activity, "weight", 0))))


def _points_for_activity(activity) -> float:
    return ASSIGNMENT_POINTS if _is_evaluative(activity) else FORMATIVE_POINTS


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
    assignment_group_ids = _create_assignment_groups(course_id, structure.activities)

    canvas_assignment_ids = {}
    for act in structure.activities:
        print(f"Creando actividad: {act.name}")
        assignment_group_id = _assignment_group_id_for_activity(act, assignment_group_ids)
        points_possible = _points_for_activity(act)
        description_html = wrap_activity_description_html(
            act.activity_type,
            act.description,
            act.related_learning_outcome,
            act.weight,
            act.evaluation_type,
            points_possible,
        )
        assignment_payload = {
            "name": act.name,
            "description": description_html,
            "points_possible": points_possible,
            "grading_type": "points" if _is_evaluative(act) else "not_graded",
            "omit_from_final_grade": not _is_evaluative(act),
            "course_id": course_id
        }
        if assignment_group_id is not None:
            assignment_payload["assignment_group_id"] = assignment_group_id

        res = create_assignment.invoke(assignment_payload)
        
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
