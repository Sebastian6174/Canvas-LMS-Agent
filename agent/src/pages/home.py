"""Página de inicio: ficha técnica, introducción, resultados, navegación y profesor."""

import re
from typing import Dict, List, Optional

from src.pages.html import CourseLinks, banner, esc, text_to_html
from src.pages.teacher import teacher_table
from src.state import CourseStructure

TH = 'style="background-color: #efefef; width: 28%; text-align: left; border: 1px solid #ffffff;" scope="row"'
TD = 'style="background-color: #ffffff; width: 29%; border: 1px solid #efefef;"'
NO_PREREQUISITES = "Ninguno"


def _fact_row(label: str, value: str) -> str:
    return (
        f'        <tr><th {TH}><p style="margin-left: 30px;"><strong>{label}</strong></p></th>'
        f'<td {TD}><p style="margin-left: 30px;">{value}</p></td></tr>'
    )


def _fact_sheet(structure: CourseStructure) -> str:
    credits = f"{structure.credits} cr&eacute;ditos" if structure.credits else ""
    hours = f"{structure.total_hours} horas" if structure.total_hours else ""
    rows = [
        _fact_row("Nombre del curso", esc(structure.name)),
        _fact_row("Programa / unidad acad&eacute;micas", esc(structure.academic_program)),
        _fact_row("Nivel acad&eacute;mico y modalidad", esc(structure.academic_level)),
        _fact_row("Cr&eacute;ditos y duraci&oacute;n del curso", " - ".join(p for p in (credits, hours) if p)),
        _fact_row("Pre-requisitos y co-requisitos", esc(", ".join(structure.prerequisites)) or NO_PREREQUISITES),
    ]
    if structure.program_url:
        rows.append(
            f'        <tr><th style="background-color: #ffffff; border: 1px solid #efefef;" colspan="2" scope="row">'
            f'<p style="margin-left: 30px; text-align: left;"><a href="{esc(structure.program_url)}" target="_blank" rel="noopener">'
            '<strong><span style="font-size: 14pt;">Programa descargable</span></strong></a></p></th></tr>'
        )
    body = "\n".join(rows)
    return f"""<table style="border-collapse: collapse; width: 60%; margin-left: auto; margin-right: auto;" border="1px">
    <caption><strong>FICHA T&Eacute;CNICA DEL CURSO</strong></caption>
    <tbody>
{body}
    </tbody>
</table>"""


def _outcomes(structure: CourseStructure, links: CourseLinks) -> str:
    items: List[str] = []
    for outcome in structure.learning_outcomes:
        match = re.match(r"^(RA\s*\d+)\.?\s*(.*)$", outcome, flags=re.IGNORECASE | re.DOTALL)
        if match:
            code = match.group(1).replace(" ", "")
            items.append(f"<li><strong>{esc(code)}. </strong>{esc(match.group(2))}</li>")
        else:
            items.append(f"<li>{esc(outcome)}</li>")
    icon = links.image(["Iconos_ResultadosAp", "resultados"], "", 'role="presentation" width="43" height="43"')
    return (
        f"    <h3><strong>{icon}Resultados de aprendizaje</strong></h3>\n"
        f'    <ul style="list-style-type: none;">{"".join(items)}</ul>'
    )


def _button(href: str, title: str, image: str, api_type: str, api_path: str) -> str:
    content = image or f"<strong>{esc(title)}</strong>"
    return (
        f'<a title="{esc(title)}" href="{href}" data-api-endpoint="{api_path}" '
        f'data-api-returntype="{api_type}">{content}</a>'
    )


def _navigation(
    structure: CourseStructure,
    links: CourseLinks,
    module_mapping: Dict[str, int],
    agenda_page_url: Optional[str],
    forum_discussion_id: Optional[int],
) -> str:
    parts: List[str] = []
    if forum_discussion_id:
        forum = _button(
            f"{links.base}/discussion_topics/{forum_discussion_id}",
            "Foro- Preguntas y Respuestas del Curso",
            links.image(["Boton_ForoDudas"], "Boton Foro Dudas", 'width="224" height="58"'),
            "Discussion",
            f"{links.api_base}/discussion_topics/{forum_discussion_id}",
        )
        parts.append(f'<p style="text-align: center;">{forum}</p>')

    buttons: List[str] = []
    if agenda_page_url:
        buttons.append(_button(
            f"{links.base}/pages/{agenda_page_url}",
            "Agenda de Actividades",
            links.image(["AgendaActividades"], "Agenda de Actividades"),
            "Page",
            f"{links.api_base}/pages/{agenda_page_url}",
        ))
    for module in structure.modules:
        module_id = module_mapping.get(module.name)
        if not module_id:
            continue
        buttons.append(_button(
            f"{links.base}/modules/{module_id}",
            module.name,
            links.image([f"Boton_U{module.number}"], f"Unidad {module.number}"),
            "Module",
            f"{links.api_base}/modules/{module_id}",
        ))
    parts.append("<h3><strong>Unidades de aprendizaje</strong></h3>")
    parts.append(f'<p style="text-align: center;">{"".join(buttons)}</p>')
    return "\n".join(parts)


def build_home_html(
    structure: CourseStructure,
    teacher_bio: str,
    links: CourseLinks,
    module_mapping: Dict[str, int],
    agenda_page_url: Optional[str] = None,
    forum_discussion_id: Optional[int] = None,
) -> str:
    introduction = text_to_html(structure.description, indent="    ")
    return f"""{banner(links)}
{_fact_sheet(structure)}
<h3><strong>Introducci&oacute;n</strong></h3>
<div>
{introduction}
{_outcomes(structure, links)}
</div>
{_navigation(structure, links, module_mapping, agenda_page_url, forum_discussion_id)}
<p style="text-align: center;">&nbsp;</p>
{teacher_table(structure.teacher, teacher_bio, links, "Profesor")}"""
