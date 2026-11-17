"""
Contenido variable de una actividad generado por el LLM.

El modelo recibe como referencia `example_activity.html` y devuelve sólo las
partes que dependen del documento: descripción en párrafos, forma de entrega
(explícita o inferida) y materiales. La estructura fija (banner, peso, tabla)
la arma `template.py`, así el LLM no puede romperla.
"""

import re
from pathlib import Path
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.activities.template import plain_text_to_paragraphs
from src.utils.llm_html import strip_code_fences
from src.activities.rules import (
    DEFAULT_DELIVERY_FORM_BY_TYPE,
    infer_evaluation_type,
    normalize_activity_type,
)

EXAMPLE_HTML = (Path(__file__).with_name("example_activity.html")).read_text(encoding="utf-8")

# Etiquetas que el LLM puede usar dentro de la descripción.
_ALLOWED_TAGS = r"p|span|strong|em|b|i|u|br|ul|ol|li|a"


class ActivityContent(BaseModel):
    description_html: str = Field(
        description=(
            "Descripción de la actividad en párrafos HTML <p><span>…</span></p>, "
            "fiel al documento. Sin títulos de sección, banner ni tabla."
        )
    )
    delivery_form: str = Field(
        description="Una frase en imperativo con la forma de entrega (explícita o inferida)."
    )
    resources: List[str] = Field(
        default_factory=list,
        description="Materiales de estudio, uno por elemento, tal como aparecen en el documento.",
    )


def _delivery_hints() -> str:
    return "\n".join(
        f"- {activity_type}: {hint}" for activity_type, hint in DEFAULT_DELIVERY_FORM_BY_TYPE.items()
    )


SYSTEM_PROMPT = f"""Eres un experto en diseño instruccional y Canvas LMS.
Preparas el contenido de una actividad para Canvas siguiendo el estilo de este ejemplo real:

{EXAMPLE_HTML}

Devuelve SOLO estos campos:
1. description_html: el texto de "Descripción de la Actividad" dividido en párrafos
   <p><span>…</span></p> como en el ejemplo. Conserva íntegro el contenido del documento
   (instrucciones, pasos, preguntas); no resumas ni agregues información nueva. Puedes usar
   <strong>, <em>, <ul>/<ol>/<li> cuando el documento tenga listas o pasos. No incluyas
   títulos de sección, banner, peso, materiales ni la tabla resumen.
2. delivery_form: una frase breve en imperativo, como "Participe del encuentro sincrónico.".
   Si el documento indica la forma de entrega, úsala. Si NO la indica, infiérela a partir del
   tipo de actividad y de lo que la descripción pide hacer (subir un documento, participar en
   el foro, responder el cuestionario, asistir a la sesión, etc.). Referencias por tipo:
{_delivery_hints()}
3. resources: los materiales de estudio indicados, un elemento por material, con su nombre
   tal cual (incluida la extensión si es un archivo). Lista vacía si no hay.
"""


def _human_prompt(activity, week: int) -> str:
    activity_type = normalize_activity_type(activity.activity_type)
    lines = [
        f"Nombre: {activity.name}",
        f"Tipo de actividad: {activity_type}",
        f"Naturaleza: {infer_evaluation_type(activity.weight, activity.evaluation_type)}",
        f"Semana: {week}",
        f"Dedicación (horas): {activity.duration}",
        f"Descripción en el documento: {activity.description}",
        f"Forma de entrega en el documento: {activity.delivery_form or 'NO INDICADA (debes inferirla)'}",
        f"Materiales en el documento: {'; '.join(activity.resources) if activity.resources else 'ninguno'}",
    ]
    return "\n".join(lines)


def _clean_description_html(html: str) -> str:
    """Quita marcas de código y cualquier etiqueta fuera de las permitidas."""
    html = strip_code_fences(html)
    html = re.sub(rf"</?(?!(?:{_ALLOWED_TAGS})\b)[a-zA-Z][^>]*>", "", html)
    return "\n".join(f"    {line.strip()}" for line in html.splitlines() if line.strip())


def fallback_content(activity) -> ActivityContent:
    """Contenido sin LLM: texto del documento en párrafos y entrega por tipo de actividad."""
    activity_type = normalize_activity_type(activity.activity_type)
    return ActivityContent(
        description_html=plain_text_to_paragraphs(activity.description),
        delivery_form=(activity.delivery_form or "").strip()
        or DEFAULT_DELIVERY_FORM_BY_TYPE[activity_type],
        resources=list(activity.resources or []),
    )


def generate_activity_content(llm, activity, week: int = 1) -> ActivityContent:
    """Contenido de la actividad con el LLM; si no hay LLM o la respuesta no sirve, usa el respaldo."""
    fallback = fallback_content(activity)
    if llm is None:
        return fallback

    try:
        result = llm.with_structured_output(ActivityContent).invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=_human_prompt(activity, week)),
        ])
        if not isinstance(result, ActivityContent):
            result = ActivityContent.model_validate(
                result.model_dump() if hasattr(result, "model_dump") else result
            )
    except Exception as error:
        print(f"No se pudo generar el contenido de '{activity.name}' con el LLM ({error}). Se usa el texto del documento.")
        return fallback

    description = _clean_description_html(result.description_html)
    return ActivityContent(
        description_html=description or fallback.description_html,
        delivery_form=result.delivery_form.strip() or fallback.delivery_form,
        resources=[r for r in result.resources if r and r.strip()] or fallback.resources,
    )


def safe_get_llm(get_llm) -> Optional[object]:
    """Crea el LLM o devuelve None si no está configurado (las actividades usan el respaldo)."""
    try:
        return get_llm()
    except Exception as error:
        print(f"LLM no disponible para el contenido de actividades: {error}")
        return None
