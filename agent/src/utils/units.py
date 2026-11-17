"""Unidades del curso: pertenencia de actividades y páginas de cada unidad."""

import re
from typing import Any, Dict, List, Optional, Sequence


def extract_unit_number(label: str) -> Optional[int]:
    """Extrae el número de unidad de un texto (p. ej. 'Unidad 2. La negociación' -> 2)."""
    if not label:
        return None
    match = re.search(r"unidad\s*(\d+)", label, re.IGNORECASE)
    return int(match.group(1)) if match else None


def canonical_unit_names_by_number(modules: Sequence[Any]) -> Dict[int, str]:
    """Mapa número de unidad -> nombre canónico del módulo en el syllabus."""
    by_number: Dict[int, str] = {}
    for mod in modules:
        name = getattr(mod, "name", None) or (
            mod.get("name", "") if isinstance(mod, dict) else ""
        )
        num = extract_unit_number(name)
        if num is not None:
            by_number[num] = name
    return by_number


def activity_belongs_to_unit(activity_module_name: str, unit_name: str) -> bool:
    """
    Indica si una actividad pertenece a una unidad.
    Tolera 'Unidad 2' frente a 'Unidad 2. La negociación'.
    """
    act_ref = activity_module_name.strip().lower()
    unit_ref = unit_name.strip().lower()
    if not act_ref:
        return False
    if act_ref == unit_ref or act_ref in unit_ref or unit_ref in act_ref:
        return True
    act_num = extract_unit_number(activity_module_name)
    unit_num = extract_unit_number(unit_name)
    return act_num is not None and unit_num is not None and act_num == unit_num


def activities_for_unit(activities: Sequence[Any], unit_name: str) -> List[Any]:
    """Actividades de una unidad según module_name (fuente de verdad para asignación)."""
    matched = [
        act
        for act in activities
        if activity_belongs_to_unit(
            getattr(act, "module_name", "") or (
                act.get("module_name", "") if isinstance(act, dict) else ""
            ),
            unit_name,
        )
    ]
    return sorted(matched, key=lambda act: getattr(act, "number", 0))


def resolve_canonical_module_name(
    module_name: str,
    canonical_by_number: Dict[int, str],
) -> str:
    """Unifica module_name al nombre exacto del módulo definido en modules[]."""
    if not module_name.strip():
        return module_name
    for canonical in canonical_by_number.values():
        if activity_belongs_to_unit(module_name, canonical):
            return canonical
    num = extract_unit_number(module_name)
    if num is not None and num in canonical_by_number:
        return canonical_by_number[num]
    return module_name


def unit_intro_page_title(unit_number: int) -> str:
    return f"Unidad {unit_number} Introducción y Resultados de Aprendizaje"


def unit_materials_page_title(unit_number: int) -> str:
    return f"Unidad {unit_number} Materiales de estudio"



def collect_unit_resources(activities: Sequence[Any], unit_name: str) -> List[str]:
    """Recursos únicos de todas las actividades de una unidad, en orden de aparición."""
    seen: set[str] = set()
    resources: List[str] = []
    for act in activities_for_unit(activities, unit_name):
        act_resources = getattr(act, "resources", None) or (
            act.get("resources", []) if isinstance(act, dict) else []
        )
        for resource in act_resources or []:
            text = str(resource).strip()
            if text and text not in seen:
                seen.add(text)
                resources.append(text)
    return resources


def build_unit_intro_page_body(title: str) -> str:
    return f"<h1>{title}</h1>"


def build_unit_materials_page_body(banner_html: str, resources: Sequence[str]) -> str:
    items = "".join(f"<li>{r}</li>" for r in resources)
    list_html = f"<ul>{items}</ul>" if items else "<p><em>Sin recursos registrados para esta unidad.</em></p>"
    return f"{banner_html}\n{list_html}"
