from src.state import (
    CourseState,
    CourseStructure,
    PartialCourseStructure,
    PartialActivity,
    PartialModule,
    Activity,
    ScheduleItem,
    Module,
    Rubric,
    RubricCriterion,
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
from pydantic import BaseModel, Field
from typing import List, Optional


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

    enriched: list[Activity] = []
    for act in structure.activities:
        module_name = act.module_name.strip() or activity_to_unit.get(act.name, "")
        if not module_name:
            lower_name = act.name.strip().lower()
            for act_key, unit_name in activity_to_unit.items():
                if act_key.strip().lower() == lower_name:
                    module_name = unit_name
                    break

        # Resolve exact unit name from modules
        existing_unit = next((m.name for m in structure.modules if m.name.strip().lower() == module_name.strip().lower()), module_name)
        enriched.append(act.model_copy(update={"module_name": existing_unit}))

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

        chunks = state.get("analysis_chunks")  # Removed conflict markers
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
class CourseMetadata(BaseModel):
    name: str = Field(description="Nombre completo del curso")
    academic_program: str = Field(description="Programa académico o facultad")
    semester: int = Field(description="Semestre del curso")
    academic_level: str = Field(description="Nivel académico")
    credits: int = Field(description="Número de créditos")
    prerequisites: List[str] = Field(default_factory=list)
    teacher: str = Field(default="")
    description: str = Field(default="")
    learning_outcomes: List[str] = Field(default_factory=list)


class ModuleExtraction(BaseModel):
    name: str
    description: str = ""


class ModulesList(BaseModel):
    modules: List[ModuleExtraction] = Field(default_factory=list)


class ActivitySkeleton(BaseModel):
    name: str
    activity_type: str = "Otros"
    evaluation_type: str = ""
    weight: float = 0
    module_name: str = ""
    related_learning_outcome: str = ""


class ActivitiesSkeletonList(BaseModel):
    activities: List[ActivitySkeleton] = Field(default_factory=list)


class ScheduleExtractionList(BaseModel):
    schedule: List[ScheduleItem] = Field(default_factory=list)


class RubricAssociation(BaseModel):
    rubric_name: str
    activity_name: str


class RubricsList(BaseModel):
    rubrics: List[Rubric] = Field(default_factory=list)
    associations: List[RubricAssociation] = Field(default_factory=list)


def extract_modules_node(state: CourseState) -> CourseState:
    """Fase 2: Extrae la lista de módulos/unidades del syllabus."""
    if state.get("errors"):
        return state

    full_text = state.get("downloadable_program") or ""
    current_structure = state.get("course_structure")
    if not current_structure:
        return {**state, "errors": ["No course structure found in modules phase"]}

    print("Extracting course modules...")
    llm = config.get_llm()
    structured_llm = llm.with_structured_output(ModulesList)

    system_prompt = (
        "Eres un experto en diseño instruccional. Tu tarea es extraer la lista completa de unidades o módulos de aprendizaje del syllabus.\n"
        "Nunca uses el término 'eje temático': cada unidad debe nombrarse como 'Unidad N' seguido del título si aparece (ej. 'Unidad 1. El conflicto').\n"
        "REGLA CRÍTICA PARA EL JSON: Reemplaza saltos de línea físicos por un simple espacio en blanco."
    )

    human_prompt = f"Contenido del syllabus:\n\n{full_text}"

    try:
        extracted = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])

        modules = []
        for m in extracted.modules:
            modules.append(
                Module(
                    name=m.name,
                    description=m.description,
                    activities=[]
                )
            )

        updated_structure = current_structure.model_copy(update={"modules": modules})
        return {
            **state,
            "course_structure": updated_structure,
        }
    except Exception as e:
        print(f"Error during modules extraction: {str(e)}")
        return {
            **state,
            "errors": [f"Error during modules extraction: {str(e)}"],
        }


