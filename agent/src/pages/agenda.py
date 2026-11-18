"""Página 'Agenda de actividades': tabla por unidad y semana con dedicación y valoración."""

from itertools import groupby
from typing import List

from src.activities.rules import format_weight, infer_evaluation_type
from src.pages.html import CourseLinks, banner, esc
from src.state import CourseStructure

HEADER_STYLE = "vertical-align: middle; background-color: #f3f4f5;"
CENTER = "text-align: center;"
COLUMNS = (
    ("UNIDAD", "9%"),
    ("SEMANAS", "10%"),
    ("ACTIVIDAD", "40%"),
    ("TIPO", "12%"),
    ("DEDICACI&Oacute;N", "14%"),
    ("VALORACI&Oacute;N", "15%"),
)


def _unit_label(structure: CourseStructure, module_name: str) -> str:
    for module in structure.modules:
        if module.name == module_name:
            return str(module.number or module.name)
    return esc(module_name)


def build_agenda_html(structure: CourseStructure, links: CourseLinks) -> str:
    header = "".join(
        f'<th style="{HEADER_STYLE} width: {width};" scope="col" align="center">{label}</th>'
        for label, width in COLUMNS
    )
    rows: List[str] = [f"        <tr>{header}</tr>"]

    for module_name, unit_group in groupby(structure.activities, key=lambda a: a.module_name):
        unit_activities = list(unit_group)
        unit_cell = (
            f'<td style="{CENTER}" rowspan="{len(unit_activities)}">{_unit_label(structure, module_name)}</td>'
        )
        for week, week_group in groupby(unit_activities, key=lambda a: a.week):
            week_activities = list(week_group)
            week_cell = f'<td style="{CENTER}" rowspan="{len(week_activities)}">{week or ""}</td>'
            for activity in week_activities:
                cells = [
                    unit_cell,
                    week_cell,
                    f"<td>{esc(activity.name)}</td>",
                    f'<td style="{CENTER}">{infer_evaluation_type(activity.weight, activity.evaluation_type)}</td>',
                    f'<td style="{CENTER}">{activity.duration}</td>',
                    f'<td style="{CENTER}">{format_weight(activity.weight)}%</td>',
                ]
                rows.append("        <tr>" + "".join(cell for cell in cells if cell) + "</tr>")
                unit_cell = week_cell = ""

    total_hours = sum(activity.duration for activity in structure.activities)
    total_weight = format_weight(sum(activity.weight for activity in structure.activities))
    rows.append(
        '        <tr><td style="text-align: right; padding: 5px;" colspan="4"><strong>Total horas</strong></td>'
        f'<td style="{CENTER}"><strong>{total_hours}</strong></td>'
        f'<td style="{CENTER}"><strong>{total_weight}%</strong></td></tr>'
    )

    body = "\n".join(rows)
    return f"""{banner(links)}
<table style="border-collapse: collapse; width: 94%; border-color: #e1e4e7; border-style: solid; margin-left: auto; margin-right: auto;" border="1" cellspacing="1" cellpadding="0">
    <caption>ACTIVIDADES DE APRENDIZAJE&nbsp;</caption>
    <tbody>
{body}
    </tbody>
</table>"""
