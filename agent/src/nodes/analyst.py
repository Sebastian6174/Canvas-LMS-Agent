from src.state import CourseState, CourseStructure, Activity, ScheduleItem
from src.tools.doc_parser import read_google_doc
from src.activity_types import (
    activity_types_prompt_section,
    normalize_activity_type,
    format_activity_display_name,
    infer_evaluation_type,
)
from config import config
from langchain_core.messages import HumanMessage, SystemMessage
from src.utils.helpers import (
    canonical_unit_names_by_number,
    resolve_canonical_module_name,
)


def _resolve_activity_key(name: str, mapping: dict[str, str]) -> str:
    """Mapea un nombre de actividad (corto o display) al nombre display final."""
    if name in mapping:
        return mapping[name]
    lower = name.strip().lower()
    for key, display in mapping.items():
        if key.strip().lower() == lower or display.strip().lower() == lower:
            return display
    return name


def _enrich_activity_unit_links(structure: CourseStructure) -> CourseStructure:
    """Completa y normaliza module_name desde modules[].activities o el campo del LLM."""
    activity_to_unit: dict[str, str] = {}
    for unit in structure.modules:
        for act_name in unit.activities:
            activity_to_unit[act_name] = unit.name

    canonical_by_number = canonical_unit_names_by_number(structure.modules)
    enriched: list[Activity] = []
    for act in structure.activities:
        module_name = act.module_name.strip() or activity_to_unit.get(act.name, "")
        if not module_name:
            lower_name = act.name.strip().lower()
            for act_key, unit_name in activity_to_unit.items():
                if act_key.strip().lower() == lower_name:
                    module_name = unit_name
                    break

        module_name = resolve_canonical_module_name(module_name, canonical_by_number)
        enriched.append(act.model_copy(update={"module_name": module_name}))

    return structure.model_copy(update={"activities": enriched})


def _enrich_activity_titles_and_types(structure: CourseStructure) -> CourseStructure:
    """Asigna número, normaliza tipo, evaluation_type y nombre display en todo el syllabus."""
    name_mapping: dict[str, str] = {}
    enriched_activities: list[Activity] = []

    for index, act in enumerate(structure.activities, start=1):
        activity_type = normalize_activity_type(act.activity_type)
        evaluation_type = infer_evaluation_type(act.weight, act.evaluation_type or None)
        display_name = format_activity_display_name(index, activity_type, act.name)
        name_mapping[act.name] = display_name
        enriched_activities.append(
            act.model_copy(
                update={
                    "number": index,
                    "activity_type": activity_type,
                    "evaluation_type": evaluation_type,
                    "name": display_name,
                }
            )
        )

    enriched_modules = [
        unit.model_copy(
            update={
                "activities": [
                    _resolve_activity_key(act_name, name_mapping)
                    for act_name in unit.activities
                ]
            }
        )
        for unit in structure.modules
    ]

    enriched_schedule: list[ScheduleItem] = []
    for item in structure.schedule:
        enriched_schedule.append(
            item.model_copy(
                update={
                    "activity_name": _resolve_activity_key(item.activity_name, name_mapping)
                }
            )
        )

    return structure.model_copy(
        update={
            "activities": enriched_activities,
            "modules": enriched_modules,
            "schedule": enriched_schedule,
        }
    )


