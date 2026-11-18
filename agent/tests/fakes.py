"""LLM simulado que responde a cada esquema del analista con un curso fijo."""

from src.analysis.schemas import (
    ActivityDetail,
    ActivityFacts,
    CourseOverview,
    LearningOutcome,
    ModuleInfo,
    ModulesExtraction,
    RubricExtraction,
    RubricsExtraction,
    ScheduleExtraction,
    ScheduleRow,
    TeacherProfile,
)
from src.state import RubricCriterion

# Tabla de secuencia del curso falso (el orden del documento es 2, 1 a propósito
# para verificar que se respeta la numeración y no el orden de respuesta).
SCHEDULE = [
    ScheduleRow(number=2, activity_type="Tarea", name="Tarea: Ensayo", module_number=1, week=2,
                evaluation_type="A. Evaluativa", independent_hours=8, accompanied_hours=1, weight=100),
    ScheduleRow(number=1, activity_type="Videoconferencia", name="Bienvenida", module_number=1, week=1,
                evaluation_type="A.Formativa", independent_hours=0, accompanied_hours=3, weight=0),
]

BIO = "Licenciada en Literatura con maestría en Lingüística y veinte años de experiencia enseñando escritura académica en programas tecnológicos."

RUBRIC = RubricExtraction(
    activity_number=2,
    activity_title="Ensayo",
    criteria=[
        RubricCriterion(name="Argumentación", points=60, excelente="E", en_desarrollo="D", basico="B", insuficiente="I"),
        RubricCriterion(name="Redacción", points=40, excelente="E", en_desarrollo="D", basico="B", insuficiente="I"),
    ],
)


def response_for(schema, prompt: str = ""):
    if schema is CourseOverview:
        return CourseOverview(
            name="Curso de Prueba",
            academic_program="Tecnología en Pruebas",
            academic_level="Tecnológico",
            credits=2,
            prerequisites=["No aplica"],
            teacher="Docente Uno",
            description="Primer párrafo.\nSegundo párrafo.",
            learning_outcomes=[LearningOutcome(code="RA. 1.", text="Reconoce los textos.")],
        )
    if schema is ModulesExtraction:
        return ModulesExtraction(modules=[
            ModuleInfo(number=1, title="Módulo 1: Inicio (Semanas 1 y 2)", weeks="1-2",
                       description="Presentación.", learning_outcomes=["RA 1"],
                       indicators=["1.1 Distingue documentos."]),
        ])
    if schema is ScheduleExtraction:
        return ScheduleExtraction(activities=SCHEDULE)
    if schema is ActivityFacts:
        return ActivityFacts(delivery_form="Suba el ensayo en PDF.", resources=["Lectura 1 (https://ejemplo.org/l1)"], has_rubric=True)
    if schema is ActivityDetail:
        return ActivityDetail(description="Detalle.", delivery_form="Participe del encuentro sincrónico.", resources=[])
    if schema is RubricExtraction:
        return RUBRIC
    if schema is RubricsExtraction:
        return RubricsExtraction(rubrics=[RUBRIC])
    if schema is TeacherProfile:
        return TeacherProfile(bio=BIO)
    raise AssertionError(f"Esquema inesperado: {schema}")


class _Structured:
    def __init__(self, llm, schema):
        self.llm, self.schema = llm, schema

    def invoke(self, messages):
        self.llm.calls.append(self.schema.__name__)
        return response_for(self.schema, messages[-1].content)


class FakeAnalystLLM:
    """Responde por esquema; `calls` registra las extracciones pedidas."""

    def __init__(self):
        self.calls = []

    def with_structured_output(self, schema):
        return _Structured(self, schema)
