from src.state import CourseState
from src.tools.canvas_api import create_page, add_item_to_module
from src.utils.helpers import (
    unit_intro_page_title,
    unit_materials_page_title,
    build_course_banner_html,
    build_unit_intro_page_body,
    build_unit_materials_page_body,
    collect_unit_resources,
    resolve_html_links,
)
from config import config

ACTIVITIES_HEADER_TITLE = "Actividades"


def unit_pages_creator_node(state: CourseState) -> CourseState:
    """
    Crea en cada unidad dos páginas Canvas antes de las actividades:
    introducción/resultados (solo título) y materiales de estudio (banner + recursos).
    """
    if state.get("errors"):
        return state

    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    module_mapping = state.get("module_mapping") or {}
    files_map = state.get("course_files_map") or {}

    if not structure or not course_id:
        return {**state, "errors": ["Faltan datos para crear páginas de unidad"]}

    if not module_mapping:
        return {**state, "errors": ["No hay unidades creadas en Canvas para añadir páginas"]}

    print(f"Creando páginas de unidad para el curso {course_id}...")

    banner_html = build_course_banner_html(files_map, config.domain, course_id)
    banner_html = resolve_html_links(banner_html, files_map, config.domain, course_id)

    for unit_index, unit in enumerate(structure.modules, start=1):
        mod_id = module_mapping.get(unit.name)
        if not mod_id:
            print(f"No se encontró módulo Canvas para la unidad '{unit.name}'. Omitiendo páginas.")
            continue

        intro_title = unit_intro_page_title(unit_index)
        materials_title = unit_materials_page_title(unit_index)
        unit_resources = collect_unit_resources(structure.activities, unit.name)

        pages = [
            (intro_title, build_unit_intro_page_body(intro_title)),
            (
                materials_title,
                build_unit_materials_page_body(banner_html, unit_resources),
            ),
        ]

        for page_title, body in pages:
            resolved_body = resolve_html_links(body, files_map, config.domain, course_id)
            result = create_page.invoke({
                "title": page_title,
                "body": resolved_body,
                "course_id": course_id,
            })
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
            })

        print(f"Agregando encabezado '{ACTIVITIES_HEADER_TITLE}' a la unidad {unit.name}")
        add_item_to_module.invoke({
            "module_id": mod_id,
            "title": ACTIVITIES_HEADER_TITLE,
            "type": "SubHeader",
            "course_id": course_id,
        })

    return state
