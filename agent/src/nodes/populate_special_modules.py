from src.constants import (
    AGENDA_PAGE_TITLE,
    ALIGNMENT_PAGE_TITLE,
    CREDITS_MODULE_NAME,
    CREDITS_PAGE_TITLE,
    FORUM_TITLE,
    INTRO_MODULE_NAME,
)
from src.nodes.base import fail, resolve_course_id
from src.state import CourseState
from src.tools.canvas_api import add_item_to_module

# (módulo destino, título del ítem, tipo Canvas, clave del estado, campo del ítem)
SPECIAL_MODULE_ITEMS = (
    (INTRO_MODULE_NAME, AGENDA_PAGE_TITLE, "Page", "agenda_page_url", "page_url"),
    (INTRO_MODULE_NAME, ALIGNMENT_PAGE_TITLE, "Page", "alignment_page_url", "page_url"),
    (INTRO_MODULE_NAME, FORUM_TITLE, "Discussion", "forum_discussion_id", "content_id"),
    (CREDITS_MODULE_NAME, CREDITS_PAGE_TITLE, "Page", "credits_page_url", "page_url"),
)


def populate_special_modules_node(state: CourseState) -> CourseState:
    """
    Añade al módulo de introducción (agenda, alineación, foro) y al de créditos
    la página correspondiente, una vez creadas las páginas y el foro.
    """
    if state.get("errors"):
        return fail(state, "Pipeline detenido: errores en etapas de contenido")

    course_id = resolve_course_id(state)
    module_mapping = state.get("module_mapping") or {}

    if not course_id or not module_mapping:
        return fail(state, "Faltan datos para poblar módulos especiales")

    for module_name, title, item_type, state_key, item_field in SPECIAL_MODULE_ITEMS:
        module_id = module_mapping.get(module_name)
        value = state.get(state_key)
        if not module_id or not value:
            continue

        print(f"Agregando {title} al módulo {module_name}")
        add_item_to_module.invoke({
            "module_id": module_id,
            "title": title,
            "type": item_type,
            item_field: value,
            "course_id": course_id,
        })

    return {}