def extract_activities_list_node(state: CourseState) -> CourseState:
    """Fase 3: Extrae el esqueleto básico de las actividades."""
    if state.get("errors"):
        return state

    full_text = state.get("downloadable_program") or ""
    current_structure = state.get("course_structure")
    if not current_structure:
        return {**state, "errors": ["No course structure found in activities phase"]}

    print("Extracting activities skeleton list...")
    llm = config.get_llm()
    structured_llm = llm.with_structured_output(ActivitiesSkeletonList)

    system_prompt = (
        "Eres un experto en diseño instruccional. Tu tarea es extraer la lista de todas las actividades del curso.\n"
        "Para cada actividad extrae:\n"
        "- name: título de la actividad (corto, sin el prefijo 'Actividad N.')\n"
        "- activity_type: Foro, Quiz, Tarea, Videoconferencia u Otros\n"
        "- evaluation_type: Formativa o Evaluativa\n"
        "- weight: ponderación de la nota final (0 a 100)\n"
        "- module_name: nombre del módulo al que pertenece de la siguiente lista:\n"
        f"{', '.join([m.name for m in current_structure.modules])}\n\n"
        "REGLA CRÍTICA PARA EL JSON: Reemplaza saltos de línea físicos por un simple espacio en blanco."
    )

    human_prompt = f"Contenido del syllabus:\n\n{full_text}"

    try:
        extracted = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])

        activities = []
        for a in extracted.activities:
            activities.append(
                Activity(
                    name=a.name,
                    description="Detalles pendientes",
                    duration=0,
                    activity_type=a.activity_type,
                    evaluation_type=a.evaluation_type,
                    related_learning_outcome=a.related_learning_outcome or "",
                    weight=a.weight,
                    delivery_form="",
                    module_name=a.module_name,
                    resources=[]
                )
            )

        # Update modules activities mappings
        modules = []
        for m in current_structure.modules:
            mod_copy = m.model_copy()
            mod_copy.activities = [act.name for act in activities if act.module_name.strip().lower() == m.name.strip().lower()]
            modules.append(mod_copy)

        updated_structure = current_structure.model_copy(update={
            "activities": activities,
            "modules": modules
        })
        return {
            **state,
            "course_structure": updated_structure,
        }
    except Exception as e:
        print(f"Error during activities list extraction: {str(e)}")
        return {
            **state,
            "errors": [f"Error during activities list extraction: {str(e)}"],
        }


def extract_schedule_node(state: CourseState) -> CourseState:
    """Fase 4: Extrae el cronograma (schedule)."""
    if state.get("errors"):
        return state

    full_text = state.get("downloadable_program") or ""
    current_structure = state.get("course_structure")
    if not current_structure:
        return {**state, "errors": ["No course structure found in schedule phase"]}

    print("Extracting schedule...")
    llm = config.get_llm()
    structured_llm = llm.with_structured_output(ScheduleExtractionList)

    system_prompt = (
        "Eres un experto en diseño instruccional. Tu tarea es extraer la tabla de cronograma o secuencia temporal (semanal) de las actividades.\n"
        "El activity_name debe coincidir con el nombre de una de las siguientes actividades:\n"
        f"{', '.join([a.name for a in current_structure.activities])}\n\n"
        "REGLA CRÍTICA PARA EL JSON: Reemplaza saltos de línea físicos por un espacio."
    )

    human_prompt = f"Contenido del syllabus:\n\n{full_text}"

    try:
        extracted = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])

        updated_structure = current_structure.model_copy(update={"schedule": extracted.schedule})
        return {
            **state,
            "course_structure": updated_structure,
        }
    except Exception as e:
        print(f"Error during schedule extraction: {str(e)}")
        return {
            **state,
            "errors": [f"Error during schedule extraction: {str(e)}"],
        }


def extract_rubrics_list_node(state: CourseState) -> CourseState:
    """Fase 5: Extrae rúbricas y las asocia a las actividades."""
    if state.get("errors"):
        return state

    full_text = state.get("downloadable_program") or ""
    current_structure = state.get("course_structure")
    if not current_structure:
        return {**state, "errors": ["No course structure found in rubrics phase"]}

    print("Extracting rubrics...")
    llm = config.get_llm()
    structured_llm = llm.with_structured_output(RubricsList)

    system_prompt = (
        "Eres un experto en diseño instruccional. Tu tarea es extraer las rúbricas de evaluación del curso.\n"
        "Para cada rúbrica, identifica su nombre (ej: 'Rúbrica N. 1') y su lista de criterios detallados con los niveles Excelente, En desarrollo, Básico e Insuficiente con sus puntos.\n"
        "Asocia cada actividad en 'activities' con su rúbrica correspondiente rellenando las asociaciones correspondientes.\n"
        "REGLA CRÍTICA PARA EL JSON: Reemplaza saltos de línea físicos por un espacio."
    )

    human_prompt = f"Contenido del syllabus:\n\n{full_text}"

    try:
        extracted = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])

        activities = []
        for a in current_structure.activities:
            act_copy = a.model_copy()
            # Apply association mapping
            for assoc in extracted.associations:
                if assoc.activity_name.strip().lower() in a.name.strip().lower() or a.name.strip().lower() in assoc.activity_name.strip().lower():
                    act_copy.rubric = assoc.rubric_name
            activities.append(act_copy)

        updated_structure = current_structure.model_copy(update={
            "rubrics": extracted.rubrics,
            "activities": activities
        })

        # Prepare lists to enrich in the next stage
        activities_to_enrich = [act.name for act in updated_structure.activities]

        is_valid = False
        if not activities_to_enrich:
            is_valid = True

        return {
            **state,
            "course_structure": updated_structure,
            "activities_to_enrich": activities_to_enrich,
            "is_valid": is_valid,
        }
    except Exception as e:
        print(f"Error during rubrics extraction: {str(e)}")
        return {
            **state,
            "errors": [f"Error during rubrics extraction: {str(e)}"],
        }


