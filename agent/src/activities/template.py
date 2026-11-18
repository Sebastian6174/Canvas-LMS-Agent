"""
Plantilla HTML de una actividad de Canvas.

Reproduce la estructura de `example_activity.html`: banner, bloque justificado
(tipo, peso, descripción, forma de entrega, materiales) y tabla resumen.
Todo el contenido sale del estado; aquí sólo se ensambla.
"""

from src.activities.rules import (
    DEFAULT_DELIVERY_FORM_BY_TYPE,
    format_weight,
    infer_evaluation_type,
    normalize_activity_type,
)
from src.pages.html import CourseLinks, banner, esc, resource_item, text_to_html
from src.state import Activity

DEFAULT_MODALITY = "Virtual"
PENDING_RESOURCES_TEXT = "PENDIENTES"
PENDING_DESCRIPTION_TEXT = "Descripción pendiente."
SECTION_TITLE = '<p><span style="font-size: 14pt;"><strong>{}</strong></span></p>'
SPACER = "<p>&nbsp;</p>"


def delivery_form_for(activity: Activity) -> str:
    """Forma de entrega del estado o, si falta, la habitual para su tipo."""
    return (activity.delivery_form or "").strip() or DEFAULT_DELIVERY_FORM_BY_TYPE[
        normalize_activity_type(activity.activity_type)
    ]


def _resources_html(activity: Activity, links: CourseLinks) -> str:
    items = [resource_item(r, links) for r in activity.resources if r and r.strip()]
    if not items:
        items = [PENDING_RESOURCES_TEXT]
    return "\n".join(f"        <li>{item}</li>" for item in items)


def render_activity_html(activity: Activity, links: CourseLinks, modality: str = DEFAULT_MODALITY) -> str:
    """HTML final del assignment con la estructura visual de Canvas."""
    eval_label = infer_evaluation_type(activity.weight, activity.evaluation_type)
    description = text_to_html(activity.description, indent="    ") or (
        f"    <p><span>{PENDING_DESCRIPTION_TEXT}</span></p>"
    )
    week = activity.week or 1

    return f"""{banner(links)}
<div style="text-align: justify;">
    <p><span><span style="font-size: 14pt;"><strong>Tipo de actividad</strong>&nbsp;</span>:</span><span>&nbsp;</span>{eval_label}&nbsp;<br /><span><span style="font-size: 14pt;"><strong>Peso nota final:</strong></span>&nbsp;</span>{format_weight(activity.weight)}%</p>
    {SPACER}
    {SECTION_TITLE.format("Descripci&oacute;n de la Actividad:")}
{description}
    {SPACER}
    {SECTION_TITLE.format("Forma de entrega:")}
    <p>{esc(delivery_form_for(activity))}</p>
    {SPACER}
    {SECTION_TITLE.format("Materiales de estudio:")}
    <ul>
{_resources_html(activity, links)}
    </ul>
</div>
{SPACER}
<table style="border-style: dotted; border-color: #e1e4e7; background-color: #ffffff;" border="1" cellspacing="5" cellpadding="5">
    <caption>Resumen para el desarrollo de la actividad</caption>
    <tbody>
        <tr>
            <th style="text-align: center; background-color: #e1e4e7; border: 1px solid #ffffff;" scope="row"><span style="font-size: 12pt;">Modalidad</span></th>
            <th style="border-style: dotted; border-color: #ffffff; background-color: #e1e4e7;" scope="row"><span style="font-size: 12pt;">Tipo de Actividad</span></th>
            <th style="border-style: dotted; border-color: #ffffff; background-color: #e1e4e7;" colspan="2" scope="row"><span style="font-size: 12pt;">Fechas (Semana No.)</span></th>
        </tr>
        <tr>
            <th style="text-align: center; background-color: #e1e4e7; border: 1px dotted #ffffff;" scope="row"><span style="font-size: 12pt;">Presencial /Virtual</span></th>
            <th style="text-align: center; background-color: #e1e4e7; border: 1px dotted #ffffff;" scope="row"><span style="font-size: 12pt;">Formativa/Evaluativa</span></th>
            <th style="text-align: center; background-color: #e1e4e7; border: 1px dotted #ffffff;" scope="col"><span style="font-size: 12pt;">Inicio</span></th>
            <td style="border-style: dotted;">Semana No. {week}</td>
        </tr>
        <tr>
            <td style="border-style: dotted; text-align: center;">{modality}</td>
            <td style="border-style: dotted; text-align: center;">{eval_label}</td>
            <th style="border-style: dotted; border-color: #ffffff; background-color: #e1e4e7; text-align: center;" scope="col"><span style="font-size: 12pt;">Fin</span></th>
            <td style="border-style: dotted;">Semana No. {week}</td>
        </tr>
        <tr>
            <td style="background-color: #e1e4e7; border-style: dotted; border-color: #ffffff; text-align: center;" colspan="4"><span style="font-size: 12pt;">Tiempo para el desarrollo de la actividad</span></td>
        </tr>
        <tr>
            <td style="text-align: center; border-style: dotted;">Dedicaci&oacute;n</td>
            <td style="text-align: center; border-style: dotted;">{activity.duration}</td>
            <td style="border-style: dotted;" colspan="2">hora(s)</td>
        </tr>
    </tbody>
</table>"""
