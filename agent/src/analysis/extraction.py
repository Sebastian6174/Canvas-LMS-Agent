"""
Extracción con LLM, una llamada enfocada por sección del documento.

Cada método recibe sólo el texto que necesita (una pestaña, una tabla) y pide un
esquema pequeño. Así las respuestas no se truncan y el orden y la numeración de
las actividades salen de la tabla de secuencia, no del orden de llegada.
"""

import re
from typing import Any, List, Optional, Type, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.activities.rules import ACTIVITY_TYPE_DEFAULT, ACTIVITY_TYPES, DEFAULT_DELIVERY_FORM_BY_TYPE
from src.analysis.schemas import (
    ActivityDetail,
    ActivityFacts,
    CourseOverview,
    ModuleInfo,
    ModulesExtraction,
    RubricExtraction,
    RubricsExtraction,
    ScheduleExtraction,
    ScheduleRow,
    TeacherProfile,
)
from src.analysis.sections import (
    Block,
    DocumentSections,
    block_to_plain,
    find_activity_block,
    labeled_cell,
    normalize,
)
from src.tools.doc_parser import blocks_to_text

Schema = TypeVar("Schema", bound=BaseModel)

MAX_ATTEMPTS = 2
MIN_BIO_WORDS = 15
# Algunos modelos devuelven el nombre del tipo como valor cuando no encuentran el dato.
_PLACEHOLDER_STRINGS = {"string", "str", "null", "none", "n/a"}

BASE_RULES = (
    "Eres un analista de documentos curriculares universitarios. Extrae únicamente lo que está en el "
    "texto recibido; no inventes ni completes con conocimiento externo. Si un dato no aparece, deja el "
    "campo vacío (\"\" , 0 o lista vacía); nunca escribas valores de relleno. Copia los textos de forma "
    "literal, sin resumir. En las tablas cada fila va entre '|', '<br>' marca un salto de línea dentro de "
    "una celda y '•' una viñeta."
)

OVERVIEW_RULES = (
    "Extrae la información general del curso y la lista completa de resultados de aprendizaje (RA). "
    "'name' es el nombre del curso, no el del programa académico. Cada RA lleva su código ('RA 1') y "
    "su enunciado completo."
)

MODULES_RULES = (
    "Extrae los módulos (unidades) del curso, en orden. Para cada uno: número, título limpio, semanas, "
    "presentación literal, códigos de los RA relacionados e indicadores de logro. Toma los indicadores "
    "de logro de la tabla de alineación (fila cuyas semanas y actividades corresponden al módulo); si "
    "allí no están, usa los de la secuencia. No incluyas actividades."
)

SCHEDULE_RULES = (
    "Extrae TODAS las filas de actividades de las tablas de secuencia (columnas Semana, Actividad, "
    "AF/AE, Dedicación en horas independientes y acompañadas, % de Valoración), en el mismo orden en "
    "que aparecen. Una fila por actividad, sin repetir ni omitir ninguna. 'module_number' es el módulo "
    "bajo el que está la tabla. "
    f"Clasifica 'activity_type' con uno de: {', '.join(ACTIVITY_TYPES)} (si el título no indica el tipo "
    f"o no encaja, usa '{ACTIVITY_TYPE_DEFAULT}'). En 'name' deja sólo el título, sin número ni tipo. "
    "'evaluation_type' sale de la columna AF/AE: 'A.Formativa' es Formativa y 'A. Evaluativa' es Evaluativa."
)


def _delivery_hints() -> str:
    return " ".join(f"{kind}: \"{hint}\"" for kind, hint in DEFAULT_DELIVERY_FORM_BY_TYPE.items())


ACTIVITY_RULES = (
    "Extrae los datos de UNA actividad del curso. "
    "'delivery_form': una frase breve en imperativo que diga cómo se entrega o se participa "
    "(p. ej. \"Participe del encuentro sincrónico.\" o \"Suba al Campus Virtual un archivo PDF con el informe.\"). "
    "Si el texto describe el entregable o el medio de entrega, básate en eso. Si NO lo indica, infiérela del "
    f"tipo de actividad y de lo que la descripción pide hacer. Referencias por tipo: {_delivery_hints()} "
    "'resources': los materiales de estudio de la sección Recursos, uno por elemento, con su nombre completo "
    "y su enlace entre paréntesis cuando lo tenga; no incluyas los títulos de grupo (como 'Bibliografía de "
    "consulta obligatoria:') y devuelve lista vacía si dice 'No aplica'. "
    "'has_rubric': true sólo si el texto dice 'Rúbrica: Si'."
)

