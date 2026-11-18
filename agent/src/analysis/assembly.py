"""
Ensamblado determinista de la estructura del curso a partir de lo extraído.

Aquí se decide todo lo que no debe depender del LLM: el orden y la numeración de
las actividades (los de la tabla de secuencia), los nombres visibles, la unidad
de cada actividad, la rúbrica que le corresponde y las validaciones.
"""

import re
from typing import Dict, List, Optional, Tuple

from src.activities.rules import (
    EVALUATIVE,
    FORMATIVE,
    format_activity_display_name,
    infer_evaluation_type,
    normalize_activity_type,
    weight_as_percent,
)
from src.analysis.schemas import (
    ActivityDetail,
    CourseOverview,
    ModuleInfo,
    RubricExtraction,
    ScheduleRow,
)
from src.analysis.sections import normalize, similarity
from src.state import Activity, CourseStructure, Module, Rubric, ScheduleItem

RUBRIC_NAME_MATCH = 0.75
RUBRIC_LOOSE_MATCH = 0.5
NO_PREREQUISITES = {"no aplica", "ninguno", "ninguna", "n a", "no"}


def unit_name(number: int, title: str) -> str:
    """'Unidad N. Título' a partir del título del módulo en el documento."""
    clean = re.sub(r"^\s*(nombre\s+del\s+)?(m[oó]dulo|unidad)\s*\d*\s*[.:\-–]?\s*", "", title or "", flags=re.IGNORECASE)
    clean = re.sub(r"\s*\(\s*semanas?[^)]*\)\s*$", "", clean, flags=re.IGNORECASE).strip()
    return f"Unidad {number}. {clean}" if clean else f"Unidad {number}"


def clean_activity_title(name: str, activity_type: str) -> str:
    """Título sin número inicial, sin el tipo repetido y sin comillas envolventes."""
    title = re.sub(r"^\s*\d+\s*[.)]\s*", "", one_line(name))
    title = re.sub(rf"^\s*{re.escape(activity_type)}\s*[.:]\s*", "", title, flags=re.IGNORECASE)
    return title.strip().strip("“”\"'«»").strip()


def one_line(text: str) -> str:
    """Texto en una sola línea, sin espacios repetidos."""
    return " ".join((text or "").split())


def outcome_code(text: str) -> str:
    """Código normalizado de un resultado de aprendizaje: 'RA. 1.' o 'RA1' -> 'RA 1'."""
    match = re.search(r"R\.?\s*A\.?\s*(\d+)", text or "", flags=re.IGNORECASE)
    return f"RA {match.group(1)}" if match else one_line(text)


def _outcome_line(code: str, text: str) -> str:
    code, text = outcome_code(code), one_line(text)
    text = re.sub(r"^R\.?\s*A\.?\s*\d+\s*[.:\-]?\s*", "", text, flags=re.IGNORECASE)
    return f"{code}. {text}" if code else text


def _explicit_evaluation(raw: str) -> Optional[str]:
    text = normalize(raw)
    if "format" in text:
        return FORMATIVE
    if "evalua" in text:
        return EVALUATIVE
    return None


def _ordered(pairs: List[Tuple[ScheduleRow, Optional[ActivityDetail]]]):
    """Orden de la secuencia: por número si es confiable; si no, el de aparición."""
    numbers = [row.number for row, _ in pairs]
    if all(number > 0 for number in numbers) and len(set(numbers)) == len(numbers):
        return sorted(pairs, key=lambda pair: pair[0].number)
    return pairs


def _build_modules(modules: List[ModuleInfo], rows: List[ScheduleRow]) -> List[Module]:
    infos = {info.number: info for info in modules if info.number > 0}
    # Un módulo que sólo aparece en la tabla de secuencia también debe existir.
    for number in sorted({row.module_number for row in rows if row.module_number > 0}):
        infos.setdefault(number, ModuleInfo(number=number, title=""))
    return [
        Module(
            number=info.number,
            name=unit_name(info.number, info.title),
            description=info.description,
            weeks=info.weeks,
            learning_outcomes=list(dict.fromkeys(outcome_code(o) for o in info.learning_outcomes)),
            indicators=[one_line(indicator) for indicator in info.indicators],
        )
        for info in sorted(infos.values(), key=lambda info: info.number)
    ]


def _module_for(row: ScheduleRow, modules: List[Module], previous: Optional[Module]) -> Optional[Module]:
    by_number = {module.number: module for module in modules}
    return by_number.get(row.module_number) or previous or (modules[0] if modules else None)


