from src.state import CourseState
from src.tools.canvas_api import create_module, list_modules, publish_module
from src.routing import INTRO_MODULE_NAME, CREDITS_MODULE_NAME
from config import config


def _get_or_create_module(
    name: str,
    course_id: str,
    existing_mods_by_name: dict,
):
    name_lower = name.strip().lower()
    if name_lower in existing_mods_by_name:
        m_id = existing_mods_by_name[name_lower]
        print(f"El modulo '{name}' ya existe. ID: {m_id}")
        publish_result = publish_module.invoke({"module_id": m_id, "course_id": course_id})
        if "error" in publish_result:
            print(f"No se pudo publicar el modulo existente '{name}': {publish_result['error']}")
        return m_id

    print(f"Creando módulo: {name}")
    result = create_module.invoke({"name": name, "course_id": course_id})
    if "error" not in result:
        m_id = result.get("id")
        existing_mods_by_name[name_lower] = m_id
        return m_id

    print(f"Error al crear el módulo '{name}': {result['error']}")
    return None


def module_generator_node(state: CourseState) -> CourseState:
    """
    Crea los módulos vacíos en Canvas: introducción, créditos y las unidades del programa.
    No requiere LLM; itera sobre la estructura del curso en el estado.
    """
    if state.get("errors"):
        return {**state, "errors": ["Pipeline detenido: errores en etapas previas"]}

    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id

    if not structure or not course_id:
        return {**state, "errors": ["Faltan datos para crear los módulos"]}

    print(f"Creando unidades (módulos Canvas) para el curso {course_id}...")

    existing_mods = list_modules.invoke({"course_id": course_id})
    existing_mods_by_name: dict[str, int] = {}
    if isinstance(existing_mods, list):
        for m in existing_mods:
            existing_mods_by_name[m.get("name", "").strip().lower()] = m.get("id")

    module_mapping: dict[str, int] = {}

    intro_id = _get_or_create_module(INTRO_MODULE_NAME, course_id, existing_mods_by_name)
    if intro_id:
        module_mapping[INTRO_MODULE_NAME] = intro_id

    credits_id = _get_or_create_module(CREDITS_MODULE_NAME, course_id, existing_mods_by_name)
    if credits_id:
        module_mapping[CREDITS_MODULE_NAME] = credits_id

    for mod in structure.modules:
        m_id = _get_or_create_module(mod.name, course_id, existing_mods_by_name)
        if m_id:
            module_mapping[mod.name] = m_id

    return {**state, "module_mapping": module_mapping}