# ========================================================
# Modelos y Nodo para Enriquecer Actividades por Lotes
# ========================================================

class ActivityDetails(BaseModel):
    name: str = Field(description="Nombre exacto de la actividad (debe coincidir o ser muy similar)")
    description: str = Field(description="Descripción e instrucciones paso a paso completas, detalladas e íntegras de la actividad tal como figuran en el documento.")
    duration: int = Field(default=0, description="Dedicación en horas")
    delivery_form: str = Field(default="", description="Forma de entrega de la actividad")
    resources: List[str] = Field(default_factory=list, description="Recursos o materiales de estudio explícitos para la actividad")


class ActivityEnrichmentBatch(BaseModel):
    activities: List[ActivityDetails] = Field(description="Lote de actividades detalladas")


def enrich_activities_node(state: CourseState) -> CourseState:
    """Fase 6: Extrae en detalle las descripciones y entregables en lotes pequeños."""
    if state.get("errors"):
        return state

    activities_to_enrich = state.get("activities_to_enrich") or []
    current_structure = state.get("course_structure")
    full_text = state.get("downloadable_program") or ""

    if not activities_to_enrich or not current_structure:
        return {
            **state,
            "activities_to_enrich": [],
            "is_valid": True,
        }

    batch = activities_to_enrich[:5]
    next_to_enrich = activities_to_enrich[5:]

    print(f"Enriching detailed descriptions for activities: {batch} ({len(next_to_enrich)} remaining)...")

    llm = config.get_llm()
    structured_llm = llm.with_structured_output(ActivityEnrichmentBatch)

    system_prompt = (
        "Eres un experto en diseño instruccional y Canvas LMS. "
        "Tu tarea es leer el documento de curso y extraer los detalles completos de las siguientes actividades específicas:\n"
        f"{', '.join(batch)}\n\n"
        "Para cada una de estas actividades, debes extraer de manera íntegra, completa y sin resumir:\n"
        "- description: el texto completo de la descripción de la actividad, incluyendo instrucciones y paso a paso si existen en el documento.\n"
        "- duration: la dedicación estimada en horas.\n"
        "- delivery_form: la forma de entrega declarada.\n"
        "- resources: la lista de recursos y materiales de estudio indicados.\n\n"
        "REGLA CRÍTICA PARA EL JSON: Reemplaza saltos de línea físicos por un simple espacio en blanco."
    )

    human_prompt = f"Contenido del syllabus/documento del curso:\n\n{full_text}"

    try:
        enrichment = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])

        activities = []
        for a in current_structure.activities:
            activities.append(a.model_copy())

        for ea in enrichment.activities:
            existing_a = next((a for a in activities if a.name.strip().lower() == ea.name.strip().lower()), None)
            if not existing_a:
                existing_a = next((a for a in activities if ea.name.strip().lower() in a.name.strip().lower() or a.name.strip().lower() in ea.name.strip().lower()), None)
            
            if existing_a:
                if ea.description and ea.description.strip():
                    existing_a.description = ea.description.strip()
                if ea.duration > 0:
                    existing_a.duration = ea.duration
                if ea.delivery_form:
                    existing_a.delivery_form = ea.delivery_form
                if ea.resources:
                    existing_a.resources = ea.resources

        updated_structure = current_structure.model_copy(update={"activities": activities})

        is_valid = False
        if not next_to_enrich:
            print("All enrichments finished. Enriching relations and titles...")
            updated_structure = _enrich_activity_unit_links(updated_structure)
            updated_structure = _enrich_activity_titles_and_types(updated_structure)
            is_valid = True

        return {
            **state,
            "course_structure": updated_structure,
            "activities_to_enrich": next_to_enrich,
            "is_valid": is_valid,
        }

    except Exception as e:
        print(f"Error during LLM enrichment of activities {batch}: {str(e)}")
        return {
            **state,
            "errors": [f"Error during LLM enrichment of activities {batch}: {str(e)}"],
        }
