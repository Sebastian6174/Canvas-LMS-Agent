"""
Tipos de actividad del curso y guías de estructura HTML para Canvas.

Amplía ACTIVITY_TYPE_HTML_GUIDE con el HTML o las instrucciones que quieras por tipo.
"""

from __future__ import annotations

from typing import Dict, Tuple

ACTIVITY_TYPE_DEFAULT = "Otros"

ACTIVITY_TYPES: Tuple[str, ...] = (
    "Foro",
    "Quiz",
    "Tarea",
    "Videoconferencia",
    "Otros",
)

# Clave: tipo de actividad. Valor: guía para el modelo sobre cómo estructurar el HTML en Canvas.
ACTIVITY_TYPE_HTML_GUIDE: Dict[str, str] = {
    "Foro": (
        "Ejemplo: pregunta detonadora, instrucciones de participación, número mínimo de "
        "intervenciones y fecha límite."
    ),
    "Quiz": (
        "Ejemplo: indicaciones previas al cuestionario, número de intentos y tiempo límite "
        "si aplica."
    ),
    "Tarea": (
        "Ejemplo: enunciado, entregables, formato de entrega y fecha límite."
    ),
    "Videoconferencia": (
        "Ejemplo: título de la sesión, objetivos breves, fecha/hora, enlace o indicaciones "
        "de acceso, y recordatorio de asistencia."
    ),
    "Otros": (
        "Ejemplo: descripción general, instrucciones claras y criterios mínimos de entrega "
        "o participación."
    ),
}

_TYPE_LOOKUP = {t.lower(): t for t in ACTIVITY_TYPES}


def normalize_activity_type(raw: str | None) -> str:
    """Devuelve un tipo válido; si no coincide, 'Otros'."""
    if not raw:
        return ACTIVITY_TYPE_DEFAULT
    cleaned = raw.strip()
    return _TYPE_LOOKUP.get(cleaned.lower(), ACTIVITY_TYPE_DEFAULT)


def format_activity_display_name(number: int, activity_type: str, name: str) -> str:
    """Actividad N. Tipo: nombre (sin duplicar prefijo si ya viene en name)."""
    short = name.strip()
    activity_type = normalize_activity_type(activity_type)
    prefix = f"Actividad {number}. {activity_type}:"
    if short.lower().startswith(prefix.lower()):
        return short
    legacy = f"actividad {number}."
    if short.lower().startswith(legacy):
        return short
    return f"{prefix} {short}"


def infer_evaluation_type(weight: float, explicit: str | None = None) -> str:
    """Formativa o Evaluativa para agenda/alineación."""
    if explicit:
        val = explicit.strip().capitalize()
        if val in ("Formativa", "Evaluativa"):
            return val
    return "Evaluativa" if weight and float(weight) > 0 else "Formativa"


def activity_types_prompt_section() -> str:
    """Texto para el system prompt del analista."""
    lines = [
        "Clasifica cada actividad con 'activity_type' usando SOLO uno de estos tipos "
        f"(si no encaja, usa '{ACTIVITY_TYPE_DEFAULT}'):",
        ", ".join(ACTIVITY_TYPES),
        "",
        "Guías de referencia por tipo (para futura estructuración HTML en Canvas):",
    ]
    for activity_type in ACTIVITY_TYPES:
        guide = ACTIVITY_TYPE_HTML_GUIDE.get(activity_type, "")
        lines.append(f"- {activity_type}: {guide}")
    lines.append(
        "En 'name' guarda solo el título corto de la actividad tal como aparece en el documento, "
        "sin el prefijo 'Actividad N.'."
    )
    lines.append(
        "En 'evaluation_type' indica 'Formativa' o 'Evaluativa' según el documento; "
        "si no está claro, usa Evaluativa cuando la ponderación (weight) sea mayor que 0."
    )
    return "\n".join(lines)


def wrap_activity_description_html(
    activity_type: str,
    description: str,
    related_learning_outcome: str,
    weight: float,
    evaluation_type: str | None = None,
    points_possible: float = 5.0,
    delivery_form: str = "",
    resources: list[str] | None = None,
    duration: int = 0,
    week: int = 1,
    files_map: dict[str, str] | None = None,
    domain: str = "",
    course_id: str = "",
) -> str:
    """Arma la descripción del assignment usando la estructura visual HTML requerida para Canvas."""
    activity_type = normalize_activity_type(activity_type)
    eval_label = infer_evaluation_type(weight, evaluation_type)
    
    # Resolviendo banner URL
    banner_url = ""
    if files_map:
        banner_url = (
            files_map.get("bannercurso")
            or files_map.get("old_id_54959")
            or files_map.get("old_id_67711")
            or files_map.get("old_id_66540")
        )
    if not banner_url:
        banner_url = f"https://{domain}/courses/{course_id}/files/54959/preview" if course_id and domain else "https://univallecolombia.instructure.com/courses/630/files/54959/preview"
        
    weight_val = float(weight or 0)
    if 0 < abs(weight_val) < 1:
        weight_val *= 100
    weight_str = str(int(weight_val)) if weight_val.is_integer() else str(weight_val).rstrip("0").rstrip(".")

    # Formatear lista de recursos
    resources_html = ""
    if resources:
        for res in resources:
            if res.strip():
                resources_html += f"<li>{res.strip()}</li>"
    if not resources_html:
        resources_html = "<li>PENDIENTES</li>"
        
    # Formatear forma de entrega
    delivery_html = delivery_form.strip() if delivery_form else "Participación en el encuentro virtual."

    # Determinar modalidad por defecto (Virtual)
    modalidad = "Virtual"

    # Generación de la tabla HTML y cuerpo final
    return f"""<h2><img id="13808" style="display: block; margin-left: auto; margin-right: auto;" src="{banner_url}" alt="Banner curso" width="100%" height="100%" data-api-endpoint="https://{domain}/api/v1/courses/{course_id}/files/54959" data-api-returntype="File" /></h2>
<p><span style="font-size: 14pt;"><strong>Tipo de actividad</strong> :</span> {eval_label}<br /><span style="font-size: 14pt;"><strong>Peso nota final:</strong> {weight_str}%</span></p>
<p>&nbsp;</p>
<p><span style="font-size: 14pt;"><strong>Descripci&oacute;n de la Actividad:</strong></span></p>
{description}
<p>&nbsp;</p>
<p><span style="font-size: 14pt;"><strong>Forma de entrega:</strong></span></p>
<p>{delivery_html}</p>
<p>&nbsp;</p>
<p><span style="font-size: 14pt;"><strong>Materiales de estudio:</strong></span></p>
<ol>
    {resources_html}
</ol>
<p>&nbsp;</p>
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
            <td style="border-style: dotted;">Semana No.{week}</td>
        </tr>
        <tr>
            <td style="border-style: dotted; text-align: center;">{modalidad}</td>
            <td style="border-style: dotted; text-align: center;">{eval_label}</td>
            <th style="border-style: dotted; border-color: #ffffff; background-color: #e1e4e7; text-align: center;" scope="col"><span style="font-size: 12pt;">Fin</span></th>
            <td style="border-style: dotted;">Semana No.{week}</td>
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
