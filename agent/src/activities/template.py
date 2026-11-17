"""
Plantilla HTML de una actividad de Canvas.

Reproduce la estructura de `example_activity.html`: banner, bloque justificado
(tipo, peso, descripción, forma de entrega, materiales) y tabla resumen.
El contenido variable (descripción, entrega, materiales) llega ya preparado;
aquí sólo se ensambla.
"""

from html import escape
from typing import Dict, Optional, Sequence

from src.activities.rules import format_weight, infer_evaluation_type
from src.utils.course_files import build_course_banner_html, file_id_from_url, normalize_filename

DEFAULT_MODALITY = "Virtual"
PENDING_RESOURCES_TEXT = "PENDIENTES"
SECTION_TITLE = '<p><span style="font-size: 14pt;"><strong>{}</strong></span></p>'
SPACER = "<p>&nbsp;</p>"


def _file_id_for_resource(resource: str, files_map: Optional[Dict[str, str]]) -> Optional[str]:
    """ID del archivo del curso cuyo nombre coincide con el recurso, si existe."""
    if not files_map:
        return None
    return file_id_from_url(
        files_map.get(resource.strip().lower()) or files_map.get(normalize_filename(resource))
    )


def _resource_item(resource: str, files_map: Optional[Dict[str, str]], domain: str, course_id: str) -> str:
    text = escape(resource.strip(), quote=False)
    file_id = _file_id_for_resource(resource, files_map)
    if not file_id:
        return f"<li>{text}</li>"
    return (
        f'<li><a id="{file_id}" class="instructure_file_link instructure_scribd_file inline_disabled" '
        f'title="Enlace" href="https://{domain}/courses/{course_id}/files/{file_id}?wrap=1" '
        'target="_blank" data-canvas-previewable="true" '
        f'data-api-endpoint="https://{domain}/api/v1/courses/{course_id}/files/{file_id}" '
        f'data-api-returntype="File" rel="noopener">{text}</a></li>'
    )


def _resources_html(resources: Sequence[str], files_map, domain: str, course_id: str) -> str:
    items = [
        _resource_item(resource, files_map, domain, course_id)
        for resource in resources or []
        if resource and resource.strip()
    ]
    if not items:
        items = [f"<li>{PENDING_RESOURCES_TEXT}</li>"]
    return "\n".join(f"        {item}" for item in items)


def plain_text_to_paragraphs(text: str) -> str:
    """Convierte texto plano en párrafos `<p><span>…</span></p>` como en el ejemplo."""
    paragraphs = [part.strip() for part in (text or "").split("\n") if part.strip()]
    if not paragraphs:
        paragraphs = ["Descripción pendiente."]
    return "\n".join(f"    <p><span>{escape(p, quote=False)}</span></p>" for p in paragraphs)


def render_activity_html(
    *,
    description_html: str,
    delivery_form: str,
    resources: Sequence[str],
    weight: float,
    evaluation_type: Optional[str] = None,
    duration: int = 0,
    week: int = 1,
    files_map: Optional[Dict[str, str]] = None,
    domain: str = "",
    course_id: str = "",
    modality: str = DEFAULT_MODALITY,
) -> str:
    """Ensambla el HTML final del assignment con la estructura visual de Canvas."""
    eval_label = infer_evaluation_type(weight, evaluation_type)
    delivery = escape((delivery_form or "").strip(), quote=False)

    return f"""{build_course_banner_html(files_map, domain, course_id)}
<div style="text-align: justify;">
    <p><span><span style="font-size: 14pt;"><strong>Tipo de actividad</strong>&nbsp;</span>:</span><span>&nbsp;</span>{eval_label}&nbsp;<br /><span><span style="font-size: 14pt;"><strong>Peso nota final:</strong></span>&nbsp;</span>{format_weight(weight)}%</p>
    {SPACER}
    {SECTION_TITLE.format("Descripci&oacute;n de la Actividad:")}
{description_html.strip(chr(10)).rstrip()}
    {SPACER}
    {SECTION_TITLE.format("Forma de entrega:")}
    <p>{delivery}</p>
    {SPACER}
    {SECTION_TITLE.format("Materiales de estudio:")}
    <ul>
{_resources_html(resources, files_map, domain, course_id)}
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
            <td style="text-align: center; border-style: dotted;">{duration}</td>
            <td style="border-style: dotted;" colspan="2">hora(s)</td>
        </tr>
    </tbody>
</table>"""
