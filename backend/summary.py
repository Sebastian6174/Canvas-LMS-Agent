from __future__ import annotations

from typing import Any


def summarize_state(state: dict[str, Any]) -> dict[str, Any]:
    structure = _model_dump(state.get("course_structure"))
    modules = _items_from_structure(structure, "modules")
    activities = _items_from_structure(structure, "activities")

    return {
        "canvasCourseId": state.get("canvas_course_id"),
        "isValid": state.get("is_valid", False),
        "errors": state.get("errors") or [],
        "course": _course_summary(structure, modules, activities),
        "urls": _urls_summary(state),
        "forumDiscussionId": state.get("forum_discussion_id"),
        "moduleMapping": state.get("module_mapping") or {},
        "canvasAssignmentIds": state.get("canvas_assignment_ids") or {},
    }


def _model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _items_from_structure(structure: Any, key: str) -> list:
    if not isinstance(structure, dict):
        return []
    return structure.get(key, [])


def _course_summary(structure: Any, modules: list, activities: list) -> dict[str, Any]:
    if not isinstance(structure, dict):
        structure = {}
    return {
        "name": structure.get("name"),
        "academicProgram": structure.get("academic_program"),
        "semester": structure.get("semester"),
        "teacher": structure.get("teacher"),
        "modulesCount": len(modules),
        "activitiesCount": len(activities),
    }


def _urls_summary(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "agenda": state.get("agenda_page_url"),
        "alignment": state.get("alignment_page_url"),
        "credits": state.get("credits_page_url"),
        "syllabus": state.get("syllabus_page_url"),
    }
