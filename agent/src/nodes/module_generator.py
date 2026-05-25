from src.state import CourseState
from src.tools.canvas_api import create_module, add_item_to_module
from config import config

def module_generator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear los módulos en el curso de Canvas y poblarlos con páginas generales.
    """
    if state.get("errors"):
        return {**state, "errors": ["Pipeline detenido: errores en etapas de contenido"]}

    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id

    if not structure or not course_id:
        return {**state, "errors": ["Faltan datos para crear los módulos"]}

    print(f"Generando módulos para el curso {course_id}...")
    
    module_mapping = {}
    
    # 1. Crear módulo de Introducción al curso
    print("Creando módulo: Introducción al curso")
    intro_result = create_module.invoke({
        "name": "Introducción al curso",
        "course_id": course_id
    })
    
    if "error" not in intro_result:
        intro_id = intro_result.get("id")
        module_mapping["Introducción al curso"] = intro_id
        
        # Agregar Agenda de actividades
        if state.get("agenda_page_url"):
            print("Agregando Agenda de actividades al módulo Introducción al curso")
            add_item_to_module.invoke({
                "module_id": intro_id,
                "title": "Agenda de actividades",
                "type": "Page",
                "page_url": state.get("agenda_page_url"),
                "course_id": course_id
            })
            
        # Agregar Alineación de actividades
        if state.get("alignment_page_url"):
            print("Agregando Alineación de actividades al módulo Introducción al curso")
            add_item_to_module.invoke({
                "module_id": intro_id,
                "title": "Alineación de actividades",
                "type": "Page",
                "page_url": state.get("alignment_page_url"),
                "course_id": course_id
            })
            
        # Agregar Foro de dudas
        if state.get("forum_discussion_id"):
            print("Agregando Foro de dudas al módulo Introducción al curso")
            add_item_to_module.invoke({
                "module_id": intro_id,
                "title": "Foro de dudas",
                "type": "Discussion",
                "content_id": state.get("forum_discussion_id"),
                "course_id": course_id
            })

    # 2. Crear módulos de contenido
    for mod in structure.modules:
        print(f"Creando módulo: {mod.name}")
        result = create_module.invoke({
            "name": mod.name,
            "course_id": course_id
        })
        
        if "error" in result:
            print(f"Error al crear el módulo {mod.name}: {result['error']}")
            continue
            
        module_mapping[mod.name] = result.get("id")

    # 3. Crear módulo de Créditos al final
    print("Creando módulo: Créditos")
    credits_result = create_module.invoke({
        "name": "Créditos",
        "course_id": course_id
    })
    
    if "error" not in credits_result:
        credits_id = credits_result.get("id")
        module_mapping["Créditos"] = credits_id
        
        # Agregar página de créditos
        if state.get("credits_page_url"):
            print("Agregando página de Créditos al módulo Créditos")
            add_item_to_module.invoke({
                "module_id": credits_id,
                "title": "Créditos",
                "type": "Page",
                "page_url": state.get("credits_page_url"),
                "course_id": course_id
            })

    return {
        **state,
        "module_mapping": module_mapping
    }
