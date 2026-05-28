from src.state import CourseState
from src.tools.canvas_api import add_item_to_module
from src.routing import INTRO_MODULE_NAME, CREDITS_MODULE_NAME
from config import config


def populate_special_modules_node(state: CourseState) -> CourseState:
    """
    Añade al módulo de introducción (agenda, alineación, foro) y al de créditos
    la página correspondiente, una vez creadas las páginas y el foro.
    """
    if state.get("errors"):
        return {**state, "errors": ["Pipeline detenido: errores en etapas de contenido"]}

    course_id = state.get("canvas_course_id") or config.course_id
    module_mapping = state.get("module_mapping") or {}

    if not course_id or not module_mapping:
        return {**state, "errors": ["Faltan datos para poblar módulos especiales"]}

    intro_id = module_mapping.get(INTRO_MODULE_NAME)
    if intro_id:
        if state.get("agenda_page_url"):
            print("Agregando Agenda de actividades al módulo Introducción al curso y ayuda")
            add_item_to_module.invoke({
                "module_id": intro_id,
                "title": "Agenda de actividades",
                "type": "Page",
                "page_url": state.get("agenda_page_url"),
                "course_id": course_id,
            })

        if state.get("alignment_page_url"):
            print("Agregando Alineación de actividades al módulo Introducción al curso y ayuda")
            add_item_to_module.invoke({
                "module_id": intro_id,
                "title": "Alineación de actividades",
                "type": "Page",
                "page_url": state.get("alignment_page_url"),
                "course_id": course_id,
            })

        if state.get("forum_discussion_id"):
            print("Agregando Foro de dudas al módulo Introducción al curso y ayuda")
            add_item_to_module.invoke({
                "module_id": intro_id,
                "title": "Foro de dudas",
                "type": "Discussion",
                "content_id": state.get("forum_discussion_id"),
                "course_id": course_id,
            })

    credits_id = module_mapping.get(CREDITS_MODULE_NAME)
    if credits_id and state.get("credits_page_url"):
        print("Agregando página de Créditos al módulo Créditos")
        add_item_to_module.invoke({
            "module_id": credits_id,
            "title": "Créditos",
            "type": "Page",
            "page_url": state.get("credits_page_url"),
            "course_id": course_id,
        })

    return {}
