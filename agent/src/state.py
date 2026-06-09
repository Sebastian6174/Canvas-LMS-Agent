import operator
from typing import TypedDict, Optional, List, Dict, Annotated
from pydantic import BaseModel, Field, model_validator


class Activity(BaseModel):
    name: str = Field(
        description="Título corto sin prefijo 'Actividad N.' (el sistema añade el nombre completo en Canvas)"
    )
    description: str
    duration: int
    activity_type: str = Field(
        default="Otros",
        description=(
            "Tipo de actividad: Videoconferencia, Taller, Foro, Tarea, Infografía, Ensayo, "
            "Quiz, Evaluación, Cuadro comparativo, Mapa mental, Entrega u Otros"
        ),
    )
    evaluation_type: str = Field(
        default="",
        description="Formativa o Evaluativa según el documento o la ponderación",
    )
    number: int = Field(
        default=0,
        description="Número secuencial de la actividad en el curso (1, 2, 3...)",
    )
    rubric: Optional[str] = None
    related_learning_outcome: str
    weight: float
    module_name: str = Field(
        default="",
        description="Nombre exacto de la unidad a la que pertenece (debe coincidir con modules[].name)",
    )
    resources: List[str] = Field(
        default_factory=list,
        description="Recursos o materiales de estudio indicados para esta actividad en el documento",
    )

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_type_field(cls, data):
        """Compatibilidad si el modelo devuelve el antiguo campo 'type'."""
        if not isinstance(data, dict) or "type" not in data:
            return data
        legacy = data.pop("type")
        if legacy in ("Formativa", "Evaluativa") and not data.get("evaluation_type"):
            data["evaluation_type"] = legacy
            data.setdefault("activity_type", "Otros")
        elif not data.get("activity_type"):
            data["activity_type"] = legacy
        return data


class ScheduleItem(BaseModel):
    week: int
    activity_name: str = Field(description="Nombre de la actividad (debe coincidir con uno en la lista de actividades)")
    time_commitment: str

class Module(BaseModel):
    """Unidad de aprendizaje del programa (módulo de contenido en Canvas)."""
    name: str = Field(
        description="Nombre de la unidad, p. ej. 'Unidad 1. Título del tema' (no usar 'eje temático')"
    )
    description: str
    activities: List[str] = Field(description="Nombres de actividades que pertenecen a esta unidad")

class RubricCriterion(BaseModel):
    name: str = Field(description="Nombre o descripción del criterio (ej: 'Criterio 1: Comprensión del concepto')")
    points: Optional[float] = Field(default=None, description="Puntos posibles para este criterio (opcional)")
    excelente: str = Field(description="Descripción del nivel Excelente")
    en_desarrollo: str = Field(description="Descripción del nivel En desarrollo")
    basico: str = Field(description="Descripción del nivel Básico")
    insuficiente: str = Field(description="Descripción del nivel Insuficiente")

class Rubric(BaseModel):
    name: str = Field(description="Nombre/Número unificado de la rúbrica (ej: 'Rúbrica N. 1', 'Rúbrica 2')")
    criteria: List[RubricCriterion] = Field(description="Lista de criterios de evaluación para esta rúbrica")

class CourseStructure(BaseModel):
    name: str
    academic_program: str
    semester: int
    academic_level: str
    credits: int
    prerequisites: List[str]
    teacher: str
    description: str = Field(description="Descripción concisa del curso")
    learning_outcomes: List[str]
    modules: List[Module]
    activities: List[Activity]
    schedule: List[ScheduleItem]
    rubrics: List[Rubric] = Field(default_factory=list, description="Lista de rúbricas inferidas del documento")

class CourseState(TypedDict):
    doc_id: str
    course_structure: Optional[CourseStructure]
    canvas_course_id: Optional[str]
    module_mapping: Optional[Dict[str, int]]
    teacher_info: Optional[str]
    alignment_page_url: Optional[str]
    agenda_page_url: Optional[str]
    forum_discussion_id: Optional[int]
    credits_page_url: Optional[str]
    rubrics_page_url: Optional[str]
    is_valid: bool
    errors: Annotated[List[str], operator.add]
    downloadable_program: str
    course_files_map: Optional[Dict[str, str]]