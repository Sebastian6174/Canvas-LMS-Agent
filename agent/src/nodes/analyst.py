from src.state import CourseState, CourseStructure, Activity, ScheduleItem, Module, Rubric, RubricCriterion
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


# ========================================================
# Pydantic Schemas for Sequential Extraction Fases
# ========================================================

class CourseMetadata(BaseModel):
    name: str = Field(description="Nombre completo del curso")
    academic_program: str = Field(description="Programa académico o facultad")
    semester: int = Field(description="Semestre del curso")
    academic_level: str = Field(description="Nivel académico (Pregrado, Posgrado, Maestría, etc.)")
    credits: int = Field(description="Número de créditos del curso")
    prerequisites: List[str] = Field(description="Lista de prerrequisitos")
    teacher: str = Field(description="Nombre completo del docente")
    description: str = Field(description="Descripción concisa y general del curso")
    learning_outcomes: List[str] = Field(description="Resultados de aprendizaje (RA)")


class ModuleExtraction(BaseModel):
    name: str = Field(description="Nombre exacto del módulo o unidad, ej: 'Unidad 1. Introducción'")
    description: str = Field(description="Breve descripción del módulo")


class ModulesList(BaseModel):
    modules: List[ModuleExtraction] = Field(description="Lista de módulos del curso")


class ActivitySkeleton(BaseModel):
    name: str = Field(description="Título corto de la actividad")
    activity_type: str = Field(default="Otros", description="Tipo: Foro, Quiz, Tarea, Videoconferencia u Otros")
    evaluation_type: str = Field(default="", description="Formativa o Evaluativa")
    weight: float = Field(description="Ponderación de la actividad (0 a 100)")
    module_name: str = Field(description="Nombre del módulo al que pertenece de la lista de módulos")
    related_learning_outcome: str = Field(default="", description="Resultado de aprendizaje (RA) al que se asocia")


class ActivitiesSkeletonList(BaseModel):
    activities: List[ActivitySkeleton] = Field(description="Lista básica de actividades")


class ScheduleExtractionList(BaseModel):
    schedule: List[ScheduleItem] = Field(description="Cronograma del curso")


class RubricAssociation(BaseModel):
    rubric_name: str = Field(description="Nombre de la rúbrica (ej: 'Rúbrica N. 1')")
    activity_name: str = Field(description="Nombre de la actividad asociada")


class RubricsList(BaseModel):
    rubrics: List[Rubric] = Field(description="Lista de rúbricas")
    associations: List[RubricAssociation] = Field(default_factory=list, description="Asociaciones de rúbricas a actividades")


# ========================================================
# Nodos del Grafo para la Extracción Secuencial
# ========================================================

def analyst_node(state: CourseState) -> CourseState:
    """Fase 1: Extrae metadatos generales del curso y lee el documento."""
    doc_id = state.get("doc_id")
    if not doc_id:
        return {**state, "is_valid": False, "errors": ["No doc_id provided in state"]}

    print(f"Reading document {doc_id}...")
    doc_content = read_google_doc(doc_id)
    if not doc_content:
        return {**state, "is_valid": False, "errors": ["Failed to read Google Doc"]}

    import re
    full_text = ""
    for tab in doc_content:
        full_text += f"Tab: {tab['title']}\n{tab['content']}\n\n"
    full_text = re.sub(r"[\x00-\x1F\x7F]", " ", full_text)

    teacher_info_text = None
    if config.teacher_doc:
        print(f"Reading teacher document {config.teacher_doc}...")
        teacher_content = read_google_doc(config.teacher_doc)
        if teacher_content:
            teacher_info_text = ""
            for tab in teacher_content:
                teacher_info_text += f"Tab: {tab['title']}\n{tab['content']}\n\n"
            teacher_info_text = re.sub(r"[\x00-\x1F\x7F]", " ", teacher_info_text)

    print("Extracting course metadata...")
    llm = config.get_llm()
    structured_llm = llm.with_structured_output(CourseMetadata)

    system_prompt = (
        "Eres un experto en diseño instruccional. Tu tarea es extraer la información general y metadatos del curso del syllabus.\n"
        "Extrae la información EXACTA proporcionada. No asumas ni inventes. "
        "Para la descripción general, extrae el texto completo e íntegro sin resumir.\n"
        "REGLA CRÍTICA PARA EL JSON: Para evitar errores de formato (Invalid JSON control character), DEBES REEMPLAZAR todos los saltos de línea físicos por un simple espacio en blanco dentro de cualquier texto que extraigas."
    )

    human_prompt = f"Contenido del syllabus:\n\n{full_text}"

    try:
        metadata = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])

        course_structure = CourseStructure(
            name=metadata.name,
            academic_program=metadata.academic_program,
            semester=metadata.semester,
            academic_level=metadata.academic_level,
            credits=metadata.credits,
            prerequisites=metadata.prerequisites,
            teacher=metadata.teacher,
            description=metadata.description,
            learning_outcomes=metadata.learning_outcomes,
            modules=[],
            activities=[],
            schedule=[],
            rubrics=[],
        )

        return {
            **state,
            "course_structure": course_structure,
            "teacher_info": teacher_info_text,
            "downloadable_program": full_text,
            "is_valid": False,
            "errors": [],
        }
    except Exception as e:
        print(f"Error during metadata extraction: {str(e)}")
        return {
            **state,
            "is_valid": False,
            "errors": [f"Error during metadata extraction: {str(e)}"],
        }


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
