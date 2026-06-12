import re
from typing import Optional

from config import config
from src.state import CourseState, Rubric
from src.tools.canvas_api import create_or_update_assignment_rubric, list_assignments


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


def _canvas_criteria_from_rubric(rubric: Rubric) -> list[dict]:
    criteria = []
    for index, criterion in enumerate(rubric.criteria, start=1):
        max_points = float(criterion.points or 4)
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

        assignment_id = _find_assignment_id(activity.name, canvas_assignment_ids, canvas_assignments)
        if not assignment_id:
            print(
                f"No se encontro assignment de Canvas para '{activity.name}'. "
                f"No se pudo asociar la rubrica '{rubric.name}'."
            )
            continue

        result = create_or_update_assignment_rubric.invoke(
            {
                "title": rubric.name,
                "criteria": _canvas_criteria_from_rubric(rubric),
                "assignment_id": assignment_id,
                "course_id": course_id,
                "use_for_grading": True,
            }
        )

        if "error" in result:
            print(f"Error creando rubrica '{rubric.name}': {result['error']}")
            return {**state, "errors": [f"Error creando rubrica: {rubric.name}"]}

        print(f"Rubrica '{rubric.name}' asociada a '{activity.name}'.")

    return state
