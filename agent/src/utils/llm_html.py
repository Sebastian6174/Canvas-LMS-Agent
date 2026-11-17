"""Generación de HTML con el LLM para las páginas de contenido del curso."""

from typing import Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from config import config
from src.utils.course_files import resolve_html_links


def strip_code_fences(text: str) -> str:
    """Quita las marcas ```html / ``` que a veces envuelven la respuesta del LLM."""
    return text.replace("```html", "").replace("```", "").strip()


def generate_html(system_prompt: str, human_prompt: str) -> str:
    """Pide HTML al LLM y elimina las marcas de bloque de código de la respuesta."""
    response = config.get_llm().invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ])
    return strip_code_fences(response.content)


def generate_course_html(
    system_prompt: str,
    human_prompt: str,
    files_map: Optional[Dict[str, str]],
    course_id: str,
) -> str:
    """Genera HTML y resuelve sus enlaces a archivos del curso actual."""
    html = generate_html(system_prompt, human_prompt)
    return resolve_html_links(html, files_map or {}, config.domain, course_id)
