"""Normalización final de la estructura inferida: unidades, numeración y títulos."""

from src.activities.rules import (
    format_activity_display_name,
    infer_evaluation_type,
    normalize_activity_type,
)
from src.state import Activity, CourseStructure, ScheduleItem


def _resolve_activity_key(name: str, mapping: dict[str, str]) -> str:
    """Mapea un nombre de actividad (corto o display) al nombre display final."""
    if name in mapping:
        return mapping[name]
    lower = name.strip().lower()
    for key, display in mapping.items():
        if key.strip().lower() == lower or display.strip().lower() == lower:
            return display
    return name


def enrich_activity_unit_links(structure: CourseStructure) -> CourseStructure:
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


def enrich_activity_titles_and_types(structure: CourseStructure) -> CourseStructure:
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


def finalize_structure(data: dict) -> CourseStructure:
    """Valida la estructura acumulada y aplica la normalización final."""
    return enrich_activity_titles_and_types(
        enrich_activity_unit_links(CourseStructure.model_validate(data))
    )
