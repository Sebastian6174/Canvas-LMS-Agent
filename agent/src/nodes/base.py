"""
Contrato común de los nodos del grafo.

`errors` usa un reducer acumulativo (operator.add): lo que devuelve un nodo se
SUMA a lo que ya hay en el estado. Por eso un nodo secuencial nunca debe
devolver los errores que recibió (se duplicarían en cada paso); sólo los nuevos.
`proceed` y `fail` garantizan esa regla.

Los nodos que corren en paralelo (agenda, alineación, foro, créditos) devuelven
únicamente las claves que escriben, para no pisarse entre sí.
"""

from typing import Any, Optional

from config import config
from src.state import CourseState


def proceed(state: CourseState, **updates: Any) -> dict:
    """Estado actualizado sin errores nuevos."""
    return {**state, **updates, "errors": []}


def fail(state: CourseState, message: str, **updates: Any) -> dict:
    """Estado actualizado registrando un único error nuevo."""
    return {**state, **updates, "errors": [message]}


def resolve_course_id(state: CourseState) -> Optional[str]:
    """Curso de Canvas sobre el que trabaja el pipeline."""
    return state.get("canvas_course_id") or config.course_id
