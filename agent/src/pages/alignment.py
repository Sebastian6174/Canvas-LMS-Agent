"""Página 'Alineación de actividades': R.A., indicadores de logro y actividades por unidad."""

from typing import List

from src.activities.rules import infer_evaluation_type
from src.pages.html import CourseLinks, banner, esc, ra_label, split_indicator
from src.state import CourseStructure

CELL = "padding: 5px;"
CENTER = "padding: 5px; text-align: center;"
COLUMNS = (
    ("R.A", "7%"),
    ("Indicadores de logro", "11%"),
    ("Descripci&oacute;n", "29%"),
    ("Actividad", "39%"),
    ("Tipo de actividad", "14%"),
)


def build_alignment_html(structure: CourseStructure, links: CourseLinks) -> str:
    header = "".join(
        f'<th style="width: {width}; padding: 5px;" scope="row">{label}</th>' for label, width in COLUMNS
    )
    rows: List[str] = []

    for module in structure.modules:
        activities = [a for a in structure.activities if a.module_name == module.name]
        if not activities:
            continue
        span = len(activities)
        indicators = [split_indicator(indicator) for indicator in module.indicators]
        outcomes = "<br />".join(ra_label(code) for code in module.learning_outcomes) or "&nbsp;"
        codes = "<br />".join(esc(code) for code, _ in indicators if code) or "&nbsp;"
        descriptions = "".join(f"<p><span>{esc(text)}</span></p>" for _, text in indicators) or "&nbsp;"

        for index, activity in enumerate(activities):
            cells = []
            if index == 0:
                cells += [
                    f'<td style="{CENTER}" rowspan="{span}">{outcomes}</td>',
                    f'<td style="{CENTER}" rowspan="{span}">{codes}</td>',
                    f'<td style="{CELL}" rowspan="{span}">{descriptions}</td>',
                ]
            cells += [
                f'<td style="{CELL}"><p><span>{esc(activity.name)}</span></p></td>',
                f'<td style="{CENTER}">{infer_evaluation_type(activity.weight, activity.evaluation_type)}</td>',
            ]
            rows.append("        <tr>" + "".join(cells) + "</tr>")

    body = "\n".join(rows)
    return f"""{banner(links)}
<table style="border-collapse: collapse; width: 100%; margin-left: auto; margin-right: auto; border: 1px solid #e1e4e7;" border="1" cellspacing="1" cellpadding="0">
    <caption>ALINEACI&Oacute;N DE ACTIVIDADES</caption>
    <thead>
        <tr style="background-color: #f3f4f5;">{header}</tr>
    </thead>
    <tbody>
{body}
    </tbody>
</table>"""
