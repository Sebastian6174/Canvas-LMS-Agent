from src.state import CourseState
from src.tools.canvas_api import (
    add_item_to_module,
    create_assignment,
    create_or_update_assignment_group,
    delete_assignment,
    enable_assignment_group_weights,
    list_assignments,
)
from src.activities.content import generate_activity_content, safe_get_llm
from src.activities.template import render_activity_html
from src.activities.rules import format_weight, is_evaluative, weight_as_percent
from src.nodes.base import fail, proceed, resolve_course_id
from src.utils.course_files import resolve_html_links
from src.utils.units import activities_for_unit
from config import config

ASSIGNMENT_POINTS = 5.0
FORMATIVE_POINTS = 0.0
FORMATIVE_GROUP_NAME = "Formativas"
EVALUATIVE_TOTAL_TARGET = 100.0


def _normalize_assignment_name(name: str) -> str:
    return (name or "").strip().lower()


def _evaluative_group_name(weight: float) -> str:
    return f"Evaluativas {format_weight(weight)}% c/u"


def _build_assignment_group_specs(activities) -> dict[tuple[str, float | None], dict[str, float | str]]:
    specs: dict[tuple[str, float | None], dict[str, float | str]] = {}
    has_formative = any(not is_evaluative(act) for act in activities)
    if has_formative:
        specs[("formative", None)] = {"name": FORMATIVE_GROUP_NAME, "group_weight": 0.0}

    for act in activities:
        if not is_evaluative(act):
            continue
        weight = weight_as_percent(getattr(act, "weight", 0))
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
        weight_as_percent(getattr(act, "weight", 0))
        for act in activities
        if is_evaluative(act)
    )
    if abs(evaluative_total - EVALUATIVE_TOTAL_TARGET) > 0.01:
        print(
            "Advertencia: la suma de ponderaciones evaluativas es "
            f"{format_weight(evaluative_total)}%, no {int(EVALUATIVE_TOTAL_TARGET)}%."
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
    if not is_evaluative(activity):
        return group_ids.get(("formative", None))
    return group_ids.get(("evaluative", weight_as_percent(getattr(activity, "weight", 0))))


def _points_for_activity(activity) -> float:
    return ASSIGNMENT_POINTS if is_evaluative(activity) else FORMATIVE_POINTS


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


def _week_for_activity(activity, schedule) -> int:
    """Semana del cronograma en la que cae la actividad (1 si no aparece)."""
    target = _normalize_assignment_name(activity.name)
    for item in schedule or []:
        if _normalize_assignment_name(item.activity_name) == target:
            return item.week
    return 1


def activity_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear las actividades y asignarlas a sus unidades (módulos Canvas).
    """
    if state.get("errors"):
        return proceed(state)

    structure = state.get("course_structure")
    course_id = resolve_course_id(state)
    module_mapping = state.get("module_mapping", {})
    files_map = state.get("course_files_map") or {}

    if not structure or not course_id:
        return fail(state, "Faltan datos para crear las actividades")

    if not module_mapping:
        return fail(state, "No hay módulos creados para asignar actividades")

    print(f"Creando actividades para el curso {course_id}...")

    current_activity_names = {_normalize_assignment_name(act.name) for act in structure.activities}
    _delete_stale_assignments(course_id, current_activity_names)
    assignment_group_ids = _create_assignment_groups(course_id, structure.activities)

    llm = safe_get_llm(config.get_llm)
    canvas_assignment_ids = {}
    for act in structure.activities:
        print(f"Creando actividad: {act.name}")
        assignment_group_id = _assignment_group_id_for_activity(act, assignment_group_ids)
        points_possible = _points_for_activity(act)

        week = _week_for_activity(act, structure.schedule)
        content = generate_activity_content(llm, act, week)

        description_html = render_activity_html(
            description_html=content.description_html,
            delivery_form=content.delivery_form,
            resources=content.resources,
            weight=act.weight,
            evaluation_type=act.evaluation_type,
            duration=act.duration,
            week=week,
            files_map=files_map,
            domain=config.domain,
            course_id=course_id,
        )
        description_html = resolve_html_links(description_html, files_map, config.domain, course_id)

        assignment_payload = {
            "name": act.name,
            "description": description_html,
            "points_possible": points_possible,
            "grading_type": "points" if is_evaluative(act) else "not_graded",
            "omit_from_final_grade": not is_evaluative(act),
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

    return proceed(state, canvas_assignment_ids=canvas_assignment_ids)