def _link_rubrics(
    activities: List[Activity],
    short_titles: Dict[int, str],
    extracted: List[RubricExtraction],
    warnings: List[str],
) -> Tuple[List[Activity], List[Rubric]]:
    """Asocia cada rúbrica a su actividad: primero por nombre y, si no, por número."""
    by_number = {activity.number: activity for activity in activities}
    assigned: Dict[int, str] = {}
    rubrics: List[Rubric] = []

    for extraction in extracted:
        if not extraction.criteria:
            continue
        free = [activity for activity in activities if activity.number not in assigned]
        scored = sorted(
            ((similarity(extraction.activity_title, short_titles[a.number]), a) for a in free),
            key=lambda pair: pair[0],
            reverse=True,
        )
        best_score, best = scored[0] if scored else (0.0, None)
        numbered = by_number.get(extraction.activity_number)
        if numbered is not None and numbered.number in assigned:
            numbered = None

        if best is not None and best_score >= RUBRIC_NAME_MATCH:
            target = best
        elif numbered is not None:
            target = numbered
        elif best is not None and best_score >= RUBRIC_LOOSE_MATCH:
            target = best
        else:
            warnings.append(f"La rúbrica «{extraction.activity_title}» no se pudo asociar a ninguna actividad.")
            continue

        rubric_name = f"Rúbrica - {target.name}"
        assigned[target.number] = rubric_name
        rubrics.append(Rubric(name=rubric_name, criteria=extraction.criteria))

    linked = [
        activity.model_copy(update={"rubric": assigned.get(activity.number)}) for activity in activities
    ]
    return linked, rubrics


def build_course_structure(
    overview: CourseOverview,
    modules: List[ModuleInfo],
    schedule: List[ScheduleRow],
    details: List[Optional[ActivityDetail]],
    rubrics: List[RubricExtraction],
) -> Tuple[CourseStructure, List[str]]:
    """
    Construye la estructura final. `details[i]` es el detalle de `schedule[i]`
    (None si no se encontró). Devuelve también las advertencias detectadas.
    """
    warnings: List[str] = []
    units = _build_modules(modules, schedule)

    activities: List[Activity] = []
    short_titles: Dict[int, str] = {}
    declared_rubric: Dict[int, bool] = {}
    previous_unit: Optional[Module] = None

    padded = list(details) + [None] * (len(schedule) - len(details))
    for number, (row, detail) in enumerate(_ordered(list(zip(schedule, padded))), start=1):
        activity_type = normalize_activity_type(row.activity_type)
        title = clean_activity_title(row.name, activity_type)
        weight = weight_as_percent(row.weight)
        unit = _module_for(row, units, previous_unit)
        previous_unit = unit
        if detail is None:
            warnings.append(f"La actividad {number} («{title}») no tiene descripción en el documento.")

        short_titles[number] = title
        declared_rubric[number] = bool(detail and detail.has_rubric)
        activities.append(
            Activity(
                number=number,
                name=format_activity_display_name(number, activity_type, title),
                activity_type=activity_type,
                evaluation_type=infer_evaluation_type(weight, _explicit_evaluation(row.evaluation_type)),
                weight=weight,
                week=row.week,
                independent_hours=row.independent_hours,
                accompanied_hours=row.accompanied_hours,
                duration=round(row.independent_hours + row.accompanied_hours),
                module_name=unit.name if unit else "",
                related_learning_outcome=", ".join(unit.learning_outcomes) if unit else "",
                description=detail.description if detail else "",
                delivery_form=detail.delivery_form if detail else "",
                resources=detail.resources if detail else [],
            )
        )

    activities, course_rubrics = _link_rubrics(activities, short_titles, rubrics, warnings)
    for activity in activities:
        if declared_rubric[activity.number] and not activity.rubric:
            warnings.append(f"«{activity.name}» indica rúbrica, pero no se encontró en el documento.")

    units = [
        unit.model_copy(update={"activities": [a.name for a in activities if a.module_name == unit.name]})
        for unit in units
    ]

    total_weight = sum(activity.weight for activity in activities)
    if activities and abs(total_weight - 100) > 0.01:
        warnings.append(f"Las ponderaciones suman {total_weight:g} %, no 100 %.")

    prerequisites = [p for p in overview.prerequisites if normalize(p) not in NO_PREREQUISITES]
    structure = CourseStructure(
        name=one_line(overview.name),
        academic_program=one_line(overview.academic_program),
        academic_level=one_line(overview.academic_level),
        credits=overview.credits,
        program_url=overview.program_url.strip(),
        total_hours=sum(activity.duration for activity in activities),
        prerequisites=prerequisites,
        teacher=one_line(overview.teacher),
        description=overview.description,
        learning_outcomes=[
            _outcome_line(outcome.code, outcome.text)
            for outcome in overview.learning_outcomes
            if outcome.text.strip()
        ],
        modules=units,
        activities=activities,
        schedule=[
            ScheduleItem(
                week=activity.week,
                activity_name=activity.name,
                time_commitment=f"{activity.duration} horas",
            )
            for activity in activities
        ],
        rubrics=course_rubrics,
    )
    return structure, warnings
