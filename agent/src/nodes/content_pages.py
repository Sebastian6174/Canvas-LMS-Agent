"""
Nodos de contenido que corren en paralelo tras crear los módulos: agenda,
alineación, créditos y foro. Todos arman su HTML sólo con datos del estado.

Como corren en paralelo, cada uno devuelve únicamente las claves que escribe.
"""

from typing import Callable

from config import config
from src.constants import AGENDA_PAGE_TITLE, ALIGNMENT_PAGE_TITLE, CREDITS_PAGE_TITLE, FORUM_TITLE
from src.nodes.base import resolve_course_id
from src.pages.agenda import build_agenda_html
from src.pages.alignment import build_alignment_html
from src.pages.credits import build_credits_html
from src.pages.forum import build_forum_html
from src.pages.html import CourseLinks
from src.state import CourseState, CourseStructure
from src.tools.canvas_api import create_discussion_topic, create_page

PageBuilder = Callable[[CourseStructure, CourseLinks, CourseState], str]


def _context(state: CourseState):
    structure = state.get("course_structure")
    course_id = resolve_course_id(state)
    if not structure or not course_id:
        return None
    return structure, course_id, CourseLinks(state.get("course_files_map"), config.domain, course_id)


def _page_node(title: str, state_key: str, label: str, build: PageBuilder):
    def node(state: CourseState) -> dict:
        context = _context(state)
        if context is None:
            return {"errors": [f"Faltan datos para crear la página de {label}"]}
        structure, course_id, links = context

        print(f"Generando página de {label} para el curso {course_id}...")
        result = create_page.invoke({
            "title": title,
            "body": build(structure, links, state),
            "course_id": course_id,
        })
        if "error" in result:
            print(f"Error al crear la página de {label}: {result['error']}")
            return {"errors": [f"Error creando {label}"]}

        page_url = result.get("url")
        print(f"Página de {label} creada exitosamente: {page_url}")
        return {state_key: page_url}

    node.__name__ = f"{state_key}_node"
    return node


agenda_creator_node = _page_node(
    AGENDA_PAGE_TITLE, "agenda_page_url", "agenda",
    lambda structure, links, state: build_agenda_html(structure, links),
)

alignment_creator_node = _page_node(
    ALIGNMENT_PAGE_TITLE, "alignment_page_url", "alineación",
    lambda structure, links, state: build_alignment_html(structure, links),
)

credits_creator_node = _page_node(
    CREDITS_PAGE_TITLE, "credits_page_url", "créditos",
    lambda structure, links, state: build_credits_html(
        structure.teacher, state.get("teacher_info") or "", links
    ),
)


def forum_creator_node(state: CourseState) -> dict:
    """Crea (o actualiza) el foro de dudas del curso."""
    context = _context(state)
    if context is None:
        return {"errors": ["Faltan datos para crear el foro de dudas"]}
    structure, course_id, links = context

    print(f"Generando foro de dudas para el curso {course_id}...")
    result = create_discussion_topic.invoke({
        "title": FORUM_TITLE,
        "message": build_forum_html(links),
        "course_id": course_id,
    })
    if "error" in result:
        print(f"Error al crear el foro de dudas: {result['error']}")
        return {"errors": ["Error creando foro"]}

    discussion_id = result.get("id")
    print(f"Foro de dudas creado exitosamente con ID: {discussion_id}")
    return {"forum_discussion_id": discussion_id}