def analyst_node(state: CourseState) -> CourseState:
    """
    Analyst node that reads a Google Doc and infers the course structure.
    """
    doc_id = state.get("doc_id")
    if not doc_id:
        return {**state, "is_valid": False, "errors": ["No doc_id provided in state"]}

    # Read the document
    print(f"Reading document {doc_id}...")
    doc_content = read_google_doc(doc_id)
    if not doc_content:
        return {**state, "is_valid": False, "errors": ["Failed to read Google Doc"]}

    # Prepare the text for the LLM
    import re
    full_text = ""
    for tab in doc_content:
        full_text += f"Tab: {tab['title']}\n{tab['content']}\n\n"

    # Preprocesamiento agresivo: Eliminar todos los caracteres de control (0x00 a 0x1F)
    full_text = re.sub(r"[\x00-\x1F\x7F]", " ", full_text)

    # Read teacher document if configured
    teacher_info_text = None
    if config.teacher_doc:
        print(f"Reading teacher document {config.teacher_doc}...")
        teacher_content = read_google_doc(config.teacher_doc)
        if teacher_content:
            teacher_info_text = ""
            for tab in teacher_content:
                teacher_info_text += f"Tab: {tab['title']}\n{tab['content']}\n\n"
            teacher_info_text = re.sub(r"[\x00-\x1F\x7F]", " ", teacher_info_text)

    # Initialize LLM with structured output
    print("Inferring course structure using LLM...")
    llm = config.get_llm()
    structured_llm = llm.with_structured_output(CourseStructure)

    system_prompt = (
        "Eres un experto en diseño instruccional y análisis de currículo. "
        "Tu tarea es analizar el contenido de un documento que describe un curso y extraer su estructura. "
        "Debes identificar al docente, descripción del curso, resultados de aprendizaje, unidades, actividades, cronograma y rúbricas. "
        "IMPORTANTE: NO asumas ni inventes información. Extrae la información EXACTA proporcionada en el documento. "
        "Para la descripción del curso y otros campos descriptivos, extrae el texto de forma íntegra y completa, tal como aparece en el documento original, SIN RESUMIR. "
        "Si algún dato requerido no se encuentra en el documento, omítelo o déjalo en blanco; bajo ningún concepto debes inventarlo. "
        "En el cronograma ('schedule'), solo usa el 'activity_name' que coincida con el nombre de una actividad definida en la lista de 'activities'. "
        "No repitas el objeto Activity completo dentro del schedule. "
        "En 'modules' incluye solo las unidades de contenido del programa académico. "
        "Nunca uses el término 'eje temático': cada unidad debe nombrarse como 'Unidad N' seguido del título si aparece en el documento (ej. 'Unidad 1. El conflicto'). "
        "Cada actividad en 'activities' debe incluir 'module_name' con el nombre exacto de su unidad (igual que modules[].name) "
        "y 'resources' con los recursos o materiales de estudio de esa actividad tal como figuran en el documento (lista vacía si no hay). "
        "En cada unidad de 'modules', lista en 'activities' solo los nombres cortos de las actividades de ESA unidad. "
        "Además, debes extraer todas las rúbricas de evaluación del curso y agregarlas a la lista 'rubrics'. "
        "Para cada rúbrica, identifica su nombre/identificador correcto (por ejemplo, 'Rúbrica N. 1', 'Rúbrica 2', etc.) "
        "y su lista de criterios. En cada criterio debes extraer: "
        "- 'name': el nombre/descripción del criterio "
        "- 'points': los puntos si se indican explícitamente en el texto del criterio (como número decimal, o dejarlo en blanco si no se indica) "
        "- 'excelente', 'en_desarrollo', 'basico', 'insuficiente': las descripciones de los niveles correspondientes. "
        "Asocia cada actividad con su rúbrica correspondiente mediante el campo 'rubric' de la actividad. "
        "Ten en cuenta que algunas actividades no tienen rúbrica (en cuyo caso su campo 'rubric' debe ser null o 'N/A') "
        "y que a veces el número de la rúbrica no coincide con el número de actividad (por ejemplo, la actividad 1 no tiene rúbrica y la actividad 3 usa la 'Rúbrica N. 1'). "
        "Infiere correctamente la correspondencia basándote en la información de las tablas de cada actividad y los encabezados de las tablas de rúbricas (ej. si una sección rotulada como 'Rúbrica No. 2' en la pestaña 'No4' corresponde a la actividad 8 que declara usar la 'Rúbrica 4', infiere que su nombre correcto es 'Rúbrica 4' o asóciala adecuadamente con la actividad 8)."
        f"{activity_types_prompt_section()} "
        "REGLA CRÍTICA PARA EL JSON: Para evitar errores de formato (Invalid JSON control character), DEBES REEMPLAZAR todos los saltos de línea físicos por un simple espacio en blanco dentro de cualquier texto que extraigas. NO dejes saltos de línea literales (enters) ni uses '\\n' en los valores de texto."
    )

    human_prompt = f"Aquí está el contenido del documento:\n\n{full_text}"

    try:
        inferred_structure = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        inferred_structure = _enrich_activity_unit_links(inferred_structure)
        inferred_structure = _enrich_activity_titles_and_types(inferred_structure)

        print("Course structure inferred successfully.")
        return {
            **state,
            "course_structure": inferred_structure,
            "teacher_info": teacher_info_text,
            "is_valid": True,
            "errors": [],
        }
    except Exception as e:
        print(f"Error during LLM inference: {str(e)}")
        return {
            **state,
            "is_valid": False,
            "errors": [f"Error during LLM inference: {str(e)}"],
        }
