from config import config
from src.constants import ACTIVITIES_HEADER_TITLE
from src.nodes.base import fail, proceed, resolve_course_id
from src.pages.html import CourseLinks
from src.pages.unit import (
    build_unit_intro_html,
    build_unit_materials_html,
    unit_intro_page_title,
    unit_materials_page_title,
)
from src.state import CourseState
from src.tools.canvas_api import add_item_to_module, create_page


def unit_pages_creator_node(state: CourseState) -> CourseState:
    """
    Crea al inicio de cada unidad la página de introducción (presentación, RA e
    indicadores), la de materiales de estudio y el encabezado "Actividades".
    """
    if state.get("errors"):
        return proceed(state)

    structure = state.get("course_structure")
    course_id = resolve_course_id(state)
    module_mapping = state.get("module_mapping") or {}

    if not structure or not course_id:
        return fail(state, "Faltan datos para crear páginas de unidad")

    if not module_mapping:
        return fail(state, "No hay unidades creadas en Canvas para añadir páginas")

    print(f"Creando páginas de unidad para el curso {course_id}...")
    links = CourseLinks(state.get("course_files_map"), config.domain, course_id)

    for unit_index, unit in enumerate(structure.modules, start=1):
        mod_id = module_mapping.get(unit.name)
        if not mod_id:
            print(f"No se encontró módulo Canvas para la unidad '{unit.name}'. Omitiendo páginas.")
            continue

        number = unit.number or unit_index
        pages = [
            (unit_intro_page_title(number), build_unit_intro_html(structure, unit, links)),
            (unit_materials_page_title(number), build_unit_materials_html(structure, unit, links)),
        ]

        for position, (page_title, body) in enumerate(pages, start=1):
            result = create_page.invoke({"title": page_title, "body": body, "course_id": course_id})
            if "error" in result:
                print(f"Error al crear página '{page_title}': {result['error']}")
                continue

            page_url = result.get("url")
            if not page_url:
                print(f"La página '{page_title}' no devolvió URL. Omitiendo del módulo.")
                continue

            print(f"Agregando '{page_title}' a la unidad {unit.name}")
            add_item_to_module.invoke({
                "module_id": mod_id,
                "title": page_title,
                "type": "Page",
                "page_url": page_url,
                "course_id": course_id,
                "position": position,
            })

        print(f"Agregando encabezado '{ACTIVITIES_HEADER_TITLE}' a la unidad {unit.name}")
        add_item_to_module.invoke({
            "module_id": mod_id,
            "title": ACTIVITIES_HEADER_TITLE,
            "type": "SubHeader",
            "course_id": course_id,
            "position": len(pages) + 1,
        })

    return proceed(state)
