from __future__ import annotations

from typing import Any

try:
    from .agent_runner import agent_config
except ImportError:
    from agent_runner import agent_config


CONFIG_FIELDS = {
    "doc_id": str,
    "teacher_doc": str,
    "domain": str,
    "course_id": str,
    "base_course_id": str,
    "create_new_course": bool,
    "openrouter_model": str,
}


def parse_config(raw_config: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for key, caster in CONFIG_FIELDS.items():
        if key not in raw_config:
            continue
        parsed_value = _parse_value(raw_config[key], caster)
        if parsed_value is not None:
            parsed[key] = parsed_value
    return parsed


def validate_config(config: dict[str, Any]) -> str | None:
    if not config.get("doc_id") and not agent_config.doc_id:
        return "DOC_ID es obligatorio."
    if _requires_course_id(config) and not config.get("course_id") and not agent_config.course_id:
        return "COURSE_ID es obligatorio cuando no se crea un curso nuevo."
    return None


def _parse_value(value: Any, caster: type) -> Any:
    if caster is bool:
        return _parse_bool(value)

    cleaned = "" if value is None else str(value).strip()
    return cleaned or None


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}
    return bool(value)


def _requires_course_id(config: dict[str, Any]) -> bool:
    return not config.get("create_new_course")
