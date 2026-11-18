"""Páginas de cada unidad: introducción con resultados de aprendizaje y materiales de estudio."""

import re
from typing import List

from src.pages.html import CourseLinks, banner, esc, resource_item, text_to_html
from src.state import CourseStructure, Module


def unit_intro_page_title(unit_number: int) -> str:
    return f"Unidad {unit_number} Introducción y Resultados de Aprendizaje"


def unit_materials_page_title(unit_number: int) -> str:
    return f"Unidad {unit_number} Materiales de estudio"


def unit_resources(structure: CourseStructure, unit: Module) -> List[str]:
    """Materiales únicos de las actividades de la unidad, en orden de aparición."""
    seen = set()
    resources: List[str] = []
    for activity in structure.activities:
        if activity.module_name != unit.name:
            continue
        for resource in activity.resources:
            text = resource.strip()
            if text and text not in seen:
                seen.add(text)
                resources.append(text)
    return resources


def _outcome_texts(structure: CourseStructure, codes: List[str]) -> List[str]:
    """Enunciado completo de cada código de RA de la unidad ('RA 1' -> 'RA 1. Reconoce...')."""
    texts = []
    for code in codes:
        number = re.search(r"\d+", code)
        match = next(
            (o for o in structure.learning_outcomes if number and re.match(rf"RA\s*{number.group()}\b", o)),
            None,
        )
        texts.append(match or code)
    return texts


def build_unit_intro_html(structure: CourseStructure, unit: Module, links: CourseLinks) -> str:
    parts = [banner(links), f"<h2>{esc(unit.name)}</h2>"]
    if unit.description:
        parts.append(text_to_html(unit.description))
    outcomes = _outcome_texts(structure, unit.learning_outcomes)
    if outcomes:
        items = "".join(f"<li>{esc(text)}</li>" for text in outcomes)
        parts.append(f"<h3><strong>Resultados de aprendizaje</strong></h3>\n<ul>{items}</ul>")
    if unit.indicators:
        items = "".join(f"<li>{esc(text)}</li>" for text in unit.indicators)
        parts.append(f"<h3><strong>Indicadores de logro</strong></h3>\n<ul>{items}</ul>")
    return "\n".join(parts)


def build_unit_materials_html(structure: CourseStructure, unit: Module, links: CourseLinks) -> str:
    resources = unit_resources(structure, unit)
    if resources:
        items = "".join(f"<li>{resource_item(resource, links)}</li>" for resource in resources)
        content = f"<ul>{items}</ul>"
    else:
        content = "<p><em>Sin recursos registrados para esta unidad.</em></p>"
    return f"{banner(links)}\n<h2>Materiales de estudio</h2>\n{content}"
