from src.state import (
    CourseState,
    CourseStructure,
    PartialCourseStructure,
    PartialActivity,
    PartialModule,
    Activity,
    ScheduleItem,
)
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


def _document_text(doc_content: list[dict]) -> str:
    import re
    text = "\n\n".join(f"Tab: {tab['title']}\n{tab['content']}" for tab in doc_content)
    return re.sub(r"[\x00-\x1F\x7F]", " ", text)


def _merge_partial(existing: dict, incoming: PartialCourseStructure) -> dict:
    merged = dict(existing)
    for field in ("name", "academic_program", "semester", "academic_level", "credits", "teacher", "description"):
        value = getattr(incoming, field)
        if value not in ("", 0, None):
            merged[field] = value

    def merge_named(items, key="name"):
        result = {item.get(key, "").strip().lower(): item for item in merged.get(field_name, []) if item.get(key)}
        for item in items:
            item_dict = item.model_dump() if hasattr(item, "model_dump") else item
            item_key = item_dict.get(key, "").strip().lower()
            if not item_key:
                continue
            if item_key in result:
                result[item_key] = {**result[item_key], **{k: v for k, v in item_dict.items() if v not in ("", 0, [], None)}}
            else:
                result[item_key] = item_dict
        return list(result.values())

    for field_name in ("modules", "activities", "rubrics"):
        merged[field_name] = merge_named(getattr(incoming, field_name))

    for field_name in ("prerequisites", "learning_outcomes", "schedule"):
        values = [item.model_dump() if hasattr(item, "model_dump") else item for item in getattr(incoming, field_name)]
        current = merged.get(field_name, [])
        for value in values:
            if value not in current:
                current.append(value)
        merged[field_name] = current
    return merged


def _finalize_structure(data: dict) -> CourseStructure:
    return _enrich_activity_titles_and_types(
        _enrich_activity_unit_links(CourseStructure.model_validate(data))
    )


def analyst_node(state: CourseState) -> CourseState:
    """Procesa un fragmento del documento y acumula su estructura en el estado."""
    import re
    doc_id = state.get("doc_id")
    if not doc_id:
        return {**state, "is_valid": False, "errors": ["No doc_id provided in state"]}

    chunks = state.get("analysis_chunks")
    index = state.get("analysis_chunk_index", 0)
    if not chunks:
        print(f"Reading document {doc_id}...")
        doc_content = read_google_doc(doc_id)
        if not doc_content:
            return {**state, "is_valid": False, "errors": ["Failed to read Google Doc"]}
        full_text = _document_text(doc_content)
        chunk_size = int(getattr(config, "analysis_chunk_size", 12000))
        chunks = [full_text[pos:pos + chunk_size] for pos in range(0, len(full_text), chunk_size)] or [""]
        index = 0

    if index >= len(chunks):
        return {**state, "is_valid": False, "errors": ["No quedan fragmentos para analizar"]}

    teacher_info = state.get("teacher_info")
    if teacher_info is None and config.teacher_doc:
        teacher_content = read_google_doc(config.teacher_doc)
        teacher_info = _document_text(teacher_content) if teacher_content else ""

    system_prompt = (
        "Analiza SOLO el fragmento recibido de un documento curricular. Devuelve un fragmento parcial "
        "compatible con el esquema. Extrae únicamente datos explícitos; no inventes ni completes con conocimiento externo. "
        "Incluye actividades, módulos, resultados, cronograma y rúbricas sólo cuando aparezcan en este fragmento. "
        "Usa nombres de actividades cortos, module_name, resources y evaluation_type. "
        f"{activity_types_prompt_section()} "
        "Usa textos compactos, sin saltos de línea dentro de valores. Devuelve sólo la estructura solicitada."
    )
    human_prompt = f"Fragmento {index + 1} de {len(chunks)}:\n{chunks[index]}"
    if teacher_info:
        human_prompt += f"\n\nDatos del docente (contexto adicional):\n{teacher_info}"

    try:
        structured_llm = config.get_llm().with_structured_output(PartialCourseStructure)
        partial = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        if isinstance(partial, CourseStructure):
            merged = partial.model_dump()
            next_index = len(chunks)
        else:
            if not isinstance(partial, PartialCourseStructure):
                partial = PartialCourseStructure.model_validate(partial.model_dump() if hasattr(partial, "model_dump") else partial)
            merged = _merge_partial(state.get("analysis_partial_structure") or {}, partial)
            next_index = index + 1
        result = {**state, "analysis_chunks": chunks, "analysis_chunk_index": next_index,
                  "analysis_partial_structure": merged, "teacher_info": teacher_info, "errors": []}
        if next_index < len(chunks):
            return {**result, "is_valid": False, "course_structure": None}
        structure = _finalize_structure(merged)
        print("Course structure inferred successfully from all document fragments.")
        return {**result, "course_structure": structure, "is_valid": True}
    except Exception as e:
        print(f"Error during LLM inference: {str(e)}")
        return {**state, "is_valid": False, "errors": [f"Error during LLM inference: {str(e)}"]}
