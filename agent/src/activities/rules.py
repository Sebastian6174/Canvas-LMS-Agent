"""
Reglas de negocio de una actividad: tipos válidos, nombre visible,
naturaleza (formativa/evaluativa), ponderación y forma de entrega por defecto.
"""

from typing import Dict, Tuple

ACTIVITY_TYPE_DEFAULT = "Otros"

ACTIVITY_TYPES: Tuple[str, ...] = (
    "Foro",
    "Quiz",
    "Tarea",
    "Videoconferencia",
    "Otros",
)

FORMATIVE = "Formativa"
EVALUATIVE = "Evaluativa"

# Forma de entrega por defecto cuando el documento no la indica. Sirve como
# referencia para que el LLM la infiera y como respaldo si el LLM no responde.
DEFAULT_DELIVERY_FORM_BY_TYPE: Dict[str, str] = {
    "Foro": "Participe en el foro con su aporte y responda a sus compañeros.",
    "Quiz": "Responda el cuestionario en Canvas dentro del plazo establecido.",
    "Tarea": "Envíe el documento a través de esta actividad en Canvas.",
    "Videoconferencia": "Participe del encuentro sincrónico.",
    "Otros": "Desarrolle la actividad según las indicaciones y entréguela en Canvas.",
}

_TYPE_LOOKUP = {t.lower(): t for t in ACTIVITY_TYPES}


def normalize_activity_type(raw: str | None) -> str:
    """Devuelve un tipo válido; si no coincide, 'Otros'."""
    if not raw:
        return ACTIVITY_TYPE_DEFAULT
    return _TYPE_LOOKUP.get(raw.strip().lower(), ACTIVITY_TYPE_DEFAULT)


def format_activity_display_name(number: int, activity_type: str, name: str) -> str:
    """Actividad N. Tipo: nombre (sin duplicar prefijo si ya viene en name)."""
    short = name.strip()
    prefix = f"Actividad {number}. {normalize_activity_type(activity_type)}:"
    if short.lower().startswith((prefix.lower(), f"actividad {number}.")):
        return short
    return f"{prefix} {short}"


def weight_as_percent(weight: float | None) -> float:
    """Ponderación en escala 0-100 (acepta fracciones como 0.2 -> 20)."""
    value = float(weight or 0)
    if 0 < abs(value) < 1:
        value *= 100
    return round(value, 4)


def format_weight(weight: float | None) -> str:
    """Ponderación en porcentaje sin decimales sobrantes ('20', '12.5')."""
    value = weight_as_percent(weight)
    return str(int(value)) if value.is_integer() else str(value).rstrip("0").rstrip(".")


def infer_evaluation_type(weight: float | None, explicit: str | None = None) -> str:
    """'Formativa' o 'Evaluativa': manda lo que diga el documento; si no, la ponderación."""
    if explicit:
        value = explicit.strip().capitalize()
        if value in (FORMATIVE, EVALUATIVE):
            return value
    return EVALUATIVE if weight_as_percent(weight) > 0 else FORMATIVE


def is_evaluative(activity) -> bool:
    """Indica si la actividad cuenta para la nota final."""
    return infer_evaluation_type(
        getattr(activity, "weight", 0),
        getattr(activity, "evaluation_type", None),
    ) == EVALUATIVE
