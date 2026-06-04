"""
Tipos de actividad del curso y guías de estructura HTML para Canvas.

Amplía ACTIVITY_TYPE_HTML_GUIDE con el HTML o las instrucciones que quieras por tipo.
"""

from __future__ import annotations

from typing import Dict, Tuple

ACTIVITY_TYPE_DEFAULT = "Otros"

ACTIVITY_TYPES: Tuple[str, ...] = (
    "Videoconferencia",
    "Taller",
    "Foro",
    "Tarea",
    "Infografía",
    "Ensayo",
    "Quiz",
    "Evaluación",
    "Cuadro comparativo",
    "Mapa mental",
    "Entrega",
    "Otros",
)

# Clave: tipo de actividad. Valor: guía para el modelo sobre cómo estructurar el HTML en Canvas.
ACTIVITY_TYPE_HTML_GUIDE: Dict[str, str] = {
    "Videoconferencia": (
        "Ejemplo: título de la sesión, objetivos breves, fecha/hora, enlace o indicaciones "
        "de acceso, y recordatorio de asistencia."
    ),
    "Taller": (
        "Ejemplo: objetivo del taller, pasos o dinámica, materiales necesarios y criterios "
        "de participación."
    ),
    "Foro": (
        "Ejemplo: pregunta detonadora, instrucciones de participación, número mínimo de "
        "intervenciones y fecha límite."
    ),
    "Tarea": (
        "Ejemplo: enunciado, entregables, formato de entrega y fecha límite."
    ),
    "Infografía": (
        "Ejemplo: tema, elementos obligatorios de la infografía, formato de archivo y "
        "criterios de diseño."
    ),
    "Ensayo": (
        "Ejemplo: pregunta o tema, extensión, formato (APA u otro) y criterios de redacción."
    ),
    "Quiz": (
        "Ejemplo: indicaciones previas al cuestionario, número de intentos y tiempo límite "
        "si aplica."
    ),
    "Evaluación": (
        "Ejemplo: alcance de la evaluación, ponderación, criterios y fecha de entrega."
    ),
    "Cuadro comparativo": (
        "Ejemplo: elementos a comparar, columnas/filas esperadas y fuentes permitidas."
    ),
    "Mapa mental": (
        "Ejemplo: núcleo central, ramas obligatorias y herramienta o formato de entrega."
    ),
    "Entrega": (
        "Ejemplo: descripción del producto a entregar, formato de archivo y plazo."
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
) -> str:
    """Arma la descripción del assignment usando la guía del tipo (plantilla simple)."""
    activity_type = normalize_activity_type(activity_type)
    guide = ACTIVITY_TYPE_HTML_GUIDE.get(activity_type, ACTIVITY_TYPE_HTML_GUIDE[ACTIVITY_TYPE_DEFAULT])
    eval_label = infer_evaluation_type(weight)
    return (
        f"<p><em>Plantilla ({activity_type}):</em> {guide}</p>"
        f"<hr />"
        f"<div>{description}</div>"
        f"<br /><br />"
        f"<strong>Resultado de aprendizaje:</strong> {related_learning_outcome}<br />"
        f"<strong>Naturaleza:</strong> {eval_label}<br />"
        f"<strong>Puntos:</strong> {weight}"
    )
