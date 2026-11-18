"""Esquemas de lo que el LLM extrae de cada sección del documento."""

from typing import List

from pydantic import BaseModel, Field

from src.state import RubricCriterion


class LearningOutcome(BaseModel):
    code: str = Field(description="Código del resultado de aprendizaje, p. ej. 'RA 1'")
    text: str = Field(description="Enunciado completo del resultado de aprendizaje")


class CourseOverview(BaseModel):
    name: str = Field(description="Nombre del curso (fila 'Curso'), no el del programa")
    academic_program: str = Field(default="", description="Programa académico tal como aparece")
    academic_level: str = Field(
        default="",
        description="Nivel académico (Tecnológico, Pregrado, Especialización, Maestría...). "
        "Si no aparece, dedúcelo del nombre del programa",
    )
    credits: int = Field(default=0, description="Número de créditos; 0 si no aparece")
    program_url: str = Field(default="", description="URL del enlace al microcurrículo o programa, si aparece")
    prerequisites: List[str] = Field(
        default_factory=list, description="Pre/co-requisitos; lista vacía si dice 'No aplica' o 'Ninguno'"
    )
    teacher: str = Field(default="", description="Nombre completo del profesor autor")
    description: str = Field(
        default="",
        description="Descripción del curso completa y literal. Separa los párrafos con saltos de línea "
        "y conserva las viñetas con '• '",
    )
    learning_outcomes: List[LearningOutcome] = Field(
        default_factory=list, description="Todos los resultados de aprendizaje, en orden"
    )


class ModuleInfo(BaseModel):
    number: int = Field(description="Número del módulo/unidad (1, 2, 3...)")
    title: str = Field(
        description="Título del módulo sin 'Módulo N', sin 'Nombre del' y sin el rango de semanas"
    )
    weeks: str = Field(default="", description="Semanas que abarca, p. ej. '1-2'")
    description: str = Field(
        default="",
        description="Texto completo y literal de la 'Presentación' del módulo; párrafos separados por saltos de línea",
    )
    learning_outcomes: List[str] = Field(
        default_factory=list, description="Sólo los códigos de los R.A. relacionados: ['RA 1', 'RA 2']"
    )
    indicators: List[str] = Field(
        default_factory=list,
        description="Indicadores de logro del módulo con su código, p. ej. '1.1 Distingue la estructura...'",
    )


class ModulesExtraction(BaseModel):
    modules: List[ModuleInfo] = Field(default_factory=list)


class ScheduleRow(BaseModel):
    number: int = Field(description="Número de la actividad tal como aparece en la tabla")
    activity_type: str = Field(description="Foro, Quiz, Tarea, Videoconferencia u Otros")
    name: str = Field(description="Título de la actividad sin el número y sin el tipo")
    module_number: int = Field(description="Número del módulo al que pertenece la tabla")
    week: int = Field(description="Semana indicada en la fila")
    evaluation_type: str = Field(description="'Formativa' o 'Evaluativa' según la columna AF/AE")
    independent_hours: float = Field(default=0, description="Horas independientes; 0 si la celda está vacía")
    accompanied_hours: float = Field(default=0, description="Horas acompañadas; 0 si la celda está vacía")
    weight: float = Field(default=0, description="% de valoración como número (10 para '10 %'); 0 si está vacío")


class ScheduleExtraction(BaseModel):
    activities: List[ScheduleRow] = Field(default_factory=list)


class ActivityFacts(BaseModel):
    delivery_form: str = Field(
        description="Una frase breve en imperativo con la forma de entrega, explícita o inferida"
    )
    resources: List[str] = Field(
        default_factory=list,
        description="Materiales de estudio, uno por elemento, con su enlace entre paréntesis si lo tiene",
    )
    has_rubric: bool = Field(default=False, description="true si el documento indica 'Rúbrica: Si'")


class ActivityDetail(ActivityFacts):
    description: str = Field(
        description="Descripción completa y literal de la actividad; párrafos separados por saltos de línea, viñetas con '• '"
    )


class RubricExtraction(BaseModel):
    activity_number: int = Field(default=0, description="Número de actividad indicado en la rúbrica; 0 si no aparece")
    activity_title: str = Field(description="Título de la actividad a la que pertenece la rúbrica")
    criteria: List[RubricCriterion] = Field(default_factory=list)


class RubricsExtraction(BaseModel):
    rubrics: List[RubricExtraction] = Field(default_factory=list)


class TeacherProfile(BaseModel):
    bio: str = Field(
        default="",
        description="Perfil profesional del docente, completo y literal; vacío si el documento no lo contiene",
    )
