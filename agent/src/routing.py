"""Funciones de enrutamiento condicional para el grafo LangGraph."""

from typing import List, Union

from langgraph.graph import END

from src.state import CourseState

CREATOR_NODES: List[str] = [
    "page_creator",
    "agenda_creator",
    "alignment_creator",
    "forum_creator",
    "credits_creator",
]


def has_errors(state: CourseState) -> bool:
    return bool(state.get("errors"))


def route_after_analyst(state: CourseState) -> str:
    if (
        state.get("is_valid")
        and state.get("course_structure")
        and not has_errors(state)
    ):
        return "setup_course"
    return END


def route_after_setup(state: CourseState) -> Union[str, List[str]]:
    if has_errors(state):
        return END
    if not state.get("canvas_course_id") or not state.get("course_structure"):
        return END
    return CREATOR_NODES


def route_after_modules(state: CourseState) -> str:
    if has_errors(state):
        return END
    mapping = state.get("module_mapping")
    if not mapping:
        return END
    return "activity_creator"
