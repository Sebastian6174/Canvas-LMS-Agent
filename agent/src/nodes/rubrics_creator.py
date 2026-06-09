import re
from typing import Optional
from src.state import CourseState, Rubric
from src.tools.canvas_api import create_page, add_item_to_module
from src.routing import INTRO_MODULE_NAME
from src.utils.helpers import build_course_banner_html, resolve_html_links
from config import config

def _normalize_rubric_name(val: str) -> str:
    if not val:
        return ""
    # Remove 'no', 'n.', 'no.' and non-alphanumeric characters, lowercase
    cleaned = val.lower().strip()
    cleaned = re.sub(r'\bn[o\.]*\b', '', cleaned)
    cleaned = re.sub(r'[^a-z0-9]', '', cleaned)
    return cleaned

def rubrics_creator_node(state: CourseState) -> CourseState:
    """
    Nodo encargado de crear y configurar la página de Rúbricas del curso.
    Genera tablas HTML estilizadas para cada rúbrica y las publica en Canvas.
    """
    if state.get("errors"):
        return state

    structure = state.get("course_structure")
    course_id = state.get("canvas_course_id") or config.course_id
    module_mapping = state.get("module_mapping", {})
    files_map = state.get("course_files_map") or {}

    if not structure or not course_id:
        return {**state, "errors": ["Faltan datos para crear la página de rúbricas"]}

    if not structure.rubrics:
        print("No se encontraron rúbricas en la estructura del curso. Omitiendo creación de página.")
        return state

    print(f"Generando página de rúbricas para el curso {course_id}...")

    # Build the header / banner
    banner_html = build_course_banner_html(files_map, config.domain, course_id)
    banner_html = resolve_html_links(banner_html, files_map, config.domain, course_id)

    html_parts = [
        banner_html,
        "<h2 style='text-align: center; color: #0f172a; font-family: \"Inter\", sans-serif; margin-top: 30px; font-weight: 700;'>RÚBRICAS DE EVALUACIÓN</h2>",
        "<p style='text-align: justify; font-family: \"Inter\", sans-serif; color: #475569; max-width: 900px; margin: 20px auto; line-height: 1.6;'>A continuación se detallan los criterios y niveles de desempeño para la evaluación de las actividades evaluativas de este curso. Use estas tablas como guía para orientar el desarrollo de sus entregas.</p>"
    ]

    # Map activities to ease lookup
    norm_activity_rubrics = {}
    for act in structure.activities:
        if act.rubric:
            norm_activity_rubrics[_normalize_rubric_name(act.rubric)] = act

    for rubric in structure.rubrics:
        norm_name = _normalize_rubric_name(rubric.name)
        associated_activity = norm_activity_rubrics.get(norm_name)
        
        # Fallback search if no exact normalized match
        if not associated_activity:
            for act in structure.activities:
                if act.rubric and norm_name in _normalize_rubric_name(act.rubric):
                    associated_activity = act
                    break

        activity_info = ""
        if associated_activity:
            activity_info = f" - {associated_activity.name}"
        
        rubric_anchor = f"rubrica-{norm_name}"
        html_parts.append(
            f"<div id='{rubric_anchor}' style='margin-top: 50px; margin-bottom: 40px;'>"
            f"<h3 style='color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; font-family: \"Inter\", sans-serif; font-weight: 600; margin-bottom: 20px;'>"
            f"{rubric.name}{activity_info}</h3>"
        )

        table_html = (
            "<table class='ic-Table ic-Table--hover-row ic-Table--striped' style='border-collapse: collapse; width: 100%; border: 1px solid #e2e8f0; font-family: \"Inter\", sans-serif; font-size: 14px;'>"
            "<thead>"
            "<tr style='background: linear-gradient(135deg, #1e293b, #0f172a); color: #ffffff; text-align: left;'>"
            "<th style='padding: 12px 16px; border: 1px solid #e2e8f0; width: 20%; font-weight: 600;'>Criterio</th>"
            "<th style='padding: 12px 16px; border: 1px solid #e2e8f0; width: 20%; font-weight: 600; color: #4ade80;'>Excelente</th>"
            "<th style='padding: 12px 16px; border: 1px solid #e2e8f0; width: 20%; font-weight: 600; color: #60a5fa;'>En desarrollo</th>"
            "<th style='padding: 12px 16px; border: 1px solid #e2e8f0; width: 20%; font-weight: 600; color: #fbbf24;'>Básico</th>"
            "<th style='padding: 12px 16px; border: 1px solid #e2e8f0; width: 20%; font-weight: 600; color: #f87171;'>Insuficiente</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
        )

        for crit in rubric.criteria:
            points_badge = ""
            if crit.points is not None:
                points_badge = f"<span style='display: inline-block; background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 12px; padding: 2px 8px; font-size: 11px; font-weight: 700; color: #475569; margin-top: 6px;'>{crit.points} pts</span>"

            table_html += (
                f"<tr>"
                f"<td style='padding: 14px 16px; border: 1px solid #e2e8f0; vertical-align: top; font-weight: 500; color: #334155;'>"
                f"{crit.name}<br/>{points_badge}"
                f"</td>"
                f"<td style='padding: 14px 16px; border: 1px solid #e2e8f0; vertical-align: top; background-color: #f8fafc; color: #1e293b; line-height: 1.5;'>{crit.excelente}</td>"
                f"<td style='padding: 14px 16px; border: 1px solid #e2e8f0; vertical-align: top; background-color: #ffffff; color: #1e293b; line-height: 1.5;'>{crit.en_desarrollo}</td>"
                f"<td style='padding: 14px 16px; border: 1px solid #e2e8f0; vertical-align: top; background-color: #f8fafc; color: #1e293b; line-height: 1.5;'>{crit.basico}</td>"
                f"<td style='padding: 14px 16px; border: 1px solid #e2e8f0; vertical-align: top; background-color: #ffffff; color: #1e293b; line-height: 1.5;'>{crit.insuficiente}</td>"
                f"</tr>"
            )

        table_html += "</tbody></table></div>"
        html_parts.append(table_html)

    full_html = "\n".join(html_parts)
    full_html = resolve_html_links(full_html, files_map, config.domain, course_id)

    # Call the canvas API tool to create/update the Rúbricas page
    result = create_page.invoke({
        "title": "Rúbricas",
        "body": full_html,
        "course_id": course_id
    })

    if "error" in result:
        print(f"Error al crear la página de rúbricas: {result['error']}")
        return {**state, "errors": ["Error creando página de rúbricas"]}

    page_url = result.get("url")
    print(f"Página de rúbricas creada exitosamente: {page_url}")

    # Add the Rúbricas page to the introductory course module
    intro_id = module_mapping.get(INTRO_MODULE_NAME)
    if intro_id:
        print(f"Agregando página de Rúbricas al módulo '{INTRO_MODULE_NAME}' (ID: {intro_id})")
        add_item_to_module.invoke({
            "module_id": intro_id,
            "title": "Rúbricas",
            "type": "Page",
            "page_url": page_url,
            "course_id": course_id,
        })
    else:
        print(f"No se encontró el módulo '{INTRO_MODULE_NAME}'. No se pudo agregar la página de rúbricas.")

    return {**state, "rubrics_page_url": page_url}
