import operator
from typing import TypedDict, Optional, List, Dict, Annotated
from pydantic import BaseModel, Field, model_validator


class Activity(BaseModel):
    name: str = Field(
        description="Nombre visible en Canvas: 'Actividad N. Tipo: título' (lo arma el analista)"
    )
    description: str = Field(
        default="",
        description="Texto completo de la actividad; '\\n' separa párrafos y '• ' marca viñetas"
    )
    duration: int = Field(default=0, description="Dedicación total en horas (independientes + acompañadas)")
    independent_hours: float = 0
    accompanied_hours: float = 0
    activity_type: str = Field(
        default="Otros",
        description="Tipo de actividad: Foro, Quiz, Tarea, Videoconferencia u Otros",
    )
    evaluation_type: str = Field(
        default="",
        description="Formativa o Evaluativa según el documento o la ponderación",
    )
    number: int = Field(
        default=0,
        description="Número de la actividad en el curso, en el orden de la secuencia (1, 2, 3...)",
    )
    week: int = Field(default=0, description="Semana del curso en la que se desarrolla")
    rubric: Optional[str] = Field(default=None, description="Nombre de la rúbrica asociada, si tiene")
    related_learning_outcome: str = Field(
        default="", description="Códigos de los R.A. relacionados, p. ej. 'RA 1, RA 2'"
    )
    weight: float = Field(default=0, description="Porcentaje de la nota final (0 a 100)")
    delivery_form: str = Field(
        default="",
        description="Forma de entrega (la del documento o la inferida por el analista)",
    )
    module_name: str = Field(
        default="",
        description="Nombre exacto de la unidad a la que pertenece (coincide con modules[].name)",
    )
    resources: List[str] = Field(
        default_factory=list,
        description="Materiales de estudio; los enlaces van como 'texto (url)'",
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
    activity_name: str = Field(description="Nombre de la actividad (coincide con activities[].name)")
    time_commitment: str


class Module(BaseModel):
    """Unidad de aprendizaje del programa (módulo de contenido en Canvas)."""
    name: str = Field(description="Nombre de la unidad: 'Unidad N. Título'")
    description: str = Field(default="", description="Presentación de la unidad")
    activities: List[str] = Field(
        default_factory=list, description="Nombres de las actividades de la unidad, en orden"
    )
    number: int = 0
    weeks: str = Field(default="", description="Semanas que abarca, p. ej. '1-2'")
    learning_outcomes: List[str] = Field(
        default_factory=list, description="Códigos de los R.A. de la unidad, p. ej. ['RA 1', 'RA 2']"
    )
    indicators: List[str] = Field(
        default_factory=list, description="Indicadores de logro con su código, p. ej. '1.1 Distingue...'"
    )


class RubricCriterion(BaseModel):
    name: str = Field(description="Nombre del criterio, sin el porcentaje")
    points: Optional[float] = Field(default=None, description="Peso del criterio dentro de la rúbrica (porcentaje o puntos)")
    excelente: str = Field(default="", description="Descripción del nivel Excelente")
    en_desarrollo: str = Field(default="", description="Descripción del nivel En desarrollo")
    basico: str = Field(default="", description="Descripción del nivel Básico")
    insuficiente: str = Field(default="", description="Descripción del nivel Insuficiente")

    @model_validator(mode="before")
    @classmethod
    def _parse_points(cls, data):
        if not isinstance(data, dict):
            return data
        points = data.get("points")
        if isinstance(points, str):
            cleaned = points.replace("%", "").replace("pts", "").replace("puntos", "").strip()
            try:
                data["points"] = float(cleaned)
            except ValueError:
                data["points"] = None
        return data


class Rubric(BaseModel):
    name: str = Field(description="Nombre de la rúbrica; las actividades la referencian en `rubric`")
    criteria: List[RubricCriterion] = Field(description="Criterios de evaluación de la rúbrica")


class CourseStructure(BaseModel):
    name: str
    academic_program: str
    semester: int = 0
    academic_level: str = ""
    credits: int = 0
    total_hours: int = Field(default=0, description="Horas totales del curso")
    program_url: str = Field(default="", description="Enlace al microcurrículo / programa descargable")
    prerequisites: List[str] = Field(default_factory=list)
    teacher: str = ""
    description: str = Field(default="", description="Descripción/introducción del curso")
    learning_outcomes: List[str] = Field(
        default_factory=list, description="Resultados de aprendizaje: 'RA 1. Texto...'"
    )
    modules: List[Module] = Field(default_factory=list)
    activities: List[Activity] = Field(default_factory=list)
    schedule: List[ScheduleItem] = Field(default_factory=list)
    rubrics: List[Rubric] = Field(default_factory=list)


class CourseState(TypedDict):
    doc_id: str
    course_structure: Optional[CourseStructure]
    canvas_course_id: Optional[str]
    module_mapping: Optional[Dict[str, int]]
    teacher_info: Optional[str]  # Perfil profesional del docente
    alignment_page_url: Optional[str]
    agenda_page_url: Optional[str]
    forum_discussion_id: Optional[int]
    credits_page_url: Optional[str]
    syllabus_page_url: Optional[str]
    is_valid: bool
    errors: Annotated[List[str], operator.add]
    course_files_map: Optional[Dict[str, str]]
    canvas_assignment_ids: Optional[Dict[str, int]]
