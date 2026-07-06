import re
from typing import Optional

from config import config
from src.state import CourseState, Rubric
from src.tools.canvas_api import create_or_update_assignment_rubric, list_assignments

EVALUATIVE_RUBRIC_POINTS = 5.0


def _normalize_rubric_name(val: str) -> str:
    if not val:
        return ""
    cleaned = val.lower().strip()
    cleaned = re.sub(r"\bn[o\.]*\b", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9]", "", cleaned)
    return cleaned


def _find_activity_for_rubric(structure, rubric: Rubric):
    norm_name = _normalize_rubric_name(rubric.name)

    for activity in structure.activities:
        if activity.rubric and _normalize_rubric_name(activity.rubric) == norm_name:
            return activity

    for activity in structure.activities:
        if activity.rubric and norm_name in _normalize_rubric_name(activity.rubric):
            return activity

    return None


def _find_assignment_id(
    activity_name: str,
    canvas_assignment_ids: dict,
    canvas_assignments: Optional[list],
) -> Optional[int]:
    assignment_id = canvas_assignment_ids.get(activity_name)
    if assignment_id:
        return assignment_id

    if not isinstance(canvas_assignments, list):
        return None

    normalized_activity_name = activity_name.strip().lower()
    for assignment in canvas_assignments:
        if assignment.get("name", "").strip().lower() == normalized_activity_name:
            return assignment.get("id")

    return None


def _is_evaluative(activity) -> bool:
    evaluation_type = (getattr(activity, "evaluation_type", "") or "").strip().lower()
    if evaluation_type == "formativa":
        return False
    return evaluation_type == "evaluativa" or float(getattr(activity, "weight", 0) or 0) > 0


def _criterion_points_for_rubric(rubric: Rubric, total_points: float) -> list[float]:
    if not rubric.criteria:
        return []

    explicit_points = [float(criterion.points or 0) for criterion in rubric.criteria]
    explicit_total = sum(explicit_points)
    if explicit_total > 0:
        scaled = [round((points / explicit_total) * total_points, 2) for points in explicit_points]
    else:
        per_criterion = round(total_points / len(rubric.criteria), 2)
        scaled = [per_criterion for _ in rubric.criteria]

    delta = round(total_points - sum(scaled), 2)
    if scaled and delta:
        scaled[-1] = round(scaled[-1] + delta, 2)
    return scaled


def _canvas_criteria_from_rubric(rubric: Rubric, total_points: float = EVALUATIVE_RUBRIC_POINTS) -> list[dict]:
    criteria = []
    points_by_criterion = _criterion_points_for_rubric(rubric, total_points)
    for criterion, max_points in zip(rubric.criteria, points_by_criterion):
        criteria.append(
            {
                "description": criterion.name,
                "long_description": criterion.name,
                "points": max_points,
                "criterion_use_range": False,
                "ratings": [
                    {
                        "description": "Excelente",
                        "long_description": criterion.excelente,
                        "points": max_points,
                    },
                    {
                        "description": "En desarrollo",
                        "long_description": criterion.en_desarrollo,
                        "points": round(max_points * 0.75, 2),
                    },
                    {
                        "description": "Basico",
                        "long_description": criterion.basico,
                        "points": round(max_points * 0.5, 2),
                    },
                    {
                        "description": "Insuficiente",
                        "long_description": criterion.insuficiente,
                        "points": 0,
                    },
                ],
            }
        )
    return criteria


def rubrics_creator_node(state: CourseState) -> CourseState:
    """
    Crea rubricas reales en Canvas y las asocia a sus actividades evaluativas.
    """
    if state.get("errors"):
        return state

    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    canvas_assignment_ids = state.get("canvas_assignment_ids") or {}

    if not structure or not course_id:
        return {**state, "errors": ["Faltan datos para crear las rubricas"]}

    if not structure.rubrics:
        print("No se encontraron rubricas en la estructura del curso. Omitiendo creacion.")
        return state

    print(f"Creando rubricas de Canvas para el curso {course_id}...")

    canvas_assignments = list_assignments.invoke({"course_id": course_id})
    for rubric in structure.rubrics:
        activity = _find_activity_for_rubric(structure, rubric)
        if not activity:
            print(f"No se encontro actividad asociada para la rubrica '{rubric.name}'. Omitiendo.")
            continue

        if not _is_evaluative(activity):
            print(f"La actividad '{activity.name}' es formativa. Omitiendo rubrica calificada.")
            continue

        assignment_id = _find_assignment_id(activity.name, canvas_assignment_ids, canvas_assignments)
        if not assignment_id:
            print(
                f"No se encontro assignment de Canvas para '{activity.name}'. "
                f"No se pudo asociar la rubrica '{rubric.name}'."
            )
            continue

        rubric_title = activity.name
        result = create_or_update_assignment_rubric.invoke(
            {
                "title": rubric_title,
                "criteria": _canvas_criteria_from_rubric(rubric),
                "assignment_id": assignment_id,
                "course_id": course_id,
                "use_for_grading": True,
            }
        )

        if "error" in result:
            print(
                f"Error creando rubrica '{rubric_title}' "
                f"(origen: '{rubric.name}'): {result['error']}"
            )
            return {**state, "errors": [f"Error creando rubrica: {rubric_title}"]}

        print(f"Rubrica '{rubric_title}' asociada a '{activity.name}' (origen: '{rubric.name}').")

    return state