RUBRIC_RULES = (
    "Extrae la rúbrica de evaluación. 'activity_title' es el título de la actividad sin la frase "
    "'Rúbrica de evaluación:'. Cada fila de criterio da: 'name' (el nombre del criterio sin el porcentaje), "
    "'points' (el porcentaje del criterio como número, 35 para '35 %'; si no tiene, null) y los cuatro "
    "niveles (excelente, en_desarrollo, basico, insuficiente) con su texto literal. Incluye todos los criterios."
)

TEACHER_RULES = (
    "Del documento recibido extrae el perfil profesional (biografía, formación y experiencia) del docente "
    "indicado, de forma literal. Si el documento no contiene ese perfil, devuelve 'bio' vacío."
)


def _scrub(value: Any) -> Any:
    """Quita valores de relleno ('string') y convierte los '<br>' copiados en saltos de línea."""
    if isinstance(value, str):
        text = re.sub(r"[ \t]*<br\s*/?>[ \t]*", "\n", value).strip()
        return "" if text.lower() in _PLACEHOLDER_STRINGS else text
    if isinstance(value, list):
        return [item for item in (_scrub(item) for item in value) if item != ""]
    if isinstance(value, dict):
        return {key: _scrub(item) for key, item in value.items()}
    return value


class Extractor:
    """Hace las preguntas al LLM sobre un documento ya dividido en secciones."""

    def __init__(self, llm, sections: DocumentSections):
        self._llm = llm
        self._sections = sections

    def _ask(self, schema: Type[Schema], rules: str, text: str) -> Schema:
        messages = [
            SystemMessage(content=f"{BASE_RULES}\n\n{rules}"),
            HumanMessage(content=text),
        ]
        last_error: Optional[Exception] = None
        for _ in range(MAX_ATTEMPTS):
            try:
                result = self._llm.with_structured_output(schema).invoke(messages)
                data = result.model_dump() if hasattr(result, "model_dump") else result
                return schema.model_validate(_scrub(data))
            except Exception as error:  # respuesta truncada, JSON inválido, error de red...
                last_error = error
        raise RuntimeError(f"No se pudo extraer {schema.__name__}: {last_error}")

    def overview(self) -> CourseOverview:
        return self._ask(CourseOverview, OVERVIEW_RULES, self._sections.text("info", "alignment"))

    def modules(self) -> List[ModuleInfo]:
        text = self._sections.text("alignment", "sequence")
        return self._ask(ModulesExtraction, MODULES_RULES, text).modules

    def schedule(self) -> List[ScheduleRow]:
        return self._ask(ScheduleExtraction, SCHEDULE_RULES, self._sections.text("sequence")).activities

    def activity(self, row: ScheduleRow) -> ActivityDetail:
        """Detalle de una actividad a partir de su tabla en la sección de actividades."""
        header = f"Actividad {row.number}. {row.activity_type}: {row.name}"
        block = find_activity_block(self._sections.tables("activities"), row.number, row.name)
        if block is None:
            text = (
                f"Extrae únicamente la actividad «{header}» del siguiente documento:\n\n"
                f"{self._sections.text('activities')}"
            )
            return self._ask(ActivityDetail, ACTIVITY_RULES, text)

        text = f"Tipo de actividad: {row.activity_type}\n\n{block_to_plain(block)}"
        description = labeled_cell(block, "Descripción")
        if description:
            # La plantilla ya delimita la descripción: se toma literal del documento.
            facts = self._ask(ActivityFacts, ACTIVITY_RULES, text)
            return ActivityDetail(description=description, **facts.model_dump())
        return self._ask(ActivityDetail, ACTIVITY_RULES, text)

    def rubric_blocks(self) -> List[Block]:
        return self._sections.tables("rubrics")

    def rubric(self, block: Block) -> RubricExtraction:
        return self._ask(RubricExtraction, RUBRIC_RULES, blocks_to_text([block]))

    def rubrics_from_full_document(self) -> List[RubricExtraction]:
        """Respaldo cuando no hay una sección de rúbricas identificable."""
        rules = RUBRIC_RULES + " El documento puede contener varias rúbricas o ninguna: devuélvelas todas."
        return self._ask(RubricsExtraction, rules, self._sections.full_text()).rubrics

    def teacher_bio(self, teacher_name: str, teacher_document_text: str) -> str:
        text = f"Docente: {teacher_name or 'el profesor autor del curso'}\n\nDocumento:\n{teacher_document_text}"
        bio = self._ask(TeacherProfile, TEACHER_RULES, text).bio
        # Un nombre o una frase suelta no es un perfil: mejor dejarlo vacío.
        if len(bio.split()) < MIN_BIO_WORDS or normalize(bio) == normalize(teacher_name):
            return ""
        return bio
