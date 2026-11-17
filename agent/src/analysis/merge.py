"""Acumulación de los fragmentos parciales que devuelve el LLM."""

from src.state import PartialCourseStructure


def merge_partial(existing: dict, incoming: PartialCourseStructure) -> dict:
    merged = dict(existing)
    for field in ("name", "academic_program", "semester", "academic_level", "credits", "teacher", "description"):
        value = getattr(incoming, field)
        if value not in ("", 0, None):
            merged[field] = value

    def merge_named(items, key="name"):
        result = {item.get(key, "").strip().lower(): item for item in merged.get(field_name, []) if item.get(key)}
        for item in items:
            item_dict = item.model_dump() if hasattr(item, "model_dump") else item
            item_key = item_dict.get(key, "").strip().lower()
            if not item_key:
                continue
            if item_key in result:
                result[item_key] = {**result[item_key], **{k: v for k, v in item_dict.items() if v not in ("", 0, [], None)}}
            else:
                result[item_key] = item_dict
        return list(result.values())

    for field_name in ("modules", "activities", "rubrics"):
        merged[field_name] = merge_named(getattr(incoming, field_name))

    for field_name in ("prerequisites", "learning_outcomes", "schedule"):
        values = [item.model_dump() if hasattr(item, "model_dump") else item for item in getattr(incoming, field_name)]
        current = merged.get(field_name, [])
        for value in values:
            if value not in current:
                current.append(value)
        merged[field_name] = current
    return merged
