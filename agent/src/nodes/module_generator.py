from src.state import CourseState
from src.tools.canvas_api import create_module, list_modules, publish_module
from src.constants import INTRO_MODULE_NAME, CREDITS_MODULE_NAME
from src.nodes.base import fail, proceed, resolve_course_id


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
        return fail(state, "Pipeline detenido: errores en etapas previas")

    structure = state.get("course_structure")
    course_id = resolve_course_id(state)

    if not structure or not course_id:
        return fail(state, "Faltan datos para crear los módulos")

    print(f"Creando unidades (módulos Canvas) para el curso {course_id}...")

    existing_mods = list_modules.invoke({"course_id": course_id})
    existing_mods_by_name: dict[str, int] = {}
    if isinstance(existing_mods, list):
        for m in existing_mods:
            existing_mods_by_name[m.get("name", "").strip().lower()] = m.get("id")

    module_mapping: dict[str, int] = {}

    module_names = [INTRO_MODULE_NAME, CREDITS_MODULE_NAME, *(mod.name for mod in structure.modules)]
    for name in module_names:
        m_id = _get_or_create_module(name, course_id, existing_mods_by_name)
        if m_id:
            module_mapping[name] = m_id

    return proceed(state, module_mapping=module_mapping)
