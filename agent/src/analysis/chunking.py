"""División del documento en fragmentos para el análisis incremental."""

import re

from config import config

DEFAULT_CHUNK_SIZE = 6000
DEFAULT_MIN_CHUNK_SIZE = 1200

TRUNCATION_MARKERS = (
    "length limit was reached",
    "max_tokens",
    "maximum length",
    "incomplete json",
    "jsondecodeerror",
    "could not parse response",
)


def _min_chunk_size() -> int:
    return int(getattr(config, "analysis_min_chunk_size", DEFAULT_MIN_CHUNK_SIZE))


def document_text(doc_content: list[dict]) -> str:
    """Une las pestañas del documento en un solo texto sin caracteres de control."""
    text = "\n\n".join(f"Tab: {tab['title']}\n{tab['content']}" for tab in doc_content)
    return re.sub(r"[\x00-\x1F\x7F]", " ", text)


def split_into_chunks(text: str) -> list[str]:
    """Trocea el texto completo en fragmentos de tamaño configurable."""
    chunk_size = max(
        int(getattr(config, "analysis_chunk_size", DEFAULT_CHUNK_SIZE)),
        _min_chunk_size() * 2,
    )
    return [text[pos:pos + chunk_size] for pos in range(0, len(text), chunk_size)] or [""]


def split_chunk(text: str) -> tuple[str, str] | None:
    """Divide un fragmento largo en dos partes, priorizando límites de palabras."""
    minimum = _min_chunk_size()
    if len(text) < minimum * 2:
        return None

    midpoint = len(text) // 2
    split_at = text.rfind(" ", minimum, midpoint + 1)
    if split_at < minimum:
        split_at = text.find(" ", midpoint)
    if split_at < minimum or split_at >= len(text) - minimum:
        split_at = midpoint
    return text[:split_at].strip(), text[split_at:].strip()


def is_truncation_error(error: Exception) -> bool:
    """Indica si el LLM cortó la respuesta por límite de longitud."""
    message = str(error).lower()
    return any(marker in message for marker in TRUNCATION_MARKERS)
